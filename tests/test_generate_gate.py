import json

def test_generate_gating(client):
    # ensure flags gate7DayToPaid is True for this test
    flags_path = 'static/content/flags.json'
    # create a small flags file with gating enabled
    with open(flags_path, 'w') as f:
        f.write(json.dumps({'gate7DayToPaid': True}))

    # unauthenticated -> 401 for 7 days
    r = client.post('/api/generate', json={'days': 7})
    assert r.status_code == 401

    # create and login user (unpaid)
    client.post('/api/signup', json={'email': 'noguy@example.com', 'password': 'pw12345'})
    client.post('/api/login', json={'email': 'noguy@example.com', 'password': 'pw12345'})
    r = client.post('/api/generate', json={'days': 7})
    assert r.status_code == 403

    # mark user paid directly in DB
    # mark user paid directly in DB using app context
    from app import get_db
    uid = client.get('/api/current_user').get_json().get('id')
    with client.application.app_context():
        db = get_db()
        db.execute('UPDATE users SET is_paid = 1 WHERE id = ?', (uid,))
        db.commit()

    # now should be allowed
    r = client.post('/api/generate', json={'days': 7})
    assert r.status_code == 200
    j = r.get_json()
    assert 'posts' in j
