import os
import json
import sqlite3
import uuid

import pytest

import app as togetherly_app


def make_fake_stripe():
    class FakePM:
        @staticmethod
        def attach(pm, customer=None):
            return {}

    class FakeCustomer:
        @staticmethod
        def create(email=None):
            return {'id': 'cus_test_123'}

        @staticmethod
        def modify(customer, invoice_settings=None):
            return {}

    class FakeSubscription:
        @staticmethod
        def create(customer=None, items=None, payment_behavior=None, expand=None, payment_settings=None):
            # return a subscription-like object with latest_invoice.payment_intent.client_secret
            return {
                'id': 'sub_test_123',
                'status': 'incomplete',
                'latest_invoice': {'payment_intent': {'client_secret': 'pi_test_secret_abc'}},
                'current_period_end': None
            }

    fake = type('FakeStripe', (), {})()
    fake.Customer = FakeCustomer
    fake.PaymentMethod = FakePM
    fake.Subscription = FakeSubscription
    # simple retrieve helpers used elsewhere
    def _retrieve_subscription(sid):
        return {'id': sid, 'status': 'active', 'current_period_end': None}
    fake.Subscription.retrieve = staticmethod(_retrieve_subscription)
    fake.Product = lambda *a, **k: None
    fake.Price = lambda *a, **k: None
    return fake


def test_signup_and_create_subscription(client, monkeypatch, tmp_path):
    # ensure Stripe env vars are set so endpoints don't return 501
    monkeypatch.setenv('STRIPE_SECRET_KEY', 'sk_test_dummy')
    monkeypatch.setenv('STRIPE_TEST_PRICE_ID', 'price_test_123')
    # patch stripe module in app to our fake
    fake = make_fake_stripe()
    monkeypatch.setattr(togetherly_app, 'stripe', fake)

    email = f"user_{uuid.uuid4().hex[:6]}@example.com"
    pw = 'pass1234'

    # signup
    r = client.post('/api/signup', json={'email': email, 'password': pw})
    assert r.status_code == 200
    j = r.get_json()
    assert j.get('ok') is True

    # ensure session set by checking current_user
    r = client.get('/api/current_user')
    assert r.status_code == 200
    u = r.get_json()
    assert u.get('email') == email

    # now create subscription using a test payment_method id
    r2 = client.post('/api/create-subscription', json={'price_id': os.getenv('STRIPE_TEST_PRICE_ID'), 'payment_method': 'pm_test_123'})
    assert r2.status_code == 200, r2.get_data(as_text=True)
    j2 = r2.get_json()
    assert j2.get('ok') is True
    assert 'client_secret' in j2 and j2['client_secret']

    # verify subscriptions table has a row for this user
    con = sqlite3.connect(togetherly_app.DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.execute('SELECT u.id as uid, s.stripe_subscription_id, s.status FROM users u JOIN subscriptions s ON u.id = s.user_id WHERE u.email = ?', (email,)).fetchone()
    con.close()
    assert cur is not None
    assert cur['stripe_subscription_id'] == 'sub_test_123' or cur['stripe_subscription_id'] is not None
