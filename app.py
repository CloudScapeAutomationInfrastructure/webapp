from flask import Flask
from flask_bcrypt import Bcrypt
from models import db
from routes import user_routes  
from config import Config  
import logging
from watchtower import CloudWatchLogHandler
import boto3

# Set the default boto3 session to include the region
boto3.setup_default_session(region_name=Config.AWS_REGION)

# Initialize the Flask application
app = Flask(__name__)
bcrypt = Bcrypt(app)

# Load configuration
app.config.from_object(Config)

# Initialize database
db.init_app(app)

# Register the blueprint for user routes
app.register_blueprint(user_routes)

# Configure CloudWatch logging
logger = logging.getLogger("flask-app")
logger.setLevel(logging.INFO)

# Create a CloudWatch handler for logging
cloudwatch_handler = CloudWatchLogHandler(log_group="webappLogGroup", stream_name="FlaskAppLogs")
cloudwatch_handler.setLevel(logging.INFO)

# Add CloudWatch handler to logger
logger.addHandler(cloudwatch_handler)

# Log a startup message
logger.info("Flask application has started.")

with app.app_context():
    # Create all database tables if they don't exist
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
#end of snippet