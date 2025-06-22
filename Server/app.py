from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager ,create_access_token
from database.db import db
from routes.key_routes import key_bp
from routes.message_routes import message_bp
from routes.auth_routes import auth_bp  # We’ll create this file
from datetime import timedelta


app = Flask(__name__)
# CORS(app)

# Configs
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///secure_exchange.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = "afa7586ad362bcad4509f70402bf766dd8999267ad29fa03084eac8d7b24ba6f"  # Replace with a secure random string!
app.config['JWT_ALGORITHM'] = "HS256"
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=8)
app.config['JWT_BLACKLIST_ENABLED'] = True
app.config['JWT_BLACKLIST_TOKEN_CHECKS'] = ['access']


# import os

# app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'OvquaoOELLeW84nObPZ1WzXUB5xZF/zaeCq2WJgMHKbmWTzz9vo5hWhECpJb5D9wNKtTUCT/FpCY9O43OfAXFA=')
# app.config['JWT_ALGORITHM'] = os.getenv('JWT_ALGORITHM', 'HS256')


jwt = JWTManager(app)
db.init_app(app)

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(key_bp, url_prefix='/keys')
app.register_blueprint(message_bp, url_prefix='/messages')

@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    from database.db import RevokedToken
    return RevokedToken.query.filter_by(jti=jwt_payload["jti"]).first() is not None


# Create DB tables
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)


