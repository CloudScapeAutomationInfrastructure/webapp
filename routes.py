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
from datetime import datetime, timedelta
import hashlib

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
        if user.verified:
            return user
        else:
            logger.info(f"Unverified user {email} attempted to log in.")
            return None
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

def publish_sns_notification(message, subject):
    if os.getenv("TEST_ENV") == "true":
        logger.info("Test environment detected. Skipping SNS publish.")
    else:
        try:
            sns_client.publish(
                TopicArn=Config.SNS_TOPIC_ARN,
                Message=json.dumps(message),
                Subject=subject
            )
            logger.info(f"SNS notification sent with subject: {subject}")
        except Exception as sns_error:
            logger.error(f"Failed to send SNS notification: {sns_error}")
            raise

def generate_verification_link(user_id):
    expiration_time = datetime.utcnow() + timedelta(minutes=2)
    token_data = f"{user_id}-{expiration_time.timestamp()}"
    token = hashlib.sha256(token_data.encode()).hexdigest()
    domain = request.host_url.strip("/") if request else "http://localhost:5000"
    return f"{domain}/v1/verify?token={token}"

def validate_verification_token(token):

    try:

        decoded_data = token.split("-")

        user_id = int(decoded_data[0])

        expiration_timestamp = float(decoded_data[1])

        if datetime.utcnow().timestamp() > expiration_timestamp:

            return None

        return user_id

    except Exception as e:

        logger.error(f"Error validating token: {e}")

        return None

def is_user_verified(user):

    """Check if the user is verified."""

    return user.verified
    
    

# Create User Endpoint
@user_routes.route('/user', methods=['POST'])
def create_user():
    try:
        data = request.json
        required_fields = ['email', 'password', 'first_name', 'last_name']
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

        email = data.get('email')
        password = data.get('password')
        first_name = data.get('first_name')
        last_name = data.get('last_name')

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({"error": "User already exists"}), 400

        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")
        new_user = User(email=email, password=hashed_password, first_name=first_name, last_name=last_name, verified=False)
        db.session.add(new_user)
        db.session.commit()

        # Generate verification link
        verification_link = generate_verification_link(new_user.id)

        email_subject = "Verify Your Email Address"
        email_body = f"""
        Hello {first_name},

        Please verify your email by clicking the link below. This link will expire in 2 minutes:
        {verification_link}

        Thank you!
        """
        send_email(email_subject, email_body, email)

        sns_message = {
            "action": "user_creation",
            "email": email,
            "user_id": new_user.id,
            "first_name": first_name,
            "last_name": last_name,
        }

        # Conditional SNS Publish
        if os.getenv("TEST_ENV") == "true":
            logger.info("Test environment detected. Skipping SNS publish.")
        else:
            try:
                sns_client.publish(
                    TopicArn=Config.SNS_TOPIC_ARN,
                    Message=json.dumps(sns_message),
                    Subject="New User Registration Notification"
                )
                logger.info(f"SNS notification sent for user {email}.")
            except Exception as sns_error:
                logger.error(f"SNS publish failed for user {email}: {sns_error}")
                return jsonify({"error": "Failed to send notification. User creation aborted."}), 500

        # Log and update metrics
        put_custom_metric('UserCreation', 1)

        return jsonify({
            "message": "User created successfully. Verification email sent.",
            "user_id": new_user.id
        }), 201

    except Exception as e:
        logger.error(f"Unexpected error during user creation: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

# Verify User Endpoint
@user_routes.route('/verify', methods=['GET'])
def verify_user():
    try:
        token = request.args.get('token')
        if not token:
            return jsonify({"error": "Token is required"}), 400

        user_id = validate_verification_token(token)
        if not user_id:
            return jsonify({"error": "Invalid or expired token"}), 400

        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        if user.verified:
            return jsonify({"message": "User is already verified"}), 200

        user.verified = True
        db.session.commit()

        sns_message = {
            "action": "user_verified",
            "email": user.email,
            "user_id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
        }
        publish_sns_notification(sns_message, "User Verified")

        return jsonify({"message": "User verified successfully"}), 200

    except Exception as e:
        logger.error(f"Error verifying user: {e}")
        return jsonify({"error": "Internal server error"}), 500

# Get User Details Endpoint
@user_routes.route('/user/self', methods=['GET'])
@auth.login_required
def get_user():
    try:
        user = auth.current_user()

        user_data = {
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "account_created": user.account_created.isoformat(),
            "account_updated": user.account_updated.isoformat(),
        }

        put_custom_metric('UserProfileFetch', 1)
        return jsonify(user_data), 200

    except Exception as e:
        logger.error(f"Failed to retrieve user profile: {e}")
        return jsonify({"error": "Internal server error"}), 500

@user_routes.route('/user/self/pic', methods=['POST'])
@auth.login_required
def upload_image():
    """
    Upload an image for the user.
    Block access for unverified users.
    """
    try:
        user = auth.current_user()
        
        # Check if user is verified
        if not is_user_verified(user):
            return jsonify({"error": "Access denied. Verify your email to access this resource."}), 403

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
    """
    Delete an uploaded image.
    Block access for unverified users.
    """
    try:
        user = auth.current_user()

        # Check if user is verified
        if not is_user_verified(user):
            return jsonify({"error": "Access denied. Verify your email to access this resource."}), 403

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
