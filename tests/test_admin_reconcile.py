import json


def test_admin_reconcile_csrf_and_auth(client, monkeypatch):
    # create two users
    client.post('/api/signup', json={'email': 'na@example.com', 'password': 'pw12345'})
    client.post('/api/logout')
    client.post('/api/signup', json={'email': 'admin@example.com', 'password': 'pw12345'})
    # set ADMIN_EMAILS to require admin
    monkeypatch.setenv('ADMIN_EMAILS', 'admin@example.com')
    # ensure stripe exists for later checks
    monkeypatch.setenv('STRIPE_SECRET_KEY', 'sk_test_dummy')

    # login as non-admin and attempt reconcile -> should be 403
    client.post('/api/login', json={'email': 'na@example.com', 'password': 'pw12345'})
    r = client.post('/api/reconcile-subscriptions')
    assert r.status_code == 403

    # login as admin, but without CSRF -> should be 403
    client.post('/api/login', json={'email': 'admin@example.com', 'password': 'pw12345'})
    r = client.post('/api/reconcile-subscriptions')
    assert r.status_code == 403

    # set a csrf token in session and call again -> 200 (mock stripe)
    with client.session_transaction() as sess:
        sess['admin_csrf'] = 'token123'

    class DummySub:
        @staticmethod
        def retrieve(sid):
            return {'id': sid, 'status': 'active', 'current_period_end': None}

    monkeypatch.setattr('app.stripe', __import__('types').SimpleNamespace(Subscription=DummySub()), raising=False)

    r = client.post('/api/reconcile-subscriptions', headers={'X-CSRF-Token': 'token123'})
    assert r.status_code == 200
    j = r.get_json()
    assert j['ok'] is True
