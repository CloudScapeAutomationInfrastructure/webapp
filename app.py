from flask import Flask
from flask_bcrypt import Bcrypt
from models import db
from routes import user_routes
from config import Config
import logging
from watchtower import CloudWatchLogHandler
import boto3
from sendgrid import SendGridAPIClient
import os

# Initialize Flask app
app = Flask(__name__)

# Set up configuration
app.config.from_object(Config)

# Initialize Bcrypt for password hashing
bcrypt = Bcrypt(app)

# Initialize database
db.init_app(app)

# Register routes
app.register_blueprint(user_routes)

# Configure AWS Boto3 session
aws_region = app.config["AWS_REGION"]
boto3.setup_default_session(region_name=aws_region)

# Set up logging with CloudWatch
logger = logging.getLogger("flask-app")
logger.setLevel(logging.INFO)

try:
    cloudwatch_handler = CloudWatchLogHandler(
        log_group="webappLogGroup",
        stream_name="FlaskAppLogs",
        boto3_session=boto3.Session(region_name=aws_region)
    )
    cloudwatch_handler.setLevel(logging.INFO)
    logger.addHandler(cloudwatch_handler)
    logger.info("CloudWatch logging configured successfully.")
except Exception as e:
    logger.error(f"Failed to configure CloudWatch logging: {e}")

# Log Flask application start
logger.info("Flask application has started.")

# Initialize SendGrid client
sendgrid_api_key = os.getenv("SENDGRID_API_KEY")
sendgrid_client = None
if not sendgrid_api_key:
    logger.error("SENDGRID_API_KEY is not set. Emails will not be sent.")
else:
    try:
        sendgrid_client = SendGridAPIClient(sendgrid_api_key)
        logger.info("SendGrid client initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize SendGrid client: {e}")

# Database table creation
with app.app_context():
    try:
        db.create_all()
        logger.info("Database tables created successfully.")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")

# Run the application
if __name__ == '__main__':
    debug_mode = app.config.get("DEBUG", False)
    try:
        app.run(host='0.0.0.0', port=5000, debug=debug_mode)
    except Exception as e:
        logger.error(f"Failed to start Flask application: {e}")
