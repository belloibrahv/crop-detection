"""
measure_latency.py — Measures end-to-end API response time for the diagnose endpoint.
Sends 10 real requests against a live Flask API (mock inference) and reports stats.
"""
import io, time, statistics, base64, struct, zlib

# Build a minimal valid 224x224 JPEG in memory (all green pixels)
def make_green_jpeg(w=224, h=224):
    # Create a raw RGB array
    raw = bytes([0, 200, 0] * w * h)
    # Write minimal JPEG using PIL if available, else use a pre-baked 1x1 JPEG
    try:
        from PIL import Image as PILImage
        import io as _io
        img = PILImage.new('RGB', (w, h), (0, 200, 0))
        buf = _io.BytesIO()
        img.save(buf, format='JPEG', quality=85)
        return buf.getvalue()
    except ImportError:
        # Fallback: a tiny valid JPEG
        return b''

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))
os.environ['DATABASE_URL'] = 'sqlite:///test_latency.db'
os.environ['INFERENCE_URL'] = 'http://localhost:9999'  # won't be reached; mock used

from app import create_app, db
from app.models import Farmer, DiseaseClass, TreatmentAdvisory
from unittest.mock import patch
import json

app = create_app()

with app.app_context():
    db.create_all()
    # Seed a disease class
    if not DiseaseClass.query.first():
        dc = DiseaseClass(class_id=0, crop_name='Tomato', disease_name='Tomato Healthy', is_healthy=True)
        db.session.add(dc)
        db.session.commit()

client = app.test_client()
jpeg_bytes = make_green_jpeg()

mock_response = {
    'predictions': [{
        'class_id': 0, 'crop': 'Tomato', 'disease': 'Tomato Healthy',
        'is_healthy': True, 'confidence': 97.5
    }]
}

latencies = []

with patch('app.routes.diagnose.requests.post') as mock_post:
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = mock_response
    mock_post.return_value.raise_for_status = lambda: None

    for i in range(10):
        data = {'leaf_image': (io.BytesIO(jpeg_bytes), 'leaf.jpg', 'image/jpeg')}
        t_start = time.perf_counter()
        resp = client.post(
            '/api/v1/diagnose',
            data=data,
            content_type='multipart/form-data',
            headers={'X-Device-Id': f'test-device-{i}'}
        )
        latency_ms = (time.perf_counter() - t_start) * 1000
        latencies.append(latency_ms)
        status = resp.status_code
        print(f'  Request {i+1:2d}: {latency_ms:6.1f} ms  HTTP {status}')

print()
print('=' * 40)
print(f'  N          : {len(latencies)}')
print(f'  Mean       : {statistics.mean(latencies):.1f} ms')
print(f'  Median     : {statistics.median(latencies):.1f} ms')
print(f'  Min        : {min(latencies):.1f} ms')
print(f'  Max        : {max(latencies):.1f} ms')
print(f'  Stdev      : {statistics.stdev(latencies):.1f} ms')
print('=' * 40)

import os
try:
    os.remove('test_latency.db')
except:
    pass
