from flask import Flask
from flask_bcrypt import Bcrypt
from models import db
from routes import user_routes  # Import the blueprint from routes.py
from config import Config  # Import the Config class

app = Flask(__name__)
bcrypt = Bcrypt(app)

# Configure the app (load from Config class)
app.config.from_object(Config)

# Initialize the database with the app
db.init_app(app)

# Register Blueprints after initializing the app
app.register_blueprint(user_routes)

# Initialize tables when the app starts
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)  # Change to port 5001

