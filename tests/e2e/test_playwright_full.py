import os
import time
import sqlite3
import requests
import subprocess
import pathlib
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]
PORT = int(os.getenv('PORT', '5001'))
BASE = f'http://127.0.0.1:{PORT}'


def start_server():
    py = './.venv/bin/python' if (ROOT / '.venv' / 'bin' / 'python').exists() else 'python3'
    env = os.environ.copy()
    # ensure .env is loaded by app.py
    p = subprocess.Popen([py, 'app.py'], cwd=str(ROOT), env=env)
    for _ in range(40):
        try:
            r = requests.get(f'{BASE}/__dev__/ping', timeout=1)
            if r.status_code == 200:
                return p
        except Exception:
            pass
        time.sleep(0.5)
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


def set_generation_usage(user_id: str, used: int, period=None):
    if period is None:
        period = time.strftime('%Y-%m')
    db_path = ROOT / 'togetherly.db'
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS generation_usage (id TEXT PRIMARY KEY, user_id TEXT, period TEXT, reels_generated INTEGER DEFAULT 0, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)')
    # upsert
    cur.execute('DELETE FROM generation_usage WHERE user_id = ? AND period = ?', (user_id, period))
    cur.execute('INSERT INTO generation_usage (id, user_id, period, reels_generated) VALUES (?, ?, ?, ?)', (str(time.time()), user_id, period, used))
    conn.commit()
    conn.close()


def test_playwright_full_flow():
    # start server
    proc = start_server()
    try:
        # create dev user (not paid)
        s = requests.Session()
        r = s.post(f'{BASE}/__dev__/create_user', json={'email': 'acceptance+dev@example.com', 'is_paid': False}, timeout=5)
        r.raise_for_status()
        uid = r.json().get('id')

        # Prepare Playwright
        headless = os.getenv('HEADLESS', '1') != '0'
        out_base = ROOT / 'tmp' / 'test-outputs' / time.strftime('%Y%m%d-%H%M%S')
        out_base.mkdir(parents=True, exist_ok=True)
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=headless, slow_mo=50)
                context = browser.new_context()
                # set session cookie(s) returned by requests into context
                for name, val in s.cookies.get_dict().items():
                    context.add_cookies([{'name': name, 'value': val, 'url': BASE}])

                page = context.new_page()
                page.goto(BASE)

                # Try generate (should fail because not paid) via UI button
                try:
                    page.click('#modal-generate-reels')
                    # wait for error toast or modal (implementation-specific) - fallback: wait briefly
                    time.sleep(1)
                except Exception:
                    # if UI element missing, we'll call API directly to assert gating
                    pass

                # Call API generate and expect 401/403 for unpaid user
                gen_r = s.post(f'{BASE}/api/generate', json={'platforms': ['short_video'], 'days': 1}, timeout=10)
                assert gen_r.status_code in (401, 403)

                # Simulate checkout.webhook to mark user paid
                payload = {
                    'type': 'checkout.session.completed',
                    'data': {'object': {'client_reference_id': uid, 'customer': 'cus_test', 'subscription': 'sub_test'}}
                }
                wh_r = requests.post(f'{BASE}/api/stripe-webhook', json=payload, timeout=5)
                assert wh_r.status_code == 200

                # Now try generate again (via UI click and wait for cards)
                page.reload()
                # ensure modal generate button present
                page.wait_for_selector('#modal-generate-reels', timeout=5000)
                page.click('#modal-generate-reels')
                # wait for result cards (app renders .card for each post)
                page.wait_for_selector('.card', timeout=10000)
                cards = page.query_selector_all('.card')
                assert len(cards) >= 1

                # Quota test: set usage to quota and assert further generation blocked
                quota = int(os.getenv('REELS_QUOTA_MONTHLY', '30'))
                set_generation_usage(uid, quota)
                # Attempt generation via API should now be blocked (403)
                blocked = s.post(f'{BASE}/api/generate', json={'platforms': ['short_video'], 'days': 1}, timeout=10)
                assert blocked.status_code == 403

                browser.close()
        except Exception as e:
            # On failure, save artifacts: screenshot, page HTML, and last API responses if present
            try:
                if 'page' in locals() and page:
                    ss_path = out_base / 'failure_screenshot.png'
                    page.screenshot(path=str(ss_path))
                    html_path = out_base / 'failure_page.html'
                    html_path.write_text(page.content())
            except Exception:
                pass
            try:
                if 'gen_r' in locals():
                    (out_base / 'gen_response.txt').write_text(getattr(gen_r, 'text', str(gen_r)))
            except Exception:
                pass
            try:
                if 'wh_r' in locals():
                    (out_base / 'wh_response.txt').write_text(getattr(wh_r, 'text', str(wh_r)))
            except Exception:
                pass
            print(f"Saved test artifacts to: {out_base}")
            raise
    finally:
        stop_server(proc)
