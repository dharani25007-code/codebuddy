import os
import json
import sqlite3
import tempfile
import subprocess
import re
import secrets
from datetime import datetime
from functools import wraps
from collections import defaultdict
import time

import requests
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, Response, redirect, url_for, session, g
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin, current_user
from flask_bcrypt import Bcrypt

# ================= INIT =================

load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", secrets.token_hex(32))

bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

# ================= RATE LIMITING =================

_rate_store = defaultdict(list)

def rate_limit(max_calls=20, window=60):
    """Allow max_calls requests per window seconds per user."""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            key = str(current_user.id) if current_user.is_authenticated else request.remote_addr
            now = time.time()
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

    conn.commit()

    # ── MIGRATIONS: add columns that may be missing from older DBs ──
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

    conn.commit()
    conn.close()

init_db()

# ================= HELPERS =================

def bump_stat(user_id, field, amount=1):
    """Increment a stat column for a user."""
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

def is_programming_related(text):
    """Broad but smart programming filter."""
    keywords = [
        "python","java","c++","c#","c","javascript","typescript","html","css",
        "sql","react","vue","angular","flask","django","fastapi","node","express",
        "api","rest","graphql","algorithm","data structure","recursion","complexity",
        "big o","machine learning","deep learning","neural","tensorflow","pytorch",
        "ai","iot","code","function","class","loop","array","list","dict","object",
        "database","mongodb","postgres","mysql","redis","docker","kubernetes",
        "git","github","linux","bash","shell","terminal","regex","json","xml",
        "debug","error","bug","exception","compile","runtime","pointer","memory",
        "stack","queue","tree","graph","hash","sort","search","binary","dsa",
        "interview","leetcode","competitive","frontend","backend","fullstack",
        "devops","cloud","aws","azure","gcp","microservice","http","tcp","ssl",
        "encrypt","security","auth","token","jwt","oauth","cors","async","thread",
        "concurrency","parallel","test","unittest","pytest","ci/cd","pipeline",
        "how to","what is","explain","write","fix","optimize","implement","build",
        "create","design","refactor","review","help","what does","how does"
    ]
    text_lower = text.lower()
    # Also allow general "how to" questions in programming context
    return any(kw in text_lower for kw in keywords) or len(text.split()) < 4

def get_conversation_history(conversation_id, limit=20):
    """Fetch last N messages for full context."""
    conn = sqlite3.connect("codebuddy.db")
    conn.row_factory = sqlite3.Row
    messages = conn.execute(
        """SELECT role, content FROM messages
           WHERE conversation_id=?
           ORDER BY id DESC LIMIT ?""",
        (conversation_id, limit)
    ).fetchall()
    conn.close()
    # Reverse to chronological order
    return [{"role": m["role"], "content": m["content"]} for m in reversed(messages)]

def generate_chat_title(user_message):
    """Generate a smart 4-6 word title from first message using AI."""
    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "meta-llama/llama-3-8b-instruct",
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
    except:
        return user_message[:40] + "..." if len(user_message) > 40 else user_message

# ================= SYSTEM PROMPTS =================

