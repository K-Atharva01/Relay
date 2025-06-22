# server/__init__.py or app.py
import os
from datetime import timedelta
from flask import Flask, jsonify
from flask_cors import CORS # Import CORS
from flask_jwt_extended import JWTManager
from werkzeug.exceptions import HTTPException # Correct import for HTTP exceptions

# --- Import database and blueprints ---
# Assuming these are in the 'database' and 'routes' subdirectories within 'server'
from database.db import db, RevokedToken # RevokedToken directly imported for blocklist loader
from routes.key_routes import key_bp
from routes.message_routes import message_bp
from routes.auth_routes import auth_bp 
# from flask_jwt_extended import create_access_token # Not used here, can remove if not needed


def create_app():
    app = Flask(__name__)

    # --- Configs ---
    # Using environment variables for production readiness
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///secure_exchange.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # --- CRITICAL SECURITY: JWT Secret Key from Environment Variable ---
    # In production, ensure JWT_SECRET_KEY is set in your environment
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'afa7586ad362bcad4509f70402bf766dd8999266ad29fa03084eac8d7b24ba6f') 
    
    # Use a strong, random, and secret key. Generate one with `os.urandom(32).hex()`
    # For production, NEVER hardcode this. Use a proper environment variable.
    if app.config['JWT_SECRET_KEY'] == 'afa7586ad362bcad4509f70402bf766dd8999266ad29fa03084eac8d7b24ba6f':
        app.logger.warning("JWT_SECRET_KEY is using a default/hardcoded value. "
                           "Set it via environment variable for production.")


    app.config['JWT_ALGORITHM'] = os.getenv('JWT_ALGORITHM', 'HS256')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES_HOURS', 8)))
    
    # Enable JWT blacklisting for token revocation
    app.config['JWT_BLACKLIST_ENABLED'] = True
    app.config['JWT_BLACKLIST_TOKEN_CHECKS'] = ['access']
    
    # Disable propagation of exceptions from JWT, so our custom error handlers can catch them
    app.config['PROPAGATE_EXCEPTIONS'] = False

    # --- CORS Configuration ---
    # For development, you might allow all origins.
    # For production, specify your exact frontend origin(s) for security.
    # e.g., CORS(app, resources={r"/*": {"origins": ["https://yourfrontend.com", "http://localhost:3000"]}})
    CORS(app) 

    # --- Initialize Extensions ---
    jwt = JWTManager(app)
    db.init_app(app)

    # --- JWT Token Blocklist Loader ---
    # This function is called by Flask-JWT-Extended to check if a token is revoked.
    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        # RevokedToken is already imported from database.db
        jti = jwt_payload["jti"]
        return RevokedToken.query.filter_by(jti=jti).first() is not None

    # --- Global Error Handler ---
    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        """Handle werkzeug HTTP exceptions (e.g., 404, 401, 400)."""
        response = e.get_response()
        response.data = jsonify({
            "code": e.code,
            "name": e.name,
            "description": e.description
        }).get_data()
        response.content_type = "application/json"
        return response

    @app.errorhandler(Exception)
    def handle_generic_exception(e):
        """Handle any unexpected internal server errors."""
        app.logger.error(f"An unhandled exception occurred: {e}", exc_info=True) # Log the full traceback

        response_data = {
            "error": "Internal Server Error",
            "description": "An unexpected error occurred. Please try again later."
        }
        
        # --- SECURITY: Only expose detailed error in debug mode ---
        if app.debug:
            response_data["details"] = str(e)
            
        return jsonify(response_data), 500

    # --- Register Blueprints ---
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(key_bp, url_prefix='/keys')
    app.register_blueprint(message_bp, url_prefix='/message')

    # --- Database Initialization (within app context) ---
    with app.app_context():
        db.create_all() # Creates tables based on your db.Model definitions

    return app

if __name__ == '__main__':
    app = create_app()
    # Ensure debug mode is False in production environments
    app.run(host='0.0.0.0', port=5000, debug=True)