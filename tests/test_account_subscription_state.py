import json
import datetime


def insert_subscription(db, uid, stripe_sub_id='sub_123', status='active', current_period_end=None):
    if current_period_end is None:
        # default to 7 days from now (unix timestamp)
        dt = datetime.datetime.utcnow() + datetime.timedelta(days=7)
        current_period_end = int(dt.replace(tzinfo=datetime.timezone.utc).timestamp())
    db.execute('INSERT INTO subscriptions (id, user_id, stripe_subscription_id, status, current_period_end) VALUES (?, ?, ?, ?, ?)', (str(uuid:= 's_'+stripe_sub_id), uid, stripe_sub_id, status, current_period_end))
    db.execute('UPDATE users SET is_paid = ? WHERE id = ?', (1 if status in ('active','trialing') else 0, uid))
    db.commit()


def test_account_api_shows_subscription_fields(client):
    # create user and login
    client.post('/api/signup', json={'email': 'acct1@example.com', 'password': 'pw12345'})
    r = client.post('/api/login', json={'email': 'acct1@example.com', 'password': 'pw12345'})
    uid = r.get_json().get('id')
    # insert subscription row with active status
    from app import get_db
    with client.application.app_context():
        db = get_db()
        # reuse helper above: create sub 7 days from now
        dt = datetime.datetime.utcnow() + datetime.timedelta(days=7)
        current_period_end = int(dt.replace(tzinfo=datetime.timezone.utc).timestamp())
        db.execute('INSERT INTO subscriptions (id, user_id, stripe_subscription_id, status, current_period_end) VALUES (?, ?, ?, ?, ?)', ('s_act', uid, 'sub_act_1', 'active', current_period_end))
        db.execute('UPDATE users SET is_paid = 1 WHERE id = ?', (uid,))
        db.commit()

    r = client.get('/api/account')
    assert r.status_code == 200
    j = r.get_json()
    assert j['ok'] is True
    sub = j.get('subscription')
    assert sub is not None
    assert sub.get('status') in ('active','trialing')
    assert 'current_period_end_iso' in sub or sub.get('current_period_end')
    assert isinstance(sub.get('days_until_renewal', 0), int)


def test_account_api_reflects_canceled_state(client):
    client.post('/api/signup', json={'email': 'acct2@example.com', 'password': 'pw12345'})
    r = client.post('/api/login', json={'email': 'acct2@example.com', 'password': 'pw12345'})
    uid = r.get_json().get('id')
    from app import get_db
    with client.application.app_context():
        db = get_db()
        db.execute('INSERT INTO subscriptions (id, user_id, stripe_subscription_id, status, current_period_end) VALUES (?, ?, ?, ?, ?)', ('s_can', uid, 'sub_can_1', 'canceled', None))
        db.execute('UPDATE users SET is_paid = 0 WHERE id = ?', (uid,))
        db.commit()

    r = client.get('/api/account')
    assert r.status_code == 200
    j = r.get_json()
    sub = j.get('subscription')
    assert sub is not None
    assert sub.get('status') == 'canceled'
    # canceled should not have days_until_renewal > 0
    assert sub.get('days_until_renewal', 0) == 0
