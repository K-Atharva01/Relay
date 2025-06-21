# server/routes/message_routes.py
from flask import Blueprint, request, jsonify
from database.db import db, EncryptedMessage

message_bp = Blueprint('messages', __name__)

@message_bp.route('/send', methods=['POST'])
def send_message():
    data = request.json
    sender = data.get('sender')
    receiver = data.get('receiver')
    message = data.get('message')

    if not sender or not receiver or not message:
        return jsonify({'error': 'Missing fields'}), 400

    msg = EncryptedMessage(sender=sender, receiver=receiver, message=message)
    db.session.add(msg)
    db.session.commit()
    return jsonify({'message': 'Message sent'}), 200

@message_bp.route('/inbox/<username>', methods=['GET'])
def inbox(username):
    messages = EncryptedMessage.query.filter_by(receiver=username).all()
    return jsonify([
        {
            'id': m.id,
            'from': m.sender,
            'message': m.message,
            'timestamp': m.timestamp
        } for m in messages
    ])
