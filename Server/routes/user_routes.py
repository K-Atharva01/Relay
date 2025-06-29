# server/routes/user_routes.py
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database.db import User, db # Import db in case needed for future routes, User for lookup

user_bp = Blueprint('user', __name__)

@user_bp.route('/isOnline/<string:username>', methods=['GET'])
@jwt_required()
def is_user_online(username):
    """
    Checks if a specific user is currently 'online' (i.e., has an active JWT session
    indicated by a non-null current_jti).
    """
    # Although not directly used for the query, it's good practice for an authenticated endpoint
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)

    if not current_user:
        return jsonify({'error': 'Authentication failed: User not found.'}), 401

    # Fetch the target user by username
    target_user = User.query.filter_by(username=username).first()

    if not target_user:
        # Return a generic not found to avoid user enumeration if it's a security concern
        # However, for 'is online' this might be okay to distinguish.
        # If you want to leak minimal info: return jsonify({'is_online': False}), 200
        return jsonify({'error': 'User not found.'}), 404
    
    # Determine online status based on current_jti
    # If current_jti is not None, it implies an active session
    is_online = target_user.current_jti is not None

    return jsonify({
        'username': username,
        'is_online': is_online
    }), 200