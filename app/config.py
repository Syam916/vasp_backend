import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key')
    
    # Database
    DB_CONFIG = {
        "host": os.getenv('DB_HOST'),
        "user": os.getenv('DB_USER'),
        "password": os.getenv('DB_PASSWORD'),
        "database": os.getenv('DB_NAME')
    }

    # print(f"DB_HOST: {host}, DB_USER: {DB_USER}, DB_NAME: {DB_NAME}")  # Debugging line
    print(f"DB_CONFIG: {DB_CONFIG['host']}")  # Debugging line
    
    # SQLAlchemy Database URI
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@"
        f"{DB_CONFIG['host']}/{DB_CONFIG['database']}?charset=utf8mb4&local_infile=1"
    )

    print(f"Connecting to database with URI: {SQLALCHEMY_DATABASE_URI}")  # Debugging line
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }
    
    # AWS
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
    S3_BUCKET = os.getenv('S3_BUCKET', 'vasp-pdf-files')
    
    # WhatsApp
    WHATSAPP_API_URL = os.getenv('WHATSAPP_API_URL')
    WHATSAPP_ACCESS_TOKEN = os.getenv('WHATSAPP_ACCESS_TOKEN')
    WHATSAPP_TEMPLATE_NAME = os.getenv('WHATSAPP_TEMPLATE_NAME', 'otp_verification')
    
    # Upload paths
    UPLOAD_FOLDER =  'uploads'
    EXTRACTED_FOLDER =  'extracted'
    EXCEL_FILE = 'queries.xlsx'
    EXCEL_TEMPLATE= 'Excel_template'
    REFERENCE_FOLDER =  'Reference_files'
    
    # JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key')
    JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1 hour 



# try:
#     db.engine.execute("SELECT 1")  # Test query
#     print("Connected to the database successfully.")
# except Exception as e:
#     print(f"Database connection failed: {e}")