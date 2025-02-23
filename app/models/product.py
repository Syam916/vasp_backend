from app.extensions import db
from datetime import datetime

class Product(db.Model):
    __tablename__ = 'product_details'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_name = db.Column(db.String(255))
    # user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    platform_name = db.Column(db.String(255))
    category = db.Column(db.String(255))
    provider = db.Column(db.String(255))
    product_brand = db.Column(db.String(255))
    product_description = db.Column(db.String(255))
    order_date = db.Column(db.String(255))
    invoice_date = db.Column(db.String(255))
    expiry_date = db.Column(db.String(255))
    gst_number = db.Column(db.String(50))
    invoice_number = db.Column(db.String(50))
    quantity = db.Column(db.String(50))
    total_amount = db.Column(db.String(255))
    discount_percentage = db.Column(db.String(50))
    tax_amount = db.Column(db.String(255))
    igst_percentage = db.Column(db.String(50))
    seller_address = db.Column(db.Text)
    billing_address = db.Column(db.Text)
    shipping_address = db.Column(db.Text)
    # customer_name = db.Column(db.String(255))
    pan_number = db.Column(db.String(250))
    payement_mode = db.Column(db.String(50))
    file_path = db.Column(db.String(255))
    # created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    # user = db.relationship('User', backref='products')
    # images = db.relationship('ProductImage', backref='product', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'file_path': self.file_path,
            'order_date': self.order_date,
            'expiry_date': self.expiry_date,
            'product_name': self.product_name,
            'product_brand': self.product_brand,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class ProductImage(db.Model):
    __tablename__ = 'product_images'

    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(255))
    product_image = db.Column(db.String(555))
    category = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'product_name': self.product_name,
            'product_image': self.product_image,
            'category': self.category
        } 