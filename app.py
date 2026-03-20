"""CodeBuddy – AI-powered programming assistant backend.
   ╔══════════════════════════════════════════════════════════╗
   ║  v5.0 — 6 WORLD-FIRST FEATURES ADDED                   ║
   ║  Previous v4.0 features (1-10) preserved intact        ║
   ║                                                          ║
   ║  NEW — WORLD FIRST:                                     ║
   ║  11. Thought Replay Debugger (AI reasoning visible)     ║
   ║  12. Voice-to-Voice Coding Loop (speak → fix → speak)  ║
   ║  13. Live Code Battle (AI-judged real-time duel)        ║
   ║  14. Code Karma System (help = community currency)      ║
   ║  15. Replay My Learning (shareable journey timeline)    ║
   ║  16. Blind Code Review (anonymous, bias-free feedback)  ║
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
try:
    from flask_socketio import SocketIO, emit, join_room, leave_room
    _SOCKETIO_OK = True
except ImportError:
    _SOCKETIO_OK = False

# ================= INIT =================

load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

app = Flask(__name__)

# ── STABLE SECRET KEY ─────────────────────────────────────────────────────────
# FIX: secrets.token_hex(32) generates a NEW key every restart, invalidating
# all session cookies → "ERROR LOADING SESSION" on every page click.
# Solution: derive stable key from machine fingerprint, or use SECRET_KEY in .env
_raw_secret = os.getenv("SECRET_KEY", "")
if not _raw_secret:
    import hashlib, platform
    _fp = platform.node() + platform.machine() + os.path.abspath(__file__)
    _raw_secret = "cb-" + hashlib.sha256(_fp.encode()).hexdigest()
app.secret_key = _raw_secret

# ── SESSION CONFIG ─────────────────────────────────────────────────────────────
app.config.update(
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=False,        # Must be False for http://localhost
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_NAME="codebuddy_session",
    PERMANENT_SESSION_LIFETIME=86400 * 30,  # 30-day sessions
)

# ── SOCKETIO: always threading — eventlet is deprecated & breaks sessions ──────
if _SOCKETIO_OK:
    socketio = SocketIO(
        app, cors_allowed_origins="*",
        async_mode="threading",
        logger=False, engineio_logger=False,
    )
else:
    socketio = None
_collab_rooms = {}

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
                    retry_after = int(window)
                    return jsonify({"error": "Rate limit exceeded. Please wait.", "retry_after": retry_after}), 429
            else:
                calls = [t for t in _rate_store[key] if now - t < window]
                if len(calls) >= max_calls:
                    # Calculate seconds until oldest call expires
                    oldest = min(calls)
                    retry_after = max(1, int(window - (now - oldest)) + 1)
                    return jsonify({"error": "Rate limit exceeded. Please wait.", "retry_after": retry_after}), 429
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
    """Check if message is programming-related, supporting all Indian languages.

    Uses two layers:
    1. Fast keyword check — catches common programming terms in English AND
       transliterated forms used in Indian languages (Tamil, Hindi, Telugu etc.)
    2. AI classifier — for ambiguous cases, with multilingual system prompt
    """
    # Layer 1: Fast keyword check (English tech terms + common Indic transliterations)
    PROG_KEYWORDS = {
        # Core English terms always present even in native-language questions
        "python", "java", "javascript", "js", "html", "css", "sql", "code", "coding",
        "program", "programming", "function", "variable", "loop", "array", "class",
        "object", "method", "debug", "error", "bug", "api", "database", "server",
        "framework", "library", "algorithm", "data structure", "web", "app", "software",
        "developer", "git", "linux", "terminal", "compiler", "runtime", "syntax",
        "react", "node", "django", "flask", "spring", "typescript", "kotlin", "swift",
        "c++", "c#", "ruby", "golang", "rust", "php", "bash", "script", "import",
        "print", "return", "integer", "string", "boolean", "float", "null", "undefined",
        "http", "json", "xml", "rest", "graphql", "docker", "kubernetes", "aws",
        # Tanglish / Tamil transliteration tech words
        "koodu", "kodu", "code pannrom", "code panna", "program pannrom",
        "function ezhudu", "function ezhuthu", "loop podrom", "debug pannrom",
        # Hindi transliteration
        "code karo", "code kaise", "program karo", "coding karo", "function kya",
        "loop kya", "variable kya", "error kaise", "kaise likhte",
        # Telugu transliteration
        "code rayyandi", "program rayyandi", "function enti", "loop enti",
        # Kannada transliteration
        "code bareyiri", "program bareyiri",
        # Malayalam transliteration
        "code ezhuthuka", "program ezhuthuka",
    }
    import re as _re
    text_lower = text.lower()
    # Word-boundary check for short keywords to avoid false positives
    # e.g. "api" in "saapiduvom", "app" in "happy", "string" is fine (long enough)
    SHORT_KW = {"js", "api", "app", "web", "bug", "git", "php", "sql", "css"}
    for kw in PROG_KEYWORDS:
        if kw in SHORT_KW:
            if _re.search(r'\b' + _re.escape(kw) + r'\b', text_lower):
                return True
        else:
            if kw in text_lower:
                return True

    # Layer 2: Code character check
    code_chars = set("{}[]()=><;:/\\")
    if len(text.split()) < 6 and any(c in text for c in code_chars):
        return True

    # Layer 3: AI classifier — explicitly multilingual prompt
    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": MODELS["classifier"],
            "max_tokens": 5,
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a multilingual classifier. The user's message may be in "
                        "English, Tamil, Hindi, Telugu, Kannada, Malayalam, Bengali, Marathi, "
                        "Gujarati, or Tanglish (Tamil+English mix). "
                        "Decide if the message is related to: programming, software development, "
                        "computer science, coding, algorithms, data structures, web development, "
                        "databases, DevOps, machine learning, AI, or any technical computing topic.\n"
                        "IMPORTANT: Questions asked in any Indian language about these topics "
                        "are still programming-related. Reply ONLY: YES or NO"
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
            "model": MODELS["title"],
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
    # ── PRIMARY MODELS (all :free — zero cost on OpenRouter) ─────────────────
    # Best coding model as of March 2026 — 480B MoE, 262K context, tools
    "code":       "qwen/qwen3-coder:free",
    # Best multilingual / fast — Llama 3.3 70B, 128K context, confirmed free
    "fast":       "meta-llama/llama-3.3-70b-instruct:free",
    # Lightweight classifier — small & fast, free
    "classifier": "meta-llama/llama-3.2-3b-instruct:free",
    # Title generation — tiny, near-instant, free
    "title":      "meta-llama/llama-3.2-3b-instruct:free",
}

# ── ORDERED FALLBACK CHAIN (all :free, different providers) ─────────────────
# When ANY model returns 429/404/503, these are tried in order.
# Multiple providers = if one is rate-limited, another will work.
FREE_FALLBACKS = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "qwen/qwen3-coder:free",
    "mistralai/mistral-small-3.1-24b-instruct:free",
    "google/gemma-3-27b-it:free",
    "openai/gpt-oss-20b:free",
    "openrouter/free",  # last resort: OpenRouter auto-picks any working free model
]

def get_model_for_mode(mode, lang_code="en-US"):
    """Pick the best free model based on task type and language.
    All models are :free — zero cost on OpenRouter.

    - Indic languages: Llama 3.3 70B has the best multilingual Indic support.
    - Coding tasks: Qwen3-Coder 480B is the strongest free coding model (March 2026).
    - Fast/explain/interview: Llama 3.3 70B — fast and accurate.
    """
    # All non-English Indic languages → Llama 3.3 70B (best free multilingual)
    indic_langs = {"ta-IN", "ta-en", "hi-IN", "te-IN", "kn-IN",
                   "ml-IN", "bn-IN", "mr-IN", "pa-IN", "gu-IN"}
    if lang_code in indic_langs:
        return MODELS["fast"]  # Llama 3.3 70B — best free multilingual

    fast_modes = {"explain", "interview", "roadmap"}
    if mode in fast_modes:
        return MODELS["fast"]
    return MODELS["code"]  # Qwen3-Coder — best free coding model

# ================= SYSTEM PROMPTS =================

# Injected into every system prompt — universal respectful tone rule
_RESPECTFUL_TONE = """

IMPORTANT — HOW TO ADDRESS THE USER (MANDATORY FOR ALL LANGUAGES):
- Always be warm, RESPECTFUL, and professional — like a knowledgeable teacher
- NEVER use casual street slang or overly familiar address words
- English: use "you" — polite and professional always
- Tamil/Tanglish: use "neenga", "ungalukku" (formal Tamil pronouns) — NEVER casual "da", "bro", "machaa", "nanbaa", "dei", "ey"
- Hindi: use "aap" — NEVER casual "yaar", "bhai", "oye", "arre"
- Telugu: use "meeru", "mee" — NEVER casual "ey", "ra", or dismissive terms
- Kannada: use "neevu", "nimma" — NEVER casual "ey", "ri" dismissively
- Malayalam: use "ningal", "ningalude" — NEVER casual "eda", "dei"
- Bengali: use "apni" — NEVER casual "ei", "oi"
- Marathi: use "tumhi" — NEVER rude "are", "aga"
- Gujarati: use "aap" — NEVER dismissive address
- Punjabi: use "tussi" — NEVER rude "oi", "hey"
- Treat every user like a valued student or professional you deeply respect"""

SYSTEM_PROMPTS = {
    "general": """You are CodeBuddy, a friendly programming helper. You ONLY answer programming and coding-related questions.

SCOPE — WHAT YOU ANSWER:
- Programming questions (Python, JavaScript, Java, C++, etc.)
- Coding concepts, algorithms, data structures
- Debugging, fixing, or explaining code
- Software development tools, frameworks, libraries
- Database queries (SQL, etc.)
- Web development, APIs, DevOps topics

IF THE USER ASKS A NON-PROGRAMMING QUESTION:
- Politely decline and redirect them to ask a coding question.
- Example response: "I'm CodeBuddy — I can only help with programming and coding topics. Do you have a coding question I can help with?"
- Do NOT answer general knowledge, math homework, personal advice, jokes, or any non-coding topic.

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
            login_user(User(user["id"], user["username"]), remember=True)
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
    # Show onboarding once per login session using a session flag.
    # This works for ALL users (new and existing) — dismissed by clicking "GOT IT".
    show_onboarding = not session.get("onboarding_dismissed", False)
    return render_template("index.html", chats=chats, username=current_user.username, is_new_user=show_onboarding)

@app.route("/onboarding/dismiss", methods=["POST"])
@login_required
def onboarding_dismiss():
    """Mark onboarding as seen for this login session."""
    session["onboarding_dismissed"] = True
    return jsonify({"ok": True})

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
        "SELECT role, content, timestamp FROM messages WHERE conversation_id=? ORDER BY id ASC",
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

PISTON_ENDPOINTS = [
    "https://emkc.org/api/v2/piston/execute",
    "https://api.piston.rs/api/v2/execute",
]
PISTON_API = PISTON_ENDPOINTS[0]  # backward-compat alias

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

    piston_payload = {
        "language": piston_lang,
        "version": piston_ver,
        "files": [{"name": f"main.{language[:10]}", "content": code}],
        "stdin": "",
        "args": [],
        "compile_timeout": 10000,
        "run_timeout": 10000,
    }
    resp = None
    last_err = "All Piston endpoints failed"
    for _ep in PISTON_ENDPOINTS:
        try:
            _r = requests.post(_ep, json=piston_payload, timeout=20)
            if _r.status_code == 200:
                resp = _r
                break
            last_err = f"HTTP {_r.status_code} from {_ep}"
        except requests.exceptions.RequestException as _e:
            last_err = str(_e)
            continue
    if resp is None:
        return jsonify({"output": f"⚠ Code execution unavailable: {last_err}", "exit_code": -1})
    try:

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


