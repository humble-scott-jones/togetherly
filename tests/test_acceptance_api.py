import os
import time
import json
import uuid
import requests
import pytest


BASE = os.getenv('TEST_BASE_URL', 'http://127.0.0.1:5001')


def wait_for_server(timeout=10.0):
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(f"{BASE}/__dev__/ping", timeout=1.0)
            # consider server up if we get any non-5xx response (200 OK or 403 Not allowed)
            if r.status_code < 500:
                return True
        except Exception:
            pass
        time.sleep(0.25)
    return False


def test_acceptance_api():
    # If a dev server isn't running at BASE, skip this acceptance test to avoid failing
    # the whole suite when the external server is intentionally not started.
    if not wait_for_server(timeout=2.0):
        pytest.skip(f"Dev server not available at {BASE}; skipping acceptance test")

    session = requests.Session()

    # Dev ping; some deployments may return 403/404 for dev endpoints even when server is up.
    r = session.get(f"{BASE}/__dev__/ping")
    if r.status_code == 200 and r.text.strip() == 'pong':
        routes_resp = session.get(f"{BASE}/__dev__/routes")
    else:
        # fall back to fetching routes to see whether dev endpoints are registered
        routes_resp = session.get(f"{BASE}/__dev__/routes")

    if routes_resp.status_code != 200:
        raise AssertionError(
            f"Dev helper endpoints not available (ping returned {r.status_code}, routes returned {routes_resp.status_code}).\n"
            "Make sure the server is running with FLASK_ENV=development or ALLOW_DEV_DEBUG=1 and restart the process."
        )

    body = routes_resp.json()
    assert body.get('ok') is True
    routes = [entry['rule'] for entry in body.get('routes', [])]
    assert '/__dev__/create_user' in routes, f"'/__dev__/create_user' not found in routes: {routes}"

    # Create an unpaid test user via dev helper
    email_unpaid = f"accept+unpaid+{uuid.uuid4().hex[:6]}@example.com"
    r = session.post(f"{BASE}/__dev__/create_user", json={'email': email_unpaid, 'password': 'passw0rd', 'is_paid': False})
    assert r.status_code == 200
    o = r.json()
    assert o.get('ok') is True

    # Confirm current_user returns correct email
    r = session.get(f"{BASE}/api/current_user")
    assert r.status_code == 200
    cu = r.json()
    assert cu.get('email') == email_unpaid

    # Save a profile with company and retrieve it
    payload = {
        'industry': 'Business',
        'tone': 'friendly',
        'platforms': ['instagram'],
        'brand_keywords': ['brand1'],
        'niche_keywords': ['niche1'],
        'goals': ['awareness'],
        'company': 'TestCo LLC',
        'include_images': True
    }
    r = session.post(f"{BASE}/api/profile", json=payload)
    assert r.status_code == 200
    pj = r.json()
    assert pj.get('ok') is True

    r = session.get(f"{BASE}/api/profile")
    assert r.status_code == 200
    prof = r.json()
    assert prof.get('company') == 'Testco Llc' or prof.get('company') == 'TestCo LLC'

    # Toggle gating flag to require paid for 7-day generation
    flags_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'content', 'flags.json')
    flags_path = os.path.normpath(flags_path)
    os.makedirs(os.path.dirname(flags_path), exist_ok=True)
    with open(flags_path, 'w', encoding='utf-8') as f:
        json.dump({'gate7DayToPaid': True}, f)

    # Attempt to generate 7 days as unpaid user -> should return 403 (paid required)
    gen_payload = {'days': 7, 'industry': 'Business'}
    r = session.post(f"{BASE}/api/generate", json=gen_payload)
    assert r.status_code in (401, 403)

    # Request password reset (dev returns token)
    r = session.post(f"{BASE}/api/request-password-reset", json={'email': email_unpaid})
    assert r.status_code == 200
    token = r.json().get('token')
    assert token

    # Confirm password reset
    r = session.post(f"{BASE}/api/confirm-password-reset", json={'token': token, 'password': 'newpass123'})
    assert r.status_code == 200
    assert r.json().get('ok') is True

    # Logout then login with new password
    r = session.post(f"{BASE}/api/logout")
    assert r.status_code == 200
    r = session.post(f"{BASE}/api/login", json={'email': email_unpaid, 'password': 'newpass123'})
    assert r.status_code == 200
    assert r.json().get('ok') is True