SYSTEM_PROMPTS = {
    "general": """You are CodeBuddy — the world's most advanced programming AI assistant.
You specialize exclusively in programming, software development, and computer science.
Always:
- Give clean, well-commented code examples
- Explain your reasoning step by step
- Mention time/space complexity when relevant
- Suggest best practices and modern approaches
- If code is provided, analyze it thoroughly
Format code in markdown code blocks with the language specified.""",

    "debug": """You are CodeBuddy Debug Engine — an elite debugging specialist.
When analyzing code:
1. IDENTIFY: List all bugs found (syntax, logic, runtime, security)
2. EXPLAIN: Clearly explain WHY each bug exists
3. FIX: Provide the corrected code with comments on changes
4. PREVENT: Suggest how to avoid similar bugs in future
Be thorough. Check for edge cases, null handling, off-by-one errors, and security issues.
Format everything cleanly with markdown.""",

    "optimize": """You are CodeBuddy Optimizer — a performance engineering expert.
When optimizing code:
1. ANALYZE: Current time complexity (Big-O) and space complexity
2. BOTTLENECKS: Identify what's slow and why
3. OPTIMIZED CODE: Rewrite with full optimization
4. COMPARISON: Before vs After complexity
5. TRADE-OFFS: Explain any readability/performance trade-offs
Always show the optimized version with detailed comments.""",

    "explain": """You are CodeBuddy Explainer — a master teacher of programming concepts.
Explain code or concepts:
- Start with a simple one-line summary
- Then give a detailed walkthrough line by line if it's code
- Use real-world analogies to make it intuitive
- Show examples
- Mention common use cases
Adjust complexity based on the user's apparent level.""",

    "interview": """You are CodeBuddy Interview Coach — a senior FAANG interviewer.
Conduct technical interviews:
- Ask one focused question at a time
- After each answer: give a score (1-10), explain what was good/missing
- Provide the ideal answer if the user struggles
- Progress from easy to hard naturally
- Cover: Problem solving, code quality, edge cases, complexity analysis
Be encouraging but honest.""",

    "ml": """You are CodeBuddy ML Engineer — an expert in Machine Learning and AI.
Help with:
- ML/DL model architecture design
- Data preprocessing and feature engineering
- Training, validation, hyperparameter tuning
- Model evaluation and debugging
- Framework-specific code (PyTorch, TensorFlow, scikit-learn, etc.)
Always provide complete, runnable code examples.""",

    "dsa": """You are CodeBuddy DSA Master — a competitive programming expert.
For every DSA problem:
1. UNDERSTAND: Restate the problem clearly
2. APPROACH: Explain your strategy (brute force → optimal)
3. CODE: Write clean, commented solution
4. COMPLEXITY: Time and Space analysis
5. EDGE CASES: List and handle them
6. VARIATIONS: Mention similar problems
Use Python as default but can switch languages.""",

    "security": """You are CodeBuddy Security Auditor — a cybersecurity expert.
When reviewing code for security:
1. VULNERABILITIES: List all security issues found (SQLi, XSS, CSRF, etc.)
2. SEVERITY: Rate each (Critical/High/Medium/Low)
3. EXPLOIT: Explain how each could be exploited
4. FIX: Provide secure, patched code
5. BEST PRACTICES: Add security hardening tips
Only analyze code for defensive purposes.""",

    "roadmap": """You are CodeBuddy Roadmap Generator.
Generate a complete, structured learning roadmap:
- Organized by phases (Beginner → Intermediate → Advanced)
- Include specific topics, resources, and estimated time
- Suggest projects to build at each stage
- Add tips for job preparation
Format as a clear, actionable plan.""",

    "review": """You are CodeBuddy Code Reviewer — a senior engineer doing a thorough PR review.
Review code like a senior engineer:
1. OVERALL: Architecture and design assessment
2. QUALITY: Readability, maintainability, naming
3. BUGS: Any potential issues or bugs
4. PERFORMANCE: Efficiency concerns
5. SECURITY: Any security red flags
6. SUGGESTIONS: Specific improvements with code examples
Be constructive and professional.""",

    "ds": """You are CodeBuddy Data Science Expert.
Help with data science tasks:
- Data analysis and visualization
- Statistical concepts and tests
- Pandas, NumPy, Matplotlib, Seaborn
- Feature engineering and selection
- Model evaluation metrics
Provide complete code with explanations."""
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
        except Exception:
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
    # Verify ownership
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

# ================= CODE EXECUTION =================

SUPPORTED_LANGUAGES = {
    "python": {"cmd": ["python3", "{file}"], "ext": ".py"},
    "javascript": {"cmd": ["node", "{file}"], "ext": ".js"},
    "bash": {"cmd": ["bash", "{file}"], "ext": ".sh"},
}

@app.route("/run_code", methods=["POST"])
@login_required
@rate_limit(max_calls=30, window=60)
def run_code():
    code = request.json.get("code", "")
    language = request.json.get("language", "python").lower()

    if language not in SUPPORTED_LANGUAGES:
        # Fallback to Python
        language = "python"

    lang_config = SUPPORTED_LANGUAGES[language]
    ext = lang_config["ext"]

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext, mode="w") as temp:
        temp.write(code)
        temp_path = temp.name

    try:
        cmd = [c.replace("{file}", temp_path) for c in lang_config["cmd"]]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            cwd=tempfile.gettempdir()
        )
        output = result.stdout or result.stderr or "(No output)"
        bump_stat(current_user.id, "code_runs")
        return jsonify({
            "output": output[:5000],  # Limit output size
            "exit_code": result.returncode,
            "language": language
        })
    except subprocess.TimeoutExpired:
        return jsonify({"output": "⏱ Execution timed out (10s limit)", "exit_code": -1})
    except FileNotFoundError:
        return jsonify({"output": f"⚠ {language} runtime not available on server.", "exit_code": -1})
    except Exception as e:
        return jsonify({"output": f"Error: {str(e)}", "exit_code": -1})
    finally:
        try:
            os.unlink(temp_path)
        except:
            pass

# ================= COMPLEXITY ANALYZER =================

@app.route("/analyze_complexity", methods=["POST"])
@login_required
def analyze_complexity():
    """Quick AI-powered complexity analysis endpoint."""
    code = request.json.get("code", "")
    if not code.strip():
        return jsonify({"error": "No code provided"}), 400

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "meta-llama/llama-3-8b-instruct",
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
        # Clean JSON
        content = re.sub(r"```json|```", "", content).strip()
        data = json.loads(content)
        return jsonify(data)
    except:
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

# ================= MAIN CHAT =================

