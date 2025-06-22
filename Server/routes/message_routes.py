# server/routes/message_routes.py
from flask import Blueprint, request, jsonify
from database.db import PublicKey, db, EncryptedMessage, User
from flask_jwt_extended import jwt_required, get_jwt_identity


message_bp = Blueprint('message', __name__)

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
    sender_username = get_jwt_identity()
    data = request.get_json()
    recipient_username = data.get('recipient')
    encrypted_message = data.get('message')
    key_uid = data.get('key_uid')
    sender = User.query.filter_by(username=sender_username).first()
    recipient = User.query.filter_by(username=recipient_username).first()
    
    # Basic validations
    if not recipient_username or not encrypted_message or not key_uid:
        return jsonify({'error': 'Recipient, message, and key_uid are required'}), 400

    if len(encrypted_message.strip()) == 0:
        return jsonify({'error': 'Message cannot be empty'}), 400

    if len(encrypted_message) > 5000:
        return jsonify({'error': 'Message too long'}), 413

    if sender_username == recipient_username:
        return jsonify({'error': 'Cannot send message to yourself'}), 400

    if not recipient:
        return jsonify({'error': 'Recipient user does not exist'}), 404

    # Validate public key UID
    key_entry = PublicKey.query.filter_by(key_uid=key_uid, user_id=recipient.unique_id).first()
    if not key_entry:
        return jsonify({'error': 'Invalid or mismatched key_uid for recipient'}), 400

    # Generate per-recipient message_uid
    message_uid = recipient.message_counter
    recipient.message_counter += 1

    recipient.current_messages += 1


    # Create and store message
    message = EncryptedMessage(
        message_uid=str(message_uid),
        sender_id=sender.unique_id,
        recipient_id=recipient.unique_id,
        encrypted_message=encrypted_message,
        key_uid=key_uid
    )

    db.session.add(message)
    db.session.commit()

    return jsonify({'message': 'Message sent successfully', 'message_uid': message_uid}), 200



@message_bp.route('/inbox', methods=['GET'])
@jwt_required()
def get_messages():
    current_username = get_jwt_identity()
    current_user = User.query.filter_by(username=current_username).first()

    if not current_user:
        return jsonify({'error': 'User not found'}), 404

    messages = EncryptedMessage.query.filter_by(recipient_id=current_user.unique_id)\
                                     .order_by(EncryptedMessage.timestamp.desc()).all()

    return jsonify([
        {
            'message_uid': msg.message_uid,
            'sender': msg.sender.username,
            'message': msg.encrypted_message,
            'key_uid': msg.key_uid,
            'timestamp': msg.timestamp.isoformat()
        }
        for msg in messages
    ]), 200


@message_bp.route('/getMessageById', methods=['POST'])
@jwt_required()
def get_message_by_uid():
    data = request.get_json()
    message_uid = data.get('message_uid') if data else None

    if not message_uid:
        return jsonify({'error': 'Missing message_uid parameter'}), 400

    current_username = get_jwt_identity()
    current_user = User.query.filter_by(username=current_username).first()

    if not current_user:
        return jsonify({'error': 'User not found'}), 404

    msg = EncryptedMessage.query.filter_by(
        recipient_id=current_user.unique_id,
        message_uid=message_uid
    ).first()

    if not msg:
        return jsonify({'error': 'Message not found'}), 404

    return jsonify({
        'message_uid': msg.message_uid,
        'sender': msg.sender.username,
        'message': msg.encrypted_message,
        'key_uid': msg.key_uid,
        'timestamp': msg.timestamp.isoformat()
    }), 200



@message_bp.route('inbox/deleteMessage', methods=['POST'])
@jwt_required()
def delete_message_by_uid():
    data = request.get_json()
    message_uid = data.get('message_uid') if data else None

    if not message_uid:
        return jsonify({'error': 'Missing message_uid parameter'}), 400

    current_username = get_jwt_identity()
    current_user = User.query.filter_by(username=current_username).first()

    if not current_user:
        return jsonify({'error': 'User not found'}), 404

    message = EncryptedMessage.query.filter_by(
        recipient_id=current_user.unique_id,
        message_uid=message_uid
    ).first()

    if not message:
        return jsonify({'error': 'Message not found'}), 404

    db.session.delete(message)
    current_user.current_messages = max(current_user.current_messages - 1, 0)
    db.session.commit()

    return jsonify({'message': 'Message deleted successfully'}), 200


