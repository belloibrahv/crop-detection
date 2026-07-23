"""
Tests for GET /api/v1/history and DELETE /api/v1/history/<id>
"""
import pytest
from app import db
from app.models import Farmer, DiagnosisRecord


DEVICE_ID = 'test-device-history-001'
OTHER_DEVICE = 'test-device-history-002'


@pytest.fixture(autouse=True)
def clean_records(app):
    """Remove test farmer records and their diagnoses after each test."""
    yield
    with app.app_context():
        farmers = Farmer.query.filter(
            Farmer.device_identifier.in_([DEVICE_ID, OTHER_DEVICE])
        ).all()
        for f in farmers:
            DiagnosisRecord.query.filter_by(farmer_id=f.farmer_id).delete()
            db.session.delete(f)
        db.session.commit()


def _seed_diagnosis(app, device_id: str) -> str:
    with app.app_context():
        farmer = Farmer.query.filter_by(device_identifier=device_id).first()
        if not farmer:
            farmer = Farmer(device_identifier=device_id)
            db.session.add(farmer)
            db.session.commit()
        rec = DiagnosisRecord(
            farmer_id=farmer.farmer_id,
            predicted_class_id=0,
            confidence_score=88.5,
            top3_predictions=[{'class_id': 0, 'crop': 'Tomato', 'disease': 'Tomato Early Blight',
                                'is_healthy': False, 'confidence': 88.5}],
        )
        db.session.add(rec)
        db.session.commit()
        return rec.diagnosis_id


def test_history_requires_device_id(client):
    res = client.get('/api/v1/history')
    assert res.status_code == 400


def test_history_empty_for_new_device(client):
    res = client.get('/api/v1/history', headers={'X-Device-Id': DEVICE_ID})
    assert res.status_code == 200
    assert res.get_json() == []


def test_history_returns_records(app, client):
    _seed_diagnosis(app, DEVICE_ID)
    res = client.get('/api/v1/history', headers={'X-Device-Id': DEVICE_ID})
    assert res.status_code == 200
    data = res.get_json()
    assert len(data) == 1
    assert data[0]['confidence_score'] == pytest.approx(88.5)


def test_history_isolation_between_devices(app, client):
    _seed_diagnosis(app, DEVICE_ID)
    res = client.get('/api/v1/history', headers={'X-Device-Id': OTHER_DEVICE})
    assert res.get_json() == []


def test_delete_own_record(app, client):
    diag_id = _seed_diagnosis(app, DEVICE_ID)
    res = client.delete(f'/api/v1/history/{diag_id}', headers={'X-Device-Id': DEVICE_ID})
    assert res.status_code == 200
    # Confirm it's gone
    remaining = client.get('/api/v1/history', headers={'X-Device-Id': DEVICE_ID}).get_json()
    assert all(r['diagnosis_id'] != diag_id for r in remaining)


def test_cannot_delete_other_devices_record(app, client):
    diag_id = _seed_diagnosis(app, DEVICE_ID)
    res = client.delete(f'/api/v1/history/{diag_id}', headers={'X-Device-Id': OTHER_DEVICE})
    assert res.status_code == 404


def test_delete_requires_device_id(app, client):
    diag_id = _seed_diagnosis(app, DEVICE_ID)
    res = client.delete(f'/api/v1/history/{diag_id}')
    assert res.status_code == 400
