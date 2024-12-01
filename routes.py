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

# Load S3 bucket and KMS key from environment variables
BUCKET_NAME = os.getenv('S3_BUCKET_NAME', 'your-default-bucket')
KMS_KEY_ID = os.getenv('KMS_KEY_ID', 'your-default-kms-key-id')

# Initialize logging
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

# Helper Functions
def send_email(subject, content, to_email):
    """Send email using SendGrid."""
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
    """Generate a verification link for a user."""
    expiration_time = datetime.utcnow() + timedelta(minutes=2)
    token_data = f"{user_id}-{expiration_time.timestamp()}"
    token = hashlib.sha256(token_data.encode()).hexdigest()
    domain = request.host_url.strip("/") if request else "http://localhost:5000"
    return f"{domain}/v1/verify?token={token}"

def validate_verification_token(token):
    """Validate the verification token."""
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

# User Management Endpoints
@user_routes.route('/user', methods=['POST'])
def create_user():
    """Create a new user."""
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        first_name = data.get('first_name')
        last_name = data.get('last_name')

        if not email or not password or not first_name or not last_name:
            return jsonify({"error": "Missing required fields"}), 400

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
        email_body = f"Hello {first_name},\n\nPlease verify your email by clicking the link below:\n{verification_link}"

        # Attempt to send email and log errors if it fails
        try:
            send_email(email_subject, email_body, email)
        except Exception as e:
            logger.error(f"Failed to send email to {email}: {e}")

        # Attempt to publish SNS notification and log errors if it fails
        sns_message = {"action": "user_creation", "email": email, "user_id": new_user.id}
        try:
            publish_sns_notification(sns_message, "New User Registered")
        except Exception as e:
            logger.error(f"Failed to publish SNS notification for user {email}: {e}")

        return jsonify({
            "message": "User created successfully. Verification email sent.",
            "user_id": new_user.id
        }), 201

    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return jsonify({"error": "Internal server error"}), 500
    
@user_routes.route('/verify', methods=['GET'])
def verify_user():
    """Verify a user's email address."""
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

        sns_message = {"action": "user_verified", "email": user.email, "user_id": user.id}
        publish_sns_notification(sns_message, "User Verified")

        return jsonify({"message": "User verified successfully"}), 200
    except Exception as e:
        logger.error(f"Error verifying user: {e}")
        return jsonify({"error": "Internal server error"}), 500

# S3 Image Management Endpoints
@user_routes.route('/user/self/pic', methods=['POST'])
@auth.login_required
def upload_image():
    """Upload an image to S3."""
    try:
        user = auth.current_user()

        if not user.verified:
            return jsonify({"error": "Access denied. Verify your email to access this resource."}), 403

        image_file = request.files.get('file')
        if not image_file:
            return jsonify({"error": "No file provided"}), 400

        # File size validation
        image_file.seek(0, 2)  # Move cursor to the end of file
        file_size = image_file.tell()
        image_file.seek(0)  # Reset cursor to the beginning of file
        if file_size > 5 * 1024 * 1024:  # Limit file size to 5MB
            return jsonify({"error": "File size exceeds 5MB limit"}), 400

        file_key = f"{user.id}/{image_file.filename}"
        s3_client.upload_fileobj(
            image_file,
            BUCKET_NAME,
            file_key,
            ExtraArgs={"ServerSideEncryption": "aws:kms", "SSEKMSKeyId": KMS_KEY_ID}
        )

        logger.info(f"Image for user {user.email} uploaded to S3 with key {file_key}")
        return jsonify({"message": "Image uploaded successfully", "file_key": file_key}), 201
    except Exception as e:
        logger.error(f"Error uploading image: {e}")
        return jsonify({"error": "Failed to upload image"}), 500

@user_routes.route('/user/self/pic', methods=['DELETE'])
@auth.login_required
def delete_image():
    """Delete an image from S3."""
    try:
        user = auth.current_user()

        if not user.verified:
            return jsonify({"error": "Access denied. Verify your email to access this resource."}), 403

        image_key = request.args.get('file_key')
        if not image_key:
            return jsonify({"error": "file_key is required"}), 400

        s3_client.delete_object(Bucket=BUCKET_NAME, Key=image_key)
        logger.info(f"Image with key {image_key} for user {user.email} deleted from S3")

        return jsonify({"message": "Image deleted successfully"}), 200
    except Exception as e:
        logger.error(f"Error deleting image: {e}")
        return jsonify({"error": "Failed to delete image"}), 500

# Health Check Endpoint
@user_routes.route('/healthz', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        # Check database connection
        db.engine.execute("SELECT 1")
        return jsonify({"status": "healthy"}), 200
    except OperationalError as e:
        logger.error(f"Database Error: {str(e)}")
        return jsonify({"error": "Service Unavailable"}), 503
