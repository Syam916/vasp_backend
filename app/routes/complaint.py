from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models.complaint import Complaint
from app.models.product import Product
from sqlalchemy.exc import SQLAlchemyError
from app.models.service_center import ServiceCenter
from app.utils.service_center_crawler import ServiceCenterCrawler
from app.models.user import User

complaint = Blueprint('complaint', __name__)

@complaint.route('/categories', methods=['GET'])
def get_categories():
    try:
        # Get username from query parameter
        username = request.args.get('user')
        if not username:
            return jsonify({'error': 'Username is required'}), 400
            
        # Get unique categories from products for this user
        categories = db.session.query(Product.category)\
                    .filter_by(user_name=username)\
                    .distinct()\
                    .all()
        
        category_list = [cat[0] for cat in categories if cat[0]]
        print("Categories found for user:", username, ":", category_list)
        
        if not category_list:
            return jsonify({
                'categories': [],
                'message': 'No categories found'
            }), 200
            
        return jsonify({
            'categories': category_list
        }), 200
        
    except SQLAlchemyError as e:
        print("Database error:", str(e))
        return jsonify({'error': 'Database error occurred'}), 500
    except Exception as e:
        print("Error fetching categories:", str(e))
        return jsonify({'error': 'Failed to fetch categories'}), 500

@complaint.route('/products/<category>', methods=['GET'])
def get_products_by_category(category):
    try:
        # Get username from query parameter
        username = request.args.get('user')
        if not username:
            return jsonify({'error': 'Username is required'}), 400
            
        # Get products for the given category and user
        products = Product.query\
                  .filter_by(category=category, user_name=username)\
                  .all()
        
        product_list = [{'id': p.id, 'name': p.product_brand} for p in products]
        print(f"Products found for user {username} in category {category}:", product_list)
        
        if not product_list:
            return jsonify({
                'products': [],
                'message': f'No products found for category: {category}'
            }), 200
            
        return jsonify({
            'products': product_list
        }), 200
        
    except SQLAlchemyError as e:
        print("Database error:", str(e))
        return jsonify({'error': 'Database error occurred'}), 500
    except Exception as e:
        print("Error fetching products:", str(e))
        return jsonify({'error': f'Failed to fetch products for category: {category}'}), 500

@complaint.route('/submit', methods=['POST'])
def submit_complaint():
    try:
        data = request.json
        username = data.get('user_name')
        
        # Create new complaint
        new_complaint = Complaint(
            user_name=username,
            category=data.get('category'),
            product=data.get('product'),
            complaint=data.get('complaint'),
            status='Pending'
        )
        
        db.session.add(new_complaint)
        db.session.commit()

        return jsonify({
            'message': 'Complaint registered successfully',
            'complaint': new_complaint.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print("Error submitting complaint:", str(e))
        return jsonify({'error': str(e)}), 500

@complaint.route('/user/<username>', methods=['GET'])
def get_user_complaints(username):
    try:
        complaints = Complaint.query.filter_by(user_name=username)\
                            .order_by(Complaint.complaint_date.desc())\
                            .all()
        
        return jsonify({
            'complaints': [complaint.to_dict() for complaint in complaints]
        }), 200
        
    except SQLAlchemyError as e:
        print("Database error:", str(e))
        return jsonify({'error': 'Database error occurred'}), 500
    except Exception as e:
        print("Error fetching user complaints:", str(e))
        return jsonify({'error': 'Failed to fetch complaints'}), 500

@complaint.route('/service-centers/<brand>/<pincode>', methods=['GET'])
def get_service_centers(brand, pincode):
    try:
        # Only check database
        centers = ServiceCenter.query.filter_by(
            brand=brand,
            pincode=pincode
        ).all()
        
        return jsonify({
            'service_centers': [center.to_dict() for center in centers],
            'source': 'database'
        }), 200
        
    except Exception as e:
        print("Error fetching service centers:", str(e))
        return jsonify({'error': str(e)}), 500

@complaint.route('/crawl-service-centers/<brand>/<pincode>', methods=['GET'])
def crawl_service_centers(brand, pincode):
    try:
        crawler = ServiceCenterCrawler()
        new_centers = crawler.find_service_centers(brand, pincode)
        
        if new_centers:
            # Get newly added centers from DB
            centers = ServiceCenter.query.filter_by(
                brand=brand,
                pincode=pincode
            ).all()
            
            return jsonify({
                'service_centers': [center.to_dict() for center in centers],
                'source': 'crawler'
            }), 200
        
        return jsonify({
            'service_centers': [],
            'message': 'No service centers found'
        }), 200
        
    except Exception as e:
        print("Error crawling service centers:", str(e))
        return jsonify({'error': str(e)}), 500 