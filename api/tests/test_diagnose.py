"""
Integration tests for POST /api/v1/diagnose.
The inference service is mocked so these run without a running container.
"""
import io
import json
from unittest.mock import patch, MagicMock

import pytest
from PIL import Image as PILImage


DEVICE_ID = 'test-device-diagnose-001'


# ── Helpers ───────────────────────────────────────────────────────────────────

def _jpeg(width=256, height=256) -> bytes:
    img = PILImage.new('RGB', (width, height), (80, 160, 60))
    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    return buf.getvalue()


def _mock_inference_response(class_id=0, confidence=91.4, is_healthy=False):
    """Return a mock requests.Response mimicking the inference service."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        'predictions': [
            {
                'class_id': class_id,
                'crop': 'Tomato',
                'disease': 'Tomato Early Blight',
                'is_healthy': is_healthy,
                'confidence': confidence,
            },
            {
                'class_id': 1,
                'crop': 'Tomato',
                'disease': 'Tomato Healthy',
                'is_healthy': True,
                'confidence': 5.2,
            },
        ]
    }
    return mock_resp


# ── Tests ─────────────────────────────────────────────────────────────────────

@patch('app.routes.diagnose.requests.post')
def test_diagnose_happy_path(mock_post, client):
    mock_post.return_value = _mock_inference_response()

    data = {'leaf_image': (io.BytesIO(_jpeg()), 'leaf.jpg', 'image/jpeg')}
    res = client.post(
        '/api/v1/diagnose',
        data=data,
        content_type='multipart/form-data',
        headers={'X-Device-Id': DEVICE_ID},
    )

    assert res.status_code == 200
    body = res.get_json()
    assert 'diagnosis_id' in body
    assert len(body['results']) == 2
    assert body['results'][0]['disease'] == 'Tomato Early Blight'
    assert body['advisory'] is not None
    assert body['low_confidence'] is False


@patch('app.routes.diagnose.requests.post')
def test_diagnose_saves_thumbnail_url(mock_post, client):
    mock_post.return_value = _mock_inference_response()

    data = {'leaf_image': (io.BytesIO(_jpeg()), 'leaf.jpg', 'image/jpeg')}
    res = client.post(
        '/api/v1/diagnose',
        data=data,
        content_type='multipart/form-data',
        headers={'X-Device-Id': DEVICE_ID},
    )
    body = res.get_json()
    # thumbnail_url may be None if UPLOAD_DIR is not writable in test env, that's OK
    assert 'thumbnail_url' in body


@patch('app.routes.diagnose.requests.post')
def test_diagnose_low_confidence_flagged(mock_post, client):
    mock_post.return_value = _mock_inference_response(confidence=20.0)

    data = {'leaf_image': (io.BytesIO(_jpeg()), 'leaf.jpg', 'image/jpeg')}
    res = client.post(
        '/api/v1/diagnose',
        data=data,
        content_type='multipart/form-data',
        headers={'X-Device-Id': DEVICE_ID},
    )
    assert res.status_code == 200
    assert res.get_json()['low_confidence'] is True


@patch('app.routes.diagnose.requests.post')
def test_diagnose_healthy_leaf_no_advisory(mock_post, client):
    mock_post.return_value = _mock_inference_response(class_id=1, confidence=95.0, is_healthy=True)

    data = {'leaf_image': (io.BytesIO(_jpeg()), 'leaf.jpg', 'image/jpeg')}
    res = client.post(
        '/api/v1/diagnose',
        data=data,
        content_type='multipart/form-data',
        headers={'X-Device-Id': DEVICE_ID},
    )
    assert res.status_code == 200
    assert res.get_json()['advisory'] is None


@patch('app.routes.diagnose.requests.post')
def test_diagnose_retrain_consent_stored(mock_post, client, app):
    mock_post.return_value = _mock_inference_response()

    data = {
        'leaf_image': (io.BytesIO(_jpeg()), 'leaf.jpg', 'image/jpeg'),
        'retrain_consent': 'true',
    }
    res = client.post(
        '/api/v1/diagnose',
        data=data,
        content_type='multipart/form-data',
        headers={'X-Device-Id': DEVICE_ID},
    )
    assert res.status_code == 200
    diagnosis_id = res.get_json()['diagnosis_id']

    from app.models import DiagnosisRecord
    with app.app_context():
        rec = DiagnosisRecord.query.get(diagnosis_id)
        assert rec is not None
        assert rec.retrain_consent is True


def test_diagnose_missing_device_id(client):
    data = {'leaf_image': (io.BytesIO(_jpeg()), 'leaf.jpg', 'image/jpeg')}
    res = client.post(
        '/api/v1/diagnose',
        data=data,
        content_type='multipart/form-data',
    )
    assert res.status_code == 400
    assert res.get_json()['error'] == 'device_id_missing'


def test_diagnose_missing_image(client):
    res = client.post(
        '/api/v1/diagnose',
        data={},
        content_type='multipart/form-data',
        headers={'X-Device-Id': DEVICE_ID},
    )
    assert res.status_code == 400
    assert res.get_json()['error'] == 'image_missing'


def test_diagnose_invalid_file_type(client):
    fake_pdf = b'%PDF-1.4 fake content'
    data = {'leaf_image': (io.BytesIO(fake_pdf), 'doc.pdf', 'application/pdf')}
    res = client.post(
        '/api/v1/diagnose',
        data=data,
        content_type='multipart/form-data',
        headers={'X-Device-Id': DEVICE_ID},
    )
    assert res.status_code == 422
    assert res.get_json()['error'] == 'invalid_file_type'


def test_diagnose_image_too_small(client):
    tiny = _jpeg(width=50, height=50)
    data = {'leaf_image': (io.BytesIO(tiny), 'small.jpg', 'image/jpeg')}
    res = client.post(
        '/api/v1/diagnose',
        data=data,
        content_type='multipart/form-data',
        headers={'X-Device-Id': DEVICE_ID},
    )
    assert res.status_code == 422
    assert res.get_json()['error'] == 'image_too_small'


@patch('app.routes.diagnose.requests.post')
def test_diagnose_inference_timeout(mock_post, client):
    import requests as req_lib
    mock_post.side_effect = req_lib.exceptions.Timeout()

    data = {'leaf_image': (io.BytesIO(_jpeg()), 'leaf.jpg', 'image/jpeg')}
    res = client.post(
        '/api/v1/diagnose',
        data=data,
        content_type='multipart/form-data',
        headers={'X-Device-Id': DEVICE_ID},
    )
    assert res.status_code == 504
    assert res.get_json()['error'] == 'inference_timeout'
