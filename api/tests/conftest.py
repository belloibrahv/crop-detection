"""
conftest.py — Pytest fixtures shared across all API tests.
Uses an in-memory SQLite database so tests are fully self-contained.
"""
import io
import os
import pytest

os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')
os.environ.setdefault('INFERENCE_URL', 'http://localhost:8501')
os.environ.setdefault('JWT_SECRET',    'test-secret')

from app import create_app, db as _db  # noqa: E402
from app.models import DiseaseClass, TreatmentAdvisory, Admin  # noqa: E402
import bcrypt  # noqa: E402


@pytest.fixture(scope='session')
def app():
    application = create_app()
    application.config['TESTING'] = True
    application.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with application.app_context():
        _db.create_all()
        _seed_db()
    yield application


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def auth_token(app, client):
    """Return a valid admin JWT."""
    res = client.post('/api/v1/auth/admin/login', json={
        'email': 'admin@agroscan.com', 'password': 'admin123',
    })
    return res.get_json()['token']


def _seed_db():
    """Insert minimal rows needed by tests."""
    # One disease class + advisory
    if not DiseaseClass.query.get(0):
        d = DiseaseClass(
            class_id=0, crop_name='Tomato',
            disease_name='Tomato Early Blight', is_healthy=False,
        )
        _db.session.add(d)
        _db.session.add(TreatmentAdvisory(
            class_id=0,
            recommended_action='Remove lower leaves. Use copper fungicides.',
            local_treatment_options='Copper oxychloride.',
        ))

    # Healthy class
    if not DiseaseClass.query.get(1):
        _db.session.add(DiseaseClass(
            class_id=1, crop_name='Tomato',
            disease_name='Tomato Healthy', is_healthy=True,
        ))

    # Admin user
    if not Admin.query.filter_by(email='admin@agroscan.com').first():
        pw = bcrypt.hashpw(b'admin123', bcrypt.gensalt()).decode()
        _db.session.add(Admin(email='admin@agroscan.com', password_hash=pw))

    _db.session.commit()


def minimal_jpeg(width: int = 256, height: int = 256) -> bytes:
    """Return a minimal valid JPEG image as bytes."""
    from PIL import Image as PILImage
    img = PILImage.new('RGB', (width, height), color=(100, 150, 80))
    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    return buf.getvalue()