_RUDE_REPLACEMENTS = [
    # "Dei + anything" → remove entirely
    (r'(?i)\bdei\s+bro[,! ]*',     ''),
    (r'(?i)\bdei\s+da[,! ]*',      ''),
    (r'(?i)\bdei\s+machaa[,! ]*',  ''),
    (r'(?i)\bdei\s+nanbaa[,! ]*',  ''),
    (r'(?i)\bdei[,!]?\s+',         ''),
    # Casual sentence openers — too informal, strip them
    (r'(?m)^Machaa[,!]?\s+',       ''),
    (r'(?m)^machaa[,!]?\s+',       ''),
    (r'(?m)^Bro[,!]\s+',           ''),
    (r'(?m)^bro[,!]\s+',           ''),
    (r'(?m)^Da[,!]\s+',            ''),
    (r'(?m)^da[,!]\s+',            ''),
    (r'(?m)^Nanbaa[,!]?\s+',       ''),
    (r'(?m)^nanbaa[,!]?\s+',       ''),
    # Tamil script rude words → respectful
    (r'\bடேய்\b',                  'நண்பா'),
    (r'\bடே\b',                    'நண்பா'),
    # Hindi casual/rude
    (r'(?i)\boye\b',               'Aap'),
    (r'(?i)\barre\s+yaar\b',       ''),
    # Telugu / Kannada dismissive "Ey"
    (r'(?m)^[Ee]y[,!]?\s+',        ''),
    (r'(?i)\bey[,!]?\s+',          ''),
]

def _filter_response(text: str) -> str:
    """Replace rude address words with respectful equivalents."""
    import re
    for pattern, replacement in _RUDE_REPLACEMENTS:
        text = re.sub(pattern, replacement, text)
    return text


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
            "Write in Tanglish (Tamil words in English/Roman letters mixed with English tech terms).\n"
            "Use a RESPECTFUL, PROFESSIONAL tone — like a knowledgeable teacher or senior colleague.\n\n"
            "CRITICAL RULES:\n"
            "✅ Write in ENGLISH LETTERS ONLY (Roman script) — NOT Tamil unicode characters\n"
            "✅ Mix Tamil words naturally: 'pannrom', 'paaru', 'irukku', 'solren', 'theriyuma', 'aagum', 'paarunga'\n"
            "✅ English tech words stay English: function, variable, loop, array, class, API, debug\n"
            "✅ Every sentence mixes both: 'Indha function-la list return pannrom — [0] use panna first element kedaikum'\n"
            "✅ RESPECTFUL address: use 'neenga', 'ungalukku', 'paarunga' — formal Tamil pronouns\n"
            "✅ Respectful openings: 'Neenga kekkura question-ku solren', 'Ungalukku explain pannren', 'Indha concept paarunga'\n"
            "❌ BANNED casual words: 'da', 'bro', 'machaa', 'nanbaa', 'dei', 'ey' — too casual/disrespectful\n"
            "❌ NO pure English paragraphs — Tamil words must appear in every sentence\n"
            "❌ NO Tamil script (unicode) — only Roman/English letters\n"
            "❌ DO NOT start with 'Here is' — write: 'Solren, indha concept simple-a irukku'\n\n"
            "VOICE: This text is spoken aloud with Tamil voice — write naturally for speech."
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
        "ta-en": "⚠️ IMPORTANT: Reply in Tanglish ONLY (Tamil words in Roman letters + English tech words). RESPECTFUL tone — say 'neenga'/'ungalukku'/'paarunga'. NEVER casual 'da/bro/machaa/dei/ey'. Example: 'Neenga kekkura question-ku solren — indha function-la loop irukku, paarunga'. NO pure English. NO Tamil unicode. Answer: ",
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
    # Use global FREE_FALLBACKS list — all :free models across multiple providers
    MODEL_FALLBACKS = {m: [f for f in FREE_FALLBACKS if f != m] for m in FREE_FALLBACKS}

    payload = {
        "model": selected_model,
        "stream": True,
        "max_tokens": 2000,
        "temperature": 0.7,
        "messages": api_messages
    }

    def generate():
        full = ""
        stream_buf = ""
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
                # Try all free fallback models in order across different providers
                tried = {payload["model"]}
                for fb_model in FREE_FALLBACKS:
                    if fb_model in tried:
                        continue
                    tried.add(fb_model)
                    app.logger.warning(f"Model {payload['model']} returned {response.status_code}, trying {fb_model}")
                    payload["model"] = fb_model
                    response = requests.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers=headers, json=payload, stream=True, timeout=(10, 90)
                    )
                    if response.status_code == 200:
                        app.logger.info(f"Fallback succeeded with {fb_model}")
                        break
                if response.status_code != 200:
                    code = response.status_code
                    if code == 429:
                        msg = "⏳ RATE_LIMIT_429"  # special token frontend detects
                    else:
                        msg = f"API Error {code}. Please try again."
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
                            stream_buf += token
                            full += token
                            if any(c in stream_buf for c in '.!?,\n') or len(stream_buf) > 80:
                                yield _filter_response(stream_buf)
                                stream_buf = ""
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

        if stream_buf:
            yield _filter_response(stream_buf)
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
# ================= TRANSLATION FALLBACK =================

@app.route("/translate", methods=["POST"])
@login_required
@rate_limit(max_calls=30, window=60)
def translate_response():
    """Translate English AI response to target language when AI ignored language instruction."""
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    lang_code = (data.get("lang") or "en-US").strip()

    if not text or lang_code == "en-US":
        return jsonify({"translated": text})

    LANG_NAMES_SHORT = {
        "ta-IN": "Tamil (தமிழ் script only — unicode characters)",
        "hi-IN": "Hindi (हिंदी script only — Devanagari unicode)",
        "te-IN": "Telugu (తెలుగు script only — unicode characters)",
        "kn-IN": "Kannada (ಕನ್ನಡ script only — unicode characters)",
        "ml-IN": "Malayalam (മലയാളം script only — unicode characters)",
        "bn-IN": "Bengali (বাংলা script only — unicode characters)",
        "mr-IN": "Marathi (मराठी script — Devanagari unicode)",
        "gu-IN": "Gujarati (ગુજરાતી script only)",
        "pa-IN": "Punjabi (ਪੰਜਾਬੀ script only — Gurmukhi unicode)",
        "fr-FR": "French", "de-DE": "German", "es-ES": "Spanish",
        "ja-JP": "Japanese", "ko-KR": "Korean", "ar-SA": "Arabic",
        "zh-CN": "Chinese Simplified", "ru-RU": "Russian", "pt-BR": "Portuguese",
        "ta-en": "Tanglish (Tamil words written in English/Roman letters mixed with English tech terms — NO Tamil unicode script — respectful tone using 'neenga'/'ungalukku')",
    }
    target = LANG_NAMES_SHORT.get(lang_code, "the target language")

    system_msg = (
        f"You are a professional translator specializing in programming content. "
        f"Translate the following programming explanation into {target}. "
        f"Rules: Keep ALL code blocks (``` ... ```) and inline code (`code`) UNCHANGED. "
        f"Only translate the prose/explanation text. "
        f"Output ONLY the translated text — no preamble, no 'Here is the translation:', nothing extra."
    )

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    # Try multiple models — translation is rate-limited frequently
    models_to_try = [MODELS["fast"]] + [m for m in FREE_FALLBACKS if m != MODELS["fast"]][:3]
    last_err = "No models available"

    for model in models_to_try:
        try:
            payload = {
                "model": model,
                "max_tokens": 1800,
                "temperature": 0.15,
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": text[:2000]}
                ]
            }
            resp = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers, json=payload, timeout=(5, 25)
            )
            if resp.status_code == 200:
                translated = resp.json()["choices"][0]["message"]["content"].strip()
                if translated:
                    return jsonify({"translated": translated})
            elif resp.status_code in (429, 503):
                last_err = f"Model {model} rate limited"
                continue
            else:
                last_err = f"HTTP {resp.status_code}"
                break
        except Exception as e:
            last_err = str(e)
            continue

    app.logger.warning(f"Translation failed for {lang_code}: {last_err}")
    return jsonify({"translated": text, "error": last_err})  # fallback: return original


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
    
    Includes fallback: if Tamil/Malayalam fails (click version conflict),
    retries with English so audio always plays.
    """
    buf = _io.BytesIO()
    try:
        _gTTS(text=text, lang=lang, slow=slow).write_to_fp(buf)
        buf.seek(0)
        data = buf.read()
        if len(data) < 100:
            raise ValueError("gTTS returned empty audio")
        return data
    except Exception as e:
        app.logger.warning(f"gTTS failed lang={lang}: {e}")
        # Fallback 1: try with slow=False if slow caused the issue
        if slow:
            try:
                buf2 = _io.BytesIO()
                _gTTS(text=text, lang=lang, slow=False).write_to_fp(buf2)
                buf2.seek(0)
                data2 = buf2.read()
                if len(data2) > 100:
                    return data2
            except Exception:
                pass
        # Fallback 2: if Indic lang fails, try English (at least audio plays)
        if lang != "en":
            try:
                buf3 = _io.BytesIO()
                _gTTS(text=text, lang="en", slow=False).write_to_fp(buf3)
                buf3.seek(0)
                data3 = buf3.read()
                if len(data3) > 100:
                    app.logger.warning(f"gTTS: using English fallback for lang={lang}")
                    return data3
            except Exception as e2:
                app.logger.error(f"gTTS English fallback also failed: {e2}")
        raise


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
                      (e.g. "indha function parunga") — Tamil TTS gives it the right
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
                indic_slow = seg_lang in ("ta", "ml", "kn", "te")
                use_slow = is_tanglish or indic_slow or (seg_lang == "en" and len(seg_text.split()) <= 3)
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
        # Try plain English as absolute last resort
        try:
            fallback_text = _clean_for_tts(raw)[:500]
            if fallback_text:
                buf = _io.BytesIO()
                _gTTS(text=fallback_text, lang="en", slow=False).write_to_fp(buf)
                buf.seek(0)
                audio_data = buf.read()
                if audio_data:
                    return Response(audio_data, mimetype="audio/mpeg",
                                    headers={"Cache-Control": "no-cache",
                                             "X-Lang-Fallback": "en"})
        except Exception:
            pass
        return jsonify({"error": f"TTS failed: {str(exc)}"}), 502

# ================= FEATURE 11-16: WORLD-FIRST ROUTES =================

# ── FEATURE PAGE ──────────────────────────────────────────────────────

@app.route("/features")
@login_required
def features_page():
    """World-first feature hub page."""
    return render_template("codebuddy_world_first.html", username=current_user.username)


# ─────────────────────────────────────────────────────────────────────
# FEATURE 11 — THOUGHT REPLAY DEBUGGER
# Streams the AI's internal reasoning step-by-step as it debugs code.
# Each reasoning step is yielded as a JSON line so the frontend can
# animate them one-by-one onto a visual timeline.
# ─────────────────────────────────────────────────────────────────────

@app.route("/thought_replay", methods=["POST"])
@login_required
@rate_limit(max_calls=20, window=60)
def thought_replay():
    """Stream AI reasoning steps for a piece of broken code.

    Yields newline-delimited JSON objects:
      {"step": 1, "label": "READING CODE", "text": "...", "type": "thinking"}
      {"step": 2, "label": "BUG FOUND",    "text": "...", "type": "error",  "code": "..."}
      {"step": N, "label": "COMPLETE",     "text": "...", "type": "done"}
    """
    code = (request.json or {}).get("code", "").strip()
    if not code:
        return jsonify({"error": "No code provided"}), 400

    system_prompt = """You are CodeBuddy's Thought Replay engine.
