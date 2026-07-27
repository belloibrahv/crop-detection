from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from app.logging_config import configure_logging
import os

db = SQLAlchemy()
migrate = Migrate()
limiter = Limiter(key_func=get_remote_address)


def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
        'DATABASE_URL', 'sqlite:///dev.db'
    ).replace('postgres://', 'postgresql://')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET'] = os.getenv('JWT_SECRET', 'devsecret')
    app.config['INFERENCE_URL'] = os.getenv('INFERENCE_URL', 'http://localhost:8501')

    # CORS: restrict to known frontend origin in production, allow all in dev
    allowed_origins = os.getenv('ALLOWED_ORIGINS', '*')
    CORS(app, origins=allowed_origins)

    db.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)

    # Structured JSON logging (NFR-10)
    configure_logging(app)

    from app.routes import diagnose, history, diseases, admin, auth, health
    app.register_blueprint(diagnose.bp, url_prefix='/api/v1')
    app.register_blueprint(history.bp, url_prefix='/api/v1')
    app.register_blueprint(diseases.bp, url_prefix='/api/v1')
    app.register_blueprint(admin.bp, url_prefix='/api/v1/admin')
    app.register_blueprint(auth.bp, url_prefix='/api/v1/auth')
    app.register_blueprint(health.bp, url_prefix='/api/v1')

    # Bare-root handlers (no blueprint) — blueprints cannot be registered twice)
    from app.routes.health import root as _health_root, health_check as _health_check
    app.add_url_rule('/', endpoint='root_root', view_func=_health_root, methods=['GET'])
    app.add_url_rule('/healthz', endpoint='root_healthz', view_func=_health_check, methods=['GET'])

    # Generic 429 handler so clients always get JSON
    @app.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify({
            'error': 'rate_limit_exceeded',
            'message': 'Too many requests. Please wait a moment before trying again.',
        }), 429

    # Friendly 404 handler — return JSON instead of the ugly Werkzeug HTML
    # "Not Found" page. Makes the API look polished when users miss routes.
    @app.errorhandler(404)
    def not_found_handler(e):
        return jsonify({
            'error': 'not_found',
            'message': 'The requested URL was not found on this server.',
            'service': 'AgroScan NG API',
            'available_base': '/api/v1',
            'health': '/healthz',
            'frontend_url': os.getenv('ALLOWED_ORIGINS', 'https://agroscan-frontend.onrender.com'),
        }), 404

    return app
