# server/routes/message_routes.py
from flask import Blueprint, request, jsonify
from database.db import PublicKey, db, EncryptedMessage, User
from flask_jwt_extended import jwt_required, get_jwt_identity


message_bp = Blueprint('messages', __name__)

@message_bp.route('/sendTo', methods=['GET'])
@jwt_required()
def get_user_list():
    current_user = get_jwt_identity()
    users = User.query.filter(User.username != current_user).all()

    user_list = [{'username': user.username} for user in users]
    return jsonify({'users': user_list}), 200


@message_bp.route('/send', methods=['POST'])
@jwt_required()
def send_message():
    sender = get_jwt_identity()
    data = request.get_json()
    recipient = data.get('recipient')
    encrypted_message = data.get('message')

    if not recipient or not encrypted_message:
        return jsonify({'error': 'Recipient and message are required'}), 400

    recipient_user = User.query.filter_by(username=recipient).first()
    if not recipient_user:
        return jsonify({'error': 'Recipient user does not exist'}), 404

    if len(encrypted_message.strip()) == 0:
        return jsonify({'error': 'Message cannot be empty'}), 400

    if sender == recipient:
        return jsonify({'error': 'Cannot send message to yourself'}), 400

    if len(encrypted_message) > 5000:
        return jsonify({'error': 'Message too long'}), 413

    latest_key = PublicKey.query.filter_by(user_id=recipient_user.id)\
                                .order_by(PublicKey.timestamp.desc()).first()

    if not latest_key:
        return jsonify({'error': 'Recipient has no public key'}), 404

    message = EncryptedMessage(
        sender=sender,
        recipient=recipient,
        encrypted_message=encrypted_message,
        key_uid=latest_key.key_uid 
    )

    db.session.add(message)
    db.session.commit()

    return jsonify({'message': 'Message sent successfully', 'key_uid': latest_key.key_uid}), 200

@message_bp.route('/send', methods=['POST'])
@jwt_required()
def send_message():
    sender = get_jwt_identity()
    data = request.get_json()

    recipient = data.get('recipient') 
    encrypted_message = data.get('message')
    key_uid = data.get('key_uid')  

    if not recipient or not encrypted_message or not key_uid:
        return jsonify({'error': 'Recipient, message, and key_uid are required'}), 400

    if len(encrypted_message.strip()) == 0:
        return jsonify({'error': 'Message cannot be empty'}), 400

    if len(encrypted_message) > 5000:
        return jsonify({'error': 'Message too long'}), 413

    if sender == recipient:
        return jsonify({'error': 'Cannot send message to yourself'}), 400

    recipient_user = User.query.filter_by(username=recipient).first()
    if not recipient_user:
        return jsonify({'error': 'Recipient user does not exist'}), 404

    key_entry = PublicKey.query.filter_by(key_uid=key_uid, user_id=recipient_user.id).first()
    if not key_entry:
        return jsonify({'error': 'Invalid or mismatched key_uid for recipient'}), 400

    message = EncryptedMessage(
        sender=sender,
        recipient=recipient,
        encrypted_message=encrypted_message,
        key_uid=key_uid
    )

    db.session.add(message)
    db.session.commit()

    return jsonify({'message': 'Message sent successfully'}), 200



@message_bp.route('/inbox', methods=['GET'])
@jwt_required()
def get_messages():
    current_user = get_jwt_identity()
    messages = EncryptedMessage.query.filter_by(recipient=current_user)\
                                     .order_by(EncryptedMessage.timestamp.desc()).all()

    return jsonify([
        {
            'sender': msg.sender,
            'message': msg.encrypted_message,
            'key_uid': msg.key_uid,
            'timestamp': msg.timestamp.isoformat()
        }
        for msg in messages
    ]), 200