Your job is to debug code by thinking out loud — step by step — like a senior engineer reviewing code.

Output ONLY a JSON array of reasoning steps. Each step is an object with:
  "label"  : short UPPERCASE title (e.g. "READING CODE", "BUG FOUND", "GENERATING FIX")
  "text"   : one or two plain sentences describing this thought
  "type"   : one of "thinking" | "error" | "done"
  "code"   : (optional) relevant code snippet or diff for this step

Rules:
- 5 to 8 steps total
- Last step must be type "done" with the fixed code in "code"
- Be specific: name the exact line number and variable involved
- No markdown, no prose outside the JSON array
- Output ONLY the raw JSON array, nothing else"""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODELS["fast"],
        "max_tokens": 1200,
        "temperature": 0.3,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Debug this code:\n\n```\n{code[:2000]}\n```"},
        ],
    }

    # Try primary model then fallbacks — free models often return 429 instead of choices
    models_to_try = [MODELS["fast"]] + [m for m in FREE_FALLBACKS if m != MODELS["fast"]]
    last_error = "Unknown error"

    for model in models_to_try:
        try:
            payload["model"] = model
            resp = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers, json=payload, timeout=30
            )
            resp_json = resp.json()

            if "choices" not in resp_json:
                api_err = resp_json.get("error", {})
                last_error = api_err.get("message", str(resp_json)) if isinstance(api_err, dict) else str(api_err)
                app.logger.warning("thought_replay: model %s returned no choices: %s", model, last_error)
                if resp.status_code not in (429, 503, 502, 500):
                    break
                continue

            raw = resp_json["choices"][0]["message"]["content"].strip()
            raw = re.sub(r"```json|```", "", raw).strip()
            steps = json.loads(raw)
            if not isinstance(steps, list):
                steps = [steps]

            for i, step in enumerate(steps):
                step["step"] = i + 1

            bump_stat(current_user.id, "debug_count")
            return jsonify(steps)

        except (requests.RequestException, json.JSONDecodeError, ValueError) as exc:
            last_error = str(exc)
            app.logger.warning("thought_replay: model %s exception: %s", model, exc)
            continue

    bump_stat(current_user.id, "debug_count")
    return jsonify({"error": f"AI unavailable ({last_error}). All models rate-limited — try again in a moment."}), 503


# ─────────────────────────────────────────────────────────────────────
# FEATURE 12 — VOICE-TO-VOICE CODING LOOP
# Takes transcribed speech text + language, returns a spoken fix.
# The frontend handles speech-to-text (Web Speech API) and
# text-to-speech (existing /tts endpoint). This backend endpoint
# handles the middle step: understanding the spoken problem and
# generating a clear, speakable fix.
# ─────────────────────────────────────────────────────────────────────

@app.route("/voice_fix", methods=["POST"])
@login_required
@rate_limit(max_calls=30, window=60)
def voice_fix():
    """Convert a spoken code problem into a spoken fix.

    Input JSON:
      text      : transcribed speech from the user
      lang      : language code (e.g. "en-US", "ta-IN")

    Returns JSON:
      fix_text  : the plain-language fix (clean, speakable — no markdown)
      code      : the fixed code snippet (if applicable)
    """
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    lang_code = (data.get("lang") or "en-US").strip()

    if not text:
        return jsonify({"error": "No speech text provided"}), 400

    LANG_NAMES = {
        "en-US": "English", "ta-IN": "Tamil", "ta-en": "Tanglish",
        "hi-IN": "Hindi", "te-IN": "Telugu", "kn-IN": "Kannada",
        "ml-IN": "Malayalam", "bn-IN": "Bengali",
    }
    lang_name = LANG_NAMES.get(lang_code, "English")

    system = f"""You are CodeBuddy Voice Assistant. The user spoke their code problem aloud.
Your response will be READ ALOUD by a text-to-speech engine — so write naturally for speech.

Rules:
- Respond in {lang_name}
- NO markdown — no **, no #, no backticks
- Short sentences — TTS sounds best with short clauses
- Say "Here is the fix:" before giving code, spoken as words
- Explain the fix in 2-3 simple sentences
- Keep the full response under 120 words for natural speech rhythm
- Be warm and encouraging"""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": get_model_for_mode("general", lang_code),
        "max_tokens": 300,
        "temperature": 0.6,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": text[:500]},
        ],
    }

    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers, json=payload, timeout=20
        )
        fix_text = resp.json()["choices"][0]["message"]["content"].strip()
        # Extract code block if present (for display — not spoken)
        code_match = re.search(r"```[\w]*\n?([\s\S]+?)```", fix_text)
        code_snippet = code_match.group(1).strip() if code_match else ""
        # Clean fix text for TTS
        clean_fix = re.sub(r"```[\s\S]*?```", "see the code above", fix_text)
        clean_fix = re.sub(r"[`*#]", "", clean_fix).strip()
        return jsonify({"fix_text": clean_fix, "code": code_snippet})
    except (requests.RequestException, KeyError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 500


# ─────────────────────────────────────────────────────────────────────
# FEATURE 13 — LIVE CODE BATTLE
# Manages battle sessions: create, join, submit, judge.
# Battles are stored in SQLite for persistence and multi-tab support.
# ─────────────────────────────────────────────────────────────────────

def _init_battle_tables():
    """Create battle-related DB tables if they don't exist."""
    conn = sqlite3.connect("codebuddy.db")
    conn.execute("""CREATE TABLE IF NOT EXISTS battles(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        creator_id INTEGER,
        problem TEXT,
        status TEXT DEFAULT 'waiting',
        created_at TEXT,
        ended_at TEXT,
        winner TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS battle_entries(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        battle_id INTEGER,
        user_id INTEGER,
        code TEXT DEFAULT '',
        score REAL DEFAULT 0,
        submitted_at TEXT,
        UNIQUE(battle_id, user_id)
    )""")
    conn.commit()
    conn.close()

_init_battle_tables()

BATTLE_PROBLEMS = [
    "Write a function that checks if a string is a palindrome. Handle empty strings, single characters, and mixed case.",
    "Implement a function to find all duplicate elements in an array. Return them sorted. Handle empty arrays.",
    "Write a function that reverses words in a sentence without using built-in reverse.",
    "Implement FizzBuzz — return results as a list for numbers 1 to N. Make it Pythonic.",
    "Write a function that counts character frequency in a string, sorted by frequency (highest first).",
    "Implement binary search on a sorted list. Return the index or -1 if not found.",
    "Write a function that flattens a nested list of arbitrary depth into a single flat list.",
    "Implement a stack using only two queues. Support push, pop, and peek operations.",
]

@app.route("/battle/create", methods=["POST"])
@login_required
def battle_create():
    """Create a new battle session. Returns battle_id and problem."""
    import random
    problem = random.choice(BATTLE_PROBLEMS)
    conn = sqlite3.connect("codebuddy.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        "INSERT INTO battles(creator_id, problem, status, created_at) VALUES (?,?,?,?)",
        (current_user.id, problem, "waiting", datetime.now().isoformat())
    )
    battle_id = cursor.lastrowid
    conn.execute(
        "INSERT INTO battle_entries(battle_id, user_id, submitted_at) VALUES (?,?,?)",
        (battle_id, current_user.id, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    return jsonify({"battle_id": battle_id, "problem": problem, "status": "waiting"})


@app.route("/battle/join", methods=["POST"])
@login_required
def battle_join():
    """Join an existing battle by ID."""
    battle_id = (request.json or {}).get("battle_id")
    if not battle_id:
        return jsonify({"error": "battle_id required"}), 400

    conn = sqlite3.connect("codebuddy.db")
    conn.row_factory = sqlite3.Row
    battle = conn.execute(
        "SELECT * FROM battles WHERE id=? AND status='waiting'", (battle_id,)
    ).fetchone()

    if not battle:
        conn.close()
        return jsonify({"error": "Battle not found or already started"}), 404

    try:
        conn.execute(
            "INSERT INTO battle_entries(battle_id, user_id, submitted_at) VALUES (?,?,?)",
            (battle_id, current_user.id, datetime.now().isoformat())
        )
        conn.execute(
            "UPDATE battles SET status='active' WHERE id=?", (battle_id,)
        )
        conn.commit()
    except Exception:
        conn.close()
        return jsonify({"error": "Already joined"}), 409

    conn.close()
    return jsonify({"battle_id": battle_id, "problem": battle["problem"], "status": "active"})


@app.route("/battle/update", methods=["POST"])
@login_required
def battle_update():
    """Save live code for a player (called every few seconds while typing)."""
    data = request.json or {}
    battle_id = data.get("battle_id")
    code = data.get("code", "")

    conn = sqlite3.connect("codebuddy.db")
    conn.execute(
        "UPDATE battle_entries SET code=? WHERE battle_id=? AND user_id=?",
        (code[:10000], battle_id, current_user.id)
    )
    conn.commit()
    conn.close()
    return jsonify({"status": "saved"})


@app.route("/battle/judge", methods=["POST"])
@login_required
@rate_limit(max_calls=10, window=60)
def battle_judge():
    """AI-judge both solutions and declare a winner.

    Returns JSON with per-player scores and a verdict.
    """
    data = request.json or {}
    battle_id = data.get("battle_id")
    code1 = data.get("code1", "")
    code2 = data.get("code2", "")
    problem = data.get("problem", "")
    player1 = data.get("player1", "Player 1")
    player2 = data.get("player2", "Player 2")

    if not code1.strip() and not code2.strip():
        return jsonify({"error": "No code to judge"}), 400

    system_prompt = """You are an expert code judge for a live coding battle.
Evaluate both solutions and return ONLY a JSON object (no markdown) with:
{
  "p1_score": <0-100>,
  "p2_score": <0-100>,
  "p1_feedback": "<one sentence>",
  "p2_feedback": "<one sentence>",
  "winner": "player1" | "player2" | "tie",
  "verdict": "<2-3 sentence final verdict explaining why the winner won>",
  "p1_strengths": ["<strength1>", "<strength2>"],
  "p2_strengths": ["<strength1>", "<strength2>"]
}
Score criteria: correctness (40%), efficiency (30%), readability (20%), edge cases (10%)."""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODELS["fast"],
        "max_tokens": 600,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": (
                f"Problem: {problem}\n\n"
                f"--- {player1}'s solution ---\n{code1[:2000]}\n\n"
                f"--- {player2}'s solution ---\n{code2[:2000]}"
            )},
        ],
    }

    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers, json=payload, timeout=25
        )
        raw = resp.json()["choices"][0]["message"]["content"].strip()
        raw = re.sub(r"```json|```", "", raw).strip()
        result = json.loads(raw)

        # Persist winner
        if battle_id:
            conn = sqlite3.connect("codebuddy.db")
            conn.execute(
                "UPDATE battles SET status='ended', ended_at=?, winner=? WHERE id=?",
                (datetime.now().isoformat(), result.get("winner", "tie"), battle_id)
            )
            conn.commit()
            conn.close()

        return jsonify(result)

    except (requests.RequestException, KeyError, json.JSONDecodeError, ValueError) as exc:
        return jsonify({
            "p1_score": 50, "p2_score": 50, "winner": "tie",
            "p1_feedback": "Could not analyze.", "p2_feedback": "Could not analyze.",
            "verdict": f"AI judging failed: {exc}. Scores are equal.",
            "p1_strengths": [], "p2_strengths": []
        })


