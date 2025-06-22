# server/routes/key_routes.py
from flask import Blueprint, request, jsonify
from database.db import PublicKey, db, User
from flask_jwt_extended import jwt_required, get_jwt_identity

key_bp = Blueprint('keys', __name__)

@key_bp.route('/addKey', methods=['POST'])
@jwt_required()
def upload_key():
    current_user = get_jwt_identity()
    user = User.query.filter_by(username=current_user).first()

    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json()
    public_key = data.get('public_key')
    if not public_key:
        return jsonify({'error': 'Public key is required'}), 400

    # Create key entry without key_uid first
    new_key = PublicKey(user_id=user.id, public_key=public_key)
    db.session.add(new_key)
    db.session.flush()  # Get new_key.id before commit

    # Assign key_uid as "userID-keyID"
    new_key.key_uid = f"{user.id}-{new_key.id}"
    db.session.commit()

    return jsonify({'message': 'Public key uploaded successfully', 'key_uid': new_key.key_uid}), 201



@key_bp.route('/getAllKeys', methods=['GET'])
@jwt_required()
def get_keys():
    current_user = get_jwt_identity()

    user = User.query.filter_by(username=current_user).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    keys = PublicKey.query.filter_by(user_id=user.id).order_by(PublicKey.timestamp.desc()).all()

    key_list = [{
        # 'key_id': key.id,
        'key_uid': key.key_uid,
        'public_key': key.public_key,
        'timestamp': key.timestamp.isoformat()
    } for key in keys]

    return jsonify({
        'username': user.username,
        # 'user_id': user.id,
        'public_keys': key_list
    }), 200


@key_bp.route('/fetchPublicKey', methods=['POST'])
@jwt_required()
def get_recipient_public_key():
    data = request.get_json()
    recipient_username = data.get('username')

    if not recipient_username:
        return jsonify({'error': 'Recipient username required'}), 400

    recipient = User.query.filter_by(username=recipient_username).first()
    if not recipient:
        return jsonify({'error': 'Recipient not found'}), 404

    latest_key = PublicKey.query.filter_by(user_id=recipient.id)\
                                .order_by(PublicKey.timestamp.desc()).first()

    if not latest_key:
        return jsonify({'error': 'No public key found for recipient'}), 404

    return jsonify({
        'username': recipient.username,
        # 'user_id': recipient.id,
        'key_uid': latest_key.key_uid,
        'public_key': latest_key.public_key
    }), 200


#Old key retrieval

# @key_bp.route('/<username>', methods=['GET'])
# @jwt_required()
# def get_key(username):
#     current_user = get_jwt_identity()
#     if username != current_user:
#         return jsonify({'error': 'Unauthorized to view other user’s keys'}), 403

#     user = User.query.filter_by(username=username).first()
#     if not user:
#         return jsonify({'error': 'User not found'}), 404

#     return jsonify({
#         'username': user.username,
#         'public_key': user.public_key,
#         'cert_uploaded': user.cert_uploaded
#     }), 200