@app.route("/chat", methods=["POST"])
@login_required
@rate_limit(max_calls=50, window=60)
def chat():
    user_message = request.form.get("message", "").strip()
    conversation_id = request.form.get("conversation_id")
    mode = request.form.get("mode", "general")
    personality = request.form.get("personality", "mentor")
    confidence = request.form.get("confidence", 0)

    if not user_message:
        return Response("Please enter a message.", mimetype="text/plain")

    if not conversation_id:
        return Response("Select or create a chat first.", mimetype="text/plain")

    # Verify conversation ownership
    conn = sqlite3.connect("codebuddy.db")
    conn.row_factory = sqlite3.Row
    convo = conn.execute(
        "SELECT id, title FROM conversations WHERE id=? AND user_id=?",
        (conversation_id, current_user.id)
    ).fetchone()
    conn.close()

    if not convo:
        return Response("Chat not found.", mimetype="text/plain")

    # Apply programming filter (skip for interview/roadmap modes)
    if mode not in ("interview", "roadmap"):
        if not is_programming_related(user_message):
            return Response(
                "❌ CodeBuddy answers programming & tech questions only. "
                "Ask me about code, algorithms, debugging, or anything CS related!",
                mimetype="text/plain"
            )

    # Save user message
    conn = sqlite3.connect("codebuddy.db")
    cursor = conn.execute(
        "INSERT INTO messages(conversation_id,role,content,timestamp) VALUES (?,?,?,?)",
        (conversation_id, "user", user_message, datetime.now().isoformat())
    )
    msg_id = cursor.lastrowid

    # Auto-title: if this is the first message, generate smart title
    if convo["title"] in ("New Chat", "", None):
        try:
            smart_title = generate_chat_title(user_message)
            conn.execute(
                "UPDATE conversations SET title=?, mode=?, updated_at=? WHERE id=?",
                (smart_title, mode, datetime.now().isoformat(), conversation_id)
            )
        except:
            pass
    else:
        conn.execute(
            "UPDATE conversations SET updated_at=? WHERE id=?",
            (datetime.now().isoformat(), conversation_id)
        )

    conn.commit()
    conn.close()

    # Build system prompt
    tone = "strict technical interviewer" if personality == "strict" else "supportive technical mentor"

    if mode == "interview":
        topic = session.get(f"topic_{conversation_id}")
        if not topic:
            session[f"topic_{conversation_id}"] = user_message
            system_prompt = (
                f"You are CodeBuddy Interview Coach — a {tone}. "
                f"The user wants to practice: {user_message}. "
                "Ask exactly ONE clear technical interview question to start. "
                "After each answer, score it 1-10, explain what was missing, then ask the next question."
            )
        else:
            system_prompt = (
                f"You are CodeBuddy Interview Coach — a {tone}. "
                f"Interview topic: {topic}. User confidence level: {confidence}/10. "
                "Evaluate the previous answer strictly, give a score, feedback, ideal answer if needed, then ask next question."
            )
        bump_stat(current_user.id, "interview_count")
    else:
        system_prompt = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS["general"])
        if mode == "debug":
            bump_stat(current_user.id, "debug_count")
        elif mode == "optimize":
            bump_stat(current_user.id, "optimize_count")

    bump_stat(current_user.id, "total_messages")

    # Build full conversation history for context
    history = get_conversation_history(conversation_id, limit=16)
    # Remove the message we just inserted (it's already the last in history)
    # Build messages array: system + history
    api_messages = [{"role": "system", "content": system_prompt}]
    # Add history (includes the just-saved user message)
    api_messages.extend(history)

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://codebuddy.ai",
        "X-Title": "CodeBuddy AI"
    }

    payload = {
        "model": "meta-llama/llama-3.1-8b-instruct",  # Updated model
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
                timeout=60
            )

            if response.status_code != 200:
                yield f"⚠ API Error {response.status_code}. Please try again."
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
                            full += token
                            yield token
                        except:
                            pass

        except requests.exceptions.Timeout:
            yield "\n\n⏱ Request timed out. Please try again."
        except Exception as e:
            yield f"\n\n⚠ Error: {str(e)}"

        # Save assistant response
        if full:
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
    """Explain selected code snippet quickly."""
    code = request.json.get("code", "")
    level = request.json.get("level", "intermediate")  # beginner / intermediate / expert

    if not code.strip():
        return jsonify({"error": "No code provided"}), 400

    level_prompts = {
        "beginner": "Explain this code as if I'm completely new to programming. Use simple words and real-world analogies.",
        "intermediate": "Explain this code clearly, covering what it does, how it works, and any important patterns used.",
        "expert": "Give a technical deep-dive of this code: design patterns, potential issues, performance implications."
    }

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "meta-llama/llama-3.1-8b-instruct",
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
        "model": "meta-llama/llama-3.1-8b-instruct",
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
                    except:
                        pass

    return Response(stream_roadmap(), mimetype="text/plain")

# ================= RUN APP =================

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)