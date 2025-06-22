# server/routes/message_routes.py
from flask import Blueprint, request, jsonify
from database.db import db, EncryptedMessage, User
from flask_jwt_extended import jwt_required, get_jwt_identity


message_bp = Blueprint('messages', __name__)

@message_bp.route('/send', methods=['POST'])
@jwt_required()
def send_message():
    sender = get_jwt_identity()
    data = request.get_json()
    recipient = data.get('recipient')
    encrypted_message = data.get('message')

    if not recipient or not encrypted_message:
        return jsonify({'error': 'Recipient and message are required'}), 400

    # 1. Check if recipient exists
    recipient_user = User.query.filter_by(username=recipient).first()
    if not recipient_user:
        return jsonify({'error': 'Recipient user does not exist'}), 404

    # 2. Prevent empty messages
    if len(encrypted_message.strip()) == 0:
        return jsonify({'error': 'Message cannot be empty'}), 400

    # 3. Optional: prevent sending message to self
    if sender == recipient:
        return jsonify({'error': 'Cannot send message to yourself'}), 400

    # 4. Optional: prevent very large messages
    if len(encrypted_message) > 5000:  # adjust limit as needed
        return jsonify({'error': 'Message too long'}), 413

    # Save to DB
    message = EncryptedMessage(sender=sender, recipient=recipient, encrypted_message=encrypted_message)
    db.session.add(message)
    db.session.commit()

    return jsonify({'message': 'Message sent successfully'}), 200


@message_bp.route('/inbox', methods=['GET'])
@jwt_required()
def get_messages():
    current_user = get_jwt_identity()
    messages = EncryptedMessage.query.filter_by(recipient=current_user).all()

    return jsonify([
        {'sender': msg.sender, 'message': msg.encrypted_message}
        for msg in messages
    ]), 200
