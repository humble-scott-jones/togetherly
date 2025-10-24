import os
import time
from app import app
from app import get_db
import sqlite3


def test_generate_requires_paid_for_reels(client):
    # create a dev user (unpaid) and ensure session is set
    r = client.post('/__dev__/create_user', json={'email': 'gating@example.com', 'is_paid': False})
    assert r.status_code == 200
    uid = r.get_json().get('id')

    # As unpaid user, generating reels should be blocked (401/403)
    r2 = client.post('/api/generate', json={'platforms': ['short_video'], 'days': 1})
    assert r2.status_code in (401, 403)

    # Mark the user as paid directly in DB
    with client.application.app_context():
        db = get_db()
        db.execute('UPDATE users SET is_paid = 1 WHERE id = ?', (uid,))
        db.commit()

    # Now generation should succeed and return posts
    r3 = client.post('/api/generate', json={'platforms': ['short_video'], 'days': 1})
    assert r3.status_code == 200
    j = r3.get_json()
    assert j and 'posts' in j

    # Set usage to full quota for this month and expect generation to be blocked
    quota = int(os.getenv('REELS_QUOTA_MONTHLY', '30'))
    period = time.strftime('%Y-%m')
    with client.application.app_context():
        db = get_db()
        db.execute('DELETE FROM generation_usage WHERE user_id = ? AND period = ?', (uid, period))
        db.execute('INSERT INTO generation_usage (id, user_id, period, reels_generated) VALUES (?, ?, ?, ?)', (str(time.time()), uid, period, quota))
        db.commit()

    r4 = client.post('/api/generate', json={'platforms': ['short_video'], 'days': 1})
    assert r4.status_code == 403
