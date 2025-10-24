import os
import time
from playwright.sync_api import sync_playwright
import subprocess
import requests
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
PORT = int(os.getenv('PORT', '5001'))
BASE = f'http://127.0.0.1:{PORT}'


def start_server():
    py = './.venv/bin/python' if (ROOT / '.venv' / 'bin' / 'python').exists() else 'python3'
    p = subprocess.Popen([py, 'app.py'], cwd=str(ROOT), env=os.environ.copy())
    for _ in range(30):
        try:
            r = requests.get(f'{BASE}/__dev__/ping', timeout=1)
            if r.status_code == 200:
                return p
        except Exception:
            pass
        time.sleep(0.5)
    p.kill()
    raise RuntimeError('server failed to start')


def stop_server(p):
    try:
        p.terminate()
        p.wait(timeout=5)
    except Exception:
        try:
            p.kill()
        except Exception:
            pass


def test_playwright_happy_path(tmp_path):
    # start server
    proc = start_server()
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page()
            # sign in via dev helper to avoid filling forms
            requests.post(f'{BASE}/__dev__/create_user', json={'email': 'pw+dev@example.com', 'is_paid': True})
            # load home page
            page.goto(BASE)
            page.wait_for_selector('text=Generate')
            # open profile modal if present and save a profile via API to simplify UI interactions
            # save profile using fetch via JS to re-use session cookie - easier approach: call API with server session cookie
            # create a dev user and retrieve cookies via requests session, then set them in the browser
            s = requests.Session()
            r = s.post(f'{BASE}/__dev__/create_user', json={'email': 'pw+dev2@example.com', 'is_paid': True})
            cookies = s.cookies.get_dict()
            # set cookies into the browser context
            for name, val in cookies.items():
                page.context.add_cookies([{'name': name, 'value': val, 'url': BASE}])
            # now call generate via UI button
            page.reload()
            # click the generate 5-reel sample if present
            try:
                page.click('#modal-generate-reels')
            except Exception:
                # fallback: call API directly
                page.evaluate("() => fetch('/api/generate', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({platforms:['short_video'], days:3})})")
            # wait a bit for generation
            time.sleep(2)
            # verify the page shows at least one result card (by CSS class used in app)
            has_card = page.query_selector('.card')
            assert has_card is not None
            browser.close()
    finally:
        stop_server(proc)
