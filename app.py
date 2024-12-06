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


boto3.setup_default_session(region_name=Config.AWS_REGION)


app = Flask(__name__)
bcrypt = Bcrypt(app)


app.config.from_object(Config)


db.init_app(app)


app.register_blueprint(user_routes)


logger = logging.getLogger("flask-app")
logger.setLevel(logging.INFO)


cloudwatch_handler = CloudWatchLogHandler(log_group="webappLogGroup", stream_name="FlaskAppLogs")
cloudwatch_handler.setLevel(logging.INFO)


logger.addHandler(cloudwatch_handler)


logger.info("Flask application has started.")


sendgrid_client = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))

with app.app_context():
    
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
