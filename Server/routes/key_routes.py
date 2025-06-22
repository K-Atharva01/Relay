# server/routes/key_routes.py
import uuid # For explicit UUID generation if needed, though model defaults
from flask import Blueprint, current_app, request, jsonify, current_app
from database.db import PublicKey, db, User
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt # get_jwt to access JTI

key_bp = Blueprint('keys', __name__)

@key_bp.route('/addKey', methods=['POST'])
@jwt_required()
def add_public_key():
    """
    Allows a user to upload a public key (either an identity certificate or an ephemeral key).
    """
    current_username = get_jwt_identity()
    user = User.query.filter_by(username=current_username).first()

    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json()
    public_key_pem = data.get('public_key_pem') # Renamed as per model
    key_type = data.get('key_type') # 'identity' or 'ephemeral'
    
    # Client can optionally provide a key_uid, otherwise server generates.
    # For identity keys, client might generate to keep consistent across devices.
    # For ephemeral, server generation is fine.
    client_provided_key_uid = data.get('key_uid')

    if not public_key_pem:
        return jsonify({'error': 'Public key (PEM format) is required'}), 400
    if not key_type or key_type not in ['identity', 'ephemeral']:
        return jsonify({'error': 'Key type ("identity" or "ephemeral") is required and must be valid'}), 400
    
    jti_to_store = None
    if key_type == 'ephemeral':
        # For ephemeral keys, link them to the current JWT's JTI
        jti_to_store = get_jwt()["jti"]
        if not jti_to_store:
            return jsonify({'error': 'Ephemeral key requires an active session JTI'}), 400
        
        # Optional: Prevent multiple ephemeral keys for the same JTI
        existing_ephemeral_key = PublicKey.query.filter_by(
            user_id=user.id, # Corrected FK
            key_type='ephemeral',
            jti=jti_to_store
        ).first()
        if existing_ephemeral_key:
            # You might choose to update it, or return an error. For now, error.
            return jsonify({'error': 'An ephemeral key already exists for this session'}), 409

    # If an identity key, handle potential existing identity keys
    if key_type == 'identity':
        # Optional: You might want to invalidate or mark previous identity keys as inactive
        # For simplicity, we just add a new one. Consider a flag like 'is_current_identity' in PublicKey
        # and update it here, or require old ones to be deleted first.
        pass # Add logic for managing current identity key if needed

    try:
        # Rely on PublicKey model's default for key_uid if not client-provided
        new_key = PublicKey(
            user_id=user.id, # --- CRITICAL FIX: Use user.id for FK ---
            public_key_pem=public_key_pem,
            key_type=key_type,
            jti=jti_to_store,
            key_uid=client_provided_key_uid if client_provided_key_uid else str(uuid.uuid4()) # Use client-provided or generate
        )
        db.session.add(new_key)
        db.session.commit()

        return jsonify({
            'message': f'{key_type.capitalize()} public key uploaded successfully',
            'key_uid': new_key.key_uid
        }), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding public key: {e}") # Log the error
        return jsonify({'error': 'Failed to upload public key', 'description': str(e)}), 500


@key_bp.route('/getAllKeys', methods=['GET'])
@jwt_required()
def get_user_public_keys():
    """
    Retrieves all public keys (identity and ephemeral) associated with the current user.
    """
    current_username = get_jwt_identity()
    user = User.query.filter_by(username=current_username).first()

    if not user:
        return jsonify({'error': 'User not found'}), 404

    # --- CRITICAL FIX: Use user.id for FK lookup ---
    keys = PublicKey.query.filter_by(user_id=user.id).order_by(PublicKey.timestamp.desc()).all()

    key_list = []
    for key in keys:
        key_data = {
            'key_uid': key.key_uid,
            'public_key_pem': key.public_key_pem, # Renamed
            'key_type': key.key_type, # NEW: Include key type
            'timestamp': key.timestamp.isoformat()
        }
        if key.jti: # Only include JTI if it exists (relevant for ephemeral keys)
            key_data['jti'] = key.jti
        key_list.append(key_data)

    return jsonify({
        'username': user.username,
        'public_keys': key_list
    }), 200


