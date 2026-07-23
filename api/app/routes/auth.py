from flask import Blueprint, request, jsonify, current_app
from app.models import Admin
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone

bp = Blueprint('auth', __name__)

ACCESS_TOKEN_TTL  = timedelta(hours=2)
REFRESH_TOKEN_TTL = timedelta(days=7)


def _make_tokens(admin_id: str, secret: str) -> dict:
    now = datetime.now(timezone.utc)
    access_token = jwt.encode(
        {'admin_id': admin_id, 'type': 'access',  'exp': now + ACCESS_TOKEN_TTL},
        secret, algorithm='HS256',
    )
    refresh_token = jwt.encode(
        {'admin_id': admin_id, 'type': 'refresh', 'exp': now + REFRESH_TOKEN_TTL},
        secret, algorithm='HS256',
    )
    return {'token': access_token, 'refresh_token': refresh_token}


@bp.route('/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json(silent=True) or {}
    email    = data.get('email', '').strip()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'error': 'email and password are required'}), 400

    admin = Admin.query.filter_by(email=email).first()
    if not admin or not bcrypt.checkpw(password.encode(), admin.password_hash.encode()):
        return jsonify({'error': 'invalid_credentials', 'message': 'Invalid email or password.'}), 401

    return jsonify(_make_tokens(admin.admin_id, current_app.config['JWT_SECRET']))


@bp.route('/admin/refresh', methods=['POST'])
def admin_refresh():
    """
    Exchange a valid refresh token for a new access token + refresh token pair.
    Body: { "refresh_token": "<token>" }
    """
    data = request.get_json(silent=True) or {}
    raw_token = data.get('refresh_token', '')

    if not raw_token:
        return jsonify({'error': 'refresh_token is required'}), 400

    try:
        payload = jwt.decode(
            raw_token,
            current_app.config['JWT_SECRET'],
            algorithms=['HS256'],
        )
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'token_expired', 'message': 'Refresh token has expired. Please log in again.'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'invalid_token', 'message': 'Invalid refresh token.'}), 401

    if payload.get('type') != 'refresh':
        return jsonify({'error': 'wrong_token_type', 'message': 'Expected a refresh token.'}), 400

    admin = Admin.query.filter_by(admin_id=payload['admin_id']).first()
    if not admin:
        return jsonify({'error': 'admin_not_found'}), 401

    return jsonify(_make_tokens(admin.admin_id, current_app.config['JWT_SECRET']))
