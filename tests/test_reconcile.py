import json


def test_reconcile_subscriptions_updates_db(client, monkeypatch):
    # create two users and subscription rows
    client.post('/api/signup', json={'email': 'r1@example.com', 'password': 'pw12345'})
    r = client.post('/api/login', json={'email': 'r1@example.com', 'password': 'pw12345'})
    uid1 = r.get_json().get('id')
    client.post('/api/signup', json={'email': 'r2@example.com', 'password': 'pw12345'})
    r2 = client.post('/api/login', json={'email': 'r2@example.com', 'password': 'pw12345'})
    uid2 = r2.get_json().get('id')

    from app import get_db
    with client.application.app_context():
        db = get_db()
        db.execute('INSERT INTO subscriptions (id, user_id, stripe_subscription_id, status) VALUES (?, ?, ?, ?)', ('s_a', uid1, 'sub_a', 'active'))
        db.execute('INSERT INTO subscriptions (id, user_id, stripe_subscription_id, status) VALUES (?, ?, ?, ?)', ('s_b', uid2, 'sub_b', 'active'))
        db.commit()

    # prepare dummy stripe.Subscription.retrieve
    class DummySub:
        @staticmethod
        def retrieve(sid):
            if sid == 'sub_a':
                return {'id': sid, 'status': 'active', 'current_period_end': 9999999999}
            if sid == 'sub_b':
                return {'id': sid, 'status': 'canceled', 'current_period_end': None}
            raise Exception('not found')

    monkeypatch.setattr('app.stripe', __import__('types').SimpleNamespace(Subscription=DummySub()), raising=False)
    monkeypatch.setenv('STRIPE_SECRET_KEY', 'sk_test_dummy')

    r = client.post('/api/reconcile-subscriptions')
    assert r.status_code == 200
    j = r.get_json()
    assert j['ok'] is True
    # verify DB updated: user1 is paid, user2 is unpaid
    r = client.get('/api/current_user')
    # current_user is last logged in (uid2), so check uid2 unpaid
    assert r.get_json().get('is_paid') is False
    # check DB rows directly
    from tests.conftest import get_user_row
    row1 = get_user_row(str(client.application.DB_PATH), 'r1@example.com')
    row2 = get_user_row(str(client.application.DB_PATH), 'r2@example.com')
    assert row1['is_paid'] == 1
    assert row2['is_paid'] == 0


def test_reconcile_requires_stripe_configured(client, monkeypatch):
    # ensure endpoint returns 501 when stripe not configured
    # ensure stripe is None in app
    monkeypatch.setattr('app.stripe', None, raising=False)
    monkeypatch.delenv('STRIPE_SECRET_KEY', raising=False)
    r = client.post('/api/reconcile-subscriptions')
    assert r.status_code == 501
    j = r.get_json()
    assert j['ok'] is False
