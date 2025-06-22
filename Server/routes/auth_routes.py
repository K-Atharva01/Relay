from datetime import timedelta
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, get_jti, get_jwt, jwt_required, current_user # Import current_user for potential future use
from database.db import RevokedToken, db, User, PublicKey # Import PublicKey for future use in auth context if setting/getting initial keys
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
        existing_revoked = RevokedToken.query.filter_by(jti=user.current_jti).first()
        if not existing_revoked: # Only revoke if it's not already in the revoked list
            revoked_token = RevokedToken(jti=user.current_jti)
            db.session.add(revoked_token)
            # db.session.commit() # Commit this after updating current_jti to combine transactions if possible
                                # For single active session enforcement, committing immediately might be desirable
                                # For now, we'll commit all at once at the end of the request.

    # Create new access token
    access_token = create_access_token(identity=username, expires_delta=timedelta(hours=1)) # Example expiry
    new_jti = get_jti(access_token)

    # Update user's current_jti to the new token's JTI
    user.current_jti = new_jti
    db.session.commit() # Commit all changes (previous revocation and new JTI)

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
    """
    jti = get_jwt()["jti"] # Get the JTI of the current token

    # Check if the JTI is already in the revoked list to avoid duplicates (UniqueConstraint)
    if not RevokedToken.query.filter_by(jti=jti).first():
        revoked_token = RevokedToken(jti=jti)
        db.session.add(revoked_token)
        
        # Optional: Clear current_jti from the User model if enforcing strict single active session
        # current_user = User.query.filter_by(username=get_jwt_identity()).first()
        # if current_user and current_user.current_jti == jti:
        #     current_user.current_jti = None
        
        db.session.commit()
        return jsonify(msg="Access token has been revoked"), 200
    else:
        # If token is already revoked (e.g., user tries to log out twice quickly)
        return jsonify(msg="Access token already revoked"), 200