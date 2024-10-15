from flask import Blueprint, request, jsonify
from models import User, db
from flask_httpauth import HTTPBasicAuth
from flask_bcrypt import Bcrypt
from sqlalchemy.exc import OperationalError  


user_routes = Blueprint('user_routes', __name__, url_prefix='/v1')


bcrypt = Bcrypt()


auth = HTTPBasicAuth()

@auth.verify_password
def verify_password(email, password):
    try:
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            return user  
        return None  
    except OperationalError:
        return None  


def is_strong_password(password):
    return len(password) >= 8  


def validate_user_data(data, fields_to_validate):
    for field in fields_to_validate:
        
        if field in data:
            if field == 'email' and not isinstance(data.get('email'), str):
                return False, "Invalid data type for 'email', expected string"
            if field == 'password' and not isinstance(data.get('password'), str):
                return False, "Invalid data type for 'password', expected string"
            if field == 'first_name' and not isinstance(data.get('first_name'), str):
                return False, "Invalid data type for 'first_name', expected string"
            if field == 'last_name' and not isinstance(data.get('last_name'), str):
                return False, "Invalid data type for 'last_name', expected string"
    return True, None


#@user_routes.route('/user', methods=['POST'])
def create_user():
    try:
        data = request.get_json()

        
        required_fields = ['email', 'password', 'first_name', 'last_name']
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

        
        valid, error_message = validate_user_data(data, required_fields)
        if not valid:
            return jsonify({"error": error_message}), 400

        
        if not is_strong_password(data.get('password')):
            return jsonify({"error": "Password is too weak, must be at least 8 characters long"}), 400

        email = data.get('email')
        password = data.get('password')
        first_name = data.get('first_name')
        last_name = data.get('last_name')

        
        if User.query.filter_by(email=email).first():
            return jsonify({"error": "User already exists"}), 400

        
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(email=email, password=hashed_password, first_name=first_name, last_name=last_name)

        db.session.add(new_user)
        db.session.commit()

        return jsonify({
            "email": new_user.email,
            "first_name": new_user.first_name,
            "last_name": new_user.last_name,
            "account_created": new_user.account_created,
            "account_updated": new_user.account_updated
        }), 201

    except OperationalError as e:
        print(f"Database Error: {str(e)}")
        return jsonify({"error": "Service Unavailable"}), 503
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": "An internal server error occurred"}), 500


#@user_routes.route('/user/self', methods=['GET'])
@auth.login_required
def get_user_info():
    try:
        user = auth.current_user()
        if user is None:
            return jsonify({"error": "User not found"}), 404

        return jsonify({
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "account_created": user.account_created,
            "account_updated": user.account_updated
        }), 200
    except OperationalError as e:
        print(f"Database Error: {str(e)}")
        return jsonify({"error": "Service Unavailable"}), 503
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": "An internal server error occurred"}), 500


@user_routes.route('/user/self', methods=['PUT'])
@auth.login_required
def update_user_info():
    try:
        user = auth.current_user()
        data = request.get_json()

        
        valid_fields = ['first_name', 'last_name', 'password']

        
        valid, error_message = validate_user_data(data, valid_fields)

        if not valid:
            return jsonify({"error": error_message}), 400

        
        if 'first_name' in data:
            user.first_name = data['first_name']
        if 'last_name' in data:
            user.last_name = data['last_name']
        if 'password' in data:
            
            if not is_strong_password(data['password']):
                return jsonify({"error": "Password is too weak, must be at least 8 characters long"}), 400
            user.password = bcrypt.generate_password_hash(data['password']).decode('utf-8')

       
        user.account_updated = db.func.now()
        db.session.commit()

        return jsonify({"message": "User information updated successfully", "account_updated": user.account_updated}), 200

    except OperationalError as e:
        print(f"Database Error: {str(e)}")
        return jsonify({"error": "Service Unavailable"}), 503
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": "An internal server error occurred"}), 500


@user_routes.route('/healthz', methods=['GET'])
def health_check():
    try:
        
        return jsonify({"status": "healthy"}), 200
    except OperationalError as e:
        print(f"Database Error: {str(e)}")
        return jsonify({"error": "Service Unavailable"}), 503
