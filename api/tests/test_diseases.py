"""
Tests for public disease endpoints:
  GET    /api/v1/diseases
  GET    /api/v1/diseases/<id>/advisory
"""


def test_get_diseases(client):
    res = client.get('/api/v1/diseases')
    assert res.status_code == 200
    body = res.get_json()
    assert isinstance(body, list)
    assert len(body) >= 2  # We seeded at least 2 diseases in conftest


def test_get_diseases_structure(client):
    res = client.get('/api/v1/diseases')
    body = res.get_json()
    if len(body) > 0:
        disease = body[0]
        assert 'class_id' in disease
        assert 'crop_name' in disease
        assert 'disease_name' in disease
        assert 'is_healthy' in disease
        assert 'description' in disease


def test_get_advisory_success(client):
    res = client.get('/api/v1/diseases/0/advisory')
    assert res.status_code == 200
    body = res.get_json()
    assert 'recommended_action' in body
    assert 'local_treatment_options' in body


def test_get_advisory_not_found(client):
    res = client.get('/api/v1/diseases/999/advisory')
    assert res.status_code == 404


def test_get_advisory_for_healthy_class(client):
    # Class 1 is a healthy class in conftest
    res = client.get('/api/v1/diseases/1/advisory')
    assert res.status_code == 404
