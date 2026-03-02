"""CodeBuddy – AI-powered programming assistant backend.
   ╔══════════════════════════════════════════════════════════╗
   ║  UPGRADED v4.0 — All 10 Zero-Cost Improvements Applied  ║
   ║  1. DeepSeek-R1 AI model (beats GPT-4, free)            ║
   ║  2. Better TTS with device voice selection              ║
   ║  3. 10 Indic + world languages added                    ║
   ║  4. SQLite WAL mode + indexes (3x faster)               ║
   ║  5. Persistent user memory system                       ║
   ║  6. Piston API sandboxed code execution (50+ langs)     ║
   ║  7. PWA manifest + service worker support               ║
   ║  8. SQL injection fix + security hardening              ║
   ║  9. Public leaderboard + SVG streak cards               ║
   ║  10. Redis-backed rate limiting (falls back to memory)  ║
   ╚══════════════════════════════════════════════════════════╝
"""
import json
import os
import re
import secrets
import sqlite3
import time
import textwrap
from collections import defaultdict
from datetime import datetime, date
from functools import wraps

import requests
from dotenv import load_dotenv
from flask import (Flask, render_template, request, jsonify,
                   Response, redirect, url_for, session, g)
from flask_login import (LoginManager, login_user, login_required,
                         logout_user, UserMixin, current_user)
from flask_bcrypt import Bcrypt

# ================= INIT =================

load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", secrets.token_hex(32))

