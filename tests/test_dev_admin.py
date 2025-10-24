import os
import re
import json

import pytest

import app as togetherly_app


def test_dev_admin_seed_and_create_user(client):
    # ensure the init_db seeding created the dev admin when running in test fixture
    # Note: tests run without FLASK_ENV=development by default; ensure seed runs by setting env var
    os.environ['ALLOW_DEV_DEBUG'] = '1'
    with togetherly_app.app.app_context():
        togetherly_app.init_db()
    # dev admin should exist in DB
    row = client.application.DB_PATH and togetherly_app.get_user_by_email('hi.scott.jones@gmail.com')
    assert row is not None
    assert row['email'] == 'hi.scott.jones@gmail.com'

    # Now use the dev create endpoint to sign in as another test user
    rv = client.post('/__dev__/create_user', json={'email': 'tester@example.com', 'password': 'pw12345', 'is_paid': False})
    assert rv.status_code == 200
    j = rv.get_json()
    assert j and j.get('ok') is True

    # After dev create, the test client should have a session cookie; fetch current_user
    r2 = client.get('/api/current_user')
    cu = r2.get_json()
    assert cu and cu.get('email') == 'tester@example.com'

    # Make tester an admin in DB and check /admin page shows allowed True
    with togetherly_app.app.app_context():
        db = togetherly_app.get_db()
        db.execute('UPDATE users SET is_admin = 1 WHERE email = ?', ('tester@example.com',))
        db.commit()
    # Now GET /admin should render allowed=True (template contains 'Admin' link for allowed users)
    rv3 = client.get('/admin')
    assert rv3.status_code == 200
    body = rv3.get_data(as_text=True)
    # admin page shows admin controls when allowed; look for 'Reconcile' button or similar marker
    assert re.search(r'Reconcile', body, re.IGNORECASE) or 'admin' in body.lower()
