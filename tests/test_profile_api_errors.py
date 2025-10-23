import json
from app import app


def test_profile_company_validation():
    client = app.test_client()
    # too long
    resp = client.post('/api/profile', json={'company': 'A' * 101})
    assert resp.status_code == 400
    j = resp.get_json()
    assert 'errors' in j and 'company' in j['errors']
    assert 'too long' in j['errors']['company'].lower()

    # invalid characters
    resp = client.post('/api/profile', json={'company': '<bad>'})
    assert resp.status_code == 400
    j = resp.get_json()
    assert 'errors' in j and 'company' in j['errors']
    assert 'invalid' in j['errors']['company'].lower()
