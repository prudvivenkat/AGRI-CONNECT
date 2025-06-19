import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Secret key for JWT
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# JWT Settings
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', SECRET_KEY)
JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

# Database
DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database', 'agri_connect.db')

# OTP settings
OTP_EXPIRY_SECONDS = 300  # 5 minutes

# Email settings
EMAIL_SENDER = os.environ.get('EMAIL_ID', '')  # Get email from environment variable
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', '')  # Use app password for Gmail
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587

# Gemini API
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', 'your-default-key-for-dev-only')