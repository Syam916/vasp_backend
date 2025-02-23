from flask import Blueprint, request, jsonify,session
from app.models.user import User
from app.extensions import db
from flask_jwt_extended import create_access_token
import random
import requests
from app.config import Config
from flask_cors import CORS

WHATSAPP_ACCESS_TOKEN = Config.WHATSAPP_ACCESS_TOKEN
WHATSAPP_API_URL = Config.WHATSAPP_API_URL
TEMPLATE_NAME = Config.WHATSAPP_TEMPLATE_NAME

auth = Blueprint('auth', __name__)

# At the top of your file, after creating the Blueprint
CORS(auth)

@auth.route('/register', methods=['POST'])
def register():
    data = request.get_json()


    print(data,'-------------------------enterede data')

    # Check if user already exists
    if User.query.filter_by(email=data['email']).first():
        print('-------------------------email already registered')
        return jsonify({'error': 'Email already registered'}), 400
    
    if User.query.filter_by(username=data['username']).first():
        print('-------------------------username already taken')
        return jsonify({'error': 'Username already taken'}), 400

    # Create new user
    user = User(
        username=data['username'],
        email=data['email'],
        mobile_number=data['mobile'],
        location=data['location'],
        pincode=data['pincode']
    )
    user.set_password(data['password'])

    db.session.add(user)
    db.session.commit()

    print(user,'-------------------------user')

    return jsonify({'message': 'Registration successful'}), 201

@auth.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(email=data['email']).first()

    if user and user.check_password(data['password']):
        access_token = create_access_token(identity=user.id)
        session['username'] = user.username  # Store username in session
        
        return jsonify({
            'token': access_token,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'mobile_number': user.mobile_number,
                'location': user.location,
                'pincode': user.pincode
                # Add other user fields as needed
            }
        }), 200

    return jsonify({'error': 'Invalid credentials'}), 401

session_otp = None

@auth.route('/send-otp', methods=['POST'])
def send_otp():
    global session_otp
    try:
        print("Received send OTP request")
        data = request.get_json()
        print("Request data:", data)
        
        country_code = data.get('country_code')
        mobile_number = data.get('mobile_number')

        if not country_code or not mobile_number:
            return jsonify({
                'status': 'error', 
                'message': 'Country code and phone number are required'
            }), 400

        full_phone_number = f"{country_code}{mobile_number}"
        otp = str(random.randint(100000, 999999))
        session_otp = otp
        print(f"Generated OTP: {otp} for number: {full_phone_number}")

        headers = {
            "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }

        payload = {
            "messaging_product": "whatsapp",
            "to": full_phone_number,
            "type": "template",
            "template": {
                "name": TEMPLATE_NAME,
                "language": {"code": "en"},
                "components": [
                    {
                        "type": "body",
                        "parameters": [{"type": "text", "text": otp}]
                    },
                    {
                        "type": "button",
                        "sub_type": "url",
                        "index": 0,
                        "parameters": [{"type": "text", "text": "Verify"}]
                    }
                ]
            }
        }

        try:
            response = requests.post(WHATSAPP_API_URL, json=payload, headers=headers)
            print("WhatsApp API Response:", response.text)

            if response.status_code == 200:
                print(f"Sending OTP back to frontend: {otp}")
                return jsonify({
                    'status': 'success', 
                    'message': 'OTP sent successfully',
                    'otp': str(otp)  # Convert to string explicitly
                })
            else:
                return jsonify({
                    'status': 'error', 
                    'message': f'Failed to send OTP: {response.text}'
                }), 500
        except Exception as e:
            print("Error in WhatsApp API call:", str(e))
            return jsonify({
                'status': 'error',
                'message': 'Server error during OTP sending'
            }), 500

    except Exception as e:
        print("Error in send_otp:", str(e))
        return jsonify({
            'status': 'error',
            'message': 'Server error during OTP sending'
        }), 500

@auth.route('/verify-otp', methods=['POST'])
def verify_otp():
    global session_otp
    print("Received verify OTP request")
    
    try:
        data = request.get_json()
        print("Full request data:", data)
        
        user_otp = str(data.get('otp', ''))
        sent_otp = session_otp

        print(f"User OTP: {user_otp}")
        print(f"Sent OTP: {sent_otp}")
        
        if not user_otp or not sent_otp:
            print("Missing OTP values")
            return jsonify({
                'status': 'error', 
                'message': 'Both OTP values are required'
            }), 400
        
        # Compare as strings
        if sent_otp == user_otp:
            print("OTP verified successfully")
            return jsonify({
                'status': 'success', 
                'message': 'OTP verified successfully'
            })
        else:
            print(f"OTP verification failed. Expected: {sent_otp}, Got: {user_otp}")
            return jsonify({
                'status': 'error', 
                'message': 'Invalid OTP'
            }), 400
            
    except Exception as e:
        print("Error in verify_otp:", str(e))
        return jsonify({
            'status': 'error',
            'message': 'Server error during verification'
        }), 500

# Or add these headers to your routes
@auth.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response 