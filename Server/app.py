# server/app.py
from flask import Flask
from flask_cors import CORS
from database.db import db
from routes.key_routes import key_bp
from routes.message_routes import message_bp

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///secure_exchange.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Register blueprints
app.register_blueprint(key_bp, url_prefix='/keys')
app.register_blueprint(message_bp, url_prefix='/messages')

# Initialize DB tables
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
