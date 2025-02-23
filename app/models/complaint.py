from app.extensions import db
from datetime import datetime

class Complaint(db.Model):
    __tablename__ = 'complaint_details'
    
    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(255))
    category = db.Column(db.String(255))
    product = db.Column(db.String(255))
    complaint = db.Column(db.Text)
    complaint_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='Pending')

    def to_dict(self):
        return {
            'id': self.id,
            'user_name': self.user_name,
            'category': self.category,
            'product': self.product,
            'complaint': self.complaint,
            'complaint_date': self.complaint_date,
            'status': self.status
        } 