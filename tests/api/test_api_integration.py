import os
import subprocess
import time
import requests
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
PORT = int(os.getenv('PORT', '5001'))
BASE = f'http://127.0.0.1:{PORT}'


def start_server():
    # start the app in background using project's python if available
    py = './.venv/bin/python' if (ROOT / '.venv' / 'bin' / 'python').exists() else 'python3'
    env = os.environ.copy()
    # ensure .env is loaded by earlier code in app.py
    p = subprocess.Popen([py, 'app.py'], cwd=str(ROOT), env=env)
    # wait for health
    for _ in range(30):
        try:
            r = requests.get(f'{BASE}/__dev__/ping', timeout=1)
            if r.status_code == 200:
                return p
        except Exception:
            pass
        time.sleep(0.5)
    # failed
    p.kill()
    raise RuntimeError('Server failed to start')


def stop_server(p):
    try:
        p.terminate()
        p.wait(timeout=5)
    except Exception:
        try:
            p.kill()
        except Exception:
            pass


def test_api_signup_profile_generate_and_webhook(tmp_path):
    # backup DB if exists
    db = ROOT / 'togetherly.db'
    bak = None
    if db.exists():
        bak = tmp_path / 'togetherly.db.bak'
        db.rename(bak)

    proc = start_server()
    try:
        # create a dev user and store cookies
        s = requests.Session()
        r = s.post(f'{BASE}/__dev__/create_user', json={'email': 'inttest@example.com', 'is_paid': False}, timeout=5)
        assert r.status_code == 200
        data = r.json()
        uid = data.get('id')
        assert uid

        # save a profile
        profile = {
            'industry': 'Realtor',
            'tone': 'friendly',
            'platforms': ['short_video'],
            'brand_keywords': ['listings'],
            'niche_keywords': [],
            'goals': ['New listings'],
            'company': 'TestCo',
            'details': {'reel_style': 'Property b-roll + captions', 'reel_length': 30},
            'include_images': False
        }
        r = s.post(f'{BASE}/api/profile', json=profile, timeout=5)
        assert r.status_code == 200

        # attempt to generate (should require paid for reels) -> expect 401 or 403 because user is not paid
        r = s.post(f'{BASE}/api/generate', json={'platforms': ['short_video'], 'days': 1}, timeout=10)
        assert r.status_code in (401, 403)

        # simulate checkout.session.completed webhook to mark user paid
        payload = {
            'type': 'checkout.session.completed',
            'data': {'object': {'client_reference_id': uid, 'customer': 'cus_test', 'subscription': 'sub_test'}}
        }
        r = requests.post(f'{BASE}/api/stripe-webhook', json=payload, timeout=5)
        assert r.status_code == 200

        # now generate should work
        r = s.post(f'{BASE}/api/generate', json={'platforms': ['short_video'], 'days': 1}, timeout=20)
        assert r.status_code == 200
        body = r.json()
        assert 'posts' in body and len(body['posts']) >= 1
        # check that reel object has expected keys
        reel = body['posts'][0].get('reel')
        assert reel is not None
        for k in ('ranked_hooks', 'beats', 'shot_list', 'srt'):
            assert k in reel

    finally:
        stop_server(proc)
        # restore db
        if bak and bak.exists():
            bak.rename(db)
