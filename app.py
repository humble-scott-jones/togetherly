import os, sqlite3, uuid, json
from datetime import date
from flask import Flask, request, jsonify, render_template, g, session
from flask_cors import CORS
from generator import generate_posts

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
    db.commit()

@app.before_request
def ensure_db():
    init_db()

@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/content")
def api_content():
    # return minimal metadata about content pack (version and flags)
    cfg_path = os.path.join(os.path.dirname(__file__), "static", "content", "config.json")
    flags_path = os.path.join(os.path.dirname(__file__), "static", "content", "flags.json")
    out = {"version": "local"}
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
    row = (
        profile_id,
        data.get("industry", "Business"),
        data.get("tone", "friendly"),
        json.dumps(platforms),
        json.dumps(data.get("brand_keywords", [])),
        json.dumps(data.get("niche_keywords", [])),
        json.dumps(data.get("goals", [])),
        company,
        1 if data.get("include_images", True) else 0,
    )
    db = get_db()
    db.execute(
        """INSERT INTO profiles (id, industry, tone, platforms, brand_keywords, niche_keywords, goals, company, include_images)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(id) DO UPDATE SET
              industry=excluded.industry,
              tone=excluded.tone,
              platforms=excluded.platforms,
              brand_keywords=excluded.brand_keywords,
              niche_keywords=excluded.niche_keywords,
              goals=excluded.goals,
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
    if not profile_id:
        return jsonify({})
    db = get_db()
    row = db.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,)).fetchone()
    if not row:
        return jsonify({})
    # parse stored JSON fields
    def parse_json_field(val):
        try:
            return json.loads(val) if val else []
        except Exception:
            return []

    return jsonify({
        "id": row["id"],
        "industry": row["industry"],
        "tone": row["tone"],
        "platforms": parse_json_field(row["platforms"]),
        "brand_keywords": parse_json_field(row["brand_keywords"]),
        "niche_keywords": parse_json_field(row["niche_keywords"]),
        "goals": parse_json_field(row["goals"]),
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
    include_images = bool(data.get("include_images", True))
    company = data.get("company", "")

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
        company=company
    )
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
    app.run(host="0.0.0.0", port=port, debug=True)