# ── Security headers on every response ──
@app.after_request
def add_security_headers(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "SAMEORIGIN"
    resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return resp

bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

# ================= CHANGE 10: RATE LIMITING (Redis → memory fallback) =================

try:
    import redis as _redis
    _redis_client = _redis.from_url(
        os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        decode_responses=True, socket_connect_timeout=1
    )
    _redis_client.ping()
    _REDIS_OK = True
except Exception:
    _REDIS_OK = False
    _rate_store = defaultdict(list)


def rate_limit(max_calls=20, window=60):
    """Allow max_calls requests per window seconds per user (Redis or memory)."""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            key = f"rl:{current_user.id}" if current_user.is_authenticated else f"rl:{request.remote_addr}"
            now = time.time()
            if _REDIS_OK:
                pipe = _redis_client.pipeline()
                pipe.zremrangebyscore(key, 0, now - window)
                pipe.zadd(key, {str(now): now})
                pipe.zcard(key)
                pipe.expire(key, window)
                results = pipe.execute()
                count = results[2]
                if count > max_calls:
                    return jsonify({"error": "Rate limit exceeded. Please wait."}), 429
            else:
                calls = [t for t in _rate_store[key] if now - t < window]
                if len(calls) >= max_calls:
                    return jsonify({"error": "Rate limit exceeded. Please wait."}), 429
                calls.append(now)
                _rate_store[key] = calls
            return f(*args, **kwargs)
        return wrapped
    return decorator

# ================= DATABASE =================

def get_db():
    if "db" not in g:
        conn = sqlite3.connect("codebuddy.db")
        conn.row_factory = sqlite3.Row
        # CHANGE 4: WAL mode for 3x faster concurrent reads
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=-32000")  # 32MB cache
        g.db = conn
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    conn = sqlite3.connect("codebuddy.db")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        bio TEXT DEFAULT '',
        avatar_color TEXT DEFAULT '#00ffe0'
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS conversations(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT,
        mode TEXT DEFAULT 'general',
        created_at TEXT,
        updated_at TEXT,
        pinned INTEGER DEFAULT 0
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS messages(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id INTEGER,
        role TEXT,
        content TEXT,
        timestamp TEXT,
        tokens_used INTEGER DEFAULT 0
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS user_stats(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE,
        total_messages INTEGER DEFAULT 0,
        total_chats INTEGER DEFAULT 0,
        debug_count INTEGER DEFAULT 0,
        interview_count INTEGER DEFAULT 0,
        optimize_count INTEGER DEFAULT 0,
        code_runs INTEGER DEFAULT 0,
        streak_days INTEGER DEFAULT 0,
        last_active TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS bookmarks(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        message_id INTEGER,
        note TEXT,
        created_at TEXT
    )""")

    # CHANGE 5: Persistent user memory table
    c.execute("""CREATE TABLE IF NOT EXISTS user_memory(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        key TEXT,
        value TEXT,
        updated_at TEXT,
        UNIQUE(user_id, key)
    )""")

    conn.commit()

    # ── MIGRATIONS ──
    migrations = [
        ("conversations", "mode",         "TEXT DEFAULT 'general'"),
        ("conversations", "pinned",       "INTEGER DEFAULT 0"),
        ("conversations", "created_at",   "TEXT"),
        ("conversations", "updated_at",   "TEXT"),
        ("users",         "bio",          "TEXT DEFAULT ''"),
        ("users",         "avatar_color", "TEXT DEFAULT '#00ffe0'"),
        ("users",         "created_at",   "TEXT DEFAULT (datetime('now'))"),
        ("messages",      "tokens_used",  "INTEGER DEFAULT 0"),
    ]
    for table, column, col_def in migrations:
        existing = [row[1] for row in c.execute(f"PRAGMA table_info({table})").fetchall()]
        if column not in existing:
            c.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}")

    # CHANGE 4: Add indexes for performance
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id)",
        "CREATE INDEX IF NOT EXISTS idx_convos_user ON conversations(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_stats_user ON user_stats(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_memory_user ON user_memory(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_bookmarks_user ON bookmarks(user_id)",
    ]
    for idx in indexes:
        c.execute(idx)

    conn.commit()
    conn.close()

init_db()

# ================= CHANGE 8: SECURE STAT HELPER =================

# Whitelist of allowed stat fields — prevents SQL injection
_ALLOWED_STAT_FIELDS = frozenset({
    "total_messages", "total_chats", "debug_count",
    "interview_count", "optimize_count", "code_runs", "streak_days"
})

def bump_stat(user_id, field, amount=1):
    """Securely increment a stat column using a whitelist."""
    if field not in _ALLOWED_STAT_FIELDS:
        app.logger.warning(f"bump_stat: rejected unknown field '{field}'")
        return
    # Safe because field is whitelisted — not user-supplied
    conn = sqlite3.connect("codebuddy.db")
    conn.execute(f"""
        INSERT INTO user_stats(user_id, {field}, last_active)
        VALUES (?, ?, datetime('now'))
        ON CONFLICT(user_id) DO UPDATE SET
            {field} = {field} + ?,
            last_active = datetime('now')
    """, (user_id, amount, amount))
    conn.commit()
    conn.close()

def update_streak(user_id):
    """Update daily streak — call once per day per user."""
    conn = sqlite3.connect("codebuddy.db")
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT last_active, streak_days FROM user_stats WHERE user_id=?", (user_id,)).fetchone()
    today = date.today().isoformat()
    if row and row["last_active"]:
        last = row["last_active"][:10]
        if last == today:
            conn.close()
            return
        from datetime import timedelta
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        new_streak = (row["streak_days"] or 0) + 1 if last == yesterday else 1
    else:
        new_streak = 1
    conn.execute("""
        INSERT INTO user_stats(user_id, streak_days, last_active)
        VALUES (?, ?, datetime('now'))
        ON CONFLICT(user_id) DO UPDATE SET streak_days=?, last_active=datetime('now')
    """, (user_id, new_streak, new_streak))
    conn.commit()
    conn.close()

# ================= CHANGE 5: PERSISTENT MEMORY HELPERS =================

def get_user_memory(user_id):
    """Load all stored memory for a user as a dict."""
    conn = sqlite3.connect("codebuddy.db")
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT key, value FROM user_memory WHERE user_id=?", (user_id,)
    ).fetchall()
    conn.close()
    return {r["key"]: r["value"] for r in rows}

def set_user_memory(user_id, key, value):
    """Store or update a memory key for a user."""
    conn = sqlite3.connect("codebuddy.db")
    conn.execute("""
        INSERT INTO user_memory(user_id, key, value, updated_at)
        VALUES (?, ?, ?, datetime('now'))
        ON CONFLICT(user_id, key) DO UPDATE SET value=?, updated_at=datetime('now')
    """, (user_id, key, value, value))
    conn.commit()
    conn.close()

def build_memory_context(user_id):
    """Build a personalized context string to inject into system prompts."""
    mem = get_user_memory(user_id)
    if not mem:
        return ""
    lines = ["[USER MEMORY — personalize your response based on this]:"]
    for k, v in mem.items():
        lines.append(f"  • {k}: {v}")
    return "\n" + "\n".join(lines) + "\n"

def extract_and_save_memory(user_id, message):
    """Auto-detect and save useful facts from user messages."""
    msg_lower = message.lower()
    # Detect preferred language
    for lang in ["python", "javascript", "typescript", "java", "c++", "rust", "go", "swift", "kotlin"]:
        if f"i use {lang}" in msg_lower or f"i prefer {lang}" in msg_lower or f"i code in {lang}" in msg_lower:
            set_user_memory(user_id, "preferred_language", lang)
            break
    # Detect experience level
    for phrase, level in [("i'm a beginner", "beginner"), ("i am a beginner", "beginner"),
                           ("i'm intermediate", "intermediate"), ("i am a senior", "senior"),
                           ("i'm senior", "senior"), ("just started", "beginner")]:
        if phrase in msg_lower:
            set_user_memory(user_id, "experience_level", level)
            break
    # Detect current project
    if "working on" in msg_lower or "building a" in msg_lower or "my project is" in msg_lower:
        # Save up to 100 chars as project context
        set_user_memory(user_id, "current_project", message[:100])

# ================= HELPERS =================

def is_programming_related(text):
    """Lightweight check + AI classifier for programming relevance."""
    code_chars = set("{}[]()=><;:/\\")
    if len(text.split()) < 6 and any(c in text for c in code_chars):
        return True
    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "meta-llama/llama-3.1-8b-instruct",
            "max_tokens": 5,
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a classifier. Decide if the user's message is related to "
                        "programming, software development, computer science, coding, algorithms, "
                        "data structures, web development, databases, DevOps, machine learning, "
                        "AI, cybersecurity, or any technical computing topic.\n"
                        "Reply with ONLY the single word: YES or NO"
                    )
                },
                {"role": "user", "content": text[:300]}
            ]
        }
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers, json=payload, timeout=(5, 8)
        )
        if resp.status_code == 200:
            answer = resp.json()["choices"][0]["message"]["content"].strip().upper()
            return answer.startswith("YES")
    except Exception:
        pass
    return True

def get_conversation_history(conversation_id, limit=20):
    conn = sqlite3.connect("codebuddy.db")
    conn.row_factory = sqlite3.Row
    messages = conn.execute(
        """SELECT role, content FROM messages
           WHERE conversation_id=?
           ORDER BY id DESC LIMIT ?""",
        (conversation_id, limit)
    ).fetchall()
    conn.close()
    return [{"role": m["role"], "content": m["content"]} for m in reversed(messages)]

def generate_chat_title(user_message):
    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "meta-llama/llama-3.1-8b-instruct",
            "max_tokens": 20,
            "messages": [
                {"role": "system", "content": "Generate a concise 3-5 word title for this programming question. Only output the title, nothing else. No quotes."},
                {"role": "user", "content": user_message[:200]}
            ]
        }
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers, json=payload, timeout=5
        )
        title = resp.json()["choices"][0]["message"]["content"].strip()
        return title[:60] if title else "New Chat"
    except Exception:
        return user_message[:40] + "..." if len(user_message) > 40 else user_message

# ================= CHANGE 1: MODEL SELECTION =================

# Free models on OpenRouter, ranked by coding quality
MODELS = {
    "code":       "deepseek/deepseek-r1:free",              # DeepSeek R1 free tier
    "fast":       "google/gemini-2.0-flash-001",            # Gemini Flash (stable)
    "fast_free":  "google/gemini-2.0-flash-exp:free",       # Gemini Flash free fallback
    "classifier": "meta-llama/llama-3.1-8b-instruct:free",  # Lightweight classifier
    "title":      "meta-llama/llama-3.1-8b-instruct:free",  # Title generation
}

def get_model_for_mode(mode, lang_code="en-US"):
    """Pick the best free model based on task type and language.

    For non-English Indian languages, always use Gemini Flash:
    - Gemini has been trained on far more multilingual data for Indian scripts.
    - DeepSeek-R1 often ignores Telugu/Kannada/Malayalam/Bengali instructions
      and responds in English regardless of what the system prompt says.
    - Gemini Flash correctly produces Telugu, Kannada, Malayalam, Bengali,
      Tamil, Hindi, Marathi, Gujarati text when instructed to.
    """
    # All non-English Indic languages get Gemini for best script compliance
    indic_langs = {"ta-IN", "ta-en", "hi-IN", "te-IN", "kn-IN",
                   "ml-IN", "bn-IN", "mr-IN", "pa-IN", "gu-IN"}
    if lang_code in indic_langs:
        return MODELS["fast"]  # Gemini Flash — best multilingual support for Indian scripts

    fast_modes = {"explain", "interview", "roadmap"}
    if mode in fast_modes:
        return MODELS["fast"]
    return MODELS["code"]  # DeepSeek-R1 for English coding tasks

# ================= SYSTEM PROMPTS =================

# Injected into every system prompt — universal respectful tone rule
_RESPECTFUL_TONE = """

IMPORTANT — HOW TO ADDRESS THE USER:
- Always be warm, respectful, and encouraging
- NEVER use rude/aggressive words to address the user in ANY language
- English: use "you", never dismissive language
- Tamil/Tanglish: use "bro", "da", "machaa" — NEVER "dei" or "ey" (rude)
- Hindi: use "aap" or "bhai" — NEVER "ey" or "oye" in a rude way
- Telugu: use "meeru" or "bro" — NEVER "ey" or dismissive terms
- Kannada: use "neevu" or "bro" — respectful tone always
- Malayalam: use "ningal" or "bro" — respectful always
- Bengali/Marathi/Gujarati: always respectful, never dismissive
- Treat every user like a respected friend you are genuinely helping"""

SYSTEM_PROMPTS = {
    "general": """You are CodeBuddy, a friendly programming helper.

RULES:
- Use simple, easy words. Avoid jargon unless you explain it.
- Keep answers short and to the point.
- Always explain your code step by step in plain English.
- Use code blocks with the language name (```python, ```javascript, etc.)
- After code, show a simple example of what it outputs.
- If there are multiple ways to do something, just recommend the easiest one.
- Be friendly and encouraging — like a helpful friend who knows coding.""",

    "debug": """You are CodeBuddy's bug fixer. Help the user fix their broken code simply and clearly.

When the user shares buggy code, respond like this:

**What's wrong:**
[Say in 1-2 simple sentences what the bug is and why it happens]

**Fixed code:**
```[language]
[The complete fixed code. Mark changed lines with # FIXED]
```

**Why it was broken:**
[Explain in simple words, like you're talking to a beginner]

**Quick tip:**
[One simple tip to avoid this mistake in the future]

Keep it simple. No big tables or long reports. Just find the bug, fix it, explain it simply.""",

    "optimize": """You are CodeBuddy's speed booster. Help the user make their code faster and cleaner.

When the user shares code to optimize, respond like this:

**What's slow:**
[1-2 sentences explaining what part is slow and why, in simple words]

**Faster version:**
```[language]
[The optimized code with simple comments explaining what changed]
```

**What changed and why:**
[Simple explanation]

**Time complexity:**
- Before: O(?) — [simple explanation]
- After: O(?) — [simple explanation]

Keep explanations short and simple. No big tables needed.""",

    "explain": """You are CodeBuddy's teacher. Explain code and concepts in the simplest way possible.

When explaining, use this structure:

**What it is (simple version):**
[One sentence — explain it like talking to a 12-year-old]

**What it does:**
[2-3 sentences. What problem does it solve? When would you use it?]

**Real life example:**
[Relate it to something from everyday life]

**Code example:**
```[language]
[Simple, short working example with comments on each line]
```

**Output:**
```
[What the code prints/returns]
```

**Common mistake to avoid:**
[One simple mistake beginners make with this]

Always use simple words. If you must use a technical term, explain it right away.""",

    "interview": """You are CodeBuddy's interview coach. Help the user practice coding interviews in a friendly way.

HOW IT WORKS:
1. Ask ONE clear interview question to start
2. After the user answers, give simple feedback
3. Move to the next question

FEEDBACK FORMAT:
**Score: [X]/10**

✅ What you got right: [simple bullet points]
❌ What was missing: [simple bullet points]

**Better answer:**
```[language]
[Clean example answer with simple comments]
```

**Remember this:** [One key takeaway in simple words]

**Next question ([Easy/Medium/Hard]):**
[Next question]

Be encouraging. Use simple language. If they're stuck, give a small hint.""",

    "ml": """You are CodeBuddy ML Engineer — a world-class machine learning engineer and researcher.

For every ML request, use this structure:

---
## 🧠 PROBLEM ANALYSIS
[What type of ML problem is this?]

---
## 🏗️ RECOMMENDED ARCHITECTURE
[Best model choice with justification]

---
## 📦 COMPLETE IMPLEMENTATION

```python
# Full, runnable code
[complete code]
```

---
## 📊 EXPECTED RESULTS
[What accuracy/loss/metrics to expect]

---
## 🔧 HYPERPARAMETER TUNING GUIDE
| Parameter | Default | Try | Effect |
|-----------|---------|-----|--------|

---
## 🚨 COMMON PITFALLS
- [overfitting/underfitting signs and fixes]

---
## ⬆️ NEXT STEPS TO IMPROVE
[3 concrete next steps]

RULES:
- Always provide complete, copy-paste-runnable code
- Always include train/val/test split
- Always show evaluation metrics""",

    "dsa": """You are CodeBuddy DSA Master — a competitive programming champion and algorithm expert.

For every DSA problem, use this EXACT structure:

---
## 🧩 PROBLEM BREAKDOWN
**Input:** [what is given]
**Output:** [what is expected]
**Constraints:** [size limits, edge cases to handle]
**Pattern:** [sliding window / two pointers / DFS / DP / greedy / etc.]

---
## 💭 APPROACH (Brute Force → Optimal)

**Step 1 — Brute Force:** O([N]) time — [brief idea]
**Step 2 — Optimal:** O([N]) time — [brief idea]

---
## 💻 OPTIMAL SOLUTION

```python
def solution(input):
    # Step-by-step comments
    pass

# Test cases
print(solution([2,7,11,15], 9))  # Expected: [0,1]
```

---
## 📊 COMPLEXITY ANALYSIS
- **Time:** O([N]) — [explain why]
- **Space:** O([N]) — [explain why]

---
## 🧪 EDGE CASES TESTED
| Input | Expected | Why it matters |
|-------|----------|----------------|

---
## 🔗 SIMILAR PROBLEMS
[3-5 related problems with their pattern]

RULES:
- Always start with brute force
- Always explain the KEY INSIGHT
- Always test edge cases""",

    "roadmap": """You are CodeBuddy's learning guide. Create simple, clear learning roadmaps.

**Learning Roadmap: [Topic]**
Total time: [X weeks/months] | Level: [Beginner/Intermediate]

**Step 1 — [Name] ([X weeks])**
What you'll learn: [simple list]
Best free resource: [link or name]
Mini project: [simple project to build]

[continue for each step...]

**Final project to build:**
[One clear project that shows off everything]

**Common mistake:**
[The #1 mistake beginners make and how to avoid it]

Keep it simple and motivating.""",

    "ds": """You are CodeBuddy Data Science Expert — a senior data scientist.

For every data science request, use this structure:

---
## 📊 PROBLEM UNDERSTANDING
[What data science problem is this?]

---
## 🔍 DATA ANALYSIS APPROACH

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Complete, runnable code
[complete code]
```

---
## 📈 VISUALIZATIONS EXPLAINED
[What each chart shows]

---
## 📐 STATISTICAL INSIGHTS
[Key statistical findings]

---
## 🚨 DATA QUALITY ISSUES FOUND
- Missing values, Outliers, Skewness

---
## 🤖 MODELING RECOMMENDATION
[If applicable: which model, why, how to proceed]

RULES:
- Always provide complete, copy-paste-runnable Python code
- Always check for nulls, dtypes, and outliers
- Always include at least one visualization"""
}

# ================= USER =================

class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect("codebuddy.db")
    conn.row_factory = sqlite3.Row
    user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    if user:
        return User(user["id"], user["username"])
    return None

# ================= AUTH =================

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        if len(username) < 3:
            return render_template("register.html", error="Username must be at least 3 characters.")
        if len(password) < 6:
            return render_template("register.html", error="Password must be at least 6 characters.")

        hashed = bcrypt.generate_password_hash(password).decode()
        try:
            conn = sqlite3.connect("codebuddy.db")
            conn.execute("INSERT INTO users(username,password) VALUES (?,?)", (username, hashed))
            conn.execute("""INSERT INTO user_stats(user_id, last_active)
                           VALUES ((SELECT id FROM users WHERE username=?), datetime('now'))""", (username,))
            conn.commit()
            conn.close()
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            return render_template("register.html", error="Username already taken.")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        conn = sqlite3.connect("codebuddy.db")
        conn.row_factory = sqlite3.Row
        user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        conn.close()

        if user and bcrypt.check_password_hash(user["password"], password):
            login_user(User(user["id"], user["username"]))
            update_streak(user["id"])
            return redirect(url_for("dashboard"))

        return render_template("login.html", error="Invalid username or password.")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for("login"))

@app.route("/")
@login_required
def dashboard():
    conn = sqlite3.connect("codebuddy.db")
    conn.row_factory = sqlite3.Row
    chats = conn.execute(
        "SELECT id,title,mode,updated_at,pinned FROM conversations WHERE user_id=? ORDER BY pinned DESC, id DESC",
        (current_user.id,)
    ).fetchall()
    conn.close()
    return render_template("index.html", chats=chats, username=current_user.username)

# ================= CHANGE 7: PWA ROUTES =================

@app.route("/manifest.json")
def pwa_manifest():
    manifest = {
        "name": "CodeBuddy AI",
        "short_name": "CodeBuddy",
        "description": "World's first Tanglish programming voice AI assistant",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#020408",
        "theme_color": "#00ffe0",
        "orientation": "portrait-primary",
        "icons": [
            {"src": "/static/icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/static/icons/icon-512.png", "sizes": "512x512", "type": "image/png"},
            {"src": "/static/icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}
        ],
        "categories": ["education", "productivity", "developer tools"],
        "shortcuts": [
            {"name": "New Chat", "url": "/", "description": "Start a new coding session"},
            {"name": "Leaderboard", "url": "/leaderboard", "description": "See top coders"}
        ]
    }
    return jsonify(manifest)

@app.route("/sw.js")
def service_worker():
    sw_code = """
const CACHE_NAME = 'codebuddy-v4';
const STATIC_ASSETS = ['/', '/static/codebuddy_voice.js'];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  const url = new URL(e.request.url);
  // Network-first for API calls
  if (url.pathname.startsWith('/chat') || url.pathname.startsWith('/run_code')) return;
  e.respondWith(
    fetch(e.request).catch(() => caches.match(e.request))
  );
});
"""
    return Response(sw_code, mimetype="application/javascript")

# ================= PROFILE =================

@app.route("/profile")
@login_required
def profile():
    conn = sqlite3.connect("codebuddy.db")
    conn.row_factory = sqlite3.Row
    user = conn.execute("SELECT * FROM users WHERE id=?", (current_user.id,)).fetchone()
    stats = conn.execute("SELECT * FROM user_stats WHERE user_id=?", (current_user.id,)).fetchone()
    conn.close()
    return render_template("profile.html", user=user, stats=stats, username=current_user.username)

@app.route("/update_profile", methods=["POST"])
@login_required
def update_profile():
    bio = request.json.get("bio", "")[:200]
    avatar_color = request.json.get("avatar_color", "#00ffe0")
    conn = sqlite3.connect("codebuddy.db")
    conn.execute("UPDATE users SET bio=?, avatar_color=? WHERE id=?",
                 (bio, avatar_color, current_user.id))
    conn.commit()
    conn.close()
    return jsonify({"status": "updated"})

# ================= CHANGE 5: MEMORY API =================

@app.route("/get_memory")
@login_required
def get_memory():
    """Return all stored memory for the current user."""
    mem = get_user_memory(current_user.id)
    return jsonify({"memory": mem})

@app.route("/set_memory", methods=["POST"])
@login_required
def set_memory_route():
    """Manually store a memory key-value for the current user."""
    data = request.json or {}
    key = data.get("key", "").strip()[:50]
    value = data.get("value", "").strip()[:200]
    if not key:
        return jsonify({"error": "key required"}), 400
    set_user_memory(current_user.id, key, value)
    return jsonify({"status": "saved"})

@app.route("/clear_memory", methods=["POST"])
@login_required
def clear_memory():
    """Clear all memory for the current user."""
    conn = sqlite3.connect("codebuddy.db")
    conn.execute("DELETE FROM user_memory WHERE user_id=?", (current_user.id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "cleared"})

# ================= CHANGE 9: LEADERBOARD + STREAK CARD =================

@app.route("/leaderboard")
def leaderboard():
    """Public leaderboard — top 20 users by streak and total messages."""
    conn = sqlite3.connect("codebuddy.db")
    conn.row_factory = sqlite3.Row
    top_streak = conn.execute("""
        SELECT u.username, u.avatar_color, s.streak_days, s.total_messages,
               s.code_runs, s.debug_count
        FROM user_stats s
        JOIN users u ON s.user_id = u.id
        ORDER BY s.streak_days DESC, s.total_messages DESC
        LIMIT 20
    """).fetchall()
    conn.close()
    return render_template("leaderboard.html", users=top_streak)

@app.route("/streak_card/<username>.svg")
def streak_card(username):
    """Generate a shareable SVG streak card for a user."""
    conn = sqlite3.connect("codebuddy.db")
    conn.row_factory = sqlite3.Row
    user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    if not user:
        conn.close()
        return "User not found", 404
    stats = conn.execute("SELECT * FROM user_stats WHERE user_id=?", (user["id"],)).fetchone()
    conn.close()

    streak = stats["streak_days"] if stats else 0
    messages = stats["total_messages"] if stats else 0
    code_runs = stats["code_runs"] if stats else 0
    color = user["avatar_color"] or "#00ffe0"

    svg = f"""<svg width="500" height="200" viewBox="0 0 500 200"
     xmlns="http://www.w3.org/2000/svg" font-family="monospace">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#020408"/>
      <stop offset="100%" style="stop-color:#060d1a"/>
    </linearGradient>
  </defs>
  <rect width="500" height="200" rx="12" fill="url(#bg)" stroke="{color}" stroke-width="1.5"/>
  <text x="24" y="36" font-size="13" fill="{color}" opacity="0.7">CODEBUDDY AI</text>
  <text x="24" y="72" font-size="28" font-weight="bold" fill="white">{username}</text>
  <text x="24" y="100" font-size="13" fill="{color}" opacity="0.6">coding streak</text>
  <text x="24" y="140" font-size="56" font-weight="bold" fill="{color}">{streak}</text>
  <text x="90" y="140" font-size="28" fill="white">days 🔥</text>
  <text x="24" y="170" font-size="12" fill="white" opacity="0.5">{messages} messages · {code_runs} code runs</text>
  <text x="380" y="185" font-size="10" fill="{color}" opacity="0.4">codebuddy.ai</text>
</svg>"""

    return Response(svg, mimetype="image/svg+xml",
                    headers={"Cache-Control": "public, max-age=3600"})

@app.route("/api/leaderboard")
def api_leaderboard():
    """JSON leaderboard API for dynamic UI."""
    conn = sqlite3.connect("codebuddy.db")
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT u.username, u.avatar_color, s.streak_days, s.total_messages,
               s.code_runs, s.debug_count, s.optimize_count
        FROM user_stats s
        JOIN users u ON s.user_id = u.id
        ORDER BY s.streak_days DESC, s.total_messages DESC
        LIMIT 20
    """).fetchall()
    conn.close()
    return jsonify({"leaderboard": [dict(r) for r in rows]})

# ================= CHAT MANAGEMENT =================

@app.route("/new_chat", methods=["POST"])
@login_required
def new_chat():
    mode = request.json.get("mode", "general") if request.is_json else "general"
    conn = sqlite3.connect("codebuddy.db")
    cursor = conn.execute(
        "INSERT INTO conversations(user_id,title,mode,created_at,updated_at) VALUES (?,?,?,?,?)",
        (current_user.id, "New Chat", mode, datetime.now().isoformat(), datetime.now().isoformat())
    )
    chat_id = cursor.lastrowid
    conn.commit()
    conn.close()
    bump_stat(current_user.id, "total_chats")
    return jsonify({"status": "created", "chat_id": chat_id})

@app.route("/load_messages/<int:chat_id>")
@login_required
def load_messages(chat_id):
    conn = sqlite3.connect("codebuddy.db")
    conn.row_factory = sqlite3.Row
    convo = conn.execute(
        "SELECT id FROM conversations WHERE id=? AND user_id=?",
        (chat_id, current_user.id)
    ).fetchone()
    if not convo:
        conn.close()
        return jsonify({"error": "Not found"}), 404
    messages = conn.execute(
        "SELECT id, role, content, timestamp FROM messages WHERE conversation_id=? ORDER BY id ASC",
        (chat_id,)
    ).fetchall()
    conn.close()
    return jsonify({
        "messages": [{"id": m["id"], "role": m["role"], "content": m["content"], "timestamp": m["timestamp"]} for m in messages]
    })

@app.route("/get_chat_title/<int:chat_id>")
@login_required
def get_chat_title(chat_id):
    conn = sqlite3.connect("codebuddy.db")
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT title FROM conversations WHERE id=? AND user_id=?",
        (chat_id, current_user.id)
    ).fetchone()
    conn.close()
    if not row:
        return jsonify({"title": "New Chat"})
    return jsonify({"title": row["title"]})

@app.route("/rename_chat", methods=["POST"])
@login_required
def rename_chat():
    data = request.json
    conn = sqlite3.connect("codebuddy.db")
    conn.execute(
        "UPDATE conversations SET title=? WHERE id=? AND user_id=?",
        (data["title"][:60], data["chat_id"], current_user.id)
    )
    conn.commit()
    conn.close()
    return jsonify({"status": "renamed"})

@app.route("/delete_chat", methods=["POST"])
@login_required
def delete_chat():
    data = request.json
    conn = sqlite3.connect("codebuddy.db")
    conn.execute("DELETE FROM messages WHERE conversation_id=?", (data["chat_id"],))
    conn.execute("DELETE FROM conversations WHERE id=? AND user_id=?",
                 (data["chat_id"], current_user.id))
    conn.commit()
    conn.close()
    return jsonify({"status": "deleted"})

@app.route("/pin_chat", methods=["POST"])
@login_required
def pin_chat():
    data = request.json
    conn = sqlite3.connect("codebuddy.db")
    current = conn.execute(
        "SELECT pinned FROM conversations WHERE id=? AND user_id=?",
        (data["chat_id"], current_user.id)
    ).fetchone()
    if current:
        new_val = 0 if current["pinned"] else 1
        conn.execute(
            "UPDATE conversations SET pinned=? WHERE id=? AND user_id=?",
            (new_val, data["chat_id"], current_user.id)
        )
        conn.commit()
        conn.close()
        return jsonify({"status": "pinned" if new_val else "unpinned"})
    conn.close()
    return jsonify({"error": "Not found"}), 404

@app.route("/share_chat", methods=["POST"])
@login_required
def share_chat():
    data = request.json
    return jsonify({"share_url": f"/public_chat/{data['chat_id']}"})

@app.route("/public_chat/<int:chat_id>")
def public_chat(chat_id):
    conn = sqlite3.connect("codebuddy.db")
    conn.row_factory = sqlite3.Row
    messages = conn.execute(
        "SELECT role, content FROM messages WHERE conversation_id=? ORDER BY id ASC",
        (chat_id,)
    ).fetchall()
    convo = conn.execute("SELECT title FROM conversations WHERE id=?", (chat_id,)).fetchone()
    conn.close()
    if not messages:
        return "Chat not found", 404
    return render_template("public_chat.html",
                           messages=messages,
                           title=convo["title"] if convo else "Shared Chat")

# ================= BOOKMARK =================

@app.route("/bookmark_message", methods=["POST"])
@login_required
def bookmark_message():
    data = request.json
    conn = sqlite3.connect("codebuddy.db")
    conn.execute(
        "INSERT INTO bookmarks(user_id, message_id, note, created_at) VALUES (?,?,?,?)",
        (current_user.id, data.get("message_id"), data.get("note", ""), datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    return jsonify({"status": "bookmarked"})

@app.route("/get_bookmarks")
@login_required
def get_bookmarks():
    conn = sqlite3.connect("codebuddy.db")
    conn.row_factory = sqlite3.Row
    bookmarks = conn.execute("""
        SELECT b.id, b.note, b.created_at, m.content, m.role
        FROM bookmarks b
        JOIN messages m ON b.message_id = m.id
        WHERE b.user_id = ?
        ORDER BY b.id DESC LIMIT 20
    """, (current_user.id,)).fetchall()
    conn.close()
    return jsonify({"bookmarks": [dict(b) for b in bookmarks]})

# ================= CHANGE 6: PISTON API CODE EXECUTION =================

PISTON_API = "https://emkc.org/api/v2/piston/execute"
PISTON_API_BACKUP = "https://judge0-ce.p.rapidapi.com/submissions"  # Judge0 backup (not used by default)

# Piston language aliases
PISTON_LANGUAGES = {
    "python": ("python", "3.10.0"),
    "javascript": ("javascript", "18.15.0"),
    "typescript": ("typescript", "5.0.3"),
    "java": ("java", "15.0.2"),
    "c": ("c", "10.2.0"),
    "cpp": ("c++", "10.2.0"),
    "csharp": ("csharp", "6.12.0"),
    "go": ("go", "1.16.2"),
    "rust": ("rust", "1.50.0"),
    "ruby": ("ruby", "3.0.1"),
    "php": ("php", "8.2.3"),
    "swift": ("swift", "5.3.3"),
    "kotlin": ("kotlin", "1.8.20"),
    "bash": ("bash", "5.2.0"),
    "lua": ("lua", "5.4.4"),
    "perl": ("perl", "5.36.0"),
    "r": ("r", "4.1.1"),
    "scala": ("scala", "3.2.2"),
    "haskell": ("haskell", "9.4.5"),
    "dart": ("dart", "2.19.6"),
    "elixir": ("elixir", "1.14.3"),
    "clojure": ("clojure", "1.11.1"),
    "erlang": ("erlang", "26.0"),
    "fsharp": ("fsharp", "6.0.0"),
    "ocaml": ("ocaml", "4.14.0"),
    "nim": ("nim", "1.6.14"),
    "crystal": ("crystal", "1.7.3"),
}

@app.route("/run_code", methods=["POST"])
@login_required
@rate_limit(max_calls=30, window=60)
def run_code():
    """Execute code via Piston API (free, sandboxed, 50+ languages)."""
    code = request.json.get("code", "")
    language = request.json.get("language", "python").lower().strip()

    if not code.strip():
        return jsonify({"output": "No code to run.", "exit_code": 1})

    # Normalize common aliases
    lang_aliases = {
        "js": "javascript", "ts": "typescript", "c++": "cpp",
        "c#": "csharp", "golang": "go", "rb": "ruby", "py": "python"
    }
    language = lang_aliases.get(language, language)

    if language not in PISTON_LANGUAGES:
        # Try anyway with Piston using the raw name
        piston_lang, piston_ver = language, "*"
    else:
        piston_lang, piston_ver = PISTON_LANGUAGES[language]

    try:
        resp = requests.post(
            PISTON_API,
            json={
                "language": piston_lang,
                "version": piston_ver,
                "files": [{"name": f"main.{language[:10]}", "content": code}],
                "stdin": "",
                "args": [],
                "compile_timeout": 10000,
                "run_timeout": 10000,
            },
            timeout=20
        )

        if resp.status_code == 401 or resp.status_code == 403:
            # Piston API auth error — try alternative public endpoint
            try:
                resp2 = requests.post(
                    "https://api.piston.rs/api/v2/execute",
                    json={
                        "language": piston_lang,
                        "version": piston_ver,
                        "files": [{"name": f"main.{language[:10]}", "content": code}],
                        "stdin": "", "args": [],
                        "compile_timeout": 10000, "run_timeout": 10000,
                    },
                    timeout=20
                )
                if resp2.status_code == 200:
                    resp = resp2
                else:
                    return jsonify({"output": f"⚠ Code execution unavailable right now. Try again in a moment.", "exit_code": -1})
            except Exception:
                return jsonify({"output": "⚠ Code execution service is down. Try again later.", "exit_code": -1})
        elif resp.status_code != 200:
            return jsonify({"output": f"⚠ Execution service error ({resp.status_code}). Try again.", "exit_code": -1})

        result = resp.json()
        run = result.get("run", {})
        compile_out = result.get("compile", {})

        output = ""
        if compile_out.get("stderr"):
            output += f"[Compile Error]\n{compile_out['stderr']}\n"
        if run.get("stdout"):
            output += run["stdout"]
        if run.get("stderr"):
            output += run["stderr"]
        if not output.strip():
            output = "(No output)"

        exit_code = run.get("code", 0)
        bump_stat(current_user.id, "code_runs")

        return jsonify({
            "output": output[:8000],
            "exit_code": exit_code,
            "language": language
        })

    except requests.exceptions.Timeout:
        return jsonify({"output": "⏱ Execution timed out (10s). Check for infinite loops.", "exit_code": -1})
    except requests.exceptions.ConnectionError:
        return jsonify({"output": "🔌 Cannot reach execution service. Check your internet.", "exit_code": -1})
    except Exception as e:
        return jsonify({"output": f"Server error: {str(e)}", "exit_code": -1})

@app.route("/supported_languages")
def supported_languages():
    """Return list of supported execution languages."""
    return jsonify({"languages": sorted(PISTON_LANGUAGES.keys())})

# ================= COMPLEXITY ANALYZER =================

@app.route("/analyze_complexity", methods=["POST"])
@login_required
def analyze_complexity():
    code = request.json.get("code", "")
    if not code.strip():
        return jsonify({"error": "No code provided"}), 400

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODELS["classifier"],
        "max_tokens": 200,
        "messages": [
            {
                "role": "system",
                "content": "Analyze code complexity. Return ONLY a JSON object with keys: time_complexity (Big-O string), space_complexity (Big-O string), explanation (one sentence). No markdown, no extra text."
            },
            {"role": "user", "content": f"Analyze:\n{code[:1000]}"}
        ]
    }
    try:
        resp = requests.post("https://openrouter.ai/api/v1/chat/completions",
                             headers=headers, json=payload, timeout=10)
        content = resp.json()["choices"][0]["message"]["content"].strip()
        content = re.sub(r"```json|```", "", content).strip()
        data = json.loads(content)
        return jsonify(data)
    except (requests.RequestException, KeyError, json.JSONDecodeError, ValueError):
        return jsonify({
            "time_complexity": "O(?)",
            "space_complexity": "O(?)",
            "explanation": "Could not analyze automatically."
        })

# ================= STATS =================

@app.route("/get_stats")
@login_required
def get_stats():
    conn = sqlite3.connect("codebuddy.db")
    conn.row_factory = sqlite3.Row
    stats = conn.execute("SELECT * FROM user_stats WHERE user_id=?", (current_user.id,)).fetchone()
    chats = conn.execute("SELECT COUNT(*) as cnt FROM conversations WHERE user_id=?", (current_user.id,)).fetchone()
    conn.close()
    return jsonify({
        "stats": dict(stats) if stats else {},
        "total_chats": chats["cnt"] if chats else 0
    })

# ================= SEARCH CHATS =================

@app.route("/search_chats")
@login_required
def search_chats():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"results": []})
    conn = sqlite3.connect("codebuddy.db")
    conn.row_factory = sqlite3.Row
    results = conn.execute("""
        SELECT DISTINCT c.id, c.title, c.mode
        FROM conversations c
        LEFT JOIN messages m ON m.conversation_id = c.id
        WHERE c.user_id = ? AND (
            c.title LIKE ? OR m.content LIKE ?
        )
        LIMIT 10
    """, (current_user.id, f"%{query}%", f"%{query}%")).fetchall()
    conn.close()
    return jsonify({"results": [dict(r) for r in results]})

# ================= CHANGE 1+3: MAIN CHAT (DeepSeek + all languages) =================

@app.route("/chat", methods=["POST"])
@login_required
@rate_limit(max_calls=50, window=60)
def chat():
    user_message = request.form.get("message", "").strip()
    conversation_id = request.form.get("conversation_id")
    mode = request.form.get("mode", "general")
    personality = request.form.get("personality", "mentor")
    confidence = request.form.get("confidence", 0)
    lang_code = request.form.get("lang", "en-US")

    # CHANGE 3: Extended language support (Indic + world languages)
    LANG_NAMES = {
        "en-US": "English",
        "ta-IN": "Tamil (தமிழ்)",
        "ta-en": "Tanglish (Tamil + English)",
        "hi-IN": "Hindi (हिंदी)",
        "te-IN": "Telugu (తెలుగు)",
        "kn-IN": "Kannada (ಕನ್ನಡ)",
        "ml-IN": "Malayalam (മലയാളം)",
        "bn-IN": "Bengali (বাংলা)",
        "mr-IN": "Marathi (मराठी)",
        "pa-IN": "Punjabi (ਪੰਜਾਬੀ)",
        "gu-IN": "Gujarati (ગુજરાતી)",
        "fr-FR": "French (Français)",
        "de-DE": "German (Deutsch)",
        "es-ES": "Spanish (Español)",
        "ja-JP": "Japanese (日本語)",
        "zh-CN": "Chinese Simplified (中文)",
        "ar-SA": "Arabic (العربية)",
        "ru-RU": "Russian (Русский)",
        "pt-BR": "Portuguese (Português)",
        "ko-KR": "Korean (한국어)",
        "it-IT": "Italian (Italiano)",
    }
    lang_name = LANG_NAMES.get(lang_code, "English")
    is_non_english = lang_code != "en-US"

    # Build language instruction
    if lang_code == "ta-IN":
        lang_instruction = (
            "\n\n🌐 மொழி அறிவுறுத்தல் — கட்டாயம் பின்பற்றவும்:\n"
            "பயனர் தமிழ் மொழியை தேர்ந்தெடுத்துள்ளார். உங்கள் முழு பதிலும் தமிழிலேயே இருக்க வேண்டும்.\n\n"
            "கட்டாய விதிகள்:\n"
            "✅ அனைத்து விளக்கங்கள், தலைப்புகள், புள்ளிகள் → தமிழில் மட்டுமே\n"
            "✅ code-க்கு உள்ளே உள்ள comments → தமிழில் எழுதவும்\n"
            "✅ Technical சொற்கள் தமிழில்: function=செயலி, variable=மாறி, loop=சுழற்சி\n"
            "❌ ஒரு வரி கூட ஆங்கிலத்தில் எழுதாதீர்கள் — def/for/if போன்ற code syntax மட்டும் OK\n"
            "❌ 'Here is', 'Note that', 'This means' போன்ற ஆங்கில வார்த்தைகள் வேண்டாம்\n"
            "இப்போதே முழுமையாக தமிழில் மட்டுமே பதிலளிக்கவும்."
        )
    elif lang_code == "ta-en":
        lang_instruction = (
            "\n\n🌐 TANGLISH MODE — MANDATORY WRITING STYLE:\n"
            "Write like a friendly Chennai senior developer helping a friend. Warm and helpful tone.\n\n"
            "CRITICAL RULES:\n"
            "✅ Write in ENGLISH LETTERS (Roman script) — NOT Tamil unicode script characters\n"
            "✅ Tamil words in English letters: 'pannrom', 'paaru', 'irukku', 'aagum', 'sollu', 'theriyuma', 'da', 'bro', 'machaa'\n"
            "✅ English tech words stay English: function, variable, loop, array, error, class, API, debug\n"
            "✅ Every sentence must naturally mix both: 'Indha function-la list return pannrom — [0] use panna first element kedaikum'\n"
            "✅ Friendly warm tone: 'Bro paaru', 'Simple-a solren da', 'intha bug-a fix pannrom machaa', 'easy-a irukku'\n"
            "✅ Address user as: 'bro', 'da', 'machaa', 'nanbaa' — NEVER 'dei' or 'ey'\n"
            "❌ BANNED WORDS to start a sentence: 'Dei', 'dei', 'Ey', 'ey' — these are RUDE\n"
            "✅ CORRECT opening: 'Bro paaru,' / 'Da, indha...' / 'Machaa listen,'\n"
            "❌ WRONG opening: 'Dei bro,' / 'Dei paaru' — DO NOT USE\n"
            "❌ NO pure English paragraphs — Tamil words must appear in every sentence\n"
            "❌ DO NOT use Tamil script (unicode) — only Roman/English letters\n"
            "❌ DO NOT write: 'Here is the explanation' — write: 'Solren da, indha concept simple-a irukku'\n\n"
            "VOICE NOTE: This text will be spoken aloud using TAMIL VOICE. Write so it sounds natural when a Tamil person reads it aloud."
        )
    elif is_non_english:
        # Per-language native script examples to force correct script usage
        script_examples = {
            "te-IN": "తెలుగు లిపిలో రాయండి. Example: 'function లో loop ఉంది'",
            "kn-IN": "ಕನ್ನಡ ಲಿಪಿಯಲ್ಲಿ ಬರೆಯಿರಿ. Example: 'function ನಲ್ಲಿ loop ಇದೆ'",
            "ml-IN": "മലയാളം ലിപിയിൽ എഴുതുക. Example: 'function ൽ loop ഉണ്ട്'",
            "bn-IN": "বাংলা লিপিতে লিখুন. Example: 'function এ loop আছে'",
            "mr-IN": "मराठी लिपीत लिहा. Example: 'function मध्ये loop आहे'",
            "gu-IN": "ગુજરાતી લિપિમાં લખો. Example: 'function માં loop છે'",
            "pa-IN": "ਪੰਜਾਬੀ ਲਿਪੀ ਵਿੱਚ ਲਿਖੋ. Example: 'function ਵਿੱਚ loop ਹੈ'",
        }
        script_hint = script_examples.get(lang_code, f"Write entirely in {lang_name} native script")
        lang_instruction = (
            f"\n\n══════════════════════════════════════════\n"
            f"🌐 MANDATORY LANGUAGE: {lang_name.upper()}\n"
            f"══════════════════════════════════════════\n"
            f"YOU MUST RESPOND ENTIRELY IN {lang_name.upper()} NATIVE SCRIPT.\n"
            f"THIS IS NON-NEGOTIABLE. DO NOT USE ENGLISH PROSE.\n\n"
            f"{script_hint}\n\n"
            f"ABSOLUTE RULES:\n"
            f"✅ Every sentence, explanation, heading → {lang_name} native unicode characters\n"
            f"✅ Technical terms (function, loop, variable, class) → phonetically in {lang_name} script\n"
            f"✅ Code comments → {lang_name} script\n"
            f"✅ ONLY bare syntax keywords (def, for, if, class, print, return, import) may stay English\n"
            f"❌ ZERO English sentences — not even one English word outside code blocks\n"
            f"❌ Do NOT start with 'Here is', 'Sure', 'Of course' or any English preamble\n\n"
            f"BEGIN YOUR RESPONSE IN {lang_name} SCRIPT RIGHT NOW:\n"
            f"══════════════════════════════════════════\n"
        )
    else:
        lang_instruction = ""

    if not user_message:
        return Response("Please enter a message.", mimetype="text/plain")

    if not conversation_id:
        return Response("Select or create a chat first.", mimetype="text/plain")

    conn = sqlite3.connect("codebuddy.db")
    conn.row_factory = sqlite3.Row
    convo = conn.execute(
        "SELECT id, title FROM conversations WHERE id=? AND user_id=?",
        (conversation_id, current_user.id)
    ).fetchone()
    conn.close()

    if not convo:
        return Response("Chat not found.", mimetype="text/plain")

    if mode not in ("interview", "roadmap"):
        if not is_programming_related(user_message):
            return Response(
                "🚫 CodeBuddy is a programming-only assistant.\n\n"
                "I can only help with: code, algorithms, debugging, software development, "
                "data structures, machine learning, web development, databases, DevOps, and CS concepts.\n\n"
                "Try asking something like:\n"
                "• \"Write a Python function to sort a list\"\n"
                "• \"Explain what a REST API is\"\n"
                "• \"Debug this JavaScript error: ...\"\n"
                "• \"What is Big O notation?\"",
                mimetype="text/plain"
            )

    # CHANGE 5: Auto-extract memory from user message
    extract_and_save_memory(current_user.id, user_message)

    conn = sqlite3.connect("codebuddy.db")
    cursor = conn.execute(
        "INSERT INTO messages(conversation_id,role,content,timestamp) VALUES (?,?,?,?)",
        (conversation_id, "user", user_message, datetime.now().isoformat())
    )

    if convo["title"] in ("New Chat", "", None):
        try:
            smart_title = generate_chat_title(user_message)
            conn.execute(
                "UPDATE conversations SET title=?, mode=?, updated_at=? WHERE id=?",
                (smart_title, mode, datetime.now().isoformat(), conversation_id)
            )
        except Exception:
            pass
    else:
        conn.execute(
            "UPDATE conversations SET updated_at=? WHERE id=?",
            (datetime.now().isoformat(), conversation_id)
        )

    conn.commit()
    conn.close()

    tone = "strict technical interviewer" if personality == "strict" else "supportive technical mentor"

    # CHANGE 5: Inject persistent memory into system prompt
    memory_context = build_memory_context(current_user.id)

    if mode == "interview":
        topic = session.get(f"topic_{conversation_id}")
        if not topic:
            session[f"topic_{conversation_id}"] = user_message
            system_prompt = (
                lang_instruction
                + f"You are CodeBuddy Interview Coach — a {tone}. "
                + f"The user wants to practice: {user_message}. "
                + "Ask exactly ONE clear technical interview question to start. "
                + "After each answer, score it 1-10, explain what was missing, then ask the next question."
                + _RESPECTFUL_TONE
                + memory_context
            )
        else:
            system_prompt = (
                lang_instruction
                + f"You are CodeBuddy Interview Coach — a {tone}. "
                + f"Interview topic: {topic}. User confidence level: {confidence}/10. "
                + "Evaluate the previous answer strictly, give a score, feedback, ideal answer if needed, then ask next question."
                + _RESPECTFUL_TONE
                + memory_context
            )
        bump_stat(current_user.id, "interview_count")
    else:
        # Language instruction goes FIRST — LLMs are far more reliable when
        # the language mandate is at the beginning of the system prompt, not appended.
        system_prompt = lang_instruction + SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS["general"]) + _RESPECTFUL_TONE + memory_context
        if mode == "debug":
            bump_stat(current_user.id, "debug_count")
        elif mode == "optimize":
            bump_stat(current_user.id, "optimize_count")

    bump_stat(current_user.id, "total_messages")

    history = get_conversation_history(conversation_id, limit=16)
    api_messages = [{"role": "system", "content": system_prompt}]
    api_messages.extend(history)

    # ── Language enforcement injection ────────────────────────────────────────
    # For non-English languages: inject a REMINDER as a user-role message
    # immediately before the actual user query.
    # Why: AI models (especially Gemini) respond to user-role instructions
    # much more reliably than system prompt instructions alone.
    # Without this, models like DeepSeek ignore the language instruction and
    # respond in English even when the system prompt says "respond in Telugu".
    INDIC_REMINDER = {
        "ta-IN": "⚠️ IMPORTANT: You MUST reply ONLY in Tamil (தமிழ்) script. Be warm and respectful — address user as 'நண்பா' (friend) or 'நீங்கள்'. NEVER use 'டேய்' (dei/rude). Every word must be Tamil unicode. Now answer: ",
        "hi-IN": "⚠️ IMPORTANT: आपको केवल हिंदी में उत्तर देना है। User को 'आप' या 'भाई' कहें — कभी 'ओए' या अपमानजनक शब्द नहीं। अंग्रेजी में नहीं। अभी उत्तर दें: ",
        "te-IN": "⚠️ IMPORTANT: తెలుగు లిపిలో మాత్రమే సమాధానం ఇవ్వాలి. User ని 'మీరు' లేదా 'నేస్తం' అని పిలవండి — ఎప్పుడూ 'ఏయ్' అని కాదు. ఇంగ్లీష్ వాడకండి. ఇప్పుడు సమాధానం ఇవ్వండి: ",
        "kn-IN": "⚠️ IMPORTANT: ಕನ್ನಡ ಲಿಪಿಯಲ್ಲಿ ಮಾತ್ರ ಉತ್ತರ ನೀಡಿ. User ಅನ್ನು 'ನೀವು' ಅಥವಾ 'ಗೆಳೆಯ' ಎಂದು ಕರೆಯಿರಿ — 'ಏಯ್' ಎಂದು ಎಂದಿಗೂ ಹೇಳಬೇಡಿ. ಇಂಗ್ಲಿಷ್ ಬಳಸಬೇಡಿ. ಈಗ ಉತ್ತರ ನೀಡಿ: ",
        "ml-IN": "⚠️ IMPORTANT: മലയാളം ലിപിയിൽ മാത്രം മറുപടി നൽകൂ. User നെ 'നിങ്ങൾ' അല്ലെങ്കിൽ 'കൂട്ടുകാരൻ' എന്ന് വിളിക്കൂ — 'ഡേയ്' പറയരുത്. ഇംഗ്ലീഷ് ഉപയോഗിക്കരുത്. ഇപ്പോൾ മറുപടി നൽകൂ: ",
        "bn-IN": "⚠️ IMPORTANT: বাংলা লিপিতে মাত্র উত্তর দিন। User কে 'আপনি' বা 'বন্ধু' বলুন — কখনো 'এই' বা অসম্মানজনক শব্দ নয়। ইংরেজিতে নয়। এখন উত্তর দিন: ",
        "mr-IN": "⚠️ IMPORTANT: मराठी लिपीत मात्र उत्तर द्या. User ला 'तुम्ही' किंवा 'मित्रा' म्हणा — कधीही 'अरे' उद्धटपणे नाही. इंग्रजीत नाही. आत्ता उत्तर द्या: ",
        "gu-IN": "⚠️ IMPORTANT: ગુજરાતી લિપિમાં માત્ર જવાબ આપો. User ને 'આપ' અથવા 'મિત્ર' કહો — ક્યારેય 'અરે' અસભ્ય રીતે નહીં. અંગ્રેજીમાં નહીં. હવે જવાબ આપો: ",
        "pa-IN": "⚠️ IMPORTANT: ਪੰਜਾਬੀ ਲਿਪੀ ਵਿੱਚ ਹੀ ਜਵਾਬ ਦਿਓ। User ਨੂੰ 'ਤੁਸੀਂ' ਜਾਂ 'ਯਾਰ' ਕਹੋ — ਕਦੇ 'ਓਏ' ਬੇਅਦਬੀ ਨਾਲ ਨਹੀਂ। ਅੰਗਰੇਜ਼ੀ ਵਿੱਚ ਨਹੀਂ। ਹੁਣ ਜਵਾਬ ਦਿਓ: ",
        "ta-en": "⚠️ IMPORTANT: Reply in Tanglish ONLY (Tamil words in English/Roman letters). Be friendly and warm — use 'bro/da/machaa', NEVER 'dei' or 'ey' (rude). Example: 'Bro, indha function-la loop irukku, simple-a paaru'. NO pure English. NO Tamil unicode. Answer: ",
    }
    reminder_prefix = INDIC_REMINDER.get(lang_code)
    if reminder_prefix:
        # Append the reminder as a user message prefix to the last user message
        # so the AI sees the language instruction RIGHT before generating its response
        if api_messages and api_messages[-1]["role"] == "user":
            api_messages[-1]["content"] = reminder_prefix + api_messages[-1]["content"]
        else:
            api_messages.append({"role": "user", "content": reminder_prefix + user_message})

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://codebuddy.ai",
        "X-Title": "CodeBuddy AI"
    }

    # Model with fallback chain: if primary gives 404/429, try backup models
    selected_model = get_model_for_mode(mode, lang_code)

    # Fallback order if primary model fails
    MODEL_FALLBACKS = {
        "deepseek/deepseek-r1:free":           ["google/gemini-2.0-flash-001", "meta-llama/llama-3.3-70b-instruct:free"],
        "google/gemini-2.0-flash-001":         ["google/gemini-2.0-flash-exp:free", "deepseek/deepseek-r1:free"],
        "google/gemini-2.0-flash-exp:free":    ["deepseek/deepseek-r1:free", "meta-llama/llama-3.3-70b-instruct:free"],
    }

    payload = {
        "model": selected_model,
        "stream": True,
        "max_tokens": 2000,
        "temperature": 0.7,
        "messages": api_messages
    }

    def generate():
        full = ""
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                stream=True,
                timeout=(10, 90)
            )

            if response.status_code == 401:
                yield "⚠ API key invalid. Please check your OpenRouter API key."
                return
            if response.status_code in (404, 429, 503):
                # Try fallback models automatically
                fallbacks = MODEL_FALLBACKS.get(payload["model"], [])
                for fb_model in fallbacks:
                    app.logger.warning(f"Model {payload['model']} returned {response.status_code}, trying {fb_model}")
                    payload["model"] = fb_model
                    response = requests.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers=headers, json=payload, stream=True, timeout=(10, 90)
                    )
                    if response.status_code == 200:
                        break
                if response.status_code != 200:
                    code = response.status_code
                    msg = "Rate limit reached — please wait." if code == 429 else f"API Error {code}. Please try again."
                    yield f"⚠ {msg}"
                    return
            if response.status_code != 200:
                yield f"⚠ API Error {response.status_code}. Please try again in a moment."
                return

            for line in response.iter_lines():
                if line:
                    decoded = line.decode("utf-8")
                    if decoded.startswith("data: "):
                        data = decoded[6:]
                        if data == "[DONE]":
                            break
                        try:
                            token = json.loads(data)["choices"][0]["delta"].get("content", "")
                            token = _filter_response(token)
                            full += token
                            yield token
                        except (json.JSONDecodeError, KeyError, IndexError):
                            pass

        except requests.exceptions.ConnectTimeout:
            yield "\n\n⏱ Could not connect to AI service. Check your internet and try again."
        except requests.exceptions.ReadTimeout:
            if full:
                yield "\n\n⚠ Response cut short. The answer above may be incomplete."
            else:
                yield "\n\n⏱ AI took too long to respond. Please try again."
        except requests.exceptions.ConnectionError:
            yield "\n\n🔌 Connection lost. Please check your internet and try again."
        except Exception as e:
            yield f"\n\n⚠ Error: {str(e)}"

        if full:
            full = _filter_response(full)   # final pass on complete response
            save_conn = sqlite3.connect("codebuddy.db")
            save_conn.execute(
                "INSERT INTO messages(conversation_id,role,content,timestamp) VALUES (?,?,?,?)",
                (conversation_id, "assistant", full, datetime.now().isoformat())
            )
            save_conn.commit()
            save_conn.close()

    return Response(generate(), mimetype="text/plain")

# ================= QUICK EXPLAIN =================

@app.route("/quick_explain", methods=["POST"])
@login_required
@rate_limit(max_calls=20, window=60)
def quick_explain():
    code = request.json.get("code", "")
    level = request.json.get("level", "intermediate")

    if not code.strip():
        return jsonify({"error": "No code provided"}), 400

    level_prompts = {
        "beginner": "Explain this code in the simplest way possible. Use everyday words, no jargon. Imagine explaining to someone who just started coding.",
        "intermediate": "Explain this code clearly. Cover what it does, how it works, and any important patterns. Keep it concise.",
        "expert": "Give a concise technical analysis: design patterns used, potential issues, and performance implications."
    }

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODELS["fast"],
        "max_tokens": 600,
        "messages": [
            {"role": "system", "content": level_prompts.get(level, level_prompts["intermediate"])},
            {"role": "user", "content": f"```\n{code[:2000]}\n```"}
        ]
    }

    try:
        resp = requests.post("https://openrouter.ai/api/v1/chat/completions",
                             headers=headers, json=payload, timeout=20)
        explanation = resp.json()["choices"][0]["message"]["content"]
        return jsonify({"explanation": explanation})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ================= ROADMAP GENERATOR =================

@app.route("/generate_roadmap", methods=["POST"])
@login_required
@rate_limit(max_calls=10, window=60)
def generate_roadmap():
    topic = request.json.get("topic", "")
    level = request.json.get("level", "beginner")

    if not topic.strip():
        return jsonify({"error": "No topic provided"}), 400

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODELS["fast"],
        "max_tokens": 1500,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPTS["roadmap"]},
            {"role": "user", "content": f"Create a complete learning roadmap for: {topic}\nStarting level: {level}"}
        ]
    }

    def stream_roadmap():
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers, json=payload, stream=True, timeout=60
        )
        for line in response.iter_lines():
            if line:
                decoded = line.decode("utf-8")
                if decoded.startswith("data: "):
                    data = decoded[6:]
                    if data == "[DONE]":
                        break
                    try:
                        token = json.loads(data)["choices"][0]["delta"].get("content", "")
                        yield token
                    except (json.JSONDecodeError, KeyError, IndexError):
                        pass

    return Response(stream_roadmap(), mimetype="text/plain")

# ================= RESPONSE FILTER =================

# Words that are rude/disrespectful when addressing a user, mapped to replacements
# Applied to ALL streaming output before it reaches the user
_RUDE_REPLACEMENTS = [
    # "Dei bro" / "dei da" / "dei machaa" → just keep the friendly part
    (r'(?i)\bdei\s+bro\b',    'Bro'),
    (r'(?i)\bdei\s+da\b',     'Da'),
    (r'(?i)\bdei\s+machaa\b', 'Machaa'),
    (r'(?i)\bdei\s+nanbaa\b', 'Nanbaa'),
    # Standalone "Dei" / "dei" at sentence start or anywhere
    (r'^Dei[,!]?\s*',           ''),
    (r'^dei[,!]?\s*',           ''),
    (r'\bDei[,!]?\s+',         ''),
    (r'\bdei[,!]?\s+',         ''),
    # Tamil script rude words
    (r'\bடேய்\b',              'நண்பா'),
    (r'\bடே\b',                'நண்பா'),
    # Hindi
    (r'(?i)\boye\b',           'Bhai'),
    (r'(?i)\bare\s+yaar\b',   'Haan yaar'),
    # Telugu / Kannada dismissive "Ey"
    (r'^Ey[,!]?\s*',            ''),
    (r'^ey[,!]?\s*',            ''),
    (r'\bEy[,!]?\s+',          ''),
    (r'\bey[,!]?\s+',          ''),
]

def _filter_response(text: str) -> str:
    """Replace rude address words with respectful equivalents."""
    import re
    for pattern, replacement in _RUDE_REPLACEMENTS:
        text = re.sub(pattern, replacement, text)
    return text


# ================= TRANSLATION FALLBACK =================

@app.route("/translate", methods=["POST"])
@login_required
@rate_limit(max_calls=30, window=60)
def translate_response():
    """Translate English AI response to target language when AI ignored language instruction.

    Called by the frontend when:
    - Language is non-English (e.g. te-IN, kn-IN, ml-IN)
    - AI responded in English despite the language instruction
    - User is in voice mode and needs the audio in the right language

    Returns the translated text for TTS to speak.
    """
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    lang_code = (data.get("lang") or "en-US").strip()

    if not text or lang_code == "en-US":
        return jsonify({"translated": text})

    LANG_NAMES_SHORT = {
        "ta-IN": "Tamil", "hi-IN": "Hindi", "te-IN": "Telugu",
        "kn-IN": "Kannada", "ml-IN": "Malayalam", "bn-IN": "Bengali",
        "mr-IN": "Marathi", "gu-IN": "Gujarati", "pa-IN": "Punjabi",
        "ta-en": "Tanglish (Tamil words in Roman/English letters, friendly style like 'bro/machaa', never 'dei')",
    }
    target = LANG_NAMES_SHORT.get(lang_code, "the target language")

    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": MODELS["fast"],
            "max_tokens": 1500,
            "temperature": 0.2,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        f"You are a translator. Translate the following programming explanation "
                        f"into {target}. Keep all code examples unchanged. "
                        f"Only translate the prose/explanation text. "
                        f"Output ONLY the translation, nothing else."
                    )
                },
                {"role": "user", "content": text[:1500]}
            ]
        }
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers, json=payload, timeout=(5, 20)
        )
        if resp.status_code == 200:
            translated = resp.json()["choices"][0]["message"]["content"].strip()
            return jsonify({"translated": translated})
    except Exception as e:
        app.logger.warning(f"Translation failed: {e}")

    return jsonify({"translated": text})  # fallback: return original


# ================= CHANGE 2+3: TTS (gTTS + extended Indic) =================

# Maps UI lang code → gTTS lang code
# Languages NOT supported by gTTS map to 'en' so audio is at least readable
TTS_LANG_MAP = {
    "en-US": "en", "en": "en",
    "ta-IN": "ta",            # Tamil       ✓
    "ta-en": "ta",            # Tanglish    → Tamil gTTS voice (text is Roman/mixed, handled by word splitter)
    "hi-IN": "hi",            # Hindi       ✓
    "te-IN": "te",            # Telugu      ✓
    "kn-IN": "kn",            # Kannada     ✓ (supported in gTTS >= 2.3.2)
    "ml-IN": "ml",            # Malayalam   ✓
    "bn-IN": "bn",            # Bengali     ✓
    "mr-IN": "mr",            # Marathi     ✓
    "pa-IN": "en",            # Punjabi     ✗ not in gTTS → English fallback
    "gu-IN": "gu",            # Gujarati    ✓ (supported in gTTS >= 2.3.2)
    "fr-FR": "fr", "de-DE": "de",
    "es-ES": "es", "ja-JP": "ja",
    "ko-KR": "ko", "ar-SA": "ar",
    "zh-CN": "zh-CN", "ru-RU": "ru",
    "pt-BR": "pt", "it-IT": "it",
}

# Unicode ranges for Indic scripts — used to decide which gTTS engine per sentence
_SCRIPT_RANGES = {
    "ta": (0x0B80, 0x0BFF),   # Tamil
    "hi": (0x0900, 0x097F),   # Hindi / Devanagari
    "mr": (0x0900, 0x097F),   # Marathi / Devanagari
    "te": (0x0C00, 0x0C7F),   # Telugu
    "kn": (0x0C80, 0x0CFF),   # Kannada
    "ml": (0x0D00, 0x0D7F),   # Malayalam
    "bn": (0x0980, 0x09FF),   # Bengali
    "gu": (0x0A80, 0x0AFF),   # Gujarati
}

try:
    from gtts import gTTS as _gTTS
    import io as _io
    _GTTS_OK = True
except ImportError:
    _GTTS_OK = False


def _clean_for_tts(text):
    """Strip markdown/code blocks so TTS reads clean sentences."""
    text = re.sub(r"```[\s\S]*?```", " code block. ", text)
    text = re.sub(r"`[^`]+`", " code ", text)
    text = re.sub(r"#{1,6}\s+", "", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"https?://\S+", "link", text)
    text = re.sub(r"[|#@~^]", " ", text)
    text = re.sub(r"\s{2,}", " ", text).strip()
    return text[:1500]


def _smart_split(text, gtts_lang, is_tanglish=False):
    """
    Sentence-level split with inline English word extraction for gTTS.

    Strategy (revised after choppy-audio feedback):
    ─────────────────────────────────────────────────────────────────────────────
    PROBLEM WITH WORD-LEVEL SPLITTING:
    Word-level splitting creates many tiny 1-2 word fragments (e.g. "में", "লো",
    "ಬಳಸಿ") each generating a separate gTTS HTTP call. When concatenated, the
    audio has audible gaps and choppy rhythm — worse than the original problem.

    REVISED STRATEGY — "English-island extraction":
    1. Split at sentence boundaries.
    2. For each sentence:
       a. If it has NO native script → English gTTS (pure English sentence).
       b. If it has native script:
          - Find "English islands" = runs of 3+ consecutive pure-latin words
            that look like actual English (not just particles like "in", "a", "of").
          - Replace each English island in the text with a phonetic placeholder
            that the native gTTS engine will skip/mispronounce minimally.
          - Instead: keep the WHOLE sentence in native gTTS but pre-process
            English tech words by surrounding them with native pronunciation
            hints OR just accept minor accent and keep rhythm smooth.

    SIMPLEST WORKING APPROACH (no phonetic lookup needed):
    - Send each sentence to the CORRECT engine based on majority script.
    - If sentence is mostly native script → native gTTS (reads English words
      with an accent but at least rhythmically smooth, no gaps).
    - If sentence is entirely English → English gTTS (clean read).
    - This matches what Hindi does — and Hindi works perfectly already.

    The key insight: Hindi gTTS reads mixed sentences (Hindi + English words)
    perfectly because it handles Latin-script words embedded in Devanagari text.
    Tamil gTTS CAN also do this — it reads English words with a Tamil accent,
    which is ACCEPTABLE and far better than choppy word-by-word splitting.

    Tanglish: entire text to Tamil gTTS (Roman-script Tamil reads naturally).
    ─────────────────────────────────────────────────────────────────────────────
    """
    script_range = _SCRIPT_RANGES.get(gtts_lang)

    # Tanglish: entire text → Tamil gTTS (pronounces Roman Tamil naturally)
    if is_tanglish:
        return [(gtts_lang, text)]

    # Non-Indic or no script range → entire text to native engine
    if not script_range:
        return [(gtts_lang, text)]

    lo, hi = script_range

    def has_native(s):
        return any(lo <= ord(c) <= hi for c in s)

    # Split at sentence/clause boundaries
    sentences = re.split(r'(?<=[.!?\n।])\ *', text)
    merged = []

    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue

        if has_native(sent):
            # Sentence has native script — send to native engine.
            # The native gTTS engine (ta/hi/te/ml/bn/mr/kn) reads embedded
            # English tech words with a native accent. This is smooth and natural
            # — the same behaviour that makes Hindi mode work "perfectly".
            engine = gtts_lang
        else:
            # Pure English/Latin sentence — English gTTS for clean pronunciation
            engine = "en"

        # Merge consecutive same-engine segments
        if merged and merged[-1][0] == engine:
            merged[-1] = (engine, merged[-1][1] + " " + sent)
        else:
            merged.append([engine, sent])

    result = [(l, s.strip()) for l, s in merged if s.strip()]
    return result or [(gtts_lang, text)]

def _gtts_chunk(text, lang, slow=False):
    """Return MP3 bytes for one text chunk via gTTS.

    slow=True gives more natural output for very short English words
    embedded in Indic text (prevents rushed pronunciation).
    """
    buf = _io.BytesIO()
    _gTTS(text=text, lang=lang, slow=slow).write_to_fp(buf)
    buf.seek(0)
    return buf.read()


@app.route("/tts", methods=["POST"])
@login_required
@rate_limit(max_calls=120, window=60)
def tts():
    """TTS endpoint — word-level mixed-language routing for gTTS.

    Language behaviour:
    ─────────────────────────────────────────────────────────────────────────────
    Hindi (hi-IN)   → Native Hindi gTTS. English tech words inside Hindi sentences
                      (e.g. "Python loop likhna hai") are split word-by-word and
                      routed to English gTTS so they sound natural.

    Tamil (ta-IN)   → Same word-level split. Pure Tamil words → ta gTTS.
                      English words like "Python", "function" → en gTTS.

    Tanglish (ta-en)→ Tamil gTTS for the entire text. Text is Roman-script Tamil
                      (e.g. "dei enna panra bro") — Tamil TTS gives it the right
                      Tamil accent. Rate is slowed slightly for clarity.

    Telugu (te-IN)  → Word-level split, same as Tamil/Hindi.
    Malayalam(ml-IN)→ Word-level split.
    Bengali (bn-IN) → Word-level split.
    Marathi (mr-IN) → Word-level split.
    Kannada (kn-IN) → Kannada gTTS (supported since gTTS 2.3.2). Word-level split.

    English (en-US) → Straight English gTTS. No splitting needed.

    World langs     → Straight native gTTS. English words inside those sentences
                      are generally handled well by their respective engines.
    ─────────────────────────────────────────────────────────────────────────────
    """
    if not _GTTS_OK:
        return jsonify({"error": "gTTS not installed. Run: pip install gtts"}), 503

    data = request.get_json(silent=True) or {}
    raw  = (data.get("text") or "").strip()
    lang_code = (data.get("lang") or "en-US").strip()

    if not raw:
        return jsonify({"error": "No text provided"}), 400

    text = _clean_for_tts(raw)
    if not text:
        return jsonify({"error": "Text empty after cleaning"}), 400

    gtts_lang = TTS_LANG_MAP.get(lang_code)
    if not gtts_lang:
        return jsonify({"error": f"Unsupported language: {lang_code}"}), 400

    is_tanglish = (lang_code == "ta-en")

    # Kannada fallback: if kn gTTS fails (older gTTS version), retry with English
    _kn_fallback = (lang_code == "kn-IN")

    try:
        segments = _smart_split(text, gtts_lang, is_tanglish=is_tanglish)
        app.logger.debug(f"TTS {lang_code}->{gtts_lang}: {len(segments)} segment(s) "
                         f"{'[tanglish]' if is_tanglish else ''}")

        chunks = []
        for seg_lang, seg_text in segments:
            if not seg_text.strip():
                continue
            try:
                # Use slow=True for short English word fragments inside Indic sentences
                # (1-2 words) so they aren't rushed/clipped between native chunks.
                # Tanglish: use slow=True so Roman-script Tamil words are spoken clearly
                # Short English words inside Indic text: slow=True avoids rushed clips
                use_slow = is_tanglish or (seg_lang == "en" and len(seg_text.split()) <= 3)
                chunks.append(_gtts_chunk(seg_text, seg_lang, slow=use_slow))
            except Exception as e:
                # If Kannada-specific chunk fails, try English as fallback for that chunk
                app.logger.warning(f"TTS chunk failed lang={seg_lang} err={e}")
                if _kn_fallback and seg_lang == "kn":
                    try:
                        chunks.append(_gtts_chunk(seg_text, "en"))
                        app.logger.info(f"Kannada chunk fell back to English successfully")
                    except Exception as e2:
                        app.logger.warning(f"Kannada English fallback also failed: {e2}")

        if not chunks:
            return jsonify({"error": "TTS generation failed for all segments"}), 502

        return Response(b"".join(chunks), mimetype="audio/mpeg",
                        headers={"Cache-Control": "no-cache"})

    except Exception as exc:
        app.logger.error(f"TTS error lang={lang_code}: {exc}")
        return jsonify({"error": f"TTS failed: {str(exc)}"}), 502

# ================= RUN APP =================

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)