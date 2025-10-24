import json
import pytest

from app import app as flask_app


@pytest.fixture
def client():
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as c:
        yield c


def post_profile(client, payload):
    return client.post('/api/profile', json=payload)


def test_profile_save_success(client):
    payload = {
        'industry': 'Tech',
        'tone': 'friendly',
        'platforms': ['instagram'],
        'brand_keywords': ['x'],
        'niche_keywords': [],
        'goals': [],
        'company': 'Good Name LLC',
        'include_images': True
    }
    r = post_profile(client, payload)
    assert r.status_code == 200
    data = r.get_json()
    assert data.get('ok') is True


def test_profile_company_too_long(client):
    payload = {'company': 'A' * 500}
    r = post_profile(client, payload)
    assert r.status_code == 400
    data = r.get_json()
    assert 'too long' in data.get('error').lower()


def test_profile_company_invalid_chars(client):
    payload = {'company': 'Bad<>Name!'}
    r = post_profile(client, payload)
    assert r.status_code == 400
    data = r.get_json()
    assert 'invalid' in data.get('error').lower()
