from flask import Blueprint, request, jsonify
import statsd
from config import Config
from models import User, db
from flask_httpauth import HTTPBasicAuth
from flask_bcrypt import Bcrypt
from sqlalchemy.exc import OperationalError
import boto3
import os
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from datetime import datetime

statsd_client = statsd.StatsClient('localhost', 8125)

sg = SendGridAPIClient(api_key=Config.SENDGRID_API_KEY)

s3_client = boto3.client('s3', region_name=Config.AWS_REGION)
cloudwatch_client = boto3.client('cloudwatch', region_name=Config.AWS_REGION)
BUCKET_NAME = os.getenv('S3_BUCKET_NAME')

logger = logging.getLogger("flask-app")

user_routes = Blueprint('user_routes', __name__, url_prefix='/v1')

bcrypt = Bcrypt()
auth = HTTPBasicAuth()

@auth.verify_password
def verify_password(email, password):
    user = User.query.filter_by(email=email).first()
    if user and bcrypt.check_password_hash(user.password, password):
        return user
    return None

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

@user_routes.route('/user', methods=['POST'])
def create_user():
    try:
        data = request.form
        required_fields = ['email', 'password', 'first_name', 'last_name']
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

        email = data.get('email')
        if User.query.filter_by(email=email).first():
            send_email("User Already Exists", "The email you tried to register with is already in use.", email)
            return jsonify({"error": "User already exists"}), 400

        hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
        new_user = User(email=email, password=hashed_password, first_name=data['first_name'], last_name=data['last_name'])
        db.session.add(new_user)
        db.session.commit()

        # Handle image upload
        image_file = request.files.get('file')
        if image_file:
            file_key = f"{new_user.id}/{image_file.filename}"
            s3_client.upload_fileobj(image_file, BUCKET_NAME, file_key)
            logger.info(f"Image for user {new_user.email} uploaded to S3 with key {file_key}")

        send_email("Welcome to WebApp!", "Thank you for registering!", email)
        logger.info(f"User {email} created successfully.")
        put_custom_metric('UserCreation', 1)

        return jsonify({
            "email": new_user.email,
            "first_name": new_user.first_name,
            "last_name": new_user.last_name,
            "account_created": new_user.account_created,
            "account_updated": new_user.account_updated
        }), 201

    except OperationalError as e:
        logger.error(f"Database Error: {str(e)}")
        return jsonify({"error": "Service Unavailable"}), 503
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return jsonify({"error": "An internal server error occurred"}), 500

@user_routes.route('/user', methods=['GET'])
@auth.login_required
def get_user():
    try:
        user = auth.current_user()
        return jsonify({
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "account_created": user.account_created,
            "account_updated": user.account_updated
        }), 200
    except Exception as e:
        logger.error(f"Failed to retrieve user: {str(e)}")
        return jsonify({"error": "Failed to retrieve user"}), 500

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
