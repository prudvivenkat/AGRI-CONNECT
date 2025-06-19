import os
import json
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, jsonify, request, make_response
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, create_refresh_token, jwt_required, get_jwt_identity
import random
import string
import re
from models import User, OTP
from equipment_models import Equipment, Booking, Review
from worker_models import WorkerProfile, WorkerHiring, WorkerReview
import config
from datetime import datetime, timedelta
import sqlite3
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from config import GEMINI_API_KEY
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app, supports_credentials=True)

# Configure app secret key
app.config['SECRET_KEY'] = config.JWT_SECRET_KEY  # Use the same secret key for simplicity

# Dictionary to store CSRF tokens
csrf_tokens = {}

# JWT Configuration
app.config['JWT_SECRET_KEY'] = config.JWT_SECRET_KEY
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = config.JWT_ACCESS_TOKEN_EXPIRES
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = config.JWT_REFRESH_TOKEN_EXPIRES
jwt = JWTManager(app)

# Validation functions
def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def is_valid_phone(phone):
    pattern = r'^\+?[0-9]{10,15}$'
    return re.match(pattern, phone) is not None

def is_valid_password(password):
    return len(password) >= 8

def generate_otp():
    return ''.join(random.choices(string.digits, k=6))

def send_otp_email(recipient_email, otp_code):
    """Send OTP code to the user's email"""
    # Check if email credentials are configured
    if not config.EMAIL_SENDER or not config.EMAIL_PASSWORD:
        print("Email credentials not configured. Please set EMAIL_ID and EMAIL_PASSWORD in .env file.")
        return False

    try:
        print(f"Attempting to send email using: {config.EMAIL_SENDER} (Password length: {len(config.EMAIL_PASSWORD)})")

        # Create message container
        msg = MIMEMultipart()
        msg['From'] = config.EMAIL_SENDER
        msg['To'] = recipient_email
        msg['Subject'] = 'AgriConnect - Your Verification Code'

        # Create the body of the message
        email_body = f'''
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee; border-radius: 10px; background-color: #f9f9f9;">
                <div style="text-align: center; margin-bottom: 20px;">
                    <h1 style="color: #4CAF50;">AgriConnect</h1>
                </div>
                <div style="background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                    <h2 style="color: #333; margin-top: 0;">Verify Your Account</h2>
                    <p>Thank you for registering with AgriConnect. Please use the following verification code to complete your registration:</p>
                    <div style="text-align: center; margin: 30px 0;">
                        <div style="display: inline-block; padding: 15px 30px; background-color: #f2f2f2; border-radius: 5px; letter-spacing: 5px; font-size: 24px; font-weight: bold;">
                            {otp_code}
                        </div>
                    </div>
                    <p>This code will expire in 5 minutes.</p>
                    <p>If you did not request this code, please ignore this email.</p>
                </div>
                <div style="margin-top: 20px; text-align: center; color: #777; font-size: 12px;">
                    <p>© {datetime.now().year} AgriConnect. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        '''

        # Attach HTML content
        msg.attach(MIMEText(email_body, 'html'))

        # Connect to SMTP server
        print(f"Connecting to SMTP server: {config.SMTP_SERVER}:{config.SMTP_PORT}")
        server = smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT)
        server.set_debuglevel(1)  # Enable debug output
        server.starttls()  # Secure the connection

        # Login to email account
        print("Attempting to login to email account...")
        server.login(config.EMAIL_SENDER, config.EMAIL_PASSWORD)

        # Send email
        print("Sending email...")
        server.send_message(msg)
        server.quit()

        print(f"Verification email sent successfully to {recipient_email}")
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"SMTP Authentication Error: {e}")
        print("This error typically occurs when:")
        print("1. The email or password is incorrect")
        print("2. You're not using an App Password (required for Gmail with 2FA)")
        print("3. Less secure app access is not enabled (if not using 2FA)")
        print("Please check your EMAIL_ID and EMAIL_PASSWORD in the .env file")
        return False
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

def calculate_rental_price(price_per_day, start_date, end_date):
    try:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        days = (end - start).days + 1  # Include both start and end day
        if days <= 0:
            return None
        return price_per_day * days
    except ValueError:
        return None

# Initialize database with required tables
def init_db():
    conn = sqlite3.connect(config.DATABASE_PATH)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT UNIQUE,
        email TEXT UNIQUE,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create equipment table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS equipment (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        description TEXT,
        price_per_day REAL NOT NULL,
        location TEXT,
        image_url TEXT,
        availability_status TEXT DEFAULT 'available',
        is_approved INTEGER DEFAULT 0,
        rejection_reason TEXT,
        reviewed_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (owner_id) REFERENCES users (id)
    )
    ''')
    
    # Create equipment categories table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS equipment_categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT
    )
    ''')
    
    # Create equipment bookings table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS equipment_bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        equipment_id INTEGER NOT NULL,
        renter_id INTEGER NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        total_price REAL NOT NULL,
        status TEXT NOT NULL,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (equipment_id) REFERENCES equipment (id),
        FOREIGN KEY (renter_id) REFERENCES users (id)
    )
    ''')
    
    # Create equipment reviews table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS equipment_reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        equipment_id INTEGER NOT NULL,
        reviewer_id INTEGER NOT NULL,
        rating INTEGER NOT NULL,
        comment TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (equipment_id) REFERENCES equipment (id),
        FOREIGN KEY (reviewer_id) REFERENCES users (id)
    )
    ''')
    
    # Create worker profiles table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS worker_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        skills TEXT NOT NULL,
        experience TEXT,
        daily_rate REAL NOT NULL,
        location TEXT,
        availability TEXT DEFAULT 'available',
        tools_owned TEXT,
        is_approved INTEGER DEFAULT 0,
        rejection_reason TEXT,
        reviewed_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # Create worker hirings table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS worker_hirings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        worker_profile_id INTEGER NOT NULL,
        farmer_id INTEGER NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        total_payment REAL NOT NULL,
        work_description TEXT,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (worker_profile_id) REFERENCES worker_profiles (id),
        FOREIGN KEY (farmer_id) REFERENCES users (id)
    )
    ''')
    
    # Create worker reviews table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS worker_reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        worker_profile_id INTEGER NOT NULL,
        reviewer_id INTEGER NOT NULL,
        rating INTEGER NOT NULL,
        comment TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (worker_profile_id) REFERENCES worker_profiles (id),
        FOREIGN KEY (reviewer_id) REFERENCES users (id)
    )
    ''')

    # Create feedback/reports table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        feedback_type TEXT NOT NULL,
        subject TEXT NOT NULL,
        description TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        admin_response TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')

    # Create system notifications table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        is_read INTEGER DEFAULT 0,
        notification_type TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database on app startup
init_db()

# Status route
@app.route('/api/status', methods=['GET'])
def status():
    return jsonify({
        'status': 'success',
        'message': 'Agri Connect API is running'
    })

