import json

def test_cancel_subscription_with_stripe(client, monkeypatch):
    # create user and mark paid with a subscription row
    client.post('/api/signup', json={'email': 'cancelme@example.com', 'password': 'pw12345'})
    r = client.post('/api/login', json={'email': 'cancelme@example.com', 'password': 'pw12345'})
    uid = r.get_json().get('id')
    # insert subscription row
    from app import get_db
    with client.application.app_context():
        db = get_db()
        sub_id = 'sub_test_abc'
        db.execute('INSERT INTO subscriptions (id, user_id, stripe_subscription_id, status) VALUES (?, ?, ?, ?)', ('s1', uid, sub_id, 'active'))
        db.execute('UPDATE users SET is_paid = 1 WHERE id = ?', (uid,))
        db.commit()

    # monkeypatch stripe.Subscription.delete
    class DummySub:
        @staticmethod
        def delete(sid):
            return {'id': sid, 'status': 'canceled'}

    monkeypatch.setattr('app.stripe', __import__('types').SimpleNamespace(Subscription=DummySub()), raising=False)
    # ensure STRIPE_SECRET_KEY appears set for this test
    monkeypatch.setenv('STRIPE_SECRET_KEY', 'sk_test_dummy')

    r = client.post('/api/cancel-subscription')
    assert r.status_code == 200
    j = r.get_json()
    assert j['ok'] is True
    # user should now be unpaid
    r = client.get('/api/current_user')
    assert r.get_json().get('is_paid') is False
