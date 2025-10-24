import os
import sys
import tempfile
import json
import sqlite3
import pytest
from pathlib import Path

# ensure repo root is on sys.path so `import app` works when pytest runs
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import app as togetherly_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('ALLOW_DEV_DEBUG', '1')
    # Use a temporary database file for isolation
    db_file = tmp_path / "test_togetherly.db"
    togetherly_app.DB_PATH = str(db_file)
    # Expose DB_PATH on the Flask app object for tests that reference client.application.DB_PATH
    togetherly_app.app.DB_PATH = togetherly_app.DB_PATH
    # ensure DB is initialized
    with togetherly_app.app.app_context():
        togetherly_app.init_db()
    togetherly_app.app.config['TESTING'] = True
    with togetherly_app.app.test_client() as client:
        yield client


def get_user_row(db_path, email):
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    r = con.execute('SELECT * FROM users WHERE email = ?', (email.lower(),)).fetchone()
    con.close()
    return r
