import json

def test_signup_and_login(client):
    # signup
    r = client.post('/api/signup', json={'email': 'test@example.com', 'password': 'secret123'})
    assert r.status_code == 200
    j = r.get_json()
    assert j['ok'] is True

    # login
    r = client.post('/api/login', json={'email': 'test@example.com', 'password': 'secret123'})
    assert r.status_code == 200
    j = r.get_json()
    assert j['ok'] is True

def test_password_reset_flow(client):
    # create user
    client.post('/api/signup', json={'email': 'reset@example.com', 'password': 'oldpass'})
    # request reset
    r = client.post('/api/request-password-reset', json={'email': 'reset@example.com'})
    assert r.status_code == 200
    j = r.get_json()
    assert j['ok'] is True
    token = j.get('token')
    assert token

    # confirm reset
    r = client.post('/api/confirm-password-reset', json={'token': token, 'password': 'newpass123'})
    assert r.status_code == 200
    j = r.get_json()
    assert j['ok'] is True

    # login with new password
    r = client.post('/api/login', json={'email': 'reset@example.com', 'password': 'newpass123'})
    assert r.status_code == 200
    j = r.get_json()
    assert j['ok'] is True
