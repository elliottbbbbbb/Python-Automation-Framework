"""Flask license validation API server."""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
        'DATABASE_URL',
        'sqlite:///licenses.db'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

    # Initialize extensions
    db.init_app(app)
    limiter.init_app(app)

    # Register blueprints
    from app.routes import api_bp
    app.register_blueprint(api_bp, url_prefix='/api/v1')

    # Create tables
    with app.app_context():
        db.create_all()

    return app