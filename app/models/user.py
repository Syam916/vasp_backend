from app.extensions import db
from datetime import datetime
import bcrypt

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True , autoincrement=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.LargeBinary)
    mobile_number = db.Column(db.String(15))
    location = db.Column(db.String(128))
    pincode = db.Column(db.String(10))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        salt = bcrypt.gensalt()
        self.password = bcrypt.hashpw(password.encode('utf-8'), salt)

    def check_password(self, password):
        if isinstance(self.password, str):
            # Convert string to bytes if needed (for legacy data)
            password_check = self.password.encode('utf-8')
        else:
            password_check = self.password
        return bcrypt.checkpw(password.encode('utf-8'), password_check)

    def to_dict(self):
        return {
            # 'id': self.id,
            'username': self.username,
            'email': self.email,
            'mobile_number': self.mobile_number,
            'location': self.location,
            'pincode': self.pincode
        } 