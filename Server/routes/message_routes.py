# server/routes/message_routes.py
import uuid 
from flask import Blueprint, request, jsonify # Removed current_app as it wasn't used
from database.db import PublicKey, db, EncryptedMessage, User
from flask_jwt_extended import jwt_required, get_jwt_identity 

message_bp = Blueprint('message', __name__)

@message_bp.route('/sendTo', methods=['GET'])
@jwt_required()
def get_user_list():
    """
    Retrieves a list of other users' usernames to whom the current user can send messages.
    """
    current_user_id = get_jwt_identity() # NEW: Get user ID from JWT
    current_user = User.query.get(current_user_id) # NEW: Fetch current user object

    if not current_user:
        # This case should ideally not happen if jwt_required is working, but for robustness
        return jsonify({'error': 'Authentication failed: User not found.'}), 401

    # Filter out the current user by their ID
    users = User.query.filter(User.id != current_user.id).all()

    # Still exposes all other usernames. Consider privacy implications for your application.
    user_list = [{'username': user.username} for user in users]
    return jsonify({'users': user_list}), 200


@message_bp.route('/send', methods=['POST'])
@jwt_required()
def send_message():
    """
    Sends an encrypted message from the current user to a specified recipient.
    Requires encrypted content, recipient's key UID, sender's signature, and sender's identity key UID.
    """
    sender_id_str = get_jwt_identity() # NEW: Get sender's ID string from JWT
    data = request.get_json()
    
    recipient_username = data.get('recipient_username')
    encrypted_content = data.get('encrypted_content')
    recipient_key_uid = data.get('recipient_key_uid')
    sender_signature = data.get('sender_signature')
    sender_public_identity_key_uid = data.get('sender_public_identity_key_uid')

    sender = User.query.get(sender_id_str) # NEW: Fetch sender by ID
    recipient = User.query.filter_by(username=recipient_username).first()
    
    # Basic validations
    if not all([recipient_username, encrypted_content, recipient_key_uid, sender_signature, sender_public_identity_key_uid]):
        return jsonify({
            'error': 'Missing required fields: recipient_username, encrypted_content, '
                     'recipient_key_uid, sender_signature, sender_public_identity_key_uid'
        }), 400

    if not isinstance(encrypted_content, str) or not encrypted_content.strip():
        return jsonify({'error': 'Encrypted content cannot be empty'}), 400

    if len(encrypted_content) > 50000: # Adjusted max length for base64 encoded encrypted data (e.g., up to 50KB)
        return jsonify({'error': 'Encrypted content too long'}), 413

    # Safety checks
    if not sender: # This should generally not happen if JWT is valid, but good for robustness
        return jsonify({'error': 'Sender user not found.'}), 401 # Use 401 as it implies token issue

    if not recipient:
        return jsonify({'error': 'Recipient user does not exist'}), 404
    
    if sender.id == recipient.id: # Compare IDs directly now
        return jsonify({'error': 'Cannot send message to yourself'}), 400


    # --- CRITICAL FIX & ENHANCEMENT: Validate recipient_key_uid rigorously ---
    # Query for the key using recipient.id (the integer PK)
    key_entry = PublicKey.query.filter_by(
        key_uid=recipient_key_uid, 
        user_id=recipient.id 
    ).first()

    if not key_entry:
        return jsonify({'error': 'Invalid or mismatched recipient_key_uid for recipient'}), 400
    
    # Validate the key type and its active status
    if key_entry.key_type == 'ephemeral':
        # For ephemeral keys, ensure the JTI matches the recipient's current active session JTI.
        # This relies on recipient.current_jti being accurately updated on login/logout.
        if key_entry.jti is None or key_entry.jti != recipient.current_jti:
            return jsonify({'error': 'Ephemeral key is not active for the recipient\'s current session.'}), 400
    elif key_entry.key_type == 'identity':
        # For identity keys, you might add checks here if a user can have multiple
        # identity certificates and only one is considered 'current' or 'active'.
        pass
    else:
        return jsonify({'error': 'Unsupported key type associated with recipient_key_uid.'}), 400

    # Generate message_uid as a UUID (server-side generation)
    message_uid = str(uuid.uuid4()) 

    # Use sender.id and recipient.id for foreign key assignments
    message = EncryptedMessage(
        message_uid=message_uid,
        sender_id=sender.id,         
        recipient_id=recipient.id,    
        encrypted_content=encrypted_content, 
        recipient_key_uid=recipient_key_uid, 
        sender_signature=sender_signature,   
        sender_public_identity_key_uid=sender_public_identity_key_uid 
    )

    db.session.add(message)
    db.session.commit()

    return jsonify({'message': 'Message sent successfully', 'message_uid': message_uid}), 200