@key_bp.route('/fetchPublicKey', methods=['POST'])
@jwt_required()
def get_recipient_public_key():
    """
    Fetches a specific type of public key (identity or ephemeral) for a given recipient.
    """
    data = request.get_json()
    recipient_username = data.get('username')
    requested_key_type = data.get('key_type') # 'identity' or 'ephemeral'

    if not recipient_username:
        return jsonify({'error': 'Recipient username is required'}), 400
    if not requested_key_type or requested_key_type not in ['identity', 'ephemeral']:
        return jsonify({'error': 'Requested key type ("identity" or "ephemeral") is required and must be valid'}), 400

    recipient = User.query.filter_by(username=recipient_username).first()
    if not recipient:
        return jsonify({'error': 'Recipient not found'}), 404

    # --- CRITICAL FIX & ENHANCEMENT: Fetch specific key type ---
    target_key = None
    if requested_key_type == 'identity':
        # Fetch the most recent identity key for the recipient
        target_key = PublicKey.query.filter_by(
            user_id=recipient.id, # Corrected FK
            key_type='identity'
        ).order_by(PublicKey.timestamp.desc()).first()
        
    elif requested_key_type == 'ephemeral':
        # Fetch the ephemeral key associated with the recipient's *current active session*
        # This assumes recipient.current_jti is updated on their login.
        if not recipient.current_jti:
            return jsonify({'error': 'Recipient does not have an active session with an ephemeral key'}), 404
        
        target_key = PublicKey.query.filter_by(
            user_id=recipient.id, # Corrected FK
            key_type='ephemeral',
            jti=recipient.current_jti # Link to their current active session
        ).first()

    if not target_key:
        return jsonify({'error': f'No active {requested_key_type} public key found for recipient'}), 404

    return jsonify({
        'username': recipient.username,
        'key_uid': target_key.key_uid,
        'public_key_pem': target_key.public_key_pem, # Renamed
        'key_type': target_key.key_type, # Include key type
        'jti': target_key.jti # Include JTI if present
    }), 200


@key_bp.route('/deleteKey', methods=['POST'])
@jwt_required()
def delete_public_key():
    """
    Deletes a specific public key belonging to the current user.
    """
    current_username = get_jwt_identity() # Returns username from JWT identity
    user = User.query.filter_by(username=current_username).first()

    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json()
    key_uid = data.get('key_uid')

    if not key_uid:
        return jsonify({'error': 'Key_uid is required'}), 400

    # --- CRITICAL FIX: Use user.id for filtering ---
    key_to_delete = PublicKey.query.filter_by(key_uid=key_uid, user_id=user.id).first()

    if not key_to_delete:
        return jsonify({'error': 'Key not found or does not belong to the user'}), 404

    # --- SECURITY CONSIDERATION: Prevent deleting the last identity key? ---
    # If a user always needs at least one 'identity' key to receive messages or verify signatures,
    # you might want to prevent deletion of the last one, or require a new one to be set first.
    # For now, allowing deletion of any key that belongs to the user.
    if key_to_delete.key_type == 'identity':
        # Count active identity keys for the user
        remaining_identity_keys = PublicKey.query.filter_by(user_id=user.id, key_type='identity').count()
        if remaining_identity_keys <= 1: # If this is the last or only identity key
            # You could enforce: return jsonify({'error': 'Cannot delete the last identity key. Upload a new one first.'}), 400
            pass # Or add a 'is_current_identity' flag and only delete if not current.
                 # For now, we allow deletion as per original code logic but raise the flag.

    db.session.delete(key_to_delete)
    db.session.commit()

    return jsonify({'message': 'Key deleted successfully'}), 200