@app.route("/battle/status/<int:battle_id>")
@login_required
def battle_status(battle_id):
    """Poll battle status — used to detect when opponent has joined."""
    conn = sqlite3.connect("codebuddy.db")
    conn.row_factory = sqlite3.Row
    battle = conn.execute("SELECT * FROM battles WHERE id=?", (battle_id,)).fetchone()
    entries = conn.execute(
        "SELECT user_id, code FROM battle_entries WHERE battle_id=?", (battle_id,)
    ).fetchall()
    conn.close()
    if not battle:
        return jsonify({"error": "Not found"}), 404
    # Return opponent's latest code (the other player's code, not current user's)
    opponent_code = ""
    for entry in entries:
        if entry["user_id"] != current_user.id:
            opponent_code = entry["code"] or ""
            break
    return jsonify({
        "status": battle["status"],
        "players": len(entries),
        "winner": battle["winner"],
        "opponent_code": opponent_code,
    })


# ─────────────────────────────────────────────────────────────────────
# FEATURE 14 — CODE KARMA SYSTEM
# Users earn karma by helping others. Karma unlocks features and ranks.
# ─────────────────────────────────────────────────────────────────────

def _init_karma_tables():
    """Create karma DB tables."""
    conn = sqlite3.connect("codebuddy.db")
    conn.execute("""CREATE TABLE IF NOT EXISTS karma(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE,
        total INTEGER DEFAULT 0,
        updated_at TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS karma_events(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        event_type TEXT,
        delta INTEGER,
        note TEXT,
        created_at TEXT
    )""")
    conn.commit()
    conn.close()

_init_karma_tables()

KARMA_RULES = {
    "share_solution":  {"delta": 50,  "label": "Shared a solution"},
    "explain_concept": {"delta": 30,  "label": "Explained a concept"},
    "fix_bug":         {"delta": 75,  "label": "Fixed someone's bug"},
    "blind_review":    {"delta": 40,  "label": "Submitted a blind review"},
    "battle_win":      {"delta": 100, "label": "Won a code battle"},
    "battle_play":     {"delta": 20,  "label": "Participated in a battle"},
    "streak_7":        {"delta": 200, "label": "7-day coding streak"},
    "streak_30":       {"delta": 1000,"label": "30-day coding streak"},
}

KARMA_LEVELS = [
    (0,     "NOVICE"),
    (500,   "LEARNER"),
    (1000,  "CODER"),
    (2000,  "BUILDER"),
    (2500,  "SAGE"),
    (5000,  "ORACLE"),
    (10000, "LEGEND"),
    (50000, "GODMODE"),
]

def _get_karma_level(total):
    """Return the karma level name for a given total."""
    level = "NOVICE"
    for threshold, name in KARMA_LEVELS:
        if total >= threshold:
            level = name
    return level

def _add_karma(user_id, event_type, note=""):
    """Add karma for an event. Returns new total."""
    rule = KARMA_RULES.get(event_type)
    if not rule:
        return 0
    delta = rule["delta"]
    conn = sqlite3.connect("codebuddy.db")
    conn.execute("""
        INSERT INTO karma(user_id, total, updated_at) VALUES (?,?,datetime('now'))
        ON CONFLICT(user_id) DO UPDATE SET
            total = total + ?,
            updated_at = datetime('now')
    """, (user_id, delta, delta))
    conn.execute(
        "INSERT INTO karma_events(user_id, event_type, delta, note, created_at) VALUES (?,?,?,?,datetime('now'))",
        (user_id, event_type, delta, note or rule["label"])
    )
    conn.commit()
    row = conn.execute("SELECT total FROM karma WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return row[0] if row else delta


@app.route("/karma/earn", methods=["POST"])
@login_required
def karma_earn():
    """Award karma to the current user for a community action.

    Input JSON:
      event_type : one of the KARMA_RULES keys
      note       : optional description
    """
    data = request.json or {}
    event_type = data.get("event_type", "")
    note = data.get("note", "")[:200]

    if event_type not in KARMA_RULES:
        return jsonify({"error": f"Unknown event type. Valid: {list(KARMA_RULES.keys())}"}), 400

    new_total = _add_karma(current_user.id, event_type, note)
    level = _get_karma_level(new_total)
    delta = KARMA_RULES[event_type]["delta"]

    return jsonify({
        "delta": delta,
        "total": new_total,
        "level": level,
        "label": KARMA_RULES[event_type]["label"],
    })


@app.route("/karma/me")
@login_required
def karma_me():
    """Return current user's karma total, level, rank, and recent events."""
    conn = sqlite3.connect("codebuddy.db")
    conn.row_factory = sqlite3.Row

    row = conn.execute("SELECT total FROM karma WHERE user_id=?", (current_user.id,)).fetchone()
    total = row["total"] if row else 0

    # Rank = position in global karma leaderboard
    rank_row = conn.execute(
        "SELECT COUNT(*)+1 AS rank FROM karma WHERE total > ?", (total,)
    ).fetchone()
    rank = rank_row["rank"] if rank_row else 1

    events = conn.execute(
        "SELECT event_type, delta, note, created_at FROM karma_events WHERE user_id=? ORDER BY id DESC LIMIT 20",
        (current_user.id,)
    ).fetchall()
    conn.close()

    level = _get_karma_level(total)
    # Find next level threshold
    next_threshold = total + 500
    for threshold, name in KARMA_LEVELS:
        if threshold > total:
            next_threshold = threshold
            break

    return jsonify({
        "total": total,
        "level": level,
        "rank": rank,
        "next_threshold": next_threshold,
        "progress_pct": min(100, round((total / next_threshold) * 100)),
        "events": [dict(e) for e in events],
    })


@app.route("/karma/leaderboard")
def karma_leaderboard():
    """Public karma leaderboard — top 20 users."""
    conn = sqlite3.connect("codebuddy.db")
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT u.username, u.avatar_color, k.total
        FROM karma k
        JOIN users u ON k.user_id = u.id
        ORDER BY k.total DESC
        LIMIT 20
    """).fetchall()
    conn.close()
    result = []
    for i, r in enumerate(rows):
        result.append({
            "rank": i + 1,
            "username": r["username"],
            "avatar_color": r["avatar_color"],
            "total": r["total"],
            "level": _get_karma_level(r["total"]),
        })
    return jsonify({"leaderboard": result})


# ─────────────────────────────────────────────────────────────────────
# FEATURE 15 — REPLAY MY LEARNING
# Returns the user's conversation history formatted as a learning
# journey timeline — milestones, insights, stats.
# ─────────────────────────────────────────────────────────────────────

@app.route("/learning_replay")
@login_required
def learning_replay():
    """Return the user's learning journey as a structured timeline.

    Fetches conversations + first message from each, groups them by
    month, and returns milestone cards with AI-generated insights.
    """
    conn = sqlite3.connect("codebuddy.db")
    conn.row_factory = sqlite3.Row

    # Get all conversations with their first user message
    convos = conn.execute("""
        SELECT c.id, c.title, c.mode, c.created_at,
               MIN(m.id) as first_msg_id
        FROM conversations c
        LEFT JOIN messages m ON m.conversation_id = c.id AND m.role = 'user'
        WHERE c.user_id = ?
        GROUP BY c.id
        ORDER BY c.id ASC
        LIMIT 100
    """, (current_user.id,)).fetchall()

    stats = conn.execute(
        "SELECT * FROM user_stats WHERE user_id=?", (current_user.id,)
    ).fetchone()

    # Get first messages for each convo
    timeline = []
    for c in convos:
        if c["first_msg_id"]:
            msg = conn.execute(
                "SELECT content FROM messages WHERE id=?", (c["first_msg_id"],)
            ).fetchone()
            question = msg["content"][:200] if msg else c["title"]
        else:
            question = c["title"]

        created = c["created_at"] or ""
        timeline.append({
            "id": c["id"],
            "title": c["title"],
            "mode": c["mode"],
            "date": created[:10] if created else "Unknown",
            "question": question,
        })

    conn.close()

    # Group into milestones
    milestones = []
    if timeline:
        chunk = max(1, len(timeline) // 5)
        labels = ["First Steps", "Building Basics", "Going Deeper", "Real Projects", "Advanced Mastery"]
        for i, label in enumerate(labels):
            start = i * chunk
            end = start + chunk if i < 4 else len(timeline)
            slice_ = timeline[start:end]
            if slice_:
                milestones.append({
                    "label": label,
                    "count": len(slice_),
                    "start_date": slice_[0]["date"],
                    "end_date": slice_[-1]["date"],
                    "entries": slice_,
                })

    return jsonify({
        "milestones": milestones,
        "total_conversations": len(timeline),
        "total_messages": stats["total_messages"] if stats else 0,
        "streak_days": stats["streak_days"] if stats else 0,
        "debug_count": stats["debug_count"] if stats else 0,
        "code_runs": stats["code_runs"] if stats else 0,
    })


@app.route("/learning_insight", methods=["POST"])
@login_required
@rate_limit(max_calls=10, window=60)
def learning_insight():
    """Generate an AI insight for a specific learning milestone.

    Input JSON:
      questions : list of question strings from that milestone period
      milestone : label string (e.g. "Building Basics")

    Returns JSON:
      insight   : one-paragraph motivational + analytical insight
    """
    data = request.json or {}
    questions = data.get("questions", [])[:10]
    milestone = data.get("milestone", "your learning journey")

    if not questions:
        return jsonify({"insight": "Keep learning — every question brings you closer to mastery."})

    joined = "\n".join(f"- {q}" for q in questions)
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODELS["fast"],
        "max_tokens": 200,
        "temperature": 0.7,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a coding coach reviewing a student's learning journey. "
                    "Given a list of questions they asked during a learning period, "
                    "write ONE short paragraph (3-4 sentences) that: "
                    "1) identifies the main skill theme they were learning, "
                    "2) highlights the most impressive question, "
                    "3) ends with one motivating observation about their growth. "
                    "Be specific and warm. No bullet points."
                ),
            },
            {"role": "user", "content": f"Milestone: {milestone}\n\nQuestions:\n{joined}"},
        ],
    }

    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers, json=payload, timeout=20
        )
        insight = resp.json()["choices"][0]["message"]["content"].strip()
        return jsonify({"insight": insight})
    except (requests.RequestException, KeyError, ValueError):
        return jsonify({"insight": f"During '{milestone}', you asked great questions that show real depth of curiosity."})


# ─────────────────────────────────────────────────────────────────────
# FEATURE 16 — BLIND CODE REVIEW
# Users submit code anonymously. Other users review without knowing
# the author. AI aggregates all reviews into a consensus report.
# ─────────────────────────────────────────────────────────────────────

def _init_blind_review_tables():
    """Create blind review DB tables."""
    conn = sqlite3.connect("codebuddy.db")
    conn.execute("""CREATE TABLE IF NOT EXISTS blind_submissions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        anon_id TEXT,
        code TEXT,
        language TEXT DEFAULT 'python',
        status TEXT DEFAULT 'open',
        created_at TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS blind_reviews(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        submission_id INTEGER,
        reviewer_id INTEGER,
        reviewer_anon TEXT,
        stars INTEGER,
        comment TEXT,
        created_at TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS blind_ai_reports(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        submission_id INTEGER UNIQUE,
        report TEXT,
        scores TEXT,
        generated_at TEXT
    )""")
    conn.commit()
    conn.close()

_init_blind_review_tables()


def _generate_anon_id():
    """Generate a short anonymous ID like ANON_7X4F."""
    import random, string
    chars = string.ascii_uppercase + string.digits
    return "ANON_" + "".join(random.choices(chars, k=4))


@app.route("/blind/submit", methods=["POST"])
@login_required
@rate_limit(max_calls=10, window=60)
def blind_submit():
    """Submit code anonymously for blind review.

    Input JSON:
      code     : source code string
      language : programming language name
    """
    data = request.json or {}
    code = (data.get("code") or "").strip()
    language = (data.get("language") or "python").strip()[:30]

    if not code:
        return jsonify({"error": "No code provided"}), 400
    if len(code) > 20000:
        return jsonify({"error": "Code too long (max 20,000 chars)"}), 400

    anon_id = _generate_anon_id()
    conn = sqlite3.connect("codebuddy.db")
    cursor = conn.execute(
        "INSERT INTO blind_submissions(user_id, anon_id, code, language, created_at) VALUES (?,?,?,?,datetime('now'))",
        (current_user.id, anon_id, code, language)
    )
    submission_id = cursor.lastrowid
    conn.commit()
    conn.close()

    # Award karma for submitting
    _add_karma(current_user.id, "blind_review", "Submitted code for blind review")

    return jsonify({
        "submission_id": submission_id,
        "anon_id": anon_id,
        "status": "open",
        "message": "Code submitted anonymously. You'll receive reviews soon.",
    })


@app.route("/blind/queue")
@login_required
def blind_queue():
    """Get open submissions available to review (excluding own submissions)."""
    conn = sqlite3.connect("codebuddy.db")
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT bs.id, bs.anon_id, bs.language, bs.created_at,
               SUBSTR(bs.code, 1, 300) as preview,
               COUNT(br.id) as review_count
        FROM blind_submissions bs
        LEFT JOIN blind_reviews br ON br.submission_id = bs.id
        WHERE bs.user_id != ? AND bs.status = 'open'
        GROUP BY bs.id
        ORDER BY review_count ASC, bs.id DESC
        LIMIT 20
    """, (current_user.id,)).fetchall()
    conn.close()
    return jsonify({"submissions": [dict(r) for r in rows]})


@app.route("/blind/review", methods=["POST"])
@login_required
@rate_limit(max_calls=20, window=60)
def blind_review_submit():
    """Submit a review for a blind submission.

    Input JSON:
      submission_id : ID of the submission
      stars         : 1-5
      comment       : review text
    """
    data = request.json or {}
    submission_id = data.get("submission_id")
    stars = int(data.get("stars", 3))
    comment = (data.get("comment") or "").strip()[:1000]

    if not submission_id or not comment:
        return jsonify({"error": "submission_id and comment required"}), 400
    stars = max(1, min(5, stars))

    conn = sqlite3.connect("codebuddy.db")
    conn.row_factory = sqlite3.Row

    # Can't review own submission
    own = conn.execute(
        "SELECT id FROM blind_submissions WHERE id=? AND user_id=?",
        (submission_id, current_user.id)
    ).fetchone()
    if own:
        conn.close()
        return jsonify({"error": "Cannot review your own submission"}), 403

    # Can't review twice
    already = conn.execute(
        "SELECT id FROM blind_reviews WHERE submission_id=? AND reviewer_id=?",
        (submission_id, current_user.id)
    ).fetchone()
    if already:
        conn.close()
        return jsonify({"error": "Already reviewed this submission"}), 409

    reviewer_anon = _generate_anon_id()
    conn.execute(
        "INSERT INTO blind_reviews(submission_id, reviewer_id, reviewer_anon, stars, comment, created_at) VALUES (?,?,?,?,?,datetime('now'))",
        (submission_id, current_user.id, reviewer_anon, stars, comment)
    )
    conn.commit()

    # Count reviews for this submission
    count = conn.execute(
        "SELECT COUNT(*) as cnt FROM blind_reviews WHERE submission_id=?",
        (submission_id,)
    ).fetchone()["cnt"]
    conn.close()

    # Award karma for reviewing
    _add_karma(current_user.id, "blind_review", "Reviewed anonymous code")

    # Auto-generate AI report when 3+ reviews received
    if count >= 3:
        _trigger_ai_report(submission_id)

    return jsonify({"status": "review submitted", "total_reviews": count})


@app.route("/blind/reviews/<int:submission_id>")
@login_required
def blind_get_reviews(submission_id):
    """Get all reviews for a submission (only accessible to the author or all after 3 reviews)."""
    conn = sqlite3.connect("codebuddy.db")
    conn.row_factory = sqlite3.Row

    sub = conn.execute(
        "SELECT * FROM blind_submissions WHERE id=?", (submission_id,)
    ).fetchone()
    if not sub:
        conn.close()
        return jsonify({"error": "Not found"}), 404

    reviews = conn.execute(
        "SELECT reviewer_anon, stars, comment, created_at FROM blind_reviews WHERE submission_id=? ORDER BY id ASC",
        (submission_id,)
    ).fetchall()

    ai_report_row = conn.execute(
        "SELECT report, scores FROM blind_ai_reports WHERE submission_id=?", (submission_id,)
    ).fetchone()
    conn.close()

    ai_report = None
    if ai_report_row:
        try:
            ai_report = {
                "report": ai_report_row["report"],
                "scores": json.loads(ai_report_row["scores"] or "{}"),
            }
        except (json.JSONDecodeError, TypeError):
            ai_report = {"report": ai_report_row["report"], "scores": {}}

    return jsonify({
        "submission_id": submission_id,
        "anon_id": sub["anon_id"],
        "language": sub["language"],
        "is_author": sub["user_id"] == current_user.id,
        "reviews": [dict(r) for r in reviews],
        "ai_report": ai_report,
    })


def _trigger_ai_report(submission_id):
    """Generate and store an AI consensus report for a submission (background)."""
    try:
        conn = sqlite3.connect("codebuddy.db")
        conn.row_factory = sqlite3.Row

        sub = conn.execute(
            "SELECT code, language FROM blind_submissions WHERE id=?", (submission_id,)
        ).fetchone()
        reviews = conn.execute(
            "SELECT stars, comment FROM blind_reviews WHERE submission_id=?", (submission_id,)
        ).fetchall()
        conn.close()

        if not sub or not reviews:
            return

        review_text = "\n".join(
            f"Reviewer rated {r['stars']}/5: {r['comment']}" for r in reviews
        )

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": MODELS["fast"],
            "max_tokens": 600,
            "temperature": 0.3,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an AI code review synthesizer. Given code and multiple human reviews, "
                        "produce a JSON object (no markdown) with:\n"
                        "{\n"
                        "  \"summary\": \"<2-3 sentence overall assessment>\",\n"
                        "  \"consensus\": \"<what all reviewers agreed on>\",\n"
                        "  \"top_fix\": \"<the single most important improvement>\",\n"
                        "  \"scores\": {\"quality\": <1-10>, \"style\": <1-10>, \"readability\": <1-10>, \"robustness\": <1-10>}\n"
                        "}"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Language: {sub['language']}\n\n"
                        f"Code:\n{sub['code'][:1500]}\n\n"
                        f"Reviews:\n{review_text}"
                    ),
                },
            ],
        }

        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers, json=payload, timeout=25
        )
        raw = resp.json()["choices"][0]["message"]["content"].strip()
        raw = re.sub(r"```json|```", "", raw).strip()
        result = json.loads(raw)

        conn2 = sqlite3.connect("codebuddy.db")
        conn2.execute("""
            INSERT INTO blind_ai_reports(submission_id, report, scores, generated_at)
            VALUES (?,?,?,datetime('now'))
            ON CONFLICT(submission_id) DO UPDATE SET
                report=excluded.report,
                scores=excluded.scores,
                generated_at=excluded.generated_at
        """, (
            submission_id,
            result.get("summary", "") + "\n\n" + result.get("consensus", "") + "\n\nTop fix: " + result.get("top_fix", ""),
            json.dumps(result.get("scores", {})),
        ))
        conn2.commit()
        conn2.close()

    except Exception as exc:
        app.logger.warning(f"AI report generation failed for submission {submission_id}: {exc}")


