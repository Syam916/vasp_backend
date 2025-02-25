from app.extensions import db

class ServiceCenter(db.Model):
    __tablename__ = 'service_centers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    address = db.Column(db.Text, nullable=False)
    brand = db.Column(db.String(100), nullable=False)
    pincode = db.Column(db.String(10), nullable=False)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'address': self.address,
            'brand': self.brand,
            'pincode': self.pincode,
            'latitude': self.latitude,
            'longitude': self.longitude
        } 