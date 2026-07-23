"""
Tests for admin-protected endpoints:
  POST   /api/v1/admin/diseases
  PUT    /api/v1/admin/diseases/<id>
  DELETE /api/v1/admin/diseases/<id>
  PUT    /api/v1/admin/advisory/<id>
  GET    /api/v1/admin/analytics/summary
  GET    /api/v1/admin/audit-logs
  GET    /api/v1/admin/farmers
  GET    /api/v1/admin/farmers/<farmer_id>
"""


def test_analytics_requires_auth(client):
    res = client.get('/api/v1/admin/analytics/summary')
    assert res.status_code == 401


def test_create_disease_requires_auth(client):
    res = client.post('/api/v1/admin/diseases', json={
        'crop_name': 'Cassava', 'disease_name': 'Test Disease',
    })
    assert res.status_code == 401


def test_analytics_with_valid_token(client, auth_token):
    res = client.get(
        '/api/v1/admin/analytics/summary',
        headers={'Authorization': f'Bearer {auth_token}'},
    )
    assert res.status_code == 200
    body = res.get_json()
    assert 'total_diagnoses' in body
    assert 'low_confidence_count' in body
    assert 'crop_stats' in body


def test_create_disease_success(client, auth_token):
    res = client.post(
        '/api/v1/admin/diseases',
        json={'crop_name': 'Cassava', 'disease_name': 'Test Blight', 'is_healthy': False},
        headers={'Authorization': f'Bearer {auth_token}'},
    )
    assert res.status_code == 201
    assert 'class_id' in res.get_json()


def test_update_advisory_success(client, auth_token):
    res = client.put(
        '/api/v1/admin/advisory/0',
        json={
            'recommended_action': 'Updated action text.',
            'local_treatment_options': 'Neem oil spray.',
        },
        headers={'Authorization': f'Bearer {auth_token}'},
    )
    assert res.status_code == 200
    assert res.get_json()['status'] == 'ok'


def test_update_disease_success(client, auth_token):
    res = client.put(
        '/api/v1/admin/diseases/0',
        json={'description': 'Updated description.'},
        headers={'Authorization': f'Bearer {auth_token}'},
    )
    assert res.status_code == 200


def test_invalid_jwt_rejected(client):
    res = client.get(
        '/api/v1/admin/analytics/summary',
        headers={'Authorization': 'Bearer totally.invalid.token'},
    )
    assert res.status_code == 401


def test_delete_disease_requires_auth(client):
    res = client.delete('/api/v1/admin/diseases/0')
    assert res.status_code == 401


def test_delete_disease_with_diagnoses_fails(client, auth_token):
    from app.models import Farmer, DiagnosisRecord
    from app import db as _db
    
    # Create a farmer and diagnosis for class_id 0
    farmer = Farmer(device_identifier='test-device')
    _db.session.add(farmer)
    _db.session.commit()
    
    diagnosis = DiagnosisRecord(
        farmer_id=farmer.farmer_id,
        predicted_class_id=0,
        confidence_score=85.0
    )
    _db.session.add(diagnosis)
    _db.session.commit()
    
    res = client.delete(
        '/api/v1/admin/diseases/0',
        headers={'Authorization': f'Bearer {auth_token}'},
    )
    assert res.status_code == 400
    assert 'Cannot delete disease with associated diagnosis records' in res.get_json()['error']


def test_delete_disease_success(client, auth_token):
    from app.models import DiseaseClass
    from app import db as _db
    
    # Create a new disease without diagnoses
    disease = DiseaseClass(
        class_id=99,
        crop_name='Test Crop',
        disease_name='Test Disease',
        is_healthy=False
    )
    _db.session.add(disease)
    _db.session.commit()
    
    res = client.delete(
        '/api/v1/admin/diseases/99',
        headers={'Authorization': f'Bearer {auth_token}'},
    )
    assert res.status_code == 200
    assert res.get_json()['status'] == 'ok'


def test_audit_logs_requires_auth(client):
    res = client.get('/api/v1/admin/audit-logs')
    assert res.status_code == 401


def test_audit_logs_success(client, auth_token):
    res = client.get(
        '/api/v1/admin/audit-logs',
        headers={'Authorization': f'Bearer {auth_token}'},
    )
    assert res.status_code == 200
    body = res.get_json()
    assert 'logs' in body
    assert 'total' in body
    assert isinstance(body['logs'], list)


def test_farmers_requires_auth(client):
    res = client.get('/api/v1/admin/farmers')
    assert res.status_code == 401


def test_farmers_success(client, auth_token):
    res = client.get(
        '/api/v1/admin/farmers',
        headers={'Authorization': f'Bearer {auth_token}'},
    )
    assert res.status_code == 200
    body = res.get_json()
    assert 'farmers' in body
    assert 'total' in body
    assert isinstance(body['farmers'], list)


def test_farmer_detail_requires_auth(client):
    res = client.get('/api/v1/admin/farmers/some-id')
    assert res.status_code == 401


def test_farmer_detail_not_found(client, auth_token):
    res = client.get(
        '/api/v1/admin/farmers/nonexistent-id',
        headers={'Authorization': f'Bearer {auth_token}'},
    )
    assert res.status_code == 404
