
Stripe local development setup

1) Install the Stripe CLI

	https://stripe.com/docs/stripe-cli

2) Create a local .env from the template and fill in your test keys

	cp .env.example .env
	# edit .env and replace the STRIPE_* placeholders with your test keys

3) Forward Stripe webhooks to your local server (Stripe CLI)

	stripe listen --forward-to http://localhost:5001/api/stripe-webhook

	The listen command prints a webhook signing secret (starts with whsec_...). Copy that value into STRIPE_WEBHOOK_SECRET in your .env.

4) Start the dev server

	FLASK_APP=app.py FLASK_ENV=development FLASK_RUN_PORT=5001 flask run --host=127.0.0.1

5) Test (examples)

	# dev ping
	curl http://127.0.0.1:5001/__dev__/ping

	# content metadata
	curl http://127.0.0.1:5001/api/content

Security notes
- Never commit a real .env with secrets. Keep keys in your local .env or in your CI secrets.
- For production, use real Stripe keys and set STRIPE_WEBHOOK_SECRET to the signing secret from your hosted webhook endpoint.

Quick test flow:

1. Install dependencies and activate your virtualenv

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Set env vars (example using your provided publishable key; you still need the secret key from Stripe test mode):

```bash
export STRIPE_SECRET_KEY="sk_test_..."
export STRIPE_TEST_PRICE_ID="price_..."
export FLASK_APP=app.py
export FLASK_ENV=development
export FLASK_RUN_PORT=5001
source .venv/bin/activate
flask run --host=127.0.0.1
```

3. Use the app UI to sign up / sign in, then click the 7-day plan button. The paywall modal will open. Click "Start free trial" to be redirected to Stripe Checkout.

4. To test webhooks locally, use the Stripe CLI:

```bash
# Install Stripe CLI: https://stripe.com/docs/stripe-cli
stripe login
stripe listen --forward-to localhost:5001/api/stripe-webhook
```

Then simulate events or complete Checkout sessions in the Stripe test dashboard to see the webhook handler update `users.is_paid` and `subscriptions` rows.

Notes:
- The front-end uses a very small prompt-based login for local convenience; replace with a proper modal form for production.
- The webhook handler verifies signatures when STRIPE_WEBHOOK_SECRET is set. Without that, it falls back to parsing JSON for local dev only.
 
Security notes:
- Do NOT commit or check in your Stripe secret key. Set STRIPE_SECRET_KEY in your shell or env file before running the app.
- Example (macOS / zsh):

```bash
export STRIPE_SECRET_KEY="sk_test_..."
export STRIPE_TEST_PRICE_ID="price_..."
export STRIPE_WEBHOOK_SECRET="whsec_..."  # when using stripe listen
```
- For production, never accept unsigned webhooks.
