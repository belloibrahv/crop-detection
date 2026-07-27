from flask import Blueprint, jsonify, redirect, url_for

bp = Blueprint('health', __name__)


@bp.route('/', methods=['GET'])
def root():
    # Render users often land directly on the service URL.
    # Provide a friendly JSON status with link pointers instead of 404.
    return jsonify({
        'service': 'AgroScan NG API',
        'status': 'ok',
        'version': '1.0.0',
        'endpoints': {
            'health': url_for('health.health_check', _external=False),
            'diseases_list': '/api/v1/diseases',
            'diagnose_submit': '/api/v1/diagnose (POST multipart/form-data: file=<image>)',
            'auth_register_farmer': '/api/v1/auth/register-farmer',
            'auth_login_admin': '/api/v1/auth/login-admin',
            'history': '/api/v1/history',
            'admin': '/api/v1/admin/...',
        },
        'frontend_url': 'https://agroscan-frontend.onrender.com',
        'docs': 'Visit frontend to use the UI. API uses /api/v1 prefix.',
    }), 200


@bp.route('/healthz', methods=['GET'])
def health_check():
    return {'status': 'ok'}