@message_bp.route('/inbox', methods=['GET'])
@jwt_required()
def get_messages():
    """
    Retrieves encrypted messages for the current user.
    Optionally filters for unopened messages.
    Marks retrieved messages as 'opened'.
    """
    current_user_id = get_jwt_identity() # NEW: Get user ID from JWT
    current_user = User.query.get(current_user_id) # NEW: Fetch current user object

    if not current_user:
        return jsonify({'error': 'Authentication failed: User not found.'}), 401

    unopened_only = request.args.get('unopened', 'false').lower() == 'true'
    
    query = EncryptedMessage.query.filter_by(recipient_id=current_user.id) 
    if unopened_only:
        query = query.filter_by(is_opened=False)

    messages = query.order_by(EncryptedMessage.timestamp.desc()).all()

    messages_to_return = []
    messages_to_mark_as_opened = [] 

    for msg in messages:
        messages_to_return.append({
            'message_uid': msg.message_uid,
            'sender_username': msg.sender.username, 
            'encrypted_content': msg.encrypted_content, 
            'recipient_key_uid': msg.recipient_key_uid, 
            'sender_signature': msg.sender_signature, 
            'sender_public_identity_key_uid': msg.sender_public_identity_key_uid, 
            'timestamp': msg.timestamp.isoformat(),
            'is_opened': msg.is_opened 
        })
        if not msg.is_opened:
            messages_to_mark_as_opened.append(msg)
    
    for msg in messages_to_mark_as_opened:
        msg.is_opened = True
    db.session.commit() 

    return jsonify(messages_to_return), 200


@message_bp.route('/getMessageById', methods=['POST'])
@jwt_required()
def get_message_by_uid():
    """
    Retrieves a single encrypted message for the current user by its message_uid.
    Marks the retrieved message as 'opened'.
    """
    data = request.get_json()
    message_uid = data.get('message_uid') if data else None

    if not message_uid:
        return jsonify({'error': 'Missing message_uid parameter'}), 400

    current_user_id = get_jwt_identity() # NEW: Get user ID from JWT
    current_user = User.query.get(current_user_id) # NEW: Fetch current user object

    if not current_user:
        return jsonify({'error': 'Authentication failed: User not found.'}), 401

    msg = EncryptedMessage.query.filter_by(
        recipient_id=current_user.id, 
        message_uid=message_uid
    ).first()

    if not msg:
        return jsonify({'error': 'Message not found or not accessible'}), 404

    if not msg.is_opened:
        msg.is_opened = True
    db.session.commit()

    return jsonify({
        'message_uid': msg.message_uid,
        'sender_username': msg.sender.username, 
        'encrypted_content': msg.encrypted_content, 
        'recipient_key_uid': msg.recipient_key_uid, 
        'sender_signature': msg.sender_signature, 
        'sender_public_identity_key_uid': msg.sender_public_identity_key_uid, 
        'timestamp': msg.timestamp.isoformat(),
        'is_opened': msg.is_opened 
    }), 200


@message_bp.route('/inbox/deleteMessage', methods=['POST'])
@jwt_required()
def delete_message_by_uid():
    """
    Deletes an encrypted message for the current user by its message_uid.
    """
    data = request.get_json()
    message_uid = data.get('message_uid') if data else None

    if not message_uid:
        return jsonify({'error': 'Missing message_uid parameter'}), 400

    current_user_id = get_jwt_identity() # NEW: Get user ID from JWT
    current_user = User.query.get(current_user_id) # NEW: Fetch current user object

    if not current_user:
        return jsonify({'error': 'Authentication failed: User not found.'}), 401

    message = EncryptedMessage.query.filter_by(
        recipient_id=current_user.id, 
        message_uid=message_uid
    ).first()

    if not message:
        return jsonify({'error': 'Message not found or not accessible'}), 404

    db.session.delete(message)
    db.session.commit()

    return jsonify({'message': 'Message deleted successfully'}), 200