# Register route
@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    
    # Validate input
    if not data or 'name' not in data or 'password' not in data or 'role' not in data:
        return jsonify({'status': 'error', 'message': 'Missing required fields'}), 400
        
    name = data.get('name')
    phone = data.get('phone', '')
    email = data.get('email', '')
    password = data.get('password')
    role = data.get('role')
    
    # Validate role
    if role not in ['farmer', 'worker', 'admin', 'renter']:
        return jsonify({'status': 'error', 'message': 'Invalid role'}), 400
    
    # Validate contact information
    if not phone and not email:
        return jsonify({'status': 'error', 'message': 'At least one contact method (phone or email) is required'}), 400
    
    if phone and not is_valid_phone(phone):
        return jsonify({'status': 'error', 'message': 'Invalid phone number format'}), 400
        
    if email and not is_valid_email(email):
        return jsonify({'status': 'error', 'message': 'Invalid email format'}), 400
    
    if not is_valid_password(password):
        return jsonify({'status': 'error', 'message': 'Password must be at least 8 characters long'}), 400
    
    # Check if user already exists
    if phone and User.find_by_phone(phone):
        return jsonify({'status': 'error', 'message': 'Phone number already registered'}), 400
        
    if email and User.find_by_email(email):
        return jsonify({'status': 'error', 'message': 'Email already registered'}), 400
    
    # Create user
    result = User.create(name, phone, email, password, role)

    # Handle different error cases
    if isinstance(result, dict) and 'error' in result:
        error_type = result['error']
        if error_type == 'phone_exists':
            return jsonify({'status': 'error', 'message': 'Phone number already registered'}), 400
        elif error_type == 'email_exists':
            return jsonify({'status': 'error', 'message': 'Email already registered'}), 400
        else:
        return jsonify({'status': 'error', 'message': 'Failed to create user'}), 500
    
    # If successful, result is the user_id
    user_id = result

    # Generate OTP for verification (phone preferred, email as fallback)
    otp_code = generate_otp()
    contact = phone if phone else email
    contact_type = 'phone' if phone else 'email'
    
    # Store OTP in database
    OTP.create(contact, otp_code, contact_type)
    
    # Send OTP via email if email is provided
    email_sent = False
    if email:
        email_sent = send_otp_email(email, otp_code)

    # For phone verification, we would integrate with an SMS service
    # This is not implemented in this version

    # Include dev_otp in response for testing purposes
    response_data = {
        'status': 'success',
        'message': 'Registration successful, verification required',
        'user_id': user_id,
        'contact': contact,
        'contact_type': contact_type
    }

    # Add email status to response
    if email:
        if email_sent:
            response_data['message'] += '. Verification code sent to your email'
        else:
            response_data['message'] += '. Failed to send verification code to email'

    # Return response without including the OTP
    return jsonify(response_data), 201

# Verify OTP route
@app.route('/api/auth/verify', methods=['POST'])
def verify_otp():
    data = request.get_json()
    
    if not data or 'contact' not in data or 'otp_code' not in data:
        return jsonify({'status': 'error', 'message': 'Missing required fields'}), 400
        
    contact = data.get('contact')
    otp_code = data.get('otp_code')
    contact_type = data.get('contact_type', 'phone')
    
    if OTP.verify(contact, otp_code, contact_type):
        # Find the user by contact
        user = None
        if contact_type == 'phone':
            user = User.find_by_phone(contact)
        else:
            user = User.find_by_email(contact)
            
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
        
        # Generate tokens
        access_token = create_access_token(identity=user['id'])
        refresh_token = create_refresh_token(identity=user['id'])
        
        return jsonify({
            'status': 'success',
            'message': 'Verification successful',
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': {
                'id': user['id'],
                'name': user['name'],
                'email': user['email'],
                'phone': user['phone'],
                'role': user['role']
            }
        }), 200
    else:
        return jsonify({'status': 'error', 'message': 'Invalid or expired OTP'}), 400

# Resend OTP route
@app.route('/api/auth/resend-otp', methods=['POST'])
def resend_otp():
    data = request.get_json()

    if not data or 'contact' not in data:
        return jsonify({'status': 'error', 'message': 'Missing required fields'}), 400

    contact = data.get('contact')
    contact_type = data.get('contact_type', 'phone')

    # Verify that the user exists
    user = None
    if contact_type == 'phone':
        user = User.find_by_phone(contact)
    else:
        user = User.find_by_email(contact)

    if not user:
        return jsonify({'status': 'error', 'message': 'User not found'}), 404

    # Generate new OTP
    otp_code = generate_otp()

    # Store OTP in database
    if OTP.create(contact, otp_code, contact_type):
        # Send OTP via email if contact type is email
        email_sent = False
        if contact_type == 'email':
            email_sent = send_otp_email(contact, otp_code)

        # For phone verification, we would integrate with an SMS service
        # This is not implemented in this version

        # Prepare response
        response_data = {
            'status': 'success',
            'message': 'Verification code sent',
            'contact': contact,
            'contact_type': contact_type
        }

        # Add email status to response
        if contact_type == 'email':
            if email_sent:
                response_data['message'] = 'Verification code sent to your email'
            else:
                response_data['message'] = 'Failed to send verification code to email'

        # Return response without including the OTP
        return jsonify(response_data), 200
    else:
        return jsonify({'status': 'error', 'message': 'Failed to generate verification code'}), 500

# Login route
@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data or 'password' not in data:
        return jsonify({'status': 'error', 'message': 'Missing required fields'}), 400
    
    # User can login with either phone or email
    phone = data.get('phone', '')
    email = data.get('email', '')
    password = data.get('password')
    
    if not phone and not email:
        return jsonify({'status': 'error', 'message': 'Phone or email is required'}), 400
    
    # Find user
    user = None
    if phone:
        user = User.find_by_phone(phone)
    elif email:
        user = User.find_by_email(email)
        
    if not user:
        return jsonify({'status': 'error', 'message': 'User not found'}), 404
    
    # Verify password
    if not User.verify_password(user['password'], password):
        return jsonify({'status': 'error', 'message': 'Invalid password'}), 401
    
    # Generate tokens
    access_token = create_access_token(identity=user['id'])
    refresh_token = create_refresh_token(identity=user['id'])
    
    return jsonify({
        'status': 'success',
        'message': 'Login successful',
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': {
            'id': user['id'],
            'name': user['name'],
            'email': user['email'],
            'phone': user['phone'],
            'role': user['role']
        }
    }), 200

