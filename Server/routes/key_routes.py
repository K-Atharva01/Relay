# server/routes/key_routes.py
from flask import Blueprint, request, jsonify
from database.db import db, User
from flask_jwt_extended import jwt_required, get_jwt_identity

key_bp = Blueprint('keys', __name__)

@key_bp.route('/register', methods=['POST'])
@jwt_required()
def register_key():
    current_user = get_jwt_identity()
    data = request.json
    username = data.get('username')
    public_key = data.get('public_key')

    if not username or not public_key:
        return jsonify({'error': 'Username and public_key are required'}), 400

    if current_user != username:
        return jsonify({'error': 'You can only register your own key.'}), 403

    user = User.query.filter_by(username=username).first()
    if user:
        user.public_key = public_key
    else:
        user = User(username=username, public_key=public_key)
        db.session.add(user)

    db.session.commit()
    return jsonify({'message': 'Public key registered'}), 200


@key_bp.route('/<username>', methods=['GET'])
@jwt_required()
def get_key(username):
    current_user = get_jwt_identity()
    if username != current_user:
        return jsonify({'error': 'Unauthorized to view other user’s keys'}), 403

    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({
        'username': user.username,
        'public_key': user.public_key,
        'cert_uploaded': user.cert_uploaded
    }), 200
