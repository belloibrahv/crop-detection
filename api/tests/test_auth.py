"""
Tests for /api/v1/auth/admin/login and /api/v1/auth/admin/refresh
"""


def test_login_success(client):
    res = client.post('/api/v1/auth/admin/login', json={
        'email': 'admin@agroscan.com', 'password': 'admin123',
    })
    assert res.status_code == 200
    data = res.get_json()
    assert 'token' in data
    assert 'refresh_token' in data


def test_login_wrong_password(client):
    res = client.post('/api/v1/auth/admin/login', json={
        'email': 'admin@agroscan.com', 'password': 'wrongpassword',
    })
    assert res.status_code == 401
    assert res.get_json()['error'] == 'invalid_credentials'


def test_login_unknown_email(client):
    res = client.post('/api/v1/auth/admin/login', json={
        'email': 'nobody@example.com', 'password': 'anything',
    })
    assert res.status_code == 401


def test_login_missing_fields(client):
    res = client.post('/api/v1/auth/admin/login', json={})
    assert res.status_code == 400


def test_refresh_success(client):
    # Get tokens
    login = client.post('/api/v1/auth/admin/login', json={
        'email': 'admin@agroscan.com', 'password': 'admin123',
    })
    refresh_token = login.get_json()['refresh_token']

    # Exchange refresh token
    res = client.post('/api/v1/auth/admin/refresh', json={'refresh_token': refresh_token})
    assert res.status_code == 200
    data = res.get_json()
    assert 'token' in data
    assert 'refresh_token' in data


def test_refresh_with_access_token_rejected(client):
    login = client.post('/api/v1/auth/admin/login', json={
        'email': 'admin@agroscan.com', 'password': 'admin123',
    })
    access_token = login.get_json()['token']

    res = client.post('/api/v1/auth/admin/refresh', json={'refresh_token': access_token})
    assert res.status_code == 400


def test_refresh_invalid_token(client):
    res = client.post('/api/v1/auth/admin/refresh', json={'refresh_token': 'garbage'})
    assert res.status_code == 401


def test_refresh_missing_body(client):
    res = client.post('/api/v1/auth/admin/refresh', json={})
    assert res.status_code == 400
