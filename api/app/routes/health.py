from flask import Blueprint

bp = Blueprint('health', __name__)


@bp.route('/healthz', methods=['GET'])
def health_check():
    return {'status': 'ok'}
