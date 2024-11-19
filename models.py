from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime

db = SQLAlchemy()
bcrypt = Bcrypt()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    account_created = db.Column(db.DateTime, default=datetime.utcnow)
    account_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    

    def set_password(self, password):
        self.password = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password, password)
    
class EmailTracking(db.Model):
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    email_type = db.Column(db.String(255), nullable=False)
    email_subject = db.Column(db.String(255))
    verification_link = db.Column(db.String(255), unique=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    status = db.Column(
        db.Enum('pending', 'verified', 'expired', name='status_enum'),
        default='pending',
        nullable=False
    )
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Define relationship with User table
    user = db.relationship('User', backref=db.backref('email_tracking', cascade='all, delete-orphan'))


