from flask import Blueprint, request, jsonify, current_app,session, send_file, send_from_directory
from werkzeug.utils import secure_filename
from app.extensions import db
from flask_jwt_extended import jwt_required, get_jwt_identity
import os
import shutil
from datetime import timedelta, datetime
from app.utils.document_processor import *
from app.utils.amazon_crawler import *
# from app.utils.aws_utils import verify_aws_cli, upload_to_s3_cli
from app.models.user import User
from app.models.product import Product, ProductImage
import pandas as pd
from flask_cors import cross_origin

from app.config import Config

UPLOAD_FOLDER = Config.UPLOAD_FOLDER
EXTRACTED_FOLDER = Config.EXTRACTED_FOLDER
EXCEL_FILE = Config.EXCEL_FILE
EXCEL_TEMPLATE=Config.EXCEL_TEMPLATE
REFERENCE_FOLDER=Config.REFERENCE_FOLDER
Excel_file_path=f"{REFERENCE_FOLDER}/{EXCEL_FILE}"

doc = Blueprint('document', __name__)

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@doc.route('/upload', methods=['POST'])
# @jwt_required()
def upload_document():
    try:

        username = request.args.get('user')
        if not username:
            return jsonify({"error": "Username is required"}), 400
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Allowed types: PDF, PNG, JPG, JPEG'}), 400

        # Create necessary folders
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(EXTRACTED_FOLDER, exist_ok=True)
        # Save the uploaded file
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)

        # Extract text based on file type
        extracted_text = ""
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            extracted_text = extract_text_from_image(file_path)
        elif filename.lower().endswith('.pdf'):
            extracted_text = extract_text_from_pdf(file_path,UPLOAD_FOLDER)
        else:
            return jsonify({"error": "Unsupported file type"}), 400

        # Save extracted text
        output_txt_path = os.path.join(
            EXTRACTED_FOLDER, 
            f"{os.path.splitext(filename)[0]}.txt"
        )
        with open(output_txt_path, 'w', encoding='utf-8') as txt_file:
            txt_file.write(extracted_text)

        print(output_txt_path,'-----------------------------------------------------------------')
        print(f"{REFERENCE_FOLDER}/{EXCEL_TEMPLATE}/{EXCEL_FILE}",'----------------------------------------')

        # file_path = "extracted_text/tumbler_invoice.txt"  # Path to your text file
        # excel_path = "queries.xlsx"  # Path to the Excel file containing queries

        shutil.copy(f"{REFERENCE_FOLDER}/{EXCEL_TEMPLATE}/{EXCEL_FILE}", Excel_file_path)

        

        answer_queries_from_file_with_prompt(output_txt_path,Excel_file_path)

        data = read_excel_and_display()
        data_dict = {
            item['Name']: (item['Answer'] if pd.notna(item['Answer']) else '') 
            for item in data
        }

        # Process dates
        order_date_str = data_dict.get('Order Date')
        if order_date_str:
            order_date_dt = standardize_date(order_date_str)
            if order_date_dt:
                expiry_date_dt = order_date_dt + timedelta(days=365)
                data_dict['Order Date'] = order_date_dt.strftime('%Y-%m-%d')
                data_dict['Expiry Date'] = expiry_date_dt.strftime('%Y-%m-%d')

        # Upload to S3 if AWS CLI is configured
        file_url = filename
        session['file_path']=file_url[8:]
        if verify_aws_cli():
            # If user is authenticated, use their username
            # username = "default"  # Replace with actual username when authentication is enabled
            upload_to_s3_cli(file_url, username)

        print(data_dict,'--------------------------------data_dict')

        return jsonify({
            'message': 'File processed successfully',
            'extracted_data': data_dict,
            'file_url': file_url,
            'success': True
        }), 200

    except Exception as e:
        print("Upload error:", str(e))
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

