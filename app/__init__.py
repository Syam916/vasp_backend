from flask import Flask
from app.config import Config
from app.extensions import db, jwt
from flask_cors import CORS
import os

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

    # Configure CORS properly
    CORS(app, 
         resources={r"/api/*": {
             "origins": ["http://localhost:3000"],
             "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
             "allow_headers": ["Content-Type", "Authorization", "Accept"],
             "supports_credentials": True,
             "expose_headers": ["Content-Type", "Authorization"],
             "max_age": 600
         }},
         supports_credentials=True
    )

    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)

    # Create required directories
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['EXTRACTED_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(app.config['REFERENCE_FOLDER'], 'Excel_template'), exist_ok=True)

    # Register blueprints
    from app.routes.auth import auth
    from app.routes.document import doc
    from app.routes.complaint import complaint
    
    app.register_blueprint(auth, url_prefix='/api/auth')
    app.register_blueprint(doc, url_prefix='/api/document')
    app.register_blueprint(complaint, url_prefix='/api/complaint')

    return app 