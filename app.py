import os, sqlite3, uuid, json, re
from datetime import date
from datetime import datetime, timezone
from flask import Flask, request, jsonify, render_template, g, session
import threading
import time
from flask_cors import CORS
from generator import generate_posts
from werkzeug.security import generate_password_hash, check_password_hash
from typing import TYPE_CHECKING

# optional stripe import (only used if STRIPE_SECRET_KEY is set)
try:
    if TYPE_CHECKING:
        # ensure type-checkers know about stripe without requiring it at runtime
        import stripe  # type: ignore
    else:
        import stripe
except Exception:
    stripe = None

USE_OPENAI = bool(os.getenv("OPENAI_API_KEY"))
if USE_OPENAI:
    try:
        from openai import OpenAI
        openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    except Exception:
        USE_OPENAI = False

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-me")
CORS(app)

DB_PATH = os.path.join(os.path.dirname(__file__), "togetherly.db")

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS profiles (
            id TEXT PRIMARY KEY,
            industry TEXT,
            tone TEXT,
            platforms TEXT,
            brand_keywords TEXT,
            niche_keywords TEXT,
            goals TEXT,
            company TEXT,
            include_images INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id TEXT,
            post_day INTEGER,
            platform TEXT,
            rating INTEGER,
            note TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE,
            password_hash TEXT,
            is_paid INTEGER DEFAULT 0,
            stripe_customer_id TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS subscriptions (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            stripe_subscription_id TEXT,
            status TEXT,
            current_period_end DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS reconcile_jobs (
            id TEXT PRIMARY KEY,
            status TEXT,
            result TEXT,
            started_at DATETIME,
            finished_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            token TEXT PRIMARY KEY,
            user_id TEXT,
            expires_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS generation_usage (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            period TEXT,
            reels_generated INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    # Backfill for upgrades
    cols = [r[1] for r in db.execute("PRAGMA table_info(profiles)").fetchall()]
    if "goals" not in cols:
        db.execute("ALTER TABLE profiles ADD COLUMN goals TEXT;")
    if "industry" not in cols:
        db.execute("ALTER TABLE profiles ADD COLUMN industry TEXT;")
    if "company" not in cols:
        try:
            db.execute("ALTER TABLE profiles ADD COLUMN company TEXT;")
        except Exception:
            pass
    if "details" not in cols:
        try:
            db.execute("ALTER TABLE profiles ADD COLUMN details TEXT;")
        except Exception:
            pass
    # ensure users table has is_admin column (backfill for older DBs)
    try:
        ucols = [r[1] for r in db.execute("PRAGMA table_info(users)").fetchall()]
        if "is_admin" not in ucols:
            try:
                db.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0;")
            except Exception:
                pass
    except Exception:
        pass
    db.commit()

    # Dev-only: seed a known admin user for local development to simplify testing
    try:
        if os.getenv('FLASK_ENV') == 'development' or os.getenv('ALLOW_DEV_DEBUG') == '1':
            dev_email = 'hi.scott.jones@gmail.com'
            dev_pw = os.getenv('DEV_ADMIN_PW') or 'OHsj1984'
            # create or update user with admin flag
            existing = db.execute('SELECT id FROM users WHERE email = ?', (dev_email,)).fetchone()
            pw_hash = generate_password_hash(dev_pw, method='pbkdf2:sha256')
            if existing:
                try:
                    db.execute('UPDATE users SET password_hash = ?, is_admin = ? WHERE id = ?', (pw_hash, 1, existing['id']))
                except Exception:
                    pass
            else:
                try:
                    uid = str(uuid.uuid4())
                    db.execute('INSERT INTO users (id, email, password_hash, is_admin, is_paid) VALUES (?, ?, ?, ?, ?)', (uid, dev_email, pw_hash, 1, 1))
                except Exception:
                    pass
            db.commit()
    except Exception:
        pass

@app.before_request
def ensure_db():
    init_db()

@app.get("/")
def index():
    is_dev = os.getenv('FLASK_ENV') == 'development' or os.getenv('ALLOW_DEV_DEBUG') == '1'
    return render_template("index.html", is_dev=is_dev)


@app.get('/account')
def account_page():
    uid = session.get('user_id')
    if not uid:
        return render_template('account.html', user=None)
    db = get_db()
    user = db.execute('SELECT id, email, is_paid, stripe_customer_id FROM users WHERE id = ?', (uid,)).fetchone()
    sub = None
    subscription = None
    if user:
        sub = db.execute('SELECT * FROM subscriptions WHERE user_id = ? ORDER BY created_at DESC LIMIT 1', (user['id'],)).fetchone()
        subscription = dict(sub) if sub else None
        # try to fetch fresh data from Stripe and enrich with human dates (best-effort)
        try:
            if subscription and stripe and os.getenv('STRIPE_SECRET_KEY') and subscription.get('stripe_subscription_id'):
                stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
                remote = stripe.Subscription.retrieve(subscription['stripe_subscription_id'])
                subscription['status'] = remote.get('status')
                subscription['current_period_end'] = remote.get('current_period_end')
        except Exception:
            pass
        # enrich human-friendly date similar to /api/account
        if subscription and subscription.get('current_period_end'):
            try:
                cpe = subscription.get('current_period_end')
                dt = None
                if isinstance(cpe, (int, float)):
                    dt = datetime.fromtimestamp(int(cpe), tz=timezone.utc)
                else:
                    try:
                        dt = datetime.fromtimestamp(int(str(cpe)), tz=timezone.utc)
                    except Exception:
                        try:
                            dt = datetime.fromisoformat(str(cpe))
                            if dt.tzinfo is None:
                                dt = dt.replace(tzinfo=timezone.utc)
                        except Exception:
                            dt = None
                if dt:
                    subscription['current_period_end_iso'] = dt.astimezone(timezone.utc).isoformat()
                    subscription['current_period_end_human'] = dt.strftime('%Y-%m-%d %H:%M UTC')
                    now = datetime.now(tz=timezone.utc)
                    delta = dt - now
                    subscription['days_until_renewal'] = max(0, delta.days)
            except Exception:
                pass
    # pass is_admin flag to template for rendering admin controls
    return render_template('account.html', user=user, subscription=subscription, is_admin=is_admin())


@app.get('/api/account')
def api_account():
    uid = session.get('user_id')
    if not uid:
        return jsonify({'ok': False, 'error': 'Not authenticated'}), 401
    db = get_db()
    user = db.execute('SELECT id, email, is_paid, stripe_customer_id FROM users WHERE id = ?', (uid,)).fetchone()
    sub = db.execute('SELECT id, stripe_subscription_id, status, current_period_end FROM subscriptions WHERE user_id = ? ORDER BY created_at DESC LIMIT 1', (uid,)).fetchone()
    subscription_data = dict(sub) if sub else None
    # if Stripe is configured and we have a stripe_subscription_id, try to fetch fresh status
    try:
        if subscription_data and stripe and os.getenv('STRIPE_SECRET_KEY') and subscription_data.get('stripe_subscription_id'):
            stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
            remote = stripe.Subscription.retrieve(subscription_data['stripe_subscription_id'])
            subscription_data['status'] = remote.get('status')
            subscription_data['current_period_end'] = remote.get('current_period_end')
    except Exception:
        # ignore Stripe errors; fall back to DB
        pass
    # Enrich subscription_data with human-friendly dates if current_period_end exists
    if subscription_data and subscription_data.get('current_period_end'):
        try:
            # Stripe returns current_period_end as a unix timestamp (int) in many cases
            cpe = subscription_data.get('current_period_end')
            if isinstance(cpe, (int, float)):
                dt = datetime.fromtimestamp(int(cpe), tz=timezone.utc)
            else:
                # sometimes it's stored as a string in DB; try parsing as int then ISO
                try:
                    dt = datetime.fromtimestamp(int(str(cpe)), tz=timezone.utc)
                except Exception:
                    # try ISO parse
                    try:
                        dt = datetime.fromisoformat(str(cpe))
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                    except Exception:
                        dt = None
            if dt:
                subscription_data['current_period_end_iso'] = dt.astimezone(timezone.utc).isoformat()
                # human readable in UTC for now; front-end can localize if desired
                subscription_data['current_period_end_human'] = dt.strftime('%Y-%m-%d %H:%M UTC')
                # days until renewal (rounding down)
                now = datetime.now(tz=timezone.utc)
                delta = dt - now
                subscription_data['days_until_renewal'] = max(0, delta.days)
        except Exception:
            # best-effort only
            pass

    return jsonify({'ok': True, 'user': {'id': user['id'], 'email': user['email'], 'is_paid': bool(user['is_paid'])}, 'subscription': subscription_data})


@app.post('/api/cancel-subscription')
def api_cancel_subscription():
    uid = session.get('user_id')
    if not uid:
        return jsonify({'ok': False, 'error': 'Not authenticated'}), 401
    db = get_db()
    # find active subscription and mark canceled (dev-only; in prod call Stripe API)
    sub = db.execute('SELECT id, stripe_subscription_id, status FROM subscriptions WHERE user_id = ? ORDER BY created_at DESC LIMIT 1', (uid,)).fetchone()
    if not sub:
        return jsonify({'ok': False, 'error': 'No subscription found'}), 400
    # If Stripe is configured and subscription id exists, cancel at Stripe
    try:
        if stripe and os.getenv('STRIPE_SECRET_KEY') and sub['stripe_subscription_id']:
            stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
            try:
                stripe.Subscription.delete(sub['stripe_subscription_id'])
            except Exception as e:
                # if deletion fails, fallback to marking canceled locally but report error
                db.execute('UPDATE subscriptions SET status = ? WHERE id = ?', ('canceled', sub['id']))
                db.execute('UPDATE users SET is_paid = 0 WHERE id = ?', (uid,))
                db.commit()
                return jsonify({'ok': False, 'error': f'stripe error: {e}'}), 502
        # mark canceled locally
        db.execute('UPDATE subscriptions SET status = ? WHERE id = ?', ('canceled', sub['id']))
        db.execute('UPDATE users SET is_paid = 0 WHERE id = ?', (uid,))
        db.commit()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.get("/api/content")
def api_content():
    # return minimal metadata about content pack (version and flags)
    cfg_path = os.path.join(os.path.dirname(__file__), "static", "content", "config.json")
    flags_path = os.path.join(os.path.dirname(__file__), "static", "content", "flags.json")
    out: dict = {"version": "local", "flags": {}}
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            out["version"] = cfg.get("version", out["version"])
    except Exception:
        pass
    try:
        with open(flags_path, "r", encoding="utf-8") as f:
            flags = json.load(f)
            out["flags"] = flags
    except Exception:
        out["flags"] = {}
    return jsonify(out)


def load_flags():
    flags_path = os.path.join(os.path.dirname(__file__), "static", "content", "flags.json")
    try:
        with open(flags_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def perform_reconcile(db=None):
    """Perform reconciliation logic and return results list."""
    close_here = False
    if db is None:
        db = get_db()
        close_here = False
    rows = db.execute('SELECT id, user_id, stripe_subscription_id FROM subscriptions WHERE stripe_subscription_id IS NOT NULL').fetchall()
    results = []
    for r in rows:
        sid = r['stripe_subscription_id']
        try:
            remote = stripe.Subscription.retrieve(sid) if stripe else {}
            status = remote.get('status') if remote else None
            cpe = remote.get('current_period_end') if remote else None
            db.execute('UPDATE subscriptions SET status = ?, current_period_end = ? WHERE id = ?', (status, cpe, r['id']))
            is_paid = 1 if status in ('active', 'trialing') else 0
            db.execute('UPDATE users SET is_paid = ? WHERE id = ?', (is_paid, r['user_id']))
            results.append({'id': r['id'], 'stripe_subscription_id': sid, 'status': status})
        except Exception as e:
            results.append({'id': r['id'], 'stripe_subscription_id': sid, 'error': str(e)})
    db.commit()
    return results


@app.post('/api/reconcile-job')
def api_reconcile_job():
    """Create a reconcile job. If wait=1 is passed, run synchronously and return results."""
    admin_emails = os.getenv('ADMIN_EMAILS', '')
    if admin_emails and not is_admin():
        return jsonify({'ok': False, 'error': 'Admin required'}), 403
    if admin_emails:
        token = request.headers.get('X-CSRF-Token')
        if not token or token != session.get('admin_csrf'):
            return jsonify({'ok': False, 'error': 'CSRF token required'}), 403
    if stripe is None or not os.getenv('STRIPE_SECRET_KEY'):
        return jsonify({'ok': False, 'error': 'Stripe not configured'}), 501

    wait = request.args.get('wait') == '1'
    job_id = str(uuid.uuid4())
    db = get_db()
    started = datetime.now(timezone.utc).isoformat()
    db.execute('INSERT INTO reconcile_jobs (id, status, started_at) VALUES (?, ?, ?)', (job_id, 'running', started))
    db.commit()

    def run_job(jid):
        try:
            results = perform_reconcile(db=db)
            finished = datetime.now(timezone.utc).isoformat()
            db.execute('UPDATE reconcile_jobs SET status = ?, result = ?, finished_at = ? WHERE id = ?', ('finished', json.dumps(results), finished, jid))
            db.commit()
        except Exception as e:
            finished = datetime.now(timezone.utc).isoformat()
            db.execute('UPDATE reconcile_jobs SET status = ?, result = ?, finished_at = ? WHERE id = ?', ('failed', str(e), finished, jid))
            db.commit()

    if wait:
        run_job(job_id)
        row = db.execute('SELECT * FROM reconcile_jobs WHERE id = ?', (job_id,)).fetchone()
        return jsonify({'ok': True, 'job': dict(row)})
    else:
        t = threading.Thread(target=run_job, args=(job_id,))
        t.daemon = True
        t.start()
        return jsonify({'ok': True, 'job_id': job_id})


@app.get('/api/reconcile-jobs/<job_id>')
def api_reconcile_job_get(job_id):
    if not is_admin() and os.getenv('ADMIN_EMAILS', ''):
        return jsonify({'ok': False, 'error': 'Admin required'}), 403
    db = get_db()
    row = db.execute('SELECT * FROM reconcile_jobs WHERE id = ?', (job_id,)).fetchone()
    if not row:
        return jsonify({'ok': False, 'error': 'Not found'}), 404
    return jsonify({'ok': True, 'job': dict(row)})


def is_admin():
    """Simple admin check based on ADMIN_EMAILS env var (comma-separated)."""
    uid = session.get('user_id')
    if not uid:
        return False
    db = get_db()
    # select is_admin flag if present
    row = db.execute('SELECT email, is_admin FROM users WHERE id = ?', (uid,)).fetchone()
    if not row:
        return False
    # Prefer explicit is_admin column if present
    try:
        # sqlite3.Row supports mapping access; treat truthy values as admin
        if 'is_admin' in row.keys() and row.get('is_admin'):
            return True
    except Exception:
        pass
    # Fallback to ADMIN_EMAILS env var if configured
    admin_emails = os.getenv('ADMIN_EMAILS', '')
    if not admin_emails:
        return False
    allowed = [e.strip().lower() for e in admin_emails.split(',') if e.strip()]
    return row['email'].lower() in allowed


### DB helpers
def get_user_by_email(email: str):
    db = get_db()
    return db.execute('SELECT * FROM users WHERE email = ?', (email.lower(),)).fetchone()

def get_user_by_id(uid: str):
    db = get_db()
    return db.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone()

def set_user_paid(uid: str, paid: bool = True):
    db = get_db()
    try:
        db.execute('UPDATE users SET is_paid = ? WHERE id = ?', (1 if paid else 0, uid))
        db.commit()
    except Exception:
        pass


@app.post('/api/signup')
def api_signup():
    data = request.get_json(force=True)
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    if not email or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return jsonify({'ok': False, 'error': 'Invalid email'}), 400
    if not password or len(password) < 6:
        return jsonify({'ok': False, 'error': 'Password too short (min 6 chars)'}), 400
    db = get_db()
    uid = str(uuid.uuid4())
    pw = generate_password_hash(password, method='pbkdf2:sha256')
    try:
        db.execute("INSERT INTO users (id, email, password_hash) VALUES (?, ?, ?)", (uid, email, pw))
        db.commit()
    except Exception as e:
        return jsonify({'ok': False, 'error': 'Email already registered'}), 400
    session['user_id'] = uid
    return jsonify({'ok': True, 'id': uid, 'email': email})


@app.post('/api/login')
def api_login():
    data = request.get_json(force=True)
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    db = get_db()
    row = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    if not row or not check_password_hash(row['password_hash'] or '', password):
        return jsonify({'ok': False, 'error': 'Invalid credentials'}), 401
    session['user_id'] = row['id']
    return jsonify({'ok': True, 'id': row['id'], 'email': row['email'], 'is_paid': bool(row['is_paid'])})


@app.post('/api/logout')
def api_logout():
    session.pop('user_id', None)
    return jsonify({'ok': True})


@app.get('/api/current_user')
def api_current_user():
    uid = session.get('user_id')
    if not uid:
        return jsonify({})
    db = get_db()
    row = db.execute('SELECT id, email, is_paid FROM users WHERE id = ?', (uid,)).fetchone()
    if not row:
        return jsonify({})
    return jsonify({'id': row['id'], 'email': row['email'], 'is_paid': bool(row['is_paid'])})


@app.post('/api/create-checkout-session')
def api_create_checkout():
    # creates a Stripe Checkout Session for the current user; requires STRIPE_SECRET_KEY
    if stripe is None or not os.getenv('STRIPE_SECRET_KEY'):
        return jsonify({'ok': False, 'error': 'Stripe not configured. Set STRIPE_SECRET_KEY in env for test mode.'}), 501
    uid = session.get('user_id')
    if not uid:
        return jsonify({'ok': False, 'error': 'Authentication required'}), 401
    data = request.get_json(force=True)
    price_id = data.get('price_id') or os.getenv('STRIPE_TEST_PRICE_ID')
    if not price_id:
        return jsonify({'ok': False, 'error': 'No price configured. Set STRIPE_TEST_PRICE_ID or pass price_id.'}), 400
    stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
    try:
        # in test mode create a session and return the URL
        sess = stripe.checkout.Session.create(
            mode='subscription',
            payment_method_types=['card'],
            line_items=[{'price': price_id, 'quantity': 1}],
            success_url=os.getenv('STRIPE_SUCCESS_URL', 'http://localhost:5001/'),
            cancel_url=os.getenv('STRIPE_CANCEL_URL', 'http://localhost:5001/'),
            client_reference_id=uid
        )
        return jsonify({'ok': True, 'url': sess.url})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.post('/api/stripe-webhook')
def api_stripe_webhook():
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    secret = os.getenv('STRIPE_WEBHOOK_SECRET')
    event = None
    db = get_db()
    if secret and stripe:
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, secret)
        except Exception as e:
            # invalid signature
            return jsonify({'ok': False, 'error': 'invalid signature'}), 400
    else:
        # fallback: try to parse JSON without verification (local dev)
        try:
            event = json.loads(payload)
        except Exception:
            return jsonify({'ok': False}), 400

    typ = event.get('type')
    data = event.get('data', {}).get('object', {})

    # Handle checkout.session.completed: mark user paid and store subscription id
    if typ == 'checkout.session.completed':
        client_ref = data.get('client_reference_id')
        customer = data.get('customer')
        subscription_id = data.get('subscription')
        if client_ref:
            try:
                db.execute('UPDATE users SET stripe_customer_id = ?, is_paid = 1 WHERE id = ?', (customer, client_ref))
                # create subscription row if subscription_id present
                if subscription_id:
                    sub_id = str(uuid.uuid4())
                    db.execute('INSERT OR REPLACE INTO subscriptions (id, user_id, stripe_subscription_id, status) VALUES (?, ?, ?, ?)',
                               (sub_id, client_ref, subscription_id, 'active'))
                db.commit()
            except Exception:
                pass

    # Handle subscription lifecycle events to update status
    if typ in ('customer.subscription.created', 'customer.subscription.updated', 'customer.subscription.deleted'):
        sub = data
        stripe_sub_id = sub.get('id')
        status = sub.get('status')
        customer = sub.get('customer')
        # try to find user by stripe_customer_id
        user_row = db.execute('SELECT id FROM users WHERE stripe_customer_id = ?', (customer,)).fetchone()
        if user_row:
            uid = user_row['id']
            # upsert subscription
            try:
                # find existing
                existing = db.execute('SELECT id FROM subscriptions WHERE stripe_subscription_id = ?', (stripe_sub_id,)).fetchone()
                if existing:
                    db.execute('UPDATE subscriptions SET status = ?, current_period_end = ? WHERE id = ?', (status, sub.get('current_period_end'), existing['id']))
                else:
                    db.execute('INSERT INTO subscriptions (id, user_id, stripe_subscription_id, status, current_period_end) VALUES (?, ?, ?, ?, ?)',
                               (str(uuid.uuid4()), uid, stripe_sub_id, status, sub.get('current_period_end')))
                # set user paid flag based on status
                is_paid = 1 if status in ('active', 'trialing') else 0
                db.execute('UPDATE users SET is_paid = ? WHERE id = ?', (is_paid, uid))
                db.commit()
            except Exception:
                pass

    # invoice payment succeeded -> ensure user is marked paid
    if typ == 'invoice.payment_succeeded':
        inv = data
        customer = inv.get('customer')
        user_row = db.execute('SELECT id FROM users WHERE stripe_customer_id = ?', (customer,)).fetchone()
        if user_row:
            try:
                db.execute('UPDATE users SET is_paid = 1 WHERE id = ?', (user_row['id'],))
                db.commit()
            except Exception:
                pass

    return jsonify({'ok': True})


@app.post('/api/create-portal-session')
def api_create_portal():
    if stripe is None or not os.getenv('STRIPE_SECRET_KEY'):
        return jsonify({'ok': False, 'error': 'Stripe not configured'}), 501
    uid = session.get('user_id')
    if not uid:
        return jsonify({'ok': False, 'error': 'Authentication required'}), 401
    db = get_db()
    user = db.execute('SELECT stripe_customer_id FROM users WHERE id = ?', (uid,)).fetchone()
    if not user or not user['stripe_customer_id']:
        return jsonify({'ok': False, 'error': 'No stripe customer for user'}), 400
    stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
    try:
        sess = stripe.billing_portal.Session.create(customer=user['stripe_customer_id'], return_url=os.getenv('STRIPE_MANAGE_URL', 'http://localhost:5001/'))
        return jsonify({'ok': True, 'url': sess.url})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.get('/api/stripe-publishable-key')
def api_stripe_publishable_key():
    """Return the Stripe publishable key for client-side Stripe.js initialization."""
    if not os.getenv('STRIPE_PUBLISHABLE_KEY'):
        return jsonify({'ok': False, 'error': 'Publishable key not configured'}), 501
    return jsonify({'ok': True, 'publishableKey': os.getenv('STRIPE_PUBLISHABLE_KEY')})


@app.post('/api/create-subscription')
def api_create_subscription():
    """Create or update Stripe Customer, attach payment method, and create a subscription.

    Expects JSON: { price_id, payment_method }
    Returns: { ok: True, client_secret?, subscription_id, status }
    """
    if stripe is None or not os.getenv('STRIPE_SECRET_KEY'):
        return jsonify({'ok': False, 'error': 'Stripe not configured'}), 501
    uid = session.get('user_id')
    if not uid:
        return jsonify({'ok': False, 'error': 'Authentication required'}), 401
    data = request.get_json(force=True)
    price_id = data.get('price_id') or os.getenv('STRIPE_TEST_PRICE_ID')
    payment_method = data.get('payment_method')
    if not price_id:
        return jsonify({'ok': False, 'error': 'price_id required'}), 400
    if not payment_method:
        return jsonify({'ok': False, 'error': 'payment_method required'}), 400

    stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
    db = get_db()
    user = db.execute('SELECT id, email, stripe_customer_id FROM users WHERE id = ?', (uid,)).fetchone()
    try:
        customer_id = user.get('stripe_customer_id') if user else None
        if not customer_id:
            # create customer
            cust = stripe.Customer.create(email=user['email'] if user else None)
            customer_id = cust['id']
            try:
                db.execute('UPDATE users SET stripe_customer_id = ? WHERE id = ?', (customer_id, uid))
                db.commit()
            except Exception:
                pass

        # attach payment method to customer
        try:
            stripe.PaymentMethod.attach(payment_method, customer=customer_id)
        except Exception:
            # ignore if already attached or other recoverable error
            pass
        # set as default payment method for invoices
        try:
            stripe.Customer.modify(customer_id, invoice_settings={'default_payment_method': payment_method})
        except Exception:
            pass

        # create subscription in incomplete state so we can handle SCA if needed
        sub = stripe.Subscription.create(
            customer=customer_id,
            items=[{'price': price_id}],
            payment_behavior='default_incomplete',
            expand=['latest_invoice.payment_intent'],
            payment_settings={'save_default_payment_method': 'on_subscription'}
        )

        # persist subscription locally
        try:
            db.execute('INSERT INTO subscriptions (id, user_id, stripe_subscription_id, status, current_period_end) VALUES (?, ?, ?, ?, ?)',
                       (str(uuid.uuid4()), uid, sub['id'], sub.get('status'), sub.get('current_period_end')))
            db.commit()
        except Exception:
            # ignore duplicate/insert errors
            pass

        client_secret = None
        latest_invoice = sub.get('latest_invoice') or {}
        payment_intent = latest_invoice.get('payment_intent') or {}
        client_secret = payment_intent.get('client_secret')
        return jsonify({'ok': True, 'subscription_id': sub['id'], 'status': sub.get('status'), 'client_secret': client_secret})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.post('/api/reconcile-subscriptions')
def api_reconcile_subscriptions():
    """Admin/dev endpoint: fetch subscription state from Stripe for all local subscription rows
    that have a stripe_subscription_id and upsert the latest status/current_period_end into DB.
    Requires STRIPE_SECRET_KEY to be set and will return 501 if not configured.
    """
    # If ADMIN_EMAILS is set, require the current user to be an admin and validate CSRF token.
    admin_emails = os.getenv('ADMIN_EMAILS', '')
    if admin_emails and not is_admin():
        return jsonify({'ok': False, 'error': 'Admin required'}), 403
    # If admin protection is enabled, require a matching CSRF token in a header
    if admin_emails:
        token = request.headers.get('X-CSRF-Token')
        if not token or token != session.get('admin_csrf'):
            return jsonify({'ok': False, 'error': 'CSRF token required'}), 403
    if stripe is None or not os.getenv('STRIPE_SECRET_KEY'):
        return jsonify({'ok': False, 'error': 'Stripe not configured'}), 501
    stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
    db = get_db()
    rows = db.execute('SELECT id, user_id, stripe_subscription_id FROM subscriptions WHERE stripe_subscription_id IS NOT NULL').fetchall()
    results = []
    for r in rows:
        sid = r['stripe_subscription_id']
        try:
            remote = stripe.Subscription.retrieve(sid)
            status = remote.get('status')
            cpe = remote.get('current_period_end')
            # upsert the values into subscriptions table
            db.execute('UPDATE subscriptions SET status = ?, current_period_end = ? WHERE id = ?', (status, cpe, r['id']))
            # update user is_paid based on status
            is_paid = 1 if status in ('active', 'trialing') else 0
            db.execute('UPDATE users SET is_paid = ? WHERE id = ?', (is_paid, r['user_id']))
            results.append({'id': r['id'], 'stripe_subscription_id': sid, 'status': status})
        except Exception as e:
            results.append({'id': r['id'], 'stripe_subscription_id': sid, 'error': str(e)})
    db.commit()
    return jsonify({'ok': True, 'results': results})


@app.get('/admin')
def admin_page():
    # basic admin interface to trigger reconciliation
    if not is_admin():
        return render_template('admin.html', allowed=False)
    return render_template('admin.html', allowed=True)


# Dev debug route to inspect session and current user (only in dev or when ALLOW_DEV_DEBUG=1)
@app.get('/__debug__/session')
def debug_session():
    if os.getenv('FLASK_ENV') != 'development' and os.getenv('ALLOW_DEV_DEBUG') != '1':
        return jsonify({'ok': False, 'error': 'Not allowed'}), 403
    out = {'session': dict(session)}
    uid = session.get('user_id')
    if uid:
        try:
            db = get_db()
            row = db.execute('SELECT id, email, is_paid FROM users WHERE id = ?', (uid,)).fetchone()
            out['current_user'] = dict(row) if row else {}
        except Exception:
            out['current_user'] = {}
    return jsonify({'ok': True, 'debug': out})


# Dev helper: list registered routes (dev-only)
@app.get('/__dev__/routes')
def dev_list_routes():
    if os.getenv('FLASK_ENV') != 'development' and os.getenv('ALLOW_DEV_DEBUG') != '1':
        return jsonify({'ok': False, 'error': 'Not allowed'}), 403
    rules = []
    for rule in app.url_map.iter_rules():
        methods = list(rule.methods) if rule.methods else []
        rules.append({'rule': str(rule), 'endpoint': rule.endpoint, 'methods': sorted(methods)})
    return jsonify({'ok': True, 'routes': rules})


# Dev helper: simple ping
@app.get('/__dev__/ping')
def dev_ping():
    if os.getenv('FLASK_ENV') != 'development' and os.getenv('ALLOW_DEV_DEBUG') != '1':
        return 'Not allowed', 403
    return 'pong'


# Dev-only helper: create or update a user and sign them in (only in dev)
@app.post('/__dev__/create_user')
def dev_create_user():
    if os.getenv('FLASK_ENV') != 'development' and os.getenv('ALLOW_DEV_DEBUG') != '1':
        return jsonify({'ok': False, 'error': 'Not allowed'}), 403
    data = request.get_json(force=True)
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or 'password'
    is_paid = bool(data.get('is_paid', False))
    if not email or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return jsonify({'ok': False, 'error': 'Invalid email'}), 400
    db = get_db()
    # if exists, update password and paid flag, else create
    row = db.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
    uid = row['id'] if row else str(uuid.uuid4())
    pw_hash = generate_password_hash(password, method='pbkdf2:sha256')
    try:
        if row:
            db.execute('UPDATE users SET password_hash = ?, is_paid = ? WHERE id = ?', (pw_hash, 1 if is_paid else 0, uid))
        else:
            db.execute('INSERT INTO users (id, email, password_hash, is_paid) VALUES (?, ?, ?, ?)', (uid, email, pw_hash, 1 if is_paid else 0))
        db.commit()
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500
    session['user_id'] = uid
    return jsonify({'ok': True, 'id': uid, 'email': email, 'is_paid': is_paid})


@app.post('/api/request-password-reset')
def api_request_password_reset():
    data = request.get_json(force=True)
    email = (data.get('email') or '').strip().lower()
    if not email:
        return jsonify({'ok': False, 'error': 'Email required'}), 400
    db = get_db()
    row = db.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
    if not row:
        # don't leak user existence in production — here we return ok for dev
        return jsonify({'ok': True})
    token = str(uuid.uuid4())
    # token valid for 1 hour
    import datetime
    expires = (datetime.datetime.utcnow() + datetime.timedelta(hours=1)).isoformat()
    try:
        db.execute('INSERT INTO password_reset_tokens (token, user_id, expires_at) VALUES (?, ?, ?)', (token, row['id'], expires))
        db.commit()
    except Exception:
        pass
    # In production, send email with reset link that contains token. For local dev, return token so tests can use it.
    return jsonify({'ok': True, 'token': token})


@app.post('/api/confirm-password-reset')
def api_confirm_password_reset():
    data = request.get_json(force=True)
    token = data.get('token')
    new_pw = data.get('password')
    if not token or not new_pw or len(new_pw) < 6:
        return jsonify({'ok': False, 'error': 'Invalid token or password too short'}), 400
    db = get_db()
    row = db.execute('SELECT * FROM password_reset_tokens WHERE token = ?', (token,)).fetchone()
    if not row:
        return jsonify({'ok': False, 'error': 'Invalid or expired token'}), 400
    import datetime
    if row['expires_at'] and datetime.datetime.fromisoformat(row['expires_at']) < datetime.datetime.utcnow():
        return jsonify({'ok': False, 'error': 'Token expired'}), 400
    # update password
    pw_hash = generate_password_hash(new_pw, method='pbkdf2:sha256')
    try:
        db.execute('UPDATE users SET password_hash = ? WHERE id = ?', (pw_hash, row['user_id']))
        db.execute('DELETE FROM password_reset_tokens WHERE token = ?', (token,))
        db.commit()
    except Exception as e:
        return jsonify({'ok': False, 'error': 'Could not reset password'}), 500
    return jsonify({'ok': True})



@app.post("/api/profile")
def save_profile():
    data = request.get_json(force=True)
    profile_id = session.get("profile_id") or str(uuid.uuid4())
    session["profile_id"] = profile_id

    platforms = data.get("platforms", ["instagram"])
    company = data.get("company", "")
    # normalize company: trim and title-case for consistency
    if isinstance(company, str):
        company = company.strip()
        company = company.title() if company else ""

    # server-side validation: length and allowed chars
    if company:
        if len(company) > 100:
            return jsonify({"ok": False, "error": "Company name is too long (max 100 chars).", "errors": {"company": "Company name is too long (max 100 chars)."}}), 400
        import re
        if not re.match(r"^[\w \-\'\.\&]+$", company):
            return jsonify({"ok": False, "error": "Company name contains invalid characters.", "errors": {"company": "Company name contains invalid characters."}}), 400
    details = data.get("details", {}) or {}
    row = (
        profile_id,
        data.get("industry", "Business"),
        data.get("tone", "friendly"),
        json.dumps(platforms),
        json.dumps(data.get("brand_keywords", [])),
        json.dumps(data.get("niche_keywords", [])),
        json.dumps(data.get("goals", [])),
        json.dumps(details),
        company,
        1 if data.get("include_images", True) else 0,
    )
    db = get_db()
    db.execute(
        """INSERT INTO profiles (id, industry, tone, platforms, brand_keywords, niche_keywords, goals, details, company, include_images)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(id) DO UPDATE SET
              industry=excluded.industry,
              tone=excluded.tone,
              platforms=excluded.platforms,
              brand_keywords=excluded.brand_keywords,
              niche_keywords=excluded.niche_keywords,
              goals=excluded.goals,
              details=excluded.details,
              company=excluded.company,
              include_images=excluded.include_images
        """,
        row,
    )
    db.commit()
    return jsonify({"ok": True, "profile_id": profile_id})


@app.get("/api/profile")
def get_profile():
    profile_id = session.get("profile_id")
    uid = session.get('user_id')
    if not profile_id:
        return jsonify({})
    db = get_db()
    row = db.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,)).fetchone()
    if not row:
        return jsonify({})
    # parse stored JSON fields
    def parse_json_field(val, default=None):
        try:
            if not val:
                return [] if default is None else default
            return json.loads(val)
        except Exception:
            return [] if default is None else default

    return jsonify({
        "id": row["id"],
        "industry": row["industry"],
        "tone": row["tone"],
        "platforms": parse_json_field(row["platforms"], []),
        "brand_keywords": parse_json_field(row["brand_keywords"], []),
        "niche_keywords": parse_json_field(row["niche_keywords"], []),
        "goals": parse_json_field(row["goals"], []),
    "details": parse_json_field(row["details"], {}),
        "company": row["company"] or "",
        "include_images": bool(row["include_images"]),
        "created_at": row["created_at"],
    })

@app.post("/api/generate")
def api_generate():
    data = request.get_json(force=True)
    profile_id = session.get("profile_id")
    days = int(data.get("days", 30))
    start_iso = data.get("start_date")
    try:
        start_day = date.fromisoformat(start_iso) if start_iso else date.today()
    except Exception:
        start_day = date.today()

    industry = data.get("industry", "Business")
    tone = data.get("tone", "friendly")
    platforms = data.get("platforms", ["instagram"])
    brand_keywords = data.get("brand_keywords", [])
    niche_keywords = data.get("niche_keywords", [])
    goals = data.get("goals", [])
    details = data.get("details", {})
    include_images = bool(data.get("include_images", True))
    company = data.get("company", "")
    details = data.get("details", {}) or {}

    # enforce server-side gating for 7-day (or longer) generation
    flags = load_flags()
    gate7 = bool(flags.get('gate7DayToPaid'))
    if gate7 and days >= 7:
        uid = session.get('user_id')
        if not uid:
            return jsonify({'ok': False, 'error': 'Authentication required for this feature'}), 401
        db = get_db()
        user = db.execute('SELECT is_paid FROM users WHERE id = ?', (uid,)).fetchone()
        if not user or not user['is_paid']:
            return jsonify({'ok': False, 'error': 'Paid subscription required for this feature'}), 403

    # Reels gating & quota: if the requested platforms will produce reels, ensure user is paid and under quota
    reel_platforms = set(['instagram', 'tiktok', 'short_video'])
    requested_reel_platforms = [p for p in (platforms or []) if p and p.lower() in reel_platforms]
    reels_requested = max(0, len(requested_reel_platforms)) * int(days)
    if reels_requested > 0:
        uid = session.get('user_id')
        if not uid:
            return jsonify({'ok': False, 'error': 'Authentication required to generate reels'}), 401
        db = get_db()
        user = db.execute('SELECT is_paid FROM users WHERE id = ?', (uid,)).fetchone()
        if not user or not user['is_paid']:
            return jsonify({'ok': False, 'error': 'Paid subscription required to generate reels'}), 403
        # check monthly quota (env var REELS_QUOTA_MONTHLY default 30)
        quota = int(os.getenv('REELS_QUOTA_MONTHLY', '30'))
        period = date.today().strftime('%Y-%m')
        row = db.execute('SELECT reels_generated FROM generation_usage WHERE user_id = ? AND period = ?', (uid, period)).fetchone()
        used = int(row['reels_generated']) if row else 0
        if used + reels_requested > quota:
            return jsonify({'ok': False, 'error': 'Reel generation quota exceeded for this billing period', 'quota': quota, 'used': used}), 403

    posts = generate_posts(
        days=days,
        start_day=start_day,
        industry=industry,
        tone=tone,
        platforms=platforms,
        brand_keywords=brand_keywords,
        include_images=include_images,
        niche_keywords=niche_keywords,
        goals=goals,
        details=details,
        company=company
    )

    # if reels were requested, increment usage after successful generation
    if reels_requested > 0:
        try:
            db = get_db()
            period = date.today().strftime('%Y-%m')
            current_uid = session.get('user_id')
            existing = db.execute('SELECT reels_generated FROM generation_usage WHERE user_id = ? AND period = ?', (current_uid, period)).fetchone()
            if existing:
                db.execute('UPDATE generation_usage SET reels_generated = reels_generated + ? WHERE user_id = ? AND period = ?', (reels_requested, current_uid, period))
            else:
                db.execute('INSERT INTO generation_usage (id, user_id, period, reels_generated) VALUES (?, ?, ?, ?)', (str(uuid.uuid4()), current_uid, period, reels_requested))
            db.commit()
        except Exception:
            # non-fatal: do not fail generation if usage increment fails
            pass
    return jsonify({"count": len(posts), "posts": posts, "profile_id": profile_id})

@app.post("/api/feedback")
def api_feedback():
    data = request.get_json(force=True)
    profile_id = session.get("profile_id")
    if not profile_id:
        return jsonify({"ok": False, "error": "No profile in session"}), 400
    db = get_db()
    db.execute(
        "INSERT INTO feedback (profile_id, post_day, platform, rating, note) VALUES (?, ?, ?, ?, ?)",
        (
            profile_id,
            int(data.get("post_day", 0)),
            data.get("platform"),
            int(data.get("rating", 0)),
            data.get("note", "")[:500],
        ),
    )
    db.commit()
    return jsonify({"ok": True})

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    # Run without the debugger/reloader here to avoid issues with the dev reloader
    # blocking incoming requests in some environments. For interactive debugging
    # set FLASK_DEBUG=1 and run with the flask CLI instead.
    app.run(host="0.0.0.0", port=port, debug=False)
