import os
import pytest

RUN_UI = os.getenv('RUN_UI_SMOKE', '')


def test_ui_root_and_save_skipped_by_default():
    """This test is intentionally gated. Set RUN_UI_SMOKE=1 to run it."""
    if not RUN_UI:
        pytest.skip('UI smoke tests are gated. Set RUN_UI_SMOKE=1 to enable')
    # If RUN_UI is set, run the same checks as before
    import requests
    BASE = 'http://127.0.0.1:5001'

    def server_up():
        try:
            r = requests.get(BASE + '/', timeout=1)
            return r.status_code == 200
        except Exception:
            return False

    if not server_up():
        pytest.skip('Dev server not running on 5001')
    r = requests.get(BASE + '/')
    assert r.status_code == 200
    payload = {'company': 'Smoke Test Co'}
    r2 = requests.post(BASE + '/api/profile', json=payload)
    assert r2.status_code in (200, 201)
