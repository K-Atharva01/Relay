# server/routes/message_routes.py
import uuid # Import uuid for generating message_uid if not client-provided
from flask import Blueprint, request, jsonify, current_app
from database.db import PublicKey, db, EncryptedMessage, User
from flask_jwt_extended import jwt_required, get_jwt_identity # current_app might not be strictly needed here, but often useful

message_bp = Blueprint('message', __name__)

@message_bp.route('/sendTo', methods=['GET'])
@jwt_required()
def get_user_list():
    """
    Retrieves a list of other users' usernames to whom the current user can send messages.
    """
    current_username = get_jwt_identity()
    # This exposes all usernames. Consider if this level of user enumeration is acceptable
    # for your security model, or if you need to filter/restrict it further.
    users = User.query.filter(User.username != current_username).all()

    user_list = [{'username': user.username} for user in users]
    return jsonify({'users': user_list}), 200


@message_bp.route('/send', methods=['POST'])
@jwt_required()
def send_message():
    """
    Sends an encrypted message from the current user to a specified recipient.
    Requires encrypted content, recipient's key UID, sender's signature, and sender's identity key UID.
    """
    sender_username = get_jwt_identity()
    data = request.get_json()
    
    # --- ENHANCED: Expecting all required E2EE fields from client ---
    recipient_username = data.get('recipient_username')
    encrypted_content = data.get('encrypted_content')
    recipient_key_uid = data.get('recipient_key_uid')
    sender_signature = data.get('sender_signature')
    sender_public_identity_key_uid = data.get('sender_public_identity_key_uid')

    sender = User.query.filter_by(username=sender_username).first()
    recipient = User.query.filter_by(username=recipient_username).first()
    
    # Basic validations
    if not all([recipient_username, encrypted_content, recipient_key_uid, sender_signature, sender_public_identity_key_uid]):
        return jsonify({
            'error': 'Missing required fields: recipient_username, encrypted_content, '
                     'recipient_key_uid, sender_signature, sender_public_identity_key_uid'
        }), 400

    if not isinstance(encrypted_content, str) or not encrypted_content.strip():
        return jsonify({'error': 'Encrypted content cannot be empty'}), 400

    # Adjusted max length for base64 encoded encrypted data (e.g., up to 50KB)
    if len(encrypted_content) > 50000:
        return jsonify({'error': 'Encrypted content too long'}), 413

    if sender_username == recipient_username:
        return jsonify({'error': 'Cannot send message to yourself'}), 400

    if not recipient:
        return jsonify({'error': 'Recipient user does not exist'}), 404
    
    if not sender: # This should generally not happen if JWT is valid, but good for robustness
        return jsonify({'error': 'Sender user does not exist'}), 404

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
        # This assumes recipient.current_jti is accurately updated on login/logout.
        # A more robust check might involve querying the RevokedToken table with key_entry.jti
        # to ensure it's not revoked, if JTI is shared for both access tokens and ephemeral keys.
        if key_entry.jti is None or key_entry.jti != recipient.current_jti:
            return jsonify({'error': 'Ephemeral key is not active for the recipient\'s current session.'}), 400
    elif key_entry.key_type == 'identity':
        # For identity keys, you might add checks here if a user can have multiple
        # identity certificates and only one is considered 'current' or 'active'.
        # For now, we assume any valid identity key_uid associated with the user is acceptable.
        pass
    else:
        return jsonify({'error': 'Unsupported key type associated with recipient_key_uid.'}), 400

    # --- CRITICAL FIX: Generate message_uid as a UUID ---
    # The client could also generate this, and send it in the payload.
    # For now, the server generates it and returns it.
    message_uid = str(uuid.uuid4()) 

    # --- CRITICAL FIX: Use sender.id and recipient.id for foreign key assignments ---
    # --- ENHANCED: Pass all new required fields to EncryptedMessage constructor ---
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
    # Removed direct manipulation of User.message_counter and current_messages.
    # These counters are less critical and can be derived via queries if needed,
    # or updated via a more robust, atomic mechanism if concurrency is high.
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
    current_username = get_jwt_identity()
    current_user = User.query.filter_by(username=current_username).first()

    if not current_user:
        return jsonify({'error': 'User not found'}), 404

    # Optional: Allow client to request only unopened messages
    unopened_only = request.args.get('unopened', 'false').lower() == 'true'
    
    query = EncryptedMessage.query.filter_by(recipient_id=current_user.id) # CORRECTED: Use current_user.id
    if unopened_only:
        query = query.filter_by(is_opened=False)

    messages = query.order_by(EncryptedMessage.timestamp.desc()).all()

    messages_to_return = []
    messages_to_mark_as_opened = [] # Collect messages to update their status

    for msg in messages:
        messages_to_return.append({
            'message_uid': msg.message_uid,
            'sender_username': msg.sender.username, # Provide sender's username
            'encrypted_content': msg.encrypted_content, 
            'recipient_key_uid': msg.recipient_key_uid, 
            'sender_signature': msg.sender_signature, # NEW: Essential for client verification
            'sender_public_identity_key_uid': msg.sender_public_identity_key_uid, # NEW: Essential for client verification
            'timestamp': msg.timestamp.isoformat(),
            'is_opened': msg.is_opened # Include status in response
        })
        # If the message hasn't been marked as opened yet, add it to the list for update
        if not msg.is_opened:
            messages_to_mark_as_opened.append(msg)
    
    # --- ENHANCED: Mark messages as opened after retrieval ---
    for msg in messages_to_mark_as_opened:
        msg.is_opened = True
    db.session.commit() # Commit changes to mark them as opened

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

    current_username = get_jwt_identity()
    current_user = User.query.filter_by(username=current_username).first()

    if not current_user:
        return jsonify({'error': 'User not found'}), 404

    msg = EncryptedMessage.query.filter_by(
        recipient_id=current_user.id, # CORRECTED: Use current_user.id
        message_uid=message_uid
    ).first()

    if not msg:
        # Avoid distinguishing between 'not found' and 'not yours' for security
        return jsonify({'error': 'Message not found or not accessible'}), 404

    # --- ENHANCED: Mark message as opened ---
    if not msg.is_opened:
        msg.is_opened = True
        db.session.commit()

    return jsonify({
        'message_uid': msg.message_uid,
        'sender_username': msg.sender.username, # Provide sender's username
        'encrypted_content': msg.encrypted_content, 
        'recipient_key_uid': msg.recipient_key_uid, 
        'sender_signature': msg.sender_signature, # NEW
        'sender_public_identity_key_uid': msg.sender_public_identity_key_uid, # NEW
        'timestamp': msg.timestamp.isoformat(),
        'is_opened': msg.is_opened # Include status
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

    current_username = get_jwt_identity()
    current_user = User.query.filter_by(username=current_username).first()

    if not current_user:
        return jsonify({'error': 'User not found'}), 404

    message = EncryptedMessage.query.filter_by(
        recipient_id=current_user.id, # CORRECTED: Use current_user.id
        message_uid=message_uid
    ).first()

    if not message:
        # Avoid distinguishing for security reasons
        return jsonify({'error': 'Message not found or not accessible'}), 404

    db.session.delete(message)
    db.session.commit()

    return jsonify({'message': 'Message deleted successfully'}), 200