from datetime import timedelta
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, get_jti, get_jwt, jwt_required
from database.db import RevokedToken, db, User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register_user():
    data = request.get_json()
    name=data['name']
    username=data['username']
    password=data['password']
    phone=data.get('phone')
    email=data.get('email')
    if not all([username, name, password,email,phone]):
        return jsonify({'error': 'name, Username, password, phone and email are required'}), 400

    if User.query.filter_by(username=username,phone=phone,email=email).first():
        return jsonify({'error': 'User already exists'}), 409
    new_user = User(
        name=name,
        username=username,
        phone=phone,
        email=email,
        password_hash=User.set_password(password)
    )

    db.session.add(new_user)
    db.session.commit()

    return jsonify({
        "message": "User registered successfully",
        # "unique_id": new_user.unique_id
    }), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not all([username, password]):
        return jsonify({'error': 'Username and password required'}), 400

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid credentials'}), 401

    if user.current_jti:
        revoked = RevokedToken(jti=user.current_jti)
        db.session.add(revoked)

    access_token = create_access_token(identity=username)
    new_jti = get_jti(access_token)

    user.current_jti = new_jti
    db.session.commit()

    return jsonify({'access_token': access_token}), 200


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    jti = get_jwt()["jti"]
    from database.db import RevokedToken  # import inside if circular issues
    if not RevokedToken.query.filter_by(jti=jti).first():
        revoked_token = RevokedToken(jti=jti)
        db.session.add(revoked_token)
        db.session.commit()
    return jsonify(msg="Access token has been revoked"), 200