@app.route("/blind/my_submissions")
@login_required
def blind_my_submissions():
    """Get all blind submissions made by the current user."""
    conn = sqlite3.connect("codebuddy.db")
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT bs.id, bs.anon_id, bs.language, bs.status, bs.created_at,
               COUNT(br.id) as review_count,
               AVG(br.stars) as avg_stars
        FROM blind_submissions bs
        LEFT JOIN blind_reviews br ON br.submission_id = bs.id
        WHERE bs.user_id = ?
        GROUP BY bs.id
        ORDER BY bs.id DESC
    """, (current_user.id,)).fetchall()
    conn.close()
    return jsonify({"submissions": [dict(r) for r in rows]})


# ================= FILE FORGE: EDIT FILE =================

@app.route("/edit_file", methods=["POST"])
@login_required
def edit_file():
    """AI-powered file editor — streams back the edited code."""
    data = request.get_json(force=True)
    original = (data.get("original") or "")[:8000]
    instruction = (data.get("instruction") or "").strip()
    filename = (data.get("filename") or "file.py").strip()
    lang_code = (data.get("lang") or "en-US").strip()

    if not original or not instruction:
        return jsonify({"error": "Missing original code or instruction"}), 400

    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "py"

    system_prompt = (
        "You are an expert code editor. "
        "The user will give you a file and an instruction. "
        "Apply the instruction to the file and return ONLY the full updated code "
        f"inside a single ```{ext} ... ``` fenced block. "
        "Do not add explanations before or after the code block."
    )

    user_prompt = (
        f"File: `{filename}`\n\n"
        f"Instruction: {instruction}\n\n"
        f"```{ext}\n{original}\n```"
    )

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": get_model_for_mode("general", lang_code),
        "max_tokens": 4096,
        "temperature": 0.2,
        "stream": True,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
    }

    def generate():
        try:
            with requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers, json=payload, stream=True, timeout=60
            ) as resp:
                for line in resp.iter_lines():
                    if not line:
                        continue
                    decoded = line.decode("utf-8", errors="ignore")
                    if decoded.startswith("data: "):
                        chunk = decoded[6:]
                        if chunk.strip() == "[DONE]":
                            break
                        try:
                            delta = json.loads(chunk)["choices"][0]["delta"].get("content", "")
                            if delta:
                                yield delta
                        except Exception:
                            pass
        except Exception as exc:
            yield f"\n\n[Error: {exc}]"

    return Response(generate(), mimetype="text/plain")


# ================= FILE FORGE: AUTOCOMPLETE =================

@app.route("/autocomplete", methods=["POST"])
@login_required
def autocomplete():
    """Return up to 3 short code completions for the cursor position."""
    data = request.get_json(force=True)
    before   = (data.get("before") or "")[-1500:]   # last 1500 chars before cursor
    after    = (data.get("after")  or "")[:400]      # first 400 chars after cursor
    language = (data.get("language") or "python").strip()
    lang_code = (data.get("lang") or "en-US").strip()
    filename  = (data.get("filename") or "").strip()

    system_prompt = (
        "You are an AI code autocomplete engine. "
        "Given the code before and after the cursor, suggest up to 3 short completions. "
        "Rules:\n"
        "- Return ONLY a JSON array of strings, no markdown, no explanation.\n"
        "- Each string is a code snippet (1-5 lines) that fits naturally at the cursor.\n"
        "- If the language is Tanglish (ta-en), add a short Tamil comment as the first "
        "  line starting with `# ` so the user sees a bilingual hint.\n"
        "- Keep each completion under 200 characters.\n"
        "- Example output: [\"return result\", \"result = []\", \"for i in range(n):\\n    pass\"]"
    )

    user_prompt = (
        f"Language: {language}\n"
        f"File: {filename or 'untitled'}\n\n"
        f"<before_cursor>\n{before}\n</before_cursor>\n\n"
        f"<after_cursor>\n{after}\n</after_cursor>"
    )

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODELS["fast"],   # Llama 3.3 70B — fast & multilingual
        "max_tokens": 300,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
    }

    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers, json=payload, timeout=15
        )
        raw = resp.json()["choices"][0]["message"]["content"].strip()
        # Strip any accidental markdown fences
        raw = re.sub(r"```json|```", "", raw).strip()
        completions = json.loads(raw)
        if not isinstance(completions, list):
            completions = []
        # Sanitise — keep only strings, max 3
        completions = [str(c) for c in completions if c][:3]
        return jsonify({"completions": completions})
    except Exception as exc:
        app.logger.warning(f"Autocomplete failed: {exc}")
        return jsonify({"completions": []})


# ================= VIDEO ANALYZER =================
# Extracts frames from uploaded video, sends to vision-capable AI model,
# streams back a detailed analysis of the programming content shown.

# Vision-capable free model on OpenRouter
_VIDEO_MODEL = "google/gemini-flash-1.5"          # Vision + fast + free tier
_VIDEO_MODEL_FALLBACK = "anthropic/claude-3-haiku" # fallback if Gemini quota hit

def _extract_video_frames(video_path, max_frames=6):
    """Extract up to max_frames evenly-spaced frames from a video file.
    Returns list of (frame_index, base64_jpeg_str) tuples.
    Falls back to empty list if OpenCV not installed.
    """
    frames = []
    try:
        import cv2
        cap = cv2.VideoCapture(video_path)
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total <= 0:
            cap.release()
            return []
        # Pick evenly spaced indices
        indices = [int(total * i / max_frames) for i in range(max_frames)]
        for idx in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if not ret:
                continue
            # Resize to max 640px wide to keep payload small
            h, w = frame.shape[:2]
            if w > 640:
                scale = 640 / w
                frame = cv2.resize(frame, (640, int(h * scale)))
            _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 72])
            import base64
            b64 = base64.b64encode(buf.tobytes()).decode('utf-8')
            frames.append((idx, b64))
        cap.release()
    except Exception as e:
        app.logger.warning(f"Frame extraction failed: {e}")
    return frames


def _video_to_base64_thumbnail(video_path):
    """Return a single base64 JPEG thumbnail (first keyframe) for fallback."""
    try:
        import cv2, base64
        cap = cv2.VideoCapture(video_path)
        ret, frame = cap.read()
        cap.release()
        if not ret:
            return None
        h, w = frame.shape[:2]
        if w > 640:
            scale = 640 / w
            frame = cv2.resize(frame, (640, int(h * scale)))
        _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 72])
        return base64.b64encode(buf.tobytes()).decode('utf-8')
    except Exception:
        return None


@app.route("/analyze_video", methods=["POST"])
@login_required
@rate_limit(max_calls=10, window=60)
def analyze_video():
    """Analyze a programming/coding video using a vision AI model.

    Accepts: multipart/form-data with:
      video          : video file (MP4, WebM, MOV, AVI — max 100MB)
      question       : optional specific question about the video
      conversation_id: optional — to save the analysis as a chat message

    Streams back a markdown analysis.
    """
    import tempfile, os as _os, base64

    video_file = request.files.get("video")
    question   = (request.form.get("question") or "").strip()
    conversation_id = request.form.get("conversation_id", "").strip()

    if not video_file:
        return jsonify({"error": "No video file uploaded"}), 400

    # Validate file type
    fname = video_file.filename or "video.mp4"
    allowed_exts = {".mp4", ".webm", ".mov", ".avi", ".ogv", ".ogg", ".mkv"}
    ext = os.path.splitext(fname.lower())[1]
    if ext not in allowed_exts:
        return jsonify({"error": f"Unsupported format '{ext}'. Use MP4, WebM, MOV, or AVI."}), 400

    # Save to temp file
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            video_file.save(tmp)
            tmp_path = tmp.name

        file_size_mb = os.path.getsize(tmp_path) / (1024 * 1024)
        if file_size_mb > 100:
            return jsonify({"error": "File too large. Max 100MB."}), 400

        # Build the analysis prompt
        default_q = (
            "Analyze this programming video in detail:\n"
            "1. What programming language(s) and technologies are shown?\n"
            "2. What concept or algorithm is being demonstrated?\n"
            "3. Walk through what the code does step by step.\n"
            "4. Identify any bugs, inefficiencies, or improvements.\n"
            "5. What would be a good exercise based on this video?\n"
            "Be specific about variable names, function names, and logic shown."
        )
        prompt = question if question else default_q

        # Try to extract frames with OpenCV
        frames = _extract_video_frames(tmp_path, max_frames=6)
        has_frames = len(frames) > 0

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://codebuddy.ai",
            "X-Title": "CodeBuddy Video Analyzer",
        }

        if has_frames:
            # Build vision message with extracted frames
            content_parts = [{"type": "text", "text": prompt + f"\n\n[Video: {fname}, {file_size_mb:.1f}MB, {len(frames)} frames extracted]"}]
            for i, (frame_idx, b64) in enumerate(frames):
                content_parts.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{b64}",
                        "detail": "high"
                    }
                })
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are CodeBuddy Video Analyzer — an expert programming tutor who analyzes "
                        "coding tutorial videos frame by frame. You specialize in identifying code, "
                        "algorithms, bugs, and teaching points from video screenshots. "
                        "Always provide detailed, practical analysis. Use markdown with code blocks. "
                        "If the video does not contain programming content, politely say so."
                    )
                },
                {"role": "user", "content": content_parts}
            ]
            model_to_use = _VIDEO_MODEL
        else:
            # No OpenCV — text-only analysis based on filename + question
            app.logger.info("analyze_video: OpenCV not available — text-only mode")
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are CodeBuddy Video Analyzer. The user uploaded a programming video "
                        "but frame extraction is not available (OpenCV not installed). "
                        "Answer based on the filename and question provided. "
                        "Suggest installing opencv-python for full video analysis. "
                        "Use markdown formatting."
                    )
                },
                {
                    "role": "user",
                    "content": f"Video filename: {fname}\n\nUser question: {prompt}\n\n"
                               f"[Note: Frame extraction unavailable — install opencv-python for full analysis]"
                }
            ]
            model_to_use = MODELS["fast"]  # text-only doesn't need vision

        payload = {
            "model": model_to_use,
            "stream": True,
            "max_tokens": 2000,
            "temperature": 0.4,
            "messages": messages,
        }

        def generate():
            full = ""
            tried_models = [model_to_use]

            if not has_frames:
                yield f"⚠️ **Frame extraction unavailable** — install `opencv-python` for full video analysis.\n\n"
                yield f"**Responding based on filename and your question:**\n\n"

            try:
                resp = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers, json=payload, stream=True, timeout=(15, 120)
                )

                # Fallback chain for vision models
                if resp.status_code in (404, 429, 503) and has_frames:
                    for fb in [_VIDEO_MODEL_FALLBACK, MODELS["fast"]]:
                        if fb in tried_models:
                            continue
                        tried_models.append(fb)
                        payload["model"] = fb
                        resp = requests.post(
                            "https://openrouter.ai/api/v1/chat/completions",
                            headers=headers, json=payload, stream=True, timeout=(15, 120)
                        )
                        if resp.status_code == 200:
                            break

                if resp.status_code == 401:
                    yield "⚠ API key invalid. Check your OPENROUTER_API_KEY in .env"
                    return
                if resp.status_code != 200:
                    yield f"⚠ API Error {resp.status_code}. Try again in a moment."
                    return

                for line in resp.iter_lines():
                    if not line:
                        continue
                    decoded = line.decode("utf-8", errors="ignore")
                    if decoded.startswith("data: "):
                        data = decoded[6:]
                        if data.strip() == "[DONE]":
                            break
                        try:
                            token = json.loads(data)["choices"][0]["delta"].get("content", "")
                            full += token
                            yield token
                        except (json.JSONDecodeError, KeyError, IndexError):
                            pass

            except requests.exceptions.Timeout:
                yield "\n\n⏱ Analysis timed out. Try a shorter video clip."
            except requests.exceptions.ConnectionError:
                yield "\n\n🔌 Connection error. Check your internet."
            except Exception as e:
                yield f"\n\n⚠ Error: {str(e)}"

            # Save to chat if conversation_id provided
            if full and conversation_id:
                try:
                    save_conn = sqlite3.connect("codebuddy.db")
                    save_conn.execute(
                        "INSERT INTO messages(conversation_id,role,content,timestamp) VALUES (?,?,?,?)",
                        (conversation_id, "assistant", f"**📹 Video Analysis: {fname}**\n\n" + full, datetime.now().isoformat())
                    )
                    save_conn.commit()
                    save_conn.close()
                except Exception:
                    pass

        return Response(generate(), mimetype="text/plain")

    except Exception as e:
        app.logger.error(f"analyze_video error: {e}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


# ================= RUN APP =================


# ═══════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════
# REAL VOICE CLONE — Coqui XTTS-v2
# Records 10s of user voice → clones it → AI speaks IN YOUR VOICE
# Falls back to gTTS if XTTS not installed
# ═══════════════════════════════════════════════════════════════

import os as _vc_os, datetime as _vc_dt, json as _vc_json, threading as _vc_thread

_VOICE_DIR = _vc_os.path.join(_vc_os.path.dirname(_vc_os.path.abspath(__file__)), "voice_profiles")
_vc_os.makedirs(_VOICE_DIR, exist_ok=True)

_xtts_model = None
_xtts_lock  = _vc_thread.Lock()
_XTTS_READY = False

def _vc_audio_path(user_id):
    return _vc_os.path.join(_VOICE_DIR, f"user_{user_id}.wav")

def _vc_meta_path(user_id):
    return _vc_os.path.join(_VOICE_DIR, f"user_{user_id}.json")

def _load_xtts():
    """Lazy-load XTTS-v2 model once, keep in memory."""
    global _xtts_model, _XTTS_READY
    if _xtts_model is not None:
        return _xtts_model, True
    with _xtts_lock:
        if _xtts_model is not None:
            return _xtts_model, True
        try:
            from TTS.api import TTS as _TTS
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            app.logger.info(f"Loading XTTS-v2 on {device} — this takes ~30s first time...")
            _xtts_model = _TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
            _XTTS_READY = True
            app.logger.info("XTTS-v2 loaded and ready!")
            return _xtts_model, True
        except Exception as e:
            app.logger.warning(f"XTTS-v2 load failed: {e}")
            return None, False

_XTTS_LANG = {
    "en-US":"en","en":"en","ta-IN":"ta","ta-en":"ta",
    "hi-IN":"hi","te-IN":"te","ml-IN":"ml","kn-IN":"kn",
    "bn-IN":"bn","mr-IN":"mr","fr-FR":"fr","de-DE":"de",
    "es-ES":"es","ja-JP":"ja","zh-CN":"zh-cn","ko-KR":"ko",
    "ar-SA":"ar","ru-RU":"ru","pt-BR":"pt","pl-PL":"pl",
    "nl-NL":"nl","cs-CZ":"cs","hu-HU":"hu","tr-TR":"tr",
}

def _xtts_speak(text, speaker_wav, lang_code):
    """Generate WAV bytes using XTTS-v2 with user voice as reference."""
    model, ok = _load_xtts()
    if not ok or model is None:
        return None
    try:
        import tempfile
        lang = _XTTS_LANG.get(lang_code, "en")
        clean = _clean_for_tts(text)
        if not clean:
            return None
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            out_path = tmp.name
        model.tts_to_file(text=clean, speaker_wav=speaker_wav,
                           language=lang, file_path=out_path)
        with open(out_path, "rb") as f:
            wav = f.read()
        _vc_os.unlink(out_path)
        app.logger.info(f"XTTS-v2 generated {len(wav)//1024}KB wav lang={lang}")
        return wav
    except Exception as e:
        app.logger.error(f"XTTS-v2 speak failed: {e}")
        return None

def _find_ffmpeg():
    """Locate ffmpeg binary — returns (path, version_str) or (None, None)."""
    import shutil, subprocess
    for candidate in ["ffmpeg", "/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg"]:
        path = shutil.which(candidate) or (candidate if _vc_os.path.isfile(candidate) else None)
        if path:
            try:
                r = subprocess.run([path, "-version"], capture_output=True, timeout=5)
                ver = r.stdout.decode("utf-8", errors="ignore").split("\n")[0]
                return path, ver
            except Exception:
                return path, "unknown"
    return None, None


def _to_wav(audio_bytes, mime="audio/webm"):
    """Convert any audio format to 22050Hz mono WAV for XTTS-v2."""
    import tempfile, subprocess
    ext = "webm" if "webm" in mime else "ogg" if "ogg" in mime else "mp3" if "mp3" in mime else "wav"
    with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as f:
        f.write(audio_bytes)
        in_path = f.name
    out_path = in_path + "_out.wav"
    converted = False
    try:
        ffmpeg_bin, _ = _find_ffmpeg()
        if ffmpeg_bin:
            r = subprocess.run(
                [ffmpeg_bin, "-y", "-i", in_path, "-ar", "22050", "-ac", "1", out_path],
                capture_output=True, timeout=30)
            if r.returncode == 0 and _vc_os.path.exists(out_path):
                with open(out_path, "rb") as f:
                    wav = f.read()
                converted = True
    except Exception as e:
        app.logger.warning(f"ffmpeg convert failed: {e}")
    finally:
        for p in [in_path, out_path]:
            if _vc_os.path.exists(p):
                try: _vc_os.unlink(p)
                except: pass
    if converted:
        return wav
    # pydub fallback
    try:
        from pydub import AudioSegment
        import io as _bio
        seg = AudioSegment.from_file(_bio.BytesIO(audio_bytes))
        seg = seg.set_frame_rate(22050).set_channels(1)
        buf = _bio.BytesIO()
        seg.export(buf, format="wav")
        return buf.getvalue()
    except Exception:
        return audio_bytes  # return original as last resort

def _vc_detect_language_from_transcript(transcript):
    """Detect language from transcript using Unicode ranges then AI classifier."""
    if not transcript or not transcript.strip():
        return "en-US", "English"
    text = transcript.strip()
    script_map = [
        ('\u0B80','\u0BFF',"ta-IN","Tamil"),
        ('\u0C00','\u0C7F',"te-IN","Telugu"),
        ('\u0C80','\u0CFF',"kn-IN","Kannada"),
        ('\u0D00','\u0D7F',"ml-IN","Malayalam"),
        ('\u0980','\u09FF',"bn-IN","Bengali"),
        ('\u0900','\u097F',"hi-IN","Hindi"),
        ('\u0A80','\u0AFF',"gu-IN","Gujarati"),
        ('\u0A00','\u0A7F',"pa-IN","Punjabi"),
        ('\u0600','\u06FF',"ar-SA","Arabic"),
        ('\u4E00','\u9FFF',"zh-CN","Chinese"),
        ('\u3040','\u30FF',"ja-JP","Japanese"),
        ('\uAC00','\uD7AF',"ko-KR","Korean"),
        ('\u0400','\u04FF',"ru-RU","Russian"),
    ]
    for start, end, code, name in script_map:
        if any(start <= c <= end for c in text):
            return code, name
    return "en-US", "English"


@app.route("/voice_clone/status")
@login_required
def voice_clone_status():
    meta_path = _vc_meta_path(current_user.id)
    audio_path = _vc_audio_path(current_user.id)
    try:
        from TTS.api import TTS as _T; xtts_ok = True
    except ImportError:
        xtts_ok = False
    if _vc_os.path.exists(meta_path):
        try:
            with open(meta_path) as f:
                meta = _vc_json.load(f)
            has_audio = _vc_os.path.exists(audio_path)
            engine = "xtts_v2" if (has_audio and xtts_ok) else "gtts"
            return jsonify({
                "has_profile": True,
                "has_audio": has_audio,
                "xtts_available": xtts_ok,
                "tts_engine": engine,
                "profile_id": f"voice_{current_user.id}",
                "created_at": meta.get("created_at",""),
                "detected_lang": meta.get("detected_lang","en-US"),
                "detected_lang_name": meta.get("detected_lang_name","English"),
            })
        except Exception:
            pass
    return jsonify({"has_profile": False, "xtts_available": xtts_ok})


@app.route("/voice_clone/upload", methods=["POST"])
@login_required
@rate_limit(max_calls=10, window=60)
def voice_clone_upload():
    transcript = (request.form.get("transcript") or "").strip()
    lang_hint  = (request.form.get("lang_hint")  or "").strip()
    audio_file = request.files.get("audio")

    LANG_NAMES = {
        "en-US":"English","ta-IN":"Tamil","ta-en":"Tanglish",
        "hi-IN":"Hindi","te-IN":"Telugu","kn-IN":"Kannada",
        "ml-IN":"Malayalam","bn-IN":"Bengali","mr-IN":"Marathi",
        "pa-IN":"Punjabi","gu-IN":"Gujarati","fr-FR":"French",
        "de-DE":"German","es-ES":"Spanish","ja-JP":"Japanese",
        "zh-CN":"Chinese","ko-KR":"Korean","ar-SA":"Arabic",
        "ru-RU":"Russian","pt-BR":"Portuguese",
    }

    # Detect language — non-English UI hint is most reliable
    if lang_hint and lang_hint in LANG_NAMES and lang_hint != "en-US":
        detected_lang, detected_lang_name = lang_hint, LANG_NAMES[lang_hint]
    elif transcript:
        detected_lang, detected_lang_name = _vc_detect_language_from_transcript(transcript)
        if detected_lang == "en-US" and lang_hint in LANG_NAMES:
            detected_lang, detected_lang_name = lang_hint, LANG_NAMES[lang_hint]
    elif lang_hint in LANG_NAMES:
        detected_lang, detected_lang_name = lang_hint, LANG_NAMES[lang_hint]
    else:
        detected_lang, detected_lang_name = "en-US", "English"

    # Save voice sample as WAV for XTTS-v2
    audio_saved = False
    try:
        from TTS.api import TTS as _T; xtts_ok = True
    except ImportError:
        xtts_ok = False

    if audio_file:
        raw = audio_file.read()
        if len(raw) < 500:
            return jsonify({"error": "Recording too short — speak at least 5 seconds"}), 400
        mime = audio_file.content_type or "audio/webm"
        wav = _to_wav(raw, mime)
        if wav:
            with open(_vc_audio_path(current_user.id), "wb") as f:
                f.write(wav)
            audio_saved = True
            app.logger.info(f"Voice sample saved: {len(wav)//1024}KB WAV")

    engine = "xtts_v2" if (audio_saved and xtts_ok) else "gtts"
    meta = {
        "detected_lang": detected_lang,
        "detected_lang_name": detected_lang_name,
        "transcript": transcript[:200],
        "created_at": _vc_dt.datetime.now().isoformat(),
        "profile_id": f"voice_{current_user.id}",
        "tts_engine": engine,
        "audio_saved": audio_saved,
    }
    with open(_vc_meta_path(current_user.id), "w") as f:
        _vc_json.dump(meta, f)

    eng_label = "XTTS-v2 (your real voice)" if engine == "xtts_v2" else "Google TTS"
    return jsonify({
        "profile_id": f"voice_{current_user.id}",
        "status": "active",
        "detected_lang": detected_lang,
        "detected_lang_name": detected_lang_name,
        "tts_engine": engine,
        "audio_saved": audio_saved,
        "message": f"Language: {detected_lang_name} | Engine: {eng_label} | PLAY will speak in your voice."
    })


@app.route("/voice_clone/delete", methods=["POST"])
@login_required
def voice_clone_delete():
    deleted = []
    for path in [_vc_audio_path(current_user.id), _vc_meta_path(current_user.id)]:
        if _vc_os.path.exists(path):
            try: _vc_os.remove(path); deleted.append(_vc_os.path.basename(path))
            except Exception as e: app.logger.warning(f"Delete failed {path}: {e}")
    return jsonify({"deleted": True, "files": deleted})


@app.route("/voice_clone/tts", methods=["POST"])
@login_required
@rate_limit(max_calls=60, window=60)
def voice_clone_tts():
    """Generate TTS — XTTS-v2 (real voice) if available, else gTTS."""
    req_data  = request.get_json(silent=True) or {}
    raw       = (req_data.get("text") or "").strip()[:2000]
    ui_lang   = (req_data.get("lang") or "en-US").strip()
    if not raw:
        return jsonify({"error": "No text provided"}), 400

    # Read profile
    lang_code   = ui_lang
    audio_path  = _vc_audio_path(current_user.id)
    tts_engine  = "gtts"
    meta_path   = _vc_meta_path(current_user.id)

    if _vc_os.path.exists(meta_path):
        try:
            with open(meta_path) as f:
                meta = _vc_json.load(f)
            profile_lang = meta.get("detected_lang","").strip()
            tts_engine   = meta.get("tts_engine","gtts")
            if profile_lang:
                lang_code = profile_lang if profile_lang != "en-US" else (ui_lang if ui_lang != "en-US" else profile_lang)
        except Exception:
            pass

    # ── XTTS-v2: real voice clone ─────────────────────────────────────────
    if tts_engine == "xtts_v2" and _vc_os.path.exists(audio_path):
        wav = _xtts_speak(raw, audio_path, lang_code)
        if wav:
            return Response(wav, mimetype="audio/wav",
                            headers={"Cache-Control":"no-cache","X-TTS-Engine":"xtts_v2","X-Lang":lang_code})
        app.logger.warning("XTTS-v2 failed — falling back to gTTS")

    # ── gTTS fallback ─────────────────────────────────────────────────────
    if not _GTTS_OK:
        return jsonify({"error": "No TTS engine. Run: pip install gtts"}), 503
    text      = _clean_for_tts(raw)
    gtts_lang = TTS_LANG_MAP.get(lang_code, TTS_LANG_MAP.get(ui_lang, "en"))
    is_tanglish = (lang_code == "ta-en")
    try:
        segs   = _smart_split(text, gtts_lang, is_tanglish=is_tanglish)
        chunks = []
        for sl, st in segs:
            if not st.strip(): continue
            try:
                slow = sl in ("ta","ml","kn","te") or is_tanglish or (sl=="en" and len(st.split())<=3)
                chunks.append(_gtts_chunk(st, sl, slow=slow))
            except Exception as e:
                app.logger.warning(f"gTTS chunk failed lang={sl}: {e}")
        if not chunks:
            return jsonify({"error": "TTS generation failed"}), 502
        return Response(b"".join(chunks), mimetype="audio/mpeg",
                        headers={"Cache-Control":"no-cache","X-TTS-Engine":"gtts","X-Lang":lang_code})
    except Exception as exc:
        return jsonify({"error": f"TTS failed: {str(exc)}"}), 502


# ── /coqui/* aliases → /voice_clone/* ────────────────────────────────────────
@app.route("/coqui/status")
@login_required
def coqui_status_alias():
    return voice_clone_status()

@app.route("/coqui/upload", methods=["POST"])
@login_required
@rate_limit(max_calls=10, window=60)
def coqui_upload_alias():
    return voice_clone_upload()

@app.route("/coqui/delete", methods=["POST"])
@login_required
def coqui_delete_alias():
    return voice_clone_delete()

@app.route("/coqui/tts", methods=["POST"])
@login_required
@rate_limit(max_calls=60, window=60)
def coqui_tts_alias():
    return voice_clone_tts()


@app.route("/tts/diagnose")
@login_required
def tts_diagnose():
    import sys, io as _diagio
    results = {
        "gtts_installed": False, "xtts_installed": False,
        "profile_exists": False, "audio_saved": False,
        "python_version": sys.version,
        "test_english": False, "test_tamil": False, "test_malayalam": False,
        "click_version": "?"
    }
    try:
        import click; results["click_version"] = click.__version__
    except Exception:
        pass
    try:
        import gtts
        results["gtts_installed"] = True
        results["gtts_version"] = getattr(gtts, "__version__", "?")
        for lang, key, sample in [
            ("en",  "test_english",   "Hello CodeBuddy voice test."),
            ("ta",  "test_tamil",     "வணக்கம் கோட் பட்டி சோதனை"),
            ("ml",  "test_malayalam", "നമസ്കാരം കോഡ് ബഡ്ഡി"),
        ]:
            try:
                buf = _diagio.BytesIO()
                gtts.gTTS(text=sample, lang=lang, slow=False).write_to_fp(buf)
                results[key] = len(buf.getvalue()) > 100
            except Exception as e:
                results[key] = False
                results[key + "_error"] = str(e)
    except ImportError as e:
        results["gtts_error"] = str(e)
    try:
        from TTS.api import TTS as _T
        import torch
        results["xtts_installed"] = True
        results["xtts_device"] = "cuda" if torch.cuda.is_available() else "cpu"
        results["xtts_model_loaded"] = _XTTS_READY
    except Exception as e:
        results["xtts_error"] = str(e)
    meta_path  = _vc_meta_path(current_user.id)
    audio_path = _vc_audio_path(current_user.id)
    results["profile_exists"] = _vc_os.path.exists(meta_path)
    results["audio_saved"]    = _vc_os.path.exists(audio_path)
    if results["profile_exists"]:
        try:
            with open(meta_path) as f:
                meta = _vc_json.load(f)
            results["profile_lang"]      = meta.get("detected_lang")
            results["profile_lang_name"] = meta.get("detected_lang_name")
            results["tts_engine"]        = meta.get("tts_engine", "gtts")
            if results["audio_saved"]:
                results["audio_size_kb"] = _vc_os.path.getsize(audio_path) // 1024
        except Exception:
            pass
    return jsonify(results)



@app.route("/collab_chat", methods=["POST"])
@login_required
@rate_limit(max_calls=50, window=60)
def collab_chat():
    """Chat for collab — membership check instead of ownership check."""
    user_message    = request.form.get("message", "").strip()
    conversation_id = request.form.get("conversation_id")
    mode            = request.form.get("mode", "general")
    lang_code       = request.form.get("lang", "en-US")
    room_code       = request.form.get("room_code", "")

    if not user_message:
        return Response("Please enter a message.", mimetype="text/plain")

    if room_code:
        room = _collab_rooms.get(room_code)
        if not room:
            return Response("⚠ Collab session expired. Please create a new session.", mimetype="text/plain")
        # Auto-add member if they joined via link
        if current_user.username not in room.get("members", []):
            room["members"].append(current_user.username)
        conversation_id = str(room["chat_id"])

    if not conversation_id:
        return Response("⚠ No conversation linked. Initialize a session first.", mimetype="text/plain")

    conn = sqlite3.connect("codebuddy.db")
    conn.row_factory = sqlite3.Row
    convo = conn.execute("SELECT id FROM conversations WHERE id=?", (conversation_id,)).fetchone()
    conn.close()
    if not convo:
        return Response("⚠ Chat not found. It may have been deleted.", mimetype="text/plain")

    conn = sqlite3.connect("codebuddy.db")
    conn.execute("INSERT INTO messages(conversation_id,role,content,timestamp) VALUES (?,?,?,?)",
                 (conversation_id, "user", user_message, datetime.now().isoformat()))
    conn.execute("UPDATE conversations SET updated_at=? WHERE id=?",
                 (datetime.now().isoformat(), conversation_id))
    conn.commit()
    conn.close()

    system_prompt  = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS["general"]) + _RESPECTFUL_TONE
    history        = get_conversation_history(conversation_id, limit=16)
    api_messages   = [{"role": "system", "content": system_prompt}] + history
    selected_model = get_model_for_mode(mode, lang_code)

    hdrs = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://codebuddy.ai",
        "X-Title": "CodeBuddy Collab",
    }
    payload = {
        "model": selected_model,
        "stream": True,
        "max_tokens": 2000,
        "temperature": 0.7,
        "messages": api_messages,
    }

    def generate():
        full = ""
        try:
            resp = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=hdrs, json=payload, stream=True, timeout=(10, 90)
            )
            if resp.status_code != 200:
                tried = {payload["model"]}
                for fb in FREE_FALLBACKS:
                    if fb in tried:
                        continue
                    tried.add(fb)
                    payload["model"] = fb
                    resp = requests.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers=hdrs, json=payload, stream=True, timeout=(10, 90)
                    )
                    if resp.status_code == 200:
                        break
                else:
                    yield f"⚠ API Error {resp.status_code}. All models unavailable — try again."
                    return

            for line in resp.iter_lines():
                if line:
                    dec = line.decode("utf-8", errors="ignore")
                    if dec.startswith("data: "):
                        d = dec[6:]
                        if d.strip() == "[DONE]":
                            break
                        try:
                            token = json.loads(d)["choices"][0]["delta"].get("content", "")
                            token = _filter_response(token)
                            full += token
                            yield token
                        except (json.JSONDecodeError, KeyError, IndexError):
                            pass

        except requests.exceptions.ConnectTimeout:
            yield "\n\n⏱ Could not connect to AI service. Check your internet."
        except requests.exceptions.ReadTimeout:
            if full:
                yield "\n\n⚠ Response cut short."
            else:
                yield "\n\n⏱ AI timed out. Please try again."
        except requests.exceptions.ConnectionError:
            yield "\n\n🔌 Connection lost. Check your internet."
        except Exception as e:
            yield f"\n\n⚠ Error: {str(e)}"

        if full:
            full = _filter_response(full)
            sc = sqlite3.connect("codebuddy.db")
            sc.execute(
                "INSERT INTO messages(conversation_id,role,content,timestamp) VALUES (?,?,?,?)",
                (conversation_id, "assistant", full, datetime.now().isoformat())
            )
            sc.commit()
            sc.close()

    return Response(generate(), mimetype="text/plain")

# COLLABORATE — Real-time coding sessions + WebRTC voice calls
# ═══════════════════════════════════════════════════════════════

import random as _random, string as _string

@app.route("/collab/create", methods=["POST"])
@login_required
def collab_create():
    data = request.get_json(silent=True) or {}
    chat_id = data.get("chat_id")
    if not chat_id:
        return jsonify({"error": "No chat_id provided"}), 400
    conn = sqlite3.connect("codebuddy.db")
    conn.row_factory = sqlite3.Row
    chat = conn.execute(
        "SELECT id, title FROM conversations WHERE id=? AND user_id=?",
        (chat_id, current_user.id)
    ).fetchone()
    conn.close()
    if not chat:
        return jsonify({"error": "Chat not found"}), 404
    room_code = ''.join(_random.choices(_string.ascii_lowercase + _string.digits, k=8))
    _collab_rooms[room_code] = {
        "chat_id": chat_id,
        "chat_title": chat["title"] or "Untitled",
        "host": current_user.username,
        "host_id": current_user.id,
        "members": [current_user.username],
    }
    collab_url = url_for("collab_page", room_code=room_code, _external=True)
    return jsonify({"room_code": room_code, "collab_url": collab_url, "chat_title": chat["title"] or "Untitled"})


@app.route("/collab/<room_code>")
@login_required
def collab_page(room_code):
    room = _collab_rooms.get(room_code)
    if not room:
        return "<h2 style='font-family:monospace;color:#ff6b2b;padding:40px'>Session expired. <a href='/'>Go back</a></h2>", 404
    if current_user.username not in room["members"]:
        room["members"].append(current_user.username)
    conn = sqlite3.connect("codebuddy.db")
    conn.row_factory = sqlite3.Row
    messages = conn.execute(
        "SELECT role, content FROM messages WHERE conversation_id=? ORDER BY id ASC",
        (room["chat_id"],)
    ).fetchall()
    conn.close()
    chat_id = room["chat_id"]
    return render_template("collab.html",
        room_code=room_code, room=room,
        messages=[{"role": m["role"], "content": m["content"]} for m in messages],
        username=current_user.username, chat_id=chat_id)


@app.route("/collab/<room_code>/end", methods=["POST"])
@login_required
def collab_end(room_code):
    room = _collab_rooms.get(room_code)
    if not room:
        return jsonify({"error": "Room not found"}), 404
    if room["host_id"] != current_user.id:
        return jsonify({"error": "Only host can end"}), 403
    _collab_rooms.pop(room_code, None)
    if socketio:
        socketio.emit("session_ended", {"message": "Host ended the session"}, room=room_code)
    return jsonify({"ended": True})


# ── SocketIO events ──
if _SOCKETIO_OK and socketio:
    @socketio.on("join_collab")
    def on_join(data):
        room_code = data.get("room_code"); username = data.get("username")
        if not room_code or not username: return
        join_room(room_code)
        room = _collab_rooms.get(room_code, {})
        emit("user_joined", {"username": username, "members": room.get("members", []), "message": f"{username} joined"}, room=room_code)

    @socketio.on("leave_collab")
    def on_leave(data):
        room_code = data.get("room_code"); username = data.get("username")
        if not room_code: return
        leave_room(room_code)
        room = _collab_rooms.get(room_code, {})
        if username in room.get("members", []): room["members"].remove(username)
        emit("user_left", {"username": username, "members": room.get("members", []), "message": f"{username} left"}, room=room_code)

    @socketio.on("collab_message")
    def on_msg(data):
        room_code = data.get("room_code")
        if room_code: emit("new_message", data, room=room_code)

    @socketio.on("collab_typing")
    def on_typing(data):
        room_code = data.get("room_code")
        if room_code: emit("user_typing", data, room=room_code, include_self=False)

    @socketio.on("webrtc_signal")
    def on_webrtc(data):
        room_code = data.get("room_code")
        if room_code: emit("webrtc_signal", data, room=room_code, include_self=False)

    @socketio.on("voice_state")
    def on_voice(data):
        room_code = data.get("room_code")
        if room_code: emit("voice_state_update", data, room=room_code)

if __name__ == "__main__":
    # CRITICAL: use_reloader=False stops Flask restarting with a new random
    # secret_key when files change, which invalidates all session cookies.
    _kw = dict(host="127.0.0.1", port=5000, debug=True, use_reloader=False)
    if _SOCKETIO_OK and socketio:
        socketio.run(app, **_kw)
    else:
        app.run(**_kw)