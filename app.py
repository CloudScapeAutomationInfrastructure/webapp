from flask import Flask
from flask_bcrypt import Bcrypt
from models import db
from routes import user_routes  
from config import Config  

app = Flask(__name__)
bcrypt = Bcrypt(app)


app.config.from_object(Config)


db.init_app(app)


app.register_blueprint(user_routes)


with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)  
#eof
