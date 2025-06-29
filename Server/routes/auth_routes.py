# server/routes/auth_routes.py
from flask import Blueprint, request, jsonify
# Import get_jwt_identity for use in logout to get current user's ID
from flask_jwt_extended import create_access_token, get_jwt, jwt_required, get_jwt_identity, get_jti 
from database.db import RevokedToken, db, User # Keep User and RevokedToken

import re # For email/phone validation (simple regex)

auth_bp = Blueprint('auth', __name__)

# Helper function for input validation
def is_valid_email(email):
    """Basic email format validation."""
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

def is_valid_phone(phone):
    """Basic phone number format validation (e.g., 10-15 digits, optional +)."""
    # Adjust regex based on your specific phone number requirements
    return re.match(r"^\+?[0-9]{10,15}$", phone)


@auth_bp.route('/register', methods=['POST'])
def register_user():
    data = request.get_json()

    # Use .get() for safer access and provide default values
    name = data.get('name')
    username = data.get('username')
    password = data.get('password')
    phone = data.get('phone')
    email = data.get('email')

    # --- ENHANCED VALIDATION: Check for presence and basic format ---
    # Ensure required fields are provided
    if not all([name, username, password]):
        return jsonify({'error': 'Name, username, and password are required'}), 400

    # Basic length/type checks (add more sophisticated checks as needed)
    if not isinstance(name, str) or not (3 <= len(name) <= 100):
        return jsonify({'error': 'Name must be a string between 3 and 100 characters'}), 400
    if not isinstance(username, str) or not (3 <= len(username) <= 50):
        return jsonify({'error': 'Username must be a string between 3 and 50 characters'}), 400
    if not isinstance(password, str) or not (8 <= len(password) <= 255): # Recommend min 8 chars
        return jsonify({'error': 'Password must be a string at least 8 characters long'}), 400
    
    # Validate optional fields if provided
    if phone and not is_valid_phone(phone):
        return jsonify({'error': 'Invalid phone number format'}), 400
    if email and not is_valid_email(email):
        return jsonify({'error': 'Invalid email address format'}), 400

    # --- ENHANCED SECURITY: Avoid user enumeration ---
    # Check for existing user by unique fields individually and return generic error
    # This prevents an attacker from knowing if a username, email, or phone specifically exists.
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Registration failed. Please try a different username, email, or phone.'}), 409
    if email and User.query.filter_by(email=email).first():
        return jsonify({'error': 'Registration failed. Please try a different username, email, or phone.'}), 409
    if phone and User.query.filter_by(phone=phone).first():
        return jsonify({'error': 'Registration failed. Please try a different username, email, or phone.'}), 409

    new_user = User(
        name=name,
        username=username,
        phone=phone, # Phone can be None if not provided
        email=email # Email can be None if not provided
    )

    # --- CRITICAL FIX: Call set_password as an instance method ---
    # This correctly hashes the password and assigns it to new_user.password_hash
    new_user.set_password(password)

    db.session.add(new_user)
    db.session.commit()

    return jsonify({
        "message": "User registered successfully",
    }), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not all([username, password]):
        return jsonify({'error': 'Username and password required'}), 400

    user = User.query.filter_by(username=username).first()
    # --- SECURITY: Generic error message for invalid credentials ---
    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid credentials'}), 401

    # --- ENHANCED: Revoke previous token more safely ---
    # Check if a JTI is currently associated with the user AND if it's not already revoked
    if user.current_jti:
        # Using the class method from RevokedToken model for consistency
        if not RevokedToken.is_jti_blocklisted(user.current_jti): 
            revoked_token = RevokedToken(jti=user.current_jti)
            db.session.add(revoked_token)
            print(f"DEBUG: Revoking old token for {user.username}: {user.current_jti}") # For debugging
        else:
            print(f"DEBUG: Old token {user.current_jti} for {user.username} already blocklisted.") # For debugging

    # Create new access token.
    # Identity is set to user.id (primary key) for easier retrieval in @jwt_required routes.
    # Expiry will be governed by app.config['JWT_ACCESS_TOKEN_EXPIRES'].
    access_token = create_access_token(identity=str(user.id)) 
    new_jti = get_jti(access_token) 


    # Update user's current_jti to the new token's JTI
    user.current_jti = new_jti
    db.session.commit() # Commit all changes (previous revocation and new JTI update)

    # You might want to return user's unique_id and their current public identity key_uid here
    # to facilitate client's key management after login.
    # For example:
    # user_identity_key = PublicKey.query.filter_by(user_id=user.id, key_type='identity').first()
    # response_data = {
    #     'access_token': access_token,
    #     'user_unique_id': user.unique_id,
    #     'identity_key_uid': user_identity_key.key_uid if user_identity_key else None
    # }
    # return jsonify(response_data), 200

    return jsonify({'access_token': access_token}), 200


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """
    Revokes the current access token, effectively logging the user out.
    Also clears the current_jti from the User model.
    """
    jti = get_jwt()["jti"] # Get the JTI of the current token making the request
    user_id = get_jwt_identity() # Get the identity (user.id) from the token

    # Check if the JTI is already in the revoked list to avoid duplicates (UniqueConstraint)
    if not RevokedToken.is_jti_blocklisted(jti):
        revoked_token = RevokedToken(jti=jti)
        db.session.add(revoked_token)
        
        # --- NEW: Clear current_jti from the User model ---
        # This ensures the User record accurately reflects no active session
        user = User.query.get(user_id)
        if user and user.current_jti == jti: # Only clear if it matches the token being revoked
            user.current_jti = None
            print(f"DEBUG: Cleared current_jti for user {user.username} on logout.")
        
        db.session.commit()
        return jsonify(msg="Access token has been revoked"), 200
    else:
        # If token is already revoked (e.g., user tries to log out twice quickly, or token was revoked by new login)
        return jsonify(msg="Access token already revoked"), 200