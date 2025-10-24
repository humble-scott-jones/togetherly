import os
import json
from app import app


def test_webhook_accepts_plain_json_when_secret_placeholder(monkeypatch):
    client = app.test_client()
    # ensure placeholder secret is present in env (simulates .env template)
    monkeypatch.setenv('STRIPE_WEBHOOK_SECRET', 'whsec_REPLACE_ME')
    # post a simple webhook payload (no signature header) and expect handler to accept it in dev fallback
    payload = {'type': 'checkout.session.completed', 'data': {'object': {'client_reference_id': 'abc'}}}
    r = client.post('/api/stripe-webhook', data=json.dumps(payload), content_type='application/json')
    assert r.status_code == 200


def test_webhook_accepts_plain_json_when_unset(monkeypatch):
    client = app.test_client()
    monkeypatch.delenv('STRIPE_WEBHOOK_SECRET', raising=False)
    payload = {'type': 'invoice.payment_succeeded', 'data': {'object': {'customer': 'cus_x'}}}
    r = client.post('/api/stripe-webhook', data=json.dumps(payload), content_type='application/json')
    assert r.status_code == 200
