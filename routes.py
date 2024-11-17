import boto3
import json
from flask import Blueprint, request, jsonify
import statsd
from config import Config
from models import User, db
from flask_httpauth import HTTPBasicAuth
from flask_bcrypt import Bcrypt
from sqlalchemy.exc import OperationalError
import os
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from datetime import datetime

# Initialize clients and configurations
statsd_client = statsd.StatsClient('localhost', 8125)
sg = SendGridAPIClient(api_key=Config.SENDGRID_API_KEY)
s3_client = boto3.client('s3', region_name=Config.AWS_REGION)
sns_client = boto3.client('sns', region_name=Config.AWS_REGION)
cloudwatch_client = boto3.client('cloudwatch', region_name=Config.AWS_REGION)
BUCKET_NAME = os.getenv('S3_BUCKET_NAME')
logger = logging.getLogger("flask-app")

# Blueprint for user routes
user_routes = Blueprint('user_routes', __name__, url_prefix='/v1')

# Bcrypt and HTTPAuth for authentication
bcrypt = Bcrypt()
auth = HTTPBasicAuth()

@auth.verify_password
def verify_password(email, password):
    user = User.query.filter_by(email=email).first()
    if user and bcrypt.check_password_hash(user.password, password):
        return user
    return None

# Helper methods
def put_custom_metric(metric_name, value):
    cloudwatch_client.put_metric_data(
        Namespace='WebAppMetrics',
        MetricData=[
            {
                'MetricName': metric_name,
                'Timestamp': datetime.utcnow(),
                'Value': value,
                'Unit': 'Count'
            },
        ]
    )
    statsd_client.incr(metric_name, value)

def send_email(subject, content, to_email):
    from_email = Email(Config.FROM_EMAIL)
    to_email = To(to_email)
    reply_to_email = Email(Config.REPLY_TO_EMAIL)
    content = Content("text/plain", content)
    mail = Mail(from_email, to_email, subject, content)
    mail.reply_to = reply_to_email
    try:
        response = sg.client.mail.send.post(request_body=mail.get())
        logger.info(f"Email sent to {to_email} with status code {response.status_code}")
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")

# Create User Endpoint
@user_routes.route('/user', methods=['POST'])
def create_user():
    try:
        # Parse incoming data
        data = request.json
        required_fields = ['email', 'password', 'first_name', 'last_name']
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

        email = data.get('email')
        password = data.get('password')
        first_name = data.get('first_name')
        last_name = data.get('last_name')

        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            logger.info(f"Attempt to create a user with an existing email: {email}")
            return jsonify({"error": "User already exists"}), 400

        # Hash password
        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

        # Create new user
        new_user = User(
            email=email,
            password=hashed_password,
            first_name=first_name,
            last_name=last_name,
            verified=False  # Default verified status
        )
        db.session.add(new_user)
        db.session.commit()

        # Publish to SNS topic
        sns_message = {
            "email": email,
            "user_id": new_user.id,
            "first_name": first_name,
            "last_name": last_name
        }
        sns_client.publish(
            TopicArn=Config.SNS_TOPIC_ARN,  # Replace with your actual SNS Topic ARN
            Message=json.dumps(sns_message),
            Subject="New User Registration Notification"
        )

        # Log and update metrics
        logger.info(f"User {email} created successfully.")
        put_custom_metric('UserCreation', 1)

        return jsonify({
            "message": "User created successfully. Verification email sent.",
            "user_id": new_user.id
        }), 201

    except Exception as e:
        logger.error(f"Error during user creation: {str(e)}")
        return jsonify({"error": "An internal server error occurred"}), 500

@user_routes.route('/user/self', methods=['GET'])
@auth.login_required
def get_user():
    try:
        user = auth.current_user()
        
        user_data = {
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "account_created": user.account_created,
            "account_updated": user.account_updated
        }
        
        logger.info(f"User {user.email} retrieved their profile data.")
        put_custom_metric('UserProfileFetch', 1)
        
        return jsonify(user_data), 200

    except Exception as e:
        logger.error(f"Failed to retrieve user profile: {str(e)}")
        return jsonify({"error": "Failed to retrieve user profile"}), 500

@user_routes.route('/user/self/pic', methods=['POST'])
@auth.login_required
def upload_image():
    try:
        user = auth.current_user()
        image_file = request.files.get('file')

        if not image_file:
            send_email("Image Upload Failed", "No image file was provided for upload.", user.email)
            return jsonify({"error": "No image file provided"}), 400

        file_key = f"{user.id}/{image_file.filename}"
        s3_client.upload_fileobj(image_file, BUCKET_NAME, file_key)
        logger.info(f"Image for user {user.email} uploaded to S3 with key {file_key}")

        put_custom_metric('ImageUpload', 1)
        send_email("Image Upload Successful", f"Your image has been successfully uploaded with key {file_key}.", user.email)

        return jsonify({"message": "Image uploaded successfully", "file_key": file_key}), 201

    except Exception as e:
        logger.error(f"Failed to upload image: {str(e)}")
        send_email("Image Upload Failed", f"Your image upload failed due to an error: {str(e)}", user.email)
        return jsonify({"error": "Failed to upload image"}), 500

@user_routes.route('/user/self/pic', methods=['DELETE'])
@auth.login_required
def delete_image():
    try:
        user = auth.current_user()
        image_key = request.args.get('file_key')

        if not image_key:
            return jsonify({"error": "file_key is required to delete an image"}), 400

        s3_client.delete_object(Bucket=BUCKET_NAME, Key=image_key)
        logger.info(f"Image with key {image_key} for user {user.email} deleted from S3")

        put_custom_metric('ImageDeletion', 1)
        send_email("Image Deletion Successful", f"Your image with key {image_key} has been successfully deleted.", user.email)

        return jsonify({"message": "Image deleted successfully"}), 200

    except Exception as e:
        logger.error(f"Failed to delete image: {str(e)}")
        send_email("Image Deletion Failed", f"Your image deletion failed due to an error: {str(e)}", user.email)
        return jsonify({"error": "Failed to delete image"}), 500

@user_routes.route('/healthz', methods=['GET'])
def health_check():
    try:
        put_custom_metric('HealthCheck', 1)
        return jsonify({"status": "healthy"}), 200
    except OperationalError as e:
        logger.error(f"Database Error: {str(e)}")
        return jsonify({"error": "Service Unavailable"}), 503