@doc.route('/save-extracted-data', methods=['POST'])
def save_extracted_data():
    try:
        data = request.get_json()
        print("Received data in backend:", data)

        if not data:
            return jsonify({"error": "No data provided"}), 422

        # Get username from query parameter
        username = request.args.get('user')
        if not username:
            return jsonify({"error": "Username is required"}), 400

        # First save to Excel
        try:
            # Load existing Excel file
            df = pd.read_excel(Excel_file_path)
            
            # Ensure required columns exist
            if 'Name' not in df.columns or 'Answer' not in df.columns:
                df['Name'] = pd.Series(dtype='str')
                df['Answer'] = pd.Series(dtype='str')

            # Update Excel with new data
            for field, value in data.items():
                if field != 'file_url':  # Skip file_url when saving to Excel
                    if field in df['Name'].values:
                        # Update existing field
                        df.loc[df['Name'] == field, 'Answer'] = str(value)
                    else:
                        # Add new field
                        new_row = pd.DataFrame({'Name': [field], 'Answer': [str(value)]})
                        df = pd.concat([df, new_row], ignore_index=True)

            # Save back to Excel
            df.to_excel(Excel_file_path, index=False)
            print("Excel file updated successfully!")

            # Now proceed with database save
            user = User.query.filter_by(username=username).first()
            print("User:", user)

            if not user:
                return jsonify({"error": "User not found"}), 404

            # Create new product record
            new_product = Product(
                user_name=username,  # Use the username from query parameter
                platform_name=str(data.get('Platform Name', '')).strip(),
                category=str(data.get('category', '')).strip(),
                provider=str(data.get('provider', '')).strip(),
                product_brand=str(data.get('product brand', '')).strip(),
                product_description=str(data.get('product description', '')).strip(),
                order_date=data.get('Order Date'),
                invoice_date=data.get('Invoice date'),
                expiry_date=data.get('Expiry Date'),
                gst_number=str(data.get('GST number', '')).strip(),
                invoice_number=str(data.get('Invoice Number', '')).strip(),
                quantity=data.get('Quantity'),
                total_amount=str(data.get('Total Amount', 0.0)),
                discount_percentage=str(data.get('Discount percentage', 0.0)),
                tax_amount=str(data.get('Tax amount', 0.0)),
                igst_percentage=str(data.get('IGST percentage', 0.0)),
                seller_address=str(data.get('Seller address', '')).strip(),
                billing_address=str(data.get('Billing Address', '')).strip(),
                shipping_address=str(data.get('Shipping address', '')).strip(),
                # customer_name=str(data.get('Customer Name', '')).strip(),
                pan_number=str(data.get('Pan No', '')).strip(),
                payement_mode=str(data.get('Mode of Payement', '')).strip(),
                file_path=str(data.get('file_url', '')).strip()
            )

            db.session.add(new_product)
            db.session.commit()

            # Get product image if category and brand are available
            if data.get('category') and data.get('product brand'):
                product_image = download_image_with_category_brand(
                    data.get('category'),
                    data.get('product brand')
                )

                if product_image:
                    product_image_record = ProductImage(
                        # product_id=new_product.id,
                        product_name=data.get('product brand'),
                        product_image=product_image,
                        category=data.get('category')
                    )
                    db.session.add(product_image_record)
                    db.session.commit()

            return jsonify({
                'message': 'Data saved successfully',
                'product': {
                    'id': new_product.id,
                    'product_brand': new_product.product_brand,
                    'product_description': new_product.product_description,
                    'category': new_product.category,
                    'order_date': new_product.order_date,
                    'expiry_date': new_product.expiry_date,
                    'total_amount': new_product.total_amount,
                    'file_path': new_product.file_path,
                    'username': new_product.user_name
                },
                'success': True
            }), 200

        except Exception as e:
            print("Error saving to Excel or database:", str(e))
            return jsonify({"error": f"Failed to save data: {str(e)}"}), 500

    except Exception as e:
        print("General error:", str(e))
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

@doc.route('/products', methods=['GET'])
def get_products():
    try:
        # Get username from query parameter
        username = request.args.get('user')
        if not username:
            return jsonify({'error': 'Username is required'}), 400

        # Get products for this user
        products = Product.query.filter_by(user_name=username).all()
        
        # Create a dictionary of product images keyed by category
        product_images = {}
        images = ProductImage.query.all()
        for image in images:
            if image.category not in product_images and image.product_image:
                image_path = image.product_image.replace('\\', '/').replace('react_backend/', '')
                product_images[image.category] = f'/static/{image_path.split("static/")[1]}'

        # Format the response
        formatted_products = []
        for product in products:
            product_image = product_images.get(
                product.category, 
                '/static/images/products/unknown.jpg'
            )
            
            formatted_products.append({
                'id': product.id,
                'product_brand': product.product_brand,
                'product_description': product.product_description,
                'category': product.category,
                'order_date': product.order_date,
                'expiry_date': product.expiry_date,
                'total_amount': product.total_amount,
                'file_path': product.file_path,
                'username': product.user_name,
                'product_image': product_image
            })

        return jsonify({
            'products': formatted_products
        }), 200

    except Exception as e:
        print("Error fetching products:", str(e))
        return jsonify({'error': str(e)}), 500

@doc.route('/download', methods=['POST'])
def download_pdf():
    try:
        data = request.json
        pdf_path = data.get('path')
        username = request.args.get('user')
        
        if not pdf_path or not username:
            return jsonify({'error': 'Missing required parameters'}), 400
            
        # Get just the filename without any path
        file_name = os.path.basename(pdf_path)
        
        # First check if file exists in the UPLOAD_FOLDER
        upload_file_path = os.path.join(UPLOAD_FOLDER, file_name)
        if os.path.exists(upload_file_path):
            try:
                return send_file(
                    upload_file_path,
                    as_attachment=True,
                    download_name=file_name,
                    mimetype='application/pdf'
                )
            except Exception as e:
                print(f"Error sending local file: {str(e)}")
                # If local file fails, try S3
                pass
        
        # Try to get from S3 using existing function
        try:
            # Use your existing download function
            s3_file_path = download_from_s3_cli(
                user_name=username,
                file_name=file_name
            )
            
            if s3_file_path and os.path.exists(s3_file_path):
                return send_file(
                    s3_file_path,
                    as_attachment=True,
                    download_name=file_name,
                    mimetype='application/pdf'
                )
            else:
                return jsonify({'error': 'File not found in S3'}), 404
                
        except Exception as e:
            print(f"S3 download error: {str(e)}")
            return jsonify({'error': 'Failed to download file'}), 500
            
    except Exception as e:
        print(f"Download error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@doc.route('/save', methods=['POST', 'OPTIONS'])
@cross_origin(supports_credentials=True)
def save_document():
    if request.method == 'OPTIONS':
        # Explicitly handle OPTIONS request
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response

    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Your existing save logic here
        new_product = Product(
            user_name=data.get('user_name'),
            category=data.get('category'),
            product_brand=data.get('product_brand'),
            product_name=data.get('product_name'),
            order_date=data.get('order_date'),
            expiry_date=data.get('expiry_date'),
            total_amount=data.get('total_amount'),
            file_path=data.get('file_path')
        )
        
        db.session.add(new_product)
        db.session.commit()

        return jsonify({
            'message': 'Document saved successfully',
            'product': {
                'id': new_product.id,
                'category': new_product.category,
                'product_brand': new_product.product_brand
            }
        }), 200

    except Exception as e:
        print(f"Save error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500