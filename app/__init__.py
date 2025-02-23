from flask import Flask
from app.config import Config
from app.extensions import db, jwt, cors
import os
from flask_cors import CORS
from app.routes.complaint import complaint

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)
    cors.init_app(app)

    # Create required directories
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['EXTRACTED_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(app.config['REFERENCE_FOLDER'], 'Excel_template'), exist_ok=True)

    # Register blueprints
    from app.routes.auth import auth
    from app.routes.document import doc
    app.register_blueprint(auth, url_prefix='/api/auth')
    app.register_blueprint(doc, url_prefix='/api/document')
    app.register_blueprint(complaint, url_prefix='/api/complaint')

    return app 