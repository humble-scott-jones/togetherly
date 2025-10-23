def test_create_checkout_session_not_configured(client, monkeypatch):
    # Ensure STRIPE_SECRET_KEY not set
    monkeypatch.delenv('STRIPE_SECRET_KEY', raising=False)
    r = client.post('/api/create-checkout-session', json={})
    assert r.status_code == 501
    j = r.get_json()
    assert j and j.get('error')
