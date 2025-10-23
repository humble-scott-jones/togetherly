import json

def test_stripe_webhook_checkout_completed(client):
    # create user
    client.post('/api/signup', json={'email': 'wh@example.com', 'password': 'pass1234'})
    r = client.post('/api/login', json={'email': 'wh@example.com', 'password': 'pass1234'})
    uid = r.get_json().get('id')

    # simulate checkout.session.completed event payload
    payload = {
        'type': 'checkout.session.completed',
        'data': {
            'object': {
                'client_reference_id': uid,
                'customer': 'cus_test_123',
                'subscription': 'sub_test_123'
            }
        }
    }
    r = client.post('/api/stripe-webhook', data=json.dumps(payload), content_type='application/json')
    assert r.status_code == 200
    # user should now be marked paid
    r = client.get('/api/current_user')
    j = r.get_json()
    assert j.get('is_paid') is True