# Refresh token route
@app.route('/api/auth/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    current_user_id = get_jwt_identity()
    access_token = create_access_token(identity=current_user_id)
    
    return jsonify({
        'status': 'success',
        'access_token': access_token
    }), 200

# Get user profile
@app.route('/api/user/profile', methods=['GET'])
@jwt_required()
def get_profile():
    current_user_id = get_jwt_identity()
    
    # Get user details from the database
    user = User.find_by_id(current_user_id)
    
    if not user:
        return jsonify({'status': 'error', 'message': 'User not found'}), 404

    # Return user data (excluding password)
    return jsonify({
        'status': 'success',
        'user': {
            'id': user['id'],
            'name': user['name'],
            'email': user['email'],
            'phone': user['phone'],
            'role': user['role'],
            'created_at': user['created_at']
        }
    }), 200

# Update user profile
@app.route('/api/user/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    current_user_id = get_jwt_identity()
    data = request.get_json()

    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400

    # Get current user data
    user = User.find_by_id(current_user_id)
    if not user:
        return jsonify({'status': 'error', 'message': 'User not found'}), 404

    # Prepare update data
    update_data = {}

    # Update name if provided
    if 'name' in data and data['name']:
        update_data['name'] = data['name']

    # Update email if provided and valid
    if 'email' in data and data['email']:
        if not is_valid_email(data['email']):
            return jsonify({'status': 'error', 'message': 'Invalid email format'}), 400

        # Check if email is already in use by another user
        existing_user = User.find_by_email(data['email'])
        if existing_user and existing_user['id'] != current_user_id:
            return jsonify({'status': 'error', 'message': 'Email already in use'}), 400

        update_data['email'] = data['email']

    # Update phone if provided and valid
    if 'phone' in data and data['phone']:
        if not is_valid_phone(data['phone']):
            return jsonify({'status': 'error', 'message': 'Invalid phone format'}), 400

        # Check if phone is already in use by another user
        existing_user = User.find_by_phone(data['phone'])
        if existing_user and existing_user['id'] != current_user_id:
            return jsonify({'status': 'error', 'message': 'Phone number already in use'}), 400

        update_data['phone'] = data['phone']

    # Update password if provided - requires CSRF token
    if 'currentPassword' in data and 'newPassword' in data and data['currentPassword'] and data['newPassword']:
        # Check for CSRF token when changing password
        if '_csrf' not in data:
            return jsonify({'status': 'error', 'message': 'CSRF token required for password changes'}), 400

        # Verify the CSRF token
        if current_user_id not in csrf_tokens or csrf_tokens.get(current_user_id) != data['_csrf']:
            return jsonify({'status': 'error', 'message': 'Invalid CSRF token'}), 400

        # Token is valid, remove it to prevent reuse
        del csrf_tokens[current_user_id]

        # Verify current password
        if not User.verify_password(user['password'], data['currentPassword']):
            return jsonify({'status': 'error', 'message': 'Current password is incorrect'}), 400

        # Validate new password
        if not is_valid_password(data['newPassword']):
            return jsonify({'status': 'error', 'message': 'New password must be at least 8 characters long'}), 400

        # Hash the new password
        update_data['password'] = User.hash_password(data['newPassword'])

    # If no updates, return success
    if not update_data:
        return jsonify({'status': 'success', 'message': 'No changes to update'}), 200

    # Update user in database
    success = User.update(current_user_id, update_data)

    if not success:
        return jsonify({'status': 'error', 'message': 'Failed to update profile'}), 500

    # Get updated user data
    updated_user = User.find_by_id(current_user_id)

    return jsonify({
        'status': 'success',
        'message': 'Profile updated successfully',
        'user': {
            'id': updated_user['id'],
            'name': updated_user['name'],
            'email': updated_user['email'],
            'phone': updated_user['phone'],
            'role': updated_user['role'],
            'created_at': updated_user['created_at']
        }
    }), 200

# ----- EQUIPMENT RENTAL API ENDPOINTS -----

# Get all equipment categories
@app.route('/api/equipment/categories', methods=['GET'])
def get_equipment_categories():
    categories = Equipment.get_categories()
    return jsonify({
        'status': 'success',
        'categories': [dict(category) for category in categories]
    }), 200

# Create new equipment
@app.route('/api/equipment', methods=['POST'])
@jwt_required()
def create_equipment():
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    # Validate input
    if not data or 'name' not in data or 'category' not in data or 'price_per_day' not in data:
        return jsonify({'status': 'error', 'message': 'Missing required fields'}), 400
    
    try:
        # Create equipment
        equipment_id, error = Equipment.create(
            owner_id=current_user_id,
            name=data.get('name'),
            category=data.get('category'),
            description=data.get('description', ''),
            price_per_day=float(data.get('price_per_day')),
            location=data.get('location'),
            image_url=data.get('image_url')
        )
        
        if not equipment_id:
            if error == "duplicate":
                return jsonify({
                    'status': 'error',
                    'message': 'You already have equipment with the same name and category',
                    'error_code': 'duplicate_equipment'
                }), 400
            else:
            return jsonify({'status': 'error', 'message': 'Failed to create equipment'}), 500
        
        return jsonify({
            'status': 'success',
            'message': 'Equipment created successfully',
            'equipment_id': equipment_id
        }), 201
        
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Invalid price format'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Get all equipment with optional filters
@app.route('/api/equipment', methods=['GET'])
def get_all_equipment():
    # Parse query parameters
    category = request.args.get('category')
    location = request.args.get('location')
    max_price = request.args.get('max_price')
    available_only = request.args.get('available_only', 'false').lower() == 'true'
    search = request.args.get('search')
    limit = int(request.args.get('limit', 20))
    offset = int(request.args.get('offset', 0))
    
    # Build filters dictionary
    filters = {}
    if category:
        filters['category'] = category
    if location:
        filters['location'] = location
    if max_price:
        try:
            filters['max_price'] = float(max_price)
        except ValueError:
            pass
    if available_only:
        filters['available_only'] = True
    if search:
        filters['search'] = search
    
    # Get equipment
    equipment_list = Equipment.find_all(filters, limit, offset)
    
    return jsonify({
        'status': 'success',
        'equipment': [dict(item) for item in equipment_list]
    }), 200

# Get equipment by ID
@app.route('/api/equipment/<int:equipment_id>', methods=['GET'])
def get_equipment(equipment_id):
    equipment = Equipment.find_by_id(equipment_id)
    
    if not equipment:
        return jsonify({'status': 'error', 'message': 'Equipment not found'}), 404
    
    # Get reviews for this equipment
    reviews = Review.find_by_equipment(equipment_id)
    
    # Calculate average rating
    avg_rating = Review.get_average_rating(equipment_id)
    
    return jsonify({
        'status': 'success',
        'equipment': dict(equipment),
        'reviews': [dict(review) for review in reviews],
        'avg_rating': avg_rating
    }), 200

# Update equipment
@app.route('/api/equipment/<int:equipment_id>', methods=['PUT'])
@jwt_required()
def update_equipment(equipment_id):
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    # Verify ownership
    equipment = Equipment.find_by_id(equipment_id)
    if not equipment:
        return jsonify({'status': 'error', 'message': 'Equipment not found'}), 404
    
    if equipment['owner_id'] != current_user_id:
        return jsonify({'status': 'error', 'message': 'You do not own this equipment'}), 403
    
    # Convert price to float if provided
    if 'price_per_day' in data:
        try:
            data['price_per_day'] = float(data['price_per_day'])
        except ValueError:
            return jsonify({'status': 'error', 'message': 'Invalid price format'}), 400
    
    # Update equipment
    if Equipment.update(equipment_id, data):
        return jsonify({
            'status': 'success',
            'message': 'Equipment updated successfully'
        }), 200
    else:
        return jsonify({'status': 'error', 'message': 'Failed to update equipment'}), 500

# Delete equipment
@app.route('/api/equipment/<int:equipment_id>', methods=['DELETE'])
@jwt_required()
def delete_equipment(equipment_id):
    current_user_id = get_jwt_identity()
    
    # Verify ownership
    equipment = Equipment.find_by_id(equipment_id)
    if not equipment:
        return jsonify({'status': 'error', 'message': 'Equipment not found'}), 404
    
    if equipment['owner_id'] != current_user_id:
        return jsonify({'status': 'error', 'message': 'You do not own this equipment'}), 403
    
    # Delete equipment
    if Equipment.delete(equipment_id):
        return jsonify({
            'status': 'success',
            'message': 'Equipment deleted successfully'
        }), 200
    else:
        return jsonify({'status': 'error', 'message': 'Failed to delete equipment'}), 500

# Get user's equipment
@app.route('/api/user/equipment', methods=['GET'])
@jwt_required()
def get_user_equipment():
    current_user_id = get_jwt_identity()
    print(f"Getting equipment for user ID: {current_user_id}")

    # Get user details to check role
    user = User.find_by_id(current_user_id)
    if not user:
        return jsonify({'status': 'error', 'message': 'User not found'}), 404

    print(f"User role: {user['role']}")

    equipment_list = Equipment.find_by_owner(current_user_id)

    print(f"Found {len(equipment_list)} equipment items for user ID: {current_user_id}")
    
    return jsonify({
        'status': 'success',
        'equipment': [dict(item) for item in equipment_list]
    }), 200

# Get equipment rented by the user
@app.route('/api/user/rented-equipment', methods=['GET'])
@jwt_required()
def get_user_rented_equipment():
    current_user_id = get_jwt_identity()
    print(f"Fetching rented equipment for user ID: {current_user_id}")

    # Get user details to check role
    user = User.find_by_id(current_user_id)
    if not user:
        return jsonify({'status': 'error', 'message': 'User not found'}), 404

    print(f"User role: {user['role']}")

    rented_equipment = Equipment.find_rented_by_user(current_user_id)

    print(f"Found {len(rented_equipment)} rented equipment items")

    return jsonify({
        'status': 'success',
        'rented_equipment': [dict(item) for item in rented_equipment]
    }), 200

# Create equipment booking
@app.route('/api/equipment/<int:equipment_id>/book', methods=['POST'])
@jwt_required()
def book_equipment(equipment_id):
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    # Validate input
    if not data or 'start_date' not in data or 'end_date' not in data:
        return jsonify({'status': 'error', 'message': 'Missing required fields'}), 400
    
    # Get equipment details
    equipment = Equipment.find_by_id(equipment_id)
    if not equipment:
        return jsonify({'status': 'error', 'message': 'Equipment not found'}), 404
    
    # Check if equipment is available
    if equipment['availability_status'] != 'available':
        return jsonify({'status': 'error', 'message': 'Equipment is not available for booking'}), 400
    
    # Prevent booking own equipment
    if equipment['owner_id'] == current_user_id:
        return jsonify({'status': 'error', 'message': 'You cannot book your own equipment'}), 400
    
    # Calculate total price
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    total_price = calculate_rental_price(equipment['price_per_day'], start_date, end_date)
    
    if total_price is None:
        return jsonify({'status': 'error', 'message': 'Invalid date range'}), 400
    
    # Create booking
    booking_id = Booking.create(
        equipment_id=equipment_id,
        renter_id=current_user_id,
        start_date=start_date,
        end_date=end_date,
        total_price=total_price,
        notes=data.get('notes')
    )
    
    if not booking_id:
        return jsonify({'status': 'error', 'message': 'Failed to create booking'}), 500
    
    return jsonify({
        'status': 'success',
        'message': 'Booking created successfully',
        'booking_id': booking_id,
        'total_price': total_price
    }), 201

# Get user's bookings (as renter)
@app.route('/api/user/bookings', methods=['GET'])
@jwt_required()
def get_user_bookings():
    current_user_id = get_jwt_identity()
    bookings = Booking.find_by_renter(current_user_id)
    
    return jsonify({
        'status': 'success',
        'bookings': [dict(booking) for booking in bookings]
    }), 200

# Get bookings for user's equipment (as owner)
@app.route('/api/user/equipment/bookings', methods=['GET'])
@jwt_required()
def get_equipment_bookings():
    current_user_id = get_jwt_identity()
    bookings = Booking.find_by_owner(current_user_id)
    
    return jsonify({
        'status': 'success',
        'bookings': [dict(booking) for booking in bookings]
    }), 200

# Update booking status
@app.route('/api/bookings/<int:booking_id>/status', methods=['PUT'])
@jwt_required()
def update_booking_status(booking_id):
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data or 'status' not in data:
        return jsonify({'status': 'error', 'message': 'Status is required'}), 400
    
    new_status = data['status']
    if new_status not in ['pending', 'confirmed', 'rejected', 'completed']:
        return jsonify({'status': 'error', 'message': 'Invalid status value'}), 400
    
    # Get the booking
    booking = Booking.find_by_id(booking_id)
    if not booking:
        return jsonify({'status': 'error', 'message': 'Booking not found'}), 404
    
    # Get the equipment
    equipment = Equipment.find_by_id(booking['equipment_id'])
    if not equipment:
        return jsonify({'status': 'error', 'message': 'Equipment not found'}), 404

    # Verify ownership - only the equipment owner can update status
    if equipment['owner_id'] != current_user_id:
        return jsonify({'status': 'error', 'message': 'You do not own this equipment'}), 403

    # Update booking status
    if Booking.update_status(booking_id, new_status):
        return jsonify({
            'status': 'success',
            'message': f'Booking status updated to {new_status}'
        }), 200
    else:
        return jsonify({'status': 'error', 'message': 'Failed to update booking status'}), 500

# Create equipment review
@app.route('/api/equipment/<int:equipment_id>/reviews', methods=['POST'])
@jwt_required()
def create_review(equipment_id):
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data or 'rating' not in data:
        return jsonify({'status': 'error', 'message': 'Rating is required'}), 400
    
    try:
        rating = int(data.get('rating'))
        if rating < 1 or rating > 5:
            return jsonify({'status': 'error', 'message': 'Rating must be between 1 and 5'}), 400
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Rating must be a number'}), 400
    
    # Verify equipment exists
    equipment = Equipment.find_by_id(equipment_id)
    if not equipment:
        return jsonify({'status': 'error', 'message': 'Equipment not found'}), 404
    
    # Don't allow reviewing own equipment
    if equipment['owner_id'] == current_user_id:
        return jsonify({'status': 'error', 'message': 'You cannot review your own equipment'}), 400
    
    # Create review
    review_id = Review.create(
        equipment_id=equipment_id,
        reviewer_id=current_user_id,
        rating=rating,
        comment=data.get('comment')
    )
    
    if not review_id:
        return jsonify({'status': 'error', 'message': 'Failed to create review'}), 500
    
    return jsonify({
        'status': 'success',
        'message': 'Review submitted successfully',
        'review_id': review_id
    }), 201

# Worker API Routes

# Get worker profile for the current user
@app.route('/api/worker/profile', methods=['GET'])
@jwt_required()
def get_worker_profile():
    user_id = get_jwt_identity()
    print(f"Getting worker profile for user ID: {user_id}")

    # Check if user is a worker
    user = User.find_by_id(user_id)
    print(f"User data: {user}")

    if not user:
        return jsonify({'status': 'error', 'message': 'User not found'}), 404

    if user['role'] != 'worker':
        return jsonify({'status': 'error', 'message': 'Only workers can access worker profiles'}), 403
    
    # Find the worker profile
    profile = WorkerProfile.find_by_user_id(user_id)
    
    if not profile:
        # Return an empty profile with a 200 status code instead of 404
        # This allows the frontend to show the profile creation form
        return jsonify({
            'status': 'success',
            'profile': None,
            'message': 'No profile exists yet. Please create one.'
        }), 200
    
    return jsonify({
        'status': 'success',
        'profile': dict(profile)
    }), 200

# Create or update worker profile
@app.route('/api/worker/profile', methods=['POST'])
@jwt_required()
def create_update_worker_profile():
    user_id = get_jwt_identity()
    print(f"Creating/updating worker profile for user ID: {user_id}")

    # Check if user is a worker
    user = User.find_by_id(user_id)
    print(f"User data: {user}")

    if not user:
        return jsonify({'status': 'error', 'message': 'User not found'}), 404

    if user['role'] != 'worker':
        return jsonify({'status': 'error', 'message': 'Only workers can create profiles'}), 403

    data = request.get_json()
    print(f"Received profile data: {data}")
    
    # Validate input
    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400
        
    required_fields = ['skills', 'daily_rate']
    for field in required_fields:
        if field not in data:
            return jsonify({'status': 'error', 'message': f'Missing required field: {field}'}), 400
    
    # Check if profile already exists
    existing_profile = WorkerProfile.find_by_user_id(user_id)
    
    if existing_profile:
        # Update existing profile
        success = WorkerProfile.update(existing_profile['id'], data)
        if not success:
            return jsonify({'status': 'error', 'message': 'Failed to update profile'}), 500
            
        updated_profile = WorkerProfile.find_by_id(existing_profile['id'])
        return jsonify({
            'status': 'success',
            'message': 'Profile updated successfully',
            'profile': dict(updated_profile)
        }), 200
    else:
        # Create new profile
        profile_id = WorkerProfile.create(
            user_id,
            data['skills'],
            data.get('experience', ''),
            data['daily_rate'],
            data.get('location', ''),
            data.get('availability', 'available'),
            data.get('tools_owned', '')
        )
        
        if not profile_id:
            return jsonify({'status': 'error', 'message': 'Failed to create profile'}), 500
            
        new_profile = WorkerProfile.find_by_id(profile_id)
        return jsonify({
            'status': 'success',
            'message': 'Profile created successfully',
            'profile': dict(new_profile)
        }), 201

# Get all workers
@app.route('/api/workers', methods=['GET'])
def get_all_workers():
    # Parse query parameters
    try:
        limit = int(request.args.get('limit', 20))
        offset = int(request.args.get('offset', 0))
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Invalid limit or offset parameters'}), 400
    
    # Build filters
    filters = {}
    if 'skills' in request.args:
        filters['skills'] = request.args.get('skills')
    if 'location' in request.args:
        filters['location'] = request.args.get('location')
    if 'max_rate' in request.args:
        try:
            filters['max_rate'] = float(request.args.get('max_rate'))
        except ValueError:
            pass
    if 'tools_owned' in request.args:
        filters['tools_owned'] = request.args.get('tools_owned')
    if request.args.get('available_only') == 'true':
        filters['available_only'] = True
    
    workers = WorkerProfile.find_all(filters=filters, limit=limit, offset=offset)
    
    # Format the response
    formatted_workers = []
    for worker in workers:
        formatted_worker = dict(worker)
        # Get rating information
        rating_info = WorkerReview.get_average_rating(worker['id'])
        formatted_worker['rating'] = rating_info['average_rating'] if rating_info['average_rating'] else 0
        formatted_worker['review_count'] = rating_info['review_count']
        formatted_workers.append(formatted_worker)
    
    return jsonify({
        'status': 'success',
        'count': len(formatted_workers),
        'workers': formatted_workers
    }), 200

# Get worker by ID
@app.route('/api/workers/<int:worker_id>', methods=['GET'])
def get_worker(worker_id):
    worker = WorkerProfile.find_by_id(worker_id)
    
    if not worker:
        return jsonify({'status': 'error', 'message': 'Worker not found'}), 404
    
    # Format the response
    formatted_worker = dict(worker)
    
    # Get rating information
    rating_info = WorkerReview.get_average_rating(worker_id)
    formatted_worker['rating'] = rating_info['average_rating'] if rating_info['average_rating'] else 0
    formatted_worker['review_count'] = rating_info['review_count']
    
    # Get reviews
    reviews = WorkerReview.find_by_worker(worker_id)
    formatted_reviews = [dict(review) for review in reviews]
    
    return jsonify({
        'status': 'success',
        'worker': formatted_worker,
        'reviews': formatted_reviews
    }), 200

# Hire a worker
@app.route('/api/workers/<int:worker_id>/hire', methods=['POST'])
@jwt_required()
def hire_worker(worker_id):
    farmer_id = get_jwt_identity()
    data = request.get_json()
    
    # Validate input
    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400
        
    required_fields = ['start_date', 'end_date']
    for field in required_fields:
        if field not in data:
            return jsonify({'status': 'error', 'message': f'Missing required field: {field}'}), 400
    
    # Get worker profile
    worker = WorkerProfile.find_by_id(worker_id)
    if not worker:
        return jsonify({'status': 'error', 'message': 'Worker not found'}), 404
    
    # Check if worker is available
    if worker['availability'] != 'available':
        return jsonify({'status': 'error', 'message': 'Worker is not currently available'}), 400
    
    # Calculate total payment
    start_date = data['start_date']
    end_date = data['end_date']
    
    try:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        days = (end - start).days + 1  # Include both start and end day
        
        if days <= 0:
            return jsonify({'status': 'error', 'message': 'End date must be after start date'}), 400
            
        total_payment = worker['daily_rate'] * days
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Invalid date format. Use YYYY-MM-DD'}), 400
    
    # Create hiring record
    hiring_id = WorkerHiring.create(
        worker_id,
        farmer_id,
        start_date,
        end_date,
        total_payment,
        data.get('work_description', '')
    )
    
    if not hiring_id:
        return jsonify({'status': 'error', 'message': 'Failed to create hiring record'}), 500
        
    # Get hiring details
    hiring = WorkerHiring.find_by_id(hiring_id)
    
    return jsonify({
        'status': 'success',
        'message': 'Worker hired successfully, pending approval',
        'hiring': dict(hiring),
        'total_payment': total_payment
    }), 201

# Get user's worker hirings (as a farmer)
@app.route('/api/user/hirings', methods=['GET'])
@jwt_required()
def get_user_hirings():
    user_id = get_jwt_identity()
    hirings = WorkerHiring.find_by_farmer(user_id)
    
    formatted_hirings = [dict(hiring) for hiring in hirings]
    
    return jsonify({
        'status': 'success',
        'hirings': formatted_hirings
    }), 200

# Submit feedback/report
@app.route('/api/feedback', methods=['POST'])
@jwt_required()
def submit_feedback():
    user_id = get_jwt_identity()
    data = request.get_json()

    if not data or 'feedback_type' not in data or 'subject' not in data or 'description' not in data:
        return jsonify({'status': 'error', 'message': 'Missing required fields'}), 400

    feedback_type = data.get('feedback_type')
    subject = data.get('subject')
    description = data.get('description')

    # Validate feedback type
    if feedback_type not in ['bug', 'feature', 'feedback']:
        return jsonify({'status': 'error', 'message': 'Invalid feedback type'}), 400

    # Create feedback record
    try:
        conn = sqlite3.connect(config.DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute(
            '''
            INSERT INTO feedback (user_id, feedback_type, subject, description)
            VALUES (?, ?, ?, ?)
            ''',
            (user_id, feedback_type, subject, description)
        )

        conn.commit()
        feedback_id = cursor.lastrowid

        return jsonify({
            'status': 'success',
            'message': 'Feedback submitted successfully',
            'feedback_id': feedback_id
        }), 201
    except sqlite3.Error as e:
        return jsonify({'status': 'error', 'message': f'Database error: {str(e)}'}), 500
    finally:
        conn.close()

# Get hiring requests (as a worker)
@app.route('/api/worker/hiring-requests', methods=['GET'])
@jwt_required()
def get_worker_hiring_requests():
    user_id = get_jwt_identity()
    hirings = WorkerHiring.find_by_worker(user_id)
    
    formatted_hirings = [dict(hiring) for hiring in hirings]
    
    return jsonify({
        'status': 'success',
        'hiring_requests': formatted_hirings
    }), 200

# Update hiring status
@app.route('/api/hirings/<int:hiring_id>/status', methods=['PUT'])
@jwt_required()
def update_hiring_status(hiring_id):
    user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data or 'status' not in data:
        return jsonify({'status': 'error', 'message': 'Status not provided'}), 400
        
    new_status = data['status']
    
    # Validate status
    valid_statuses = ['pending', 'accepted', 'rejected', 'completed', 'cancelled']
    if new_status not in valid_statuses:
        return jsonify({'status': 'error', 'message': 'Invalid status'}), 400
    
    # Get the hiring record
    hiring = WorkerHiring.find_by_id(hiring_id)
    if not hiring:
        return jsonify({'status': 'error', 'message': 'Hiring record not found'}), 404
    
    # Check permissions
    worker_profile = WorkerProfile.find_by_id(hiring['worker_profile_id'])
    if not worker_profile:
        return jsonify({'status': 'error', 'message': 'Worker profile not found'}), 404
        
    is_worker = worker_profile['user_id'] == user_id
    is_farmer = hiring['farmer_id'] == user_id
    
    if not (is_worker or is_farmer):
        return jsonify({'status': 'error', 'message': 'Not authorized to update this hiring'}), 403
    
    # Apply status update rules
    current_status = hiring['status']
    
    # Workers can only accept/reject pending requests
    if is_worker and not is_farmer:
        if current_status != 'pending' and new_status in ['accepted', 'rejected']:
            return jsonify({'status': 'error', 'message': 'Can only accept or reject pending requests'}), 400
        
        if current_status != 'accepted' and new_status == 'completed':
            return jsonify({'status': 'error', 'message': 'Only accepted hirings can be marked as completed'}), 400
            
    # Farmers can only cancel pending or accepted hirings
    if is_farmer and not is_worker:
        if new_status != 'cancelled':
            return jsonify({'status': 'error', 'message': 'Farmers can only cancel hirings'}), 400
            
        if current_status not in ['pending', 'accepted']:
            return jsonify({'status': 'error', 'message': 'Cannot cancel hiring in current state'}), 400
    
    # Update status
    success = WorkerHiring.update_status(hiring_id, new_status)
    
    if not success:
        return jsonify({'status': 'error', 'message': 'Failed to update status'}), 500
        
    updated_hiring = WorkerHiring.find_by_id(hiring_id)
    
    return jsonify({
        'status': 'success',
        'message': f'Hiring status updated to {new_status}',
        'hiring': dict(updated_hiring)
    }), 200

# Add a review for a worker
@app.route('/api/workers/<int:worker_id>/reviews', methods=['POST'])
@jwt_required()
def create_worker_review(worker_id):
    reviewer_id = get_jwt_identity()
    data = request.get_json()
    
    if not data or 'rating' not in data:
        return jsonify({'status': 'error', 'message': 'Rating not provided'}), 400
        
    rating = data['rating']
    comment = data.get('comment', '')
    
    # Validate rating
    try:
        rating = int(rating)
        if rating < 1 or rating > 5:
            return jsonify({'status': 'error', 'message': 'Rating must be between 1 and 5'}), 400
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Rating must be an integer'}), 400
    
    # Check if worker exists
    worker = WorkerProfile.find_by_id(worker_id)
    if not worker:
        return jsonify({'status': 'error', 'message': 'Worker not found'}), 404
    
    # Check if reviewer has hired this worker before
    hirings = WorkerHiring.find_by_farmer(reviewer_id)
    has_hired = False
    
    for hiring in hirings:
        if hiring['worker_profile_id'] == worker_id and hiring['status'] == 'completed':
            has_hired = True
            break
    
    if not has_hired:
        return jsonify({'status': 'error', 'message': 'You can only review workers you have hired'}), 403
    
    # Create review
    review_id = WorkerReview.create(worker_id, reviewer_id, rating, comment)
    
    if not review_id:
        return jsonify({'status': 'error', 'message': 'Failed to create review'}), 500
    
    return jsonify({
        'status': 'success',
        'message': 'Review added successfully'
    }), 201

# Gemini API setup
def setup_gemini_api():
    try:
    api_key = GEMINI_API_KEY
        print(f"Using Gemini API key: {api_key[:5]}...{api_key[-5:]}")
    genai.configure(api_key=api_key)
    
    # Configure the safety settings
    safety_settings = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    }
    
        # List available models
        models = list(genai.list_models())
        print(f"Available models: {[m.name for m in models]}")

        # Find a suitable model (gemini-1.5-pro or gemini-pro)
        model_name = None
        for m in models:
            if 'gemini-1.5-pro' in m.name:
                model_name = m.name
                break
            elif 'gemini-pro' in m.name:
                model_name = m.name

        if not model_name:
            print("No suitable Gemini model found")
            return None

        print(f"Using model: {model_name}")
    model = genai.GenerativeModel(
            model_name=model_name,
        safety_settings=safety_settings
    )
        print("Gemini API setup successful")
    return model
    except Exception as e:
        print(f"Error setting up Gemini API: {str(e)}")
        return None

gemini_model = setup_gemini_api()

# Crop prediction endpoint
@app.route('/api/predict-crop', methods=['POST'])
def predict_crop():
    try:
        data = request.json
        crop_name = data.get('crop')
        area = data.get('area')
        soil_type = data.get('soilType')
        irrigation = data.get('irrigation')
        region = data.get('region', 'Unknown')

        print(f"Received crop prediction request: {data}")
        
        if not all([crop_name, area, soil_type, irrigation]):
            return jsonify({"error": "Missing required parameters"}), 400
        
        # Check if Gemini API is available
        if gemini_model is None:
            print("Gemini API not available, using fallback response")
            # Return a fallback response with mock data
            return jsonify({
                "initialInvestment": f"{int(float(area) * 15000)}",
                "yieldPerAcre": f"{int(1500 + random.randint(-200, 200))}",
                "marketRate": f"{int(40 + random.randint(-5, 10))}",
                "expectedProfit": f"{int(float(area) * 25000)}",
                "suitabilityScore": 7,
                "challenges": [
                    "Weather unpredictability",
                    "Pest management",
                    "Water availability"
                ],
                "recommendations": [
                    "Use organic fertilizers",
                    "Implement crop rotation",
                    "Install drip irrigation",
                    "Monitor soil health regularly"
                ]
            })

        # Create prompt for Gemini
        prompt = f"""
        As an agricultural expert, analyze the farming potential for:
        
        - Crop: {crop_name}
        - Land Area: {area} acres
        - Soil Type: {soil_type}
        - Irrigation Type: {irrigation}
        - Region: {region}
        
        Please provide:
        1. Estimated initial investment (in INR)
        2. Expected yield per acre (in kg)
        3. Current market rate (in INR per kg)
        4. Expected profit (in INR)
        5. Suitability score (1-10)
        6. Key challenges
        7. Recommended practices
        
        Return your analysis in a structured JSON format only, with these keys: 
        initialInvestment, yieldPerAcre, marketRate, expectedProfit, suitabilityScore, 
        challenges (array), and recommendations (array).
        """
        
        print("Sending request to Gemini API")
        # Get response from Gemini
        response = gemini_model.generate_content(prompt)
        print(f"Received response from Gemini API: {response.text[:100]}...")
        
        # Extract JSON from response
        try:
            # Try to directly parse the response text as JSON
            result = json.loads(response.text)
        except json.JSONDecodeError:
            # If that fails, try to extract JSON from the text
            import re
            json_match = re.search(r'({[\s\S]*})', response.text)
            if json_match:
                result = json.loads(json_match.group(0))
            else:
                # Fallback to a structured response
                print("Failed to parse JSON from Gemini response, using fallback")
                result = {
                    "initialInvestment": f"{int(float(area) * 15000)}",
                    "yieldPerAcre": f"{int(1500 + random.randint(-200, 200))}",
                    "marketRate": f"{int(40 + random.randint(-5, 10))}",
                    "expectedProfit": f"{int(float(area) * 25000)}",
                    "suitabilityScore": 6,
                    "challenges": ["Weather unpredictability", "Pest management", "Water availability"],
                    "recommendations": ["Use organic fertilizers", "Implement crop rotation", "Install drip irrigation"]
                }

        print(f"Returning prediction result: {result}")
        return jsonify(result)
    
    except Exception as e:
        print(f"Error in crop prediction: {str(e)}")
        # Return a fallback response with mock data
        return jsonify({
            "initialInvestment": f"{int(float(data.get('area', 1)) * 15000)}",
            "yieldPerAcre": "1500",
            "marketRate": "40",
            "expectedProfit": f"{int(float(data.get('area', 1)) * 25000)}",
            "suitabilityScore": 5,
            "challenges": ["API error", "Data unavailable"],
            "recommendations": ["Consult local agricultural extension office"]
        })

# Admin API Routes

# Admin dashboard stats
@app.route('/api/admin/stats', methods=['GET'])
@jwt_required()
def admin_dashboard_stats():
    current_user_id = get_jwt_identity()

    # Get the user to check if admin
    user = None
    try:
        conn = sqlite3.connect(config.DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM users WHERE id = ?', (current_user_id,))
        user = cursor.fetchone()
    finally:
        conn.close()

    if not user or user['role'] != 'admin':
        return jsonify({'status': 'error', 'message': 'Admin access required'}), 403

    # Gather statistics
    try:
        conn = sqlite3.connect(config.DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # User stats
        cursor.execute('SELECT COUNT(*) as count FROM users WHERE role = "farmer"')
        farmer_count = cursor.fetchone()['count']

        cursor.execute('SELECT COUNT(*) as count FROM users WHERE role = "worker"')
        worker_count = cursor.fetchone()['count']

        # Equipment stats
        cursor.execute('SELECT COUNT(*) as count FROM equipment')
        equipment_count = cursor.fetchone()['count']

        # Booking stats
        cursor.execute('SELECT COUNT(*) as count FROM equipment_bookings')
        booking_count = cursor.fetchone()['count']

        # Hiring stats
        cursor.execute('SELECT COUNT(*) as count FROM worker_hirings')
        hiring_count = cursor.fetchone()['count']

        # Recent users
        cursor.execute('''
            SELECT id, name, role, created_at
            FROM users
            ORDER BY created_at DESC
            LIMIT 5
        ''')
        recent_users = [dict(row) for row in cursor.fetchall()]

        # Recent equipment
        cursor.execute('''
            SELECT e.id, e.name, e.price_per_day, e.created_at, u.name as owner_name
            FROM equipment e
            JOIN users u ON e.owner_id = u.id
            ORDER BY e.created_at DESC
            LIMIT 5
        ''')
        recent_equipment = [dict(row) for row in cursor.fetchall()]

        # Recent bookings
        cursor.execute('''
            SELECT b.id, b.status, b.total_price, b.created_at,
                   e.name as equipment_name, u.name as renter_name
            FROM equipment_bookings b
            JOIN equipment e ON b.equipment_id = e.id
            JOIN users u ON b.renter_id = u.id
            ORDER BY b.created_at DESC
            LIMIT 5
        ''')
        recent_bookings = [dict(row) for row in cursor.fetchall()]

        return jsonify({
            'status': 'success',
            'stats': {
                'farmers': farmer_count,
                'workers': worker_count,
                'equipment': equipment_count,
                'bookings': booking_count,
                'hirings': hiring_count
            },
            'recent_users': recent_users,
            'recent_equipment': recent_equipment,
            'recent_bookings': recent_bookings
        }), 200

    except sqlite3.Error as e:
        return jsonify({'status': 'error', 'message': f'Database error: {str(e)}'}), 500
    finally:
        conn.close()

# Get all users (admin only)
@app.route('/api/admin/users', methods=['GET'])
@jwt_required()
def get_all_users():
    current_user_id = get_jwt_identity()

    # Check if admin
    user = User.find_by_id(current_user_id)
    if not user or user['role'] != 'admin':
        return jsonify({'status': 'error', 'message': 'Admin access required'}), 403

    # Parse query parameters
    try:
        limit = int(request.args.get('limit', 20))
        offset = int(request.args.get('offset', 0))
        role = request.args.get('role', None)
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Invalid parameters'}), 400

    # Get users
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = 'SELECT id, name, phone, email, role, created_at FROM users'
    params = []

    if role:
        query += ' WHERE role = ?'
        params.append(role)

    query += ' ORDER BY created_at DESC LIMIT ? OFFSET ?'
    params.extend([limit, offset])

    try:
        cursor.execute(query, params)
        users = [dict(row) for row in cursor.fetchall()]

        # Count total users
        count_query = 'SELECT COUNT(*) as count FROM users'
        count_params = []

        if role:
            count_query += ' WHERE role = ?'
            count_params.append(role)

        cursor.execute(count_query, count_params)
        total_count = cursor.fetchone()['count']

        return jsonify({
            'status': 'success',
            'count': len(users),
            'total': total_count,
            'users': users
        }), 200
    except sqlite3.Error as e:
        return jsonify({'status': 'error', 'message': f'Database error: {str(e)}'}), 500
    finally:
        conn.close()

# Get equipment pending approval (admin only)
@app.route('/api/admin/equipment/pending', methods=['GET'])
@jwt_required()
def get_pending_equipment():
    current_user_id = get_jwt_identity()

    # Check if admin
    user = User.find_by_id(current_user_id)
    if not user or user['role'] != 'admin':
        return jsonify({'status': 'error', 'message': 'Admin access required'}), 403

    # Get pending equipment
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT e.*, u.name as owner_name
            FROM equipment e
            JOIN users u ON e.owner_id = u.id
            WHERE e.is_approved = 0
            ORDER BY e.created_at DESC
        ''')
        equipment_list = [dict(row) for row in cursor.fetchall()]

        return jsonify({
            'status': 'success',
            'count': len(equipment_list),
            'equipment': equipment_list
        }), 200
    except sqlite3.Error as e:
        return jsonify({'status': 'error', 'message': f'Database error: {str(e)}'}), 500
    finally:
        conn.close()

# Approve or reject equipment
@app.route('/api/admin/equipment/<int:equipment_id>/review', methods=['PUT'])
@jwt_required()
def review_equipment(equipment_id):
    current_user_id = get_jwt_identity()

    # Check if admin
    user = User.find_by_id(current_user_id)
    if not user or user['role'] != 'admin':
        return jsonify({'status': 'error', 'message': 'Admin access required'}), 403

    data = request.get_json()
    if not data or 'approved' not in data:
        return jsonify({'status': 'error', 'message': 'Missing required fields'}), 400

    is_approved = data['approved']
    rejection_reason = data.get('rejection_reason', '') if not is_approved else None

    # Update equipment
    conn = sqlite3.connect(config.DATABASE_PATH)
    try:
        cursor = conn.cursor()

        if is_approved:
            cursor.execute(
                'UPDATE equipment SET is_approved = 1, reviewed_at = CURRENT_TIMESTAMP WHERE id = ?',
                (equipment_id,)
            )
        else:
            cursor.execute(
                'UPDATE equipment SET is_approved = 0, rejection_reason = ?, reviewed_at = CURRENT_TIMESTAMP WHERE id = ?',
                (rejection_reason, equipment_id)
            )

        conn.commit()

        if cursor.rowcount == 0:
            return jsonify({'status': 'error', 'message': 'Equipment not found'}), 404

        return jsonify({
            'status': 'success',
            'message': 'Equipment review completed',
            'is_approved': is_approved
        }), 200
    except sqlite3.Error as e:
        return jsonify({'status': 'error', 'message': f'Database error: {str(e)}'}), 500
    finally:
        conn.close()

# Get worker profiles pending approval (admin only)
@app.route('/api/admin/workers/pending', methods=['GET'])
@jwt_required()
def get_pending_workers():
    current_user_id = get_jwt_identity()

    # Check if admin
    user = User.find_by_id(current_user_id)
    if not user or user['role'] != 'admin':
        return jsonify({'status': 'error', 'message': 'Admin access required'}), 403

    # Get pending worker profiles
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT wp.*, u.name, u.phone, u.email
            FROM worker_profiles wp
            JOIN users u ON wp.user_id = u.id
            WHERE wp.is_approved = 0
            ORDER BY wp.created_at DESC
        ''')
        workers = [dict(row) for row in cursor.fetchall()]

        return jsonify({
            'status': 'success',
            'count': len(workers),
            'workers': workers
        }), 200
    except sqlite3.Error as e:
        return jsonify({'status': 'error', 'message': f'Database error: {str(e)}'}), 500
    finally:
        conn.close()

# Approve or reject worker profile
@app.route('/api/admin/workers/<int:worker_id>/review', methods=['PUT'])
@jwt_required()
def review_worker(worker_id):
    current_user_id = get_jwt_identity()

    # Check if admin
    user = User.find_by_id(current_user_id)
    if not user or user['role'] != 'admin':
        return jsonify({'status': 'error', 'message': 'Admin access required'}), 403

    data = request.get_json()
    if not data or 'approved' not in data:
        return jsonify({'status': 'error', 'message': 'Missing required fields'}), 400

    is_approved = data['approved']
    rejection_reason = data.get('rejection_reason', '') if not is_approved else None

    # Update worker profile
    conn = sqlite3.connect(config.DATABASE_PATH)
    try:
        cursor = conn.cursor()

        if is_approved:
            cursor.execute(
                'UPDATE worker_profiles SET is_approved = 1, reviewed_at = CURRENT_TIMESTAMP WHERE id = ?',
                (worker_id,)
            )
        else:
            cursor.execute(
                'UPDATE worker_profiles SET is_approved = 0, rejection_reason = ?, reviewed_at = CURRENT_TIMESTAMP WHERE id = ?',
                (rejection_reason, worker_id)
            )

        conn.commit()

        if cursor.rowcount == 0:
            return jsonify({'status': 'error', 'message': 'Worker profile not found'}), 404

        return jsonify({
            'status': 'success',
            'message': 'Worker profile review completed',
            'is_approved': is_approved
        }), 200
    except sqlite3.Error as e:
        return jsonify({'status': 'error', 'message': f'Database error: {str(e)}'}), 500
    finally:
        conn.close()

# Get all feedback/reports
@app.route('/api/admin/feedback', methods=['GET'])
@jwt_required()
def get_all_feedback():
    current_user_id = get_jwt_identity()

    # Check if admin
    user = User.find_by_id(current_user_id)
    if not user or user['role'] != 'admin':
        return jsonify({'status': 'error', 'message': 'Admin access required'}), 403

    # Parse query parameters
    try:
        limit = int(request.args.get('limit', 20))
        offset = int(request.args.get('offset', 0))
        status = request.args.get('status', None)
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Invalid parameters'}), 400

    # Get feedback
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = '''
        SELECT f.*, u.name as reporter_name
        FROM feedback f
        JOIN users u ON f.user_id = u.id
    '''
    params = []

    if status:
        query += ' WHERE f.status = ?'
        params.append(status)

    query += ' ORDER BY f.created_at DESC LIMIT ? OFFSET ?'
    params.extend([limit, offset])

    try:
        cursor.execute(query, params)
        feedback_list = [dict(row) for row in cursor.fetchall()]

        # Count total feedback
        count_query = 'SELECT COUNT(*) as count FROM feedback'
        count_params = []

        if status:
            count_query += ' WHERE status = ?'
            count_params.append(status)

        cursor.execute(count_query, count_params)
        total_count = cursor.fetchone()['count']

        return jsonify({
            'status': 'success',
            'count': len(feedback_list),
            'total': total_count,
            'feedback': feedback_list
        }), 200
    except sqlite3.Error as e:
        return jsonify({'status': 'error', 'message': f'Database error: {str(e)}'}), 500
    finally:
        conn.close()

# Add route to update feedback status
@app.route('/api/admin/feedback/<int:feedback_id>/status', methods=['PUT'])
@jwt_required()
def update_feedback_status(feedback_id):
    current_user_id = get_jwt_identity()

    # Check if admin
    user = User.find_by_id(current_user_id)
    if not user or user['role'] != 'admin':
        return jsonify({'status': 'error', 'message': 'Admin access required'}), 403

    data = request.get_json()
    if not data or 'status' not in data:
        return jsonify({'status': 'error', 'message': 'Missing required fields'}), 400

    new_status = data['status']
    admin_response = data.get('admin_response', '')

    # Update feedback
    conn = sqlite3.connect(config.DATABASE_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE feedback SET status = ?, admin_response = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            (new_status, admin_response, feedback_id)
        )
        conn.commit()

        if cursor.rowcount == 0:
            return jsonify({'status': 'error', 'message': 'Feedback not found'}), 404

        return jsonify({
            'status': 'success',
            'message': 'Feedback status updated'
        }), 200
    except sqlite3.Error as e:
        return jsonify({'status': 'error', 'message': f'Database error: {str(e)}'}), 500
    finally:
        conn.close()

# CSRF token route
@app.route('/api/csrf-token', methods=['GET'])
@jwt_required()
def get_csrf_token():
    user_id = get_jwt_identity()
    token = secrets.token_hex(16)  # Generate a secure random token

    # Store the token with the user ID
    csrf_tokens[user_id] = token

    response = jsonify({'csrf_token': token})
    response.headers.set('X-CSRFToken', token)
    return response

# Initialize database
init_db()

if __name__ == '__main__':
    app.run(debug=True) 