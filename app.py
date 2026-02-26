import os
import json
import sqlite3
import tempfile
import subprocess
from datetime import datetime

import requests
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, Response, redirect, url_for, session
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin, current_user
from flask_bcrypt import Bcrypt

# ================= INIT =================

load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

app = Flask(__name__)
app.secret_key = "supersecretkey"

bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

# ================= DATABASE =================

def get_db():
    conn = sqlite3.connect("codebuddy.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS conversations(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT,
        is_public INTEGER DEFAULT 0,
        created_at TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS messages(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id INTEGER,
        role TEXT,
        content TEXT,
        timestamp TEXT
    )""")

    conn.commit()
    conn.close()

init_db()

# ================= USER =================

class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    if user:
        return User(user["id"], user["username"])
    return None

# ================= AUTH =================

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = bcrypt.generate_password_hash(request.form["password"]).decode()

        conn = get_db()
        try:
            conn.execute("INSERT INTO users(username,password) VALUES (?,?)",
                         (username,password))
            conn.commit()
        except:
            conn.close()
            return "Username exists"
        conn.close()
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username=?",
                            (username,)).fetchone()
        conn.close()

        if user and bcrypt.check_password_hash(user["password"], password):
            login_user(User(user["id"], user["username"]))
            return redirect(url_for("dashboard"))

        return "Invalid credentials"

    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/profile")
@login_required
def profile():
    return render_template("profile.html", username=current_user.username)

# ================= DASHBOARD =================

@app.route("/")
@login_required
def dashboard():
    conn = get_db()
    chats = conn.execute(
        "SELECT id,title FROM conversations WHERE user_id=? ORDER BY id DESC",
        (current_user.id,)
    ).fetchall()
    conn.close()
    return render_template("index.html", chats=chats, username=current_user.username)

# ================= CHAT MANAGEMENT =================

@app.route("/new_chat", methods=["POST"])
@login_required
def new_chat():
    conn = get_db()
    conn.execute(
        "INSERT INTO conversations(user_id,title,created_at) VALUES (?,?,?)",
        (current_user.id,"New Chat",datetime.now())
    )
    conn.commit()
    conn.close()
    return jsonify({"status":"created"})

@app.route("/load_messages/<int:chat_id>")
@login_required
def load_messages(chat_id):
    conn = get_db()
    messages = conn.execute(
        "SELECT role,content FROM messages WHERE conversation_id=? ORDER BY id ASC",
        (chat_id,)
    ).fetchall()
    conn.close()
    return jsonify({"messages":[[m["role"],m["content"]] for m in messages]})

@app.route("/rename_chat", methods=["POST"])
@login_required
def rename_chat():
    data = request.json
    conn = get_db()
    conn.execute(
        "UPDATE conversations SET title=? WHERE id=? AND user_id=?",
        (data["title"], data["chat_id"], current_user.id)
    )
    conn.commit()
    conn.close()
    return jsonify({"status":"renamed"})

@app.route("/delete_chat", methods=["POST"])
@login_required
def delete_chat():
    data = request.json
    conn = get_db()
    conn.execute("DELETE FROM messages WHERE conversation_id=?",
                 (data["chat_id"],))
    conn.execute("DELETE FROM conversations WHERE id=? AND user_id=?",
                 (data["chat_id"], current_user.id))
    conn.commit()
    conn.close()
    return jsonify({"status":"deleted"})

@app.route("/share_chat", methods=["POST"])
@login_required
def share_chat():
    data = request.json
    conn = get_db()
    conn.execute(
        "UPDATE conversations SET is_public=1 WHERE id=? AND user_id=?",
        (data["chat_id"], current_user.id)
    )
    conn.commit()
    conn.close()
    return jsonify({"share_url": f"/public_chat/{data['chat_id']}"})

# ================= CODE RUN =================

@app.route("/run_code", methods=["POST"])
@login_required
def run_code():
    code = request.json.get("code","")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as temp:
        temp.write(code.encode())
        temp_path = temp.name

    try:
        result = subprocess.run(
            ["python", temp_path],
            capture_output=True,
            text=True,
            timeout=5
        )
        return jsonify({"output": result.stdout or result.stderr})
    except Exception as e:
        return jsonify({"output": str(e)})

# ================= CHAT =================

@app.route("/chat", methods=["POST"])
@login_required
def chat():

    user_message = request.form.get("message","")
    conversation_id = request.form.get("conversation_id")
    mode = request.form.get("mode","general")

    if not conversation_id:
        return Response("Select chat first.")

    conn = get_db()
    conn.execute(
        "INSERT INTO messages(conversation_id,role,content,timestamp) VALUES (?,?,?,?)",
        (conversation_id,"user",user_message,datetime.now())
    )
    conn.commit()

    if mode == "interview":
        topic = session.get("topic")

        if not topic:
            session["topic"] = user_message
            system_prompt = f"Start a strict interview on {user_message}. Ask one question only."
        else:
            system_prompt = f"Continue strict interview on {topic}. Evaluate answer strictly."

    elif mode == "debug":
        system_prompt = "You are a debugging expert. Identify bug and fix it."

    elif mode == "optimize":
        system_prompt = "You are an optimization expert. Improve performance."

    elif mode == "ml":
        system_prompt = "You are an ML architect. Design ML pipeline."

    elif mode == "ds":
        system_prompt = "You are a data science expert."

    else:
        system_prompt = "You are a professional programming assistant."

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model":"meta-llama/llama-3-8b-instruct",
        "stream":True,
        "messages":[
            {"role":"system","content":system_prompt},
            {"role":"user","content":user_message}
        ]
    }

    def generate():
        full=""
        response=requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            stream=True
        )

        for line in response.iter_lines():
            if line:
                decoded=line.decode("utf-8")
                if decoded.startswith("data: "):
                    data=decoded.replace("data: ","")
                    if data=="[DONE]":
                        break
                    try:
                        token=json.loads(data)["choices"][0]["delta"].get("content","")
                        full+=token
                        yield token
                    except:
                        pass

        conn.execute(
            "INSERT INTO messages(conversation_id,role,content,timestamp) VALUES (?,?,?,?)",
            (conversation_id,"assistant",full,datetime.now())
        )
        conn.commit()
        conn.close()

    return Response(generate(), mimetype="text/plain")

if __name__ == "__main__":
    app.run(debug=True)