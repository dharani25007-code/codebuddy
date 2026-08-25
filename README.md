<div align="center">
<img src="https://capsule-render.vercel.app/api?type=waving&color=0:0f1117,50:7C3AED,100:4ecdc4&height=200&section=header&text=CodeBuddy%20AI&fontSize=52&fontColor=ffffff&fontAlignY=40&desc=Tanglish%20AI%20Coding%20Assistant&descAlignY=60&descSize=18&animation=fadeIn"/>
</div>

<div align="center">

![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0%2B-000000?style=for-the-badge&logo=flask&logoColor=white)
![Supabase](https://img.shields.io/badge/PostgreSQL-Supabase-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-Local%20Dev-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-Local%20AI-FF6F00?style=for-the-badge&logo=ollama&logoColor=white)
![Free AI Fallbacks](https://img.shields.io/badge/Free%20AI%20Fallbacks-Open%20Source%20%2B%20Free%20Tier-7C3AED?style=for-the-badge)
![Socket.IO](https://img.shields.io/badge/Socket.IO-4.0%2B-010101?style=for-the-badge&logo=socket.io&logoColor=white)
![Render](https://img.shields.io/badge/Deployed%20on-Render-46E3B7?style=for-the-badge&logo=render&logoColor=white)
![Piston](https://img.shields.io/badge/Piston-API-4ecdc4?style=for-the-badge)
![gTTS](https://img.shields.io/badge/gTTS-TTS-4ecdc4?style=for-the-badge)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-Welcome-brightgreen.svg?style=for-the-badge)](https://github.com/dharani25007-code/codebuddy/pulls)

> ⚡ **25+ Features · 5 Themes · 20+ Languages · Ollama Local AI + Free Cloud Fallbacks · Live on Render**

🌐 **[Live Demo → https://codebuddy-ai-nzea.onrender.com](https://codebuddy-ai-nzea.onrender.com)**

</div>

--- 

## 📌 Overview

CodeBuddy is a full-stack AI-powered programming assistant with **25+ features** — including Tanglish (Tamil + English) voice coding, File Forge upload/edit/run, Video Analyzer, Code DNA fingerprinting, Rubber Duck+ Mode, and a **triple-provider AI architecture** (Ollama local GPU → Groq → OpenRouter). The app is deployed live on **Render** with a **Supabase PostgreSQL** database for permanent cloud storage, and also supports SQLite for local development with zero configuration.

---

## ✨ Core Features

| Feature | Description |
|---|---|
| 🧠 **8 AI Modes** | General, Debug, Optimize, Explain, Interview, ML, DSA, Roadmap |
| 🌍 **20+ Languages** | 9 Indian languages + French, German, Spanish, Japanese, Chinese & more |
| 🗣️ **Tanglish AI** |  Tamil+English mixed language coding assistant |
| 🔁 **Streaming** | Token-by-token with free-tier and local fallbacks |
| ▶️ **Code Execution** | AI execution simulator (predicts outputs of all 50+ languages with zero local setup) + local compiler fallbacks |
| 🧬 **Code DNA** | Builds your personal coding style — AI silently matches it |
| 📁 **File Forge** | Upload, edit, run, and AI-refactor code files in the browser |
| 🎬 **Video Analyzer** | Upload videos or analyze coding/tutorial links from the UI |
| 🦆 **Rubber Duck+** | AI refuses to give answers, only asks Socratic questions |
| 🎭 **Mood Engine** | Detects frustration and adapts AI tone in real-time |
| 🔮 **Bug Prophecy** | Predicts which lines will break based on your past bug history |
| 🕰️ **Thought Replay** | Watch AI debug step-by-step as a live timeline |
| 🎤 **Voice-to-Voice** | Speak your bug → hear the fix spoken back (XTTS-v2 / gTTS) |
| ⚔️ **Live Code Battle** | 1v1 real-time coding challenges, AI-judged |
| 📓 **Personal Changelog** | Auto-generated daily learning diary from your sessions |
| 🏆 **Karma + Leaderboard** | Earn points, unlock ranks NOVICE → GODMODE |
| 👥 **Real-time Collab** | Multi-user rooms with SocketIO + WebRTC voice |
| 🔬 **Error Autopsy** | Probabilistic root-cause ranking + diagnosis tree |
| 🏷️ **Pair Naming Assistant** | Name quality scoring + reverse name-to-body check |
| 🎯 **Focus Zone Detector** | Peak window analytics from your session timestamps |
| 📱 **PWA Support** | Installable Progressive Web App with offline assets caching and startup icon generator |
| 🔑 **Secure Recovery** | Self-service timed token-based password reset/recovery flow powered by SMTP mailers

---

## 🗂️ Project Structure

```
codebuddy/
├── app.py                          # Main Flask backend (being decomposed — routes + orchestration)
├── appcore/                        # Layered helpers extracted from the historical monolith
│   ├── __init__.py
│   └── db.py                       # SQLite ↔ PostgreSQL connection layer (patches sqlite3.connect)
├── Procfile                        # Render/Heroku startup command
├── .env                            # API keys (local dev only, not committed)
├── codebuddy.db                    # SQLite database (auto-created for local dev)
├── requirements.txt
├── gunicorn.conf.py                # Production Gunicorn defaults
├── static/
│   ├── css/
│   │   ├── theme-system.css        # Shared theme variables for non-index pages
│   │   ├── auth-theme-switcher.css # Auth-page theme selector styling
│   │   └── cursor.css              # Shared custom cursor styling
│   └── js/
│       ├── theme-system.js         # Shared 5-theme initializer
│       ├── auth-theme-switcher.js  # Login/register theme picker
│       └── cursor.js               # Shared custom cursor controller
├── templates/
│   ├── index.html                  # Main dashboard + chat interface (with PWA manifest link)
│   ├── login.html / register.html
│   ├── forgot_password.html        # New: Request password recovery token UI
│   ├── reset_password.html         # New: Reset password with timed token UI
│   ├── profile.html
│   ├── leaderboard.html
│   ├── collab.html
│   └── codebuddy_world_first.html  # Features Hub
├── scripts/
│   └── load_benchmark.py           # Concurrent endpoint benchmark harness
├── scratch/
│   └── generate_pwa_icons.py       # New: Generates high-quality PWA icons (192px/512px) using PIL
└── coqui_profiles/                 # Voice clone samples (auto-created)
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10 or newer
- Pip (bundled with modern Python) and a virtual environment (recommended)
- No paid API keys are required for the default free-only mode
- **[Ollama](https://ollama.com)** (optional, recommended) — run AI locally on your GPU, zero cost, unlimited
- Optional free-tier API keys for higher-quality cloud replies: OpenRouter and/or Groq

### Install
```bash
git clone https://github.com/dharani25007-code/codebuddy.git
cd codebuddy
pip install -r requirements.txt
```

### Configure (Local Development)
Create a `.env` file in the project root:
```env
SECRET_KEY=any-long-random-string
FREE_ONLY_MODE=false
OPENROUTER_API_KEY=your-openrouter-key
GROQ_API_KEY=your-groq-key
# Leave DATABASE_URL commented out for local SQLite development
# DATABASE_URL=postgresql://...

# Ollama Local AI (optional — auto-detected at localhost:11434)
OLLAMA_ENABLED=true
OLLAMA_MODEL=qwen2.5-coder:7b
# OLLAMA_URL=http://localhost:11434

# Alphanumeric code accepted for account-deletion OTP ONLY when SMTP is
# unreachable in local dev. LEAVE UNSET in production — when unset there is no
# bypass at all and the recovery path is the generated code in the server logs.
# OTP_FALLBACK_CODE=some-secret-dev-only-code

# SMTP Config for Password Recovery (optional, logs fallback if omitted)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_SENDER=your-email@gmail.com
```

The app runs without any AI keys in free-only mode. Add optional free-tier keys only if you want better hosted responses. If SMTP configuration is omitted, generated recovery links are safely output to the server logs.

### Run Locally

**With Ollama (recommended — free, fastest, unlimited):**
```bash
# Terminal 1: Start Ollama (if not running as service)
ollama serve

# Terminal 2: Pull models (one-time)
ollama pull qwen2.5-coder:7b
ollama pull llama3.2:3b

# Terminal 3: Start CodeBuddy
python app.py
```

**Without Ollama (uses cloud APIs):**
```bash
python app.py
```

Open: `http://127.0.0.1:5000` → Register → New Chat → Pick a mode 🚀

> **Note:** Running locally uses **SQLite** by default (fast, no configuration needed). The cloud deployment uses PostgreSQL. If Ollama is running, all AI queries hit your local GPU (₹0 cost). If not, the app falls back to Groq/OpenRouter cloud APIs automatically.

---

## ☁️ Free Cloud Deployment (Render + Supabase)

CodeBuddy is deployed 100% free using:
- **[Render.com](https://render.com)** — Free web hosting (no credit card required)
- **[Supabase.com](https://supabase.com)** — Free PostgreSQL cloud database (no credit card required)

### Deploy Your Own Instance

1. **Fork** this repository to your GitHub account.
2. **Create a free Supabase project** at [supabase.com](https://supabase.com) and copy your PostgreSQL connection string (`DATABASE_URL`).
3. **Create a new Web Service** on [render.com](https://render.com) and connect your GitHub repo.
4. **Set the following Environment Variables** in the Render dashboard:

| Key | Value |
|---|---|
| `SECRET_KEY` | Any long random string |
| `DATABASE_URL` | Your Supabase `postgresql://...` connection string |
| `OPENROUTER_API_KEY` | Your OpenRouter free API key |
| `GROQ_API_KEY` | Your Groq free API key |
| `FREE_ONLY_MODE` | `false` |
| `COOKIE_SECURE` | `true` |
| `BREVO_API_KEY` | *(Optional)* Brevo API key for transactional emails |
| `GOOGLE_CLIENT_ID` | *(Optional)* Google OAuth Client ID |
| `GOOGLE_CLIENT_SECRET` | *(Optional)* Google OAuth Client Secret |
| `SMTP_SERVER` | *(Optional)* SMTP server address (e.g., `smtp.gmail.com`) |
| `SMTP_PORT` | *(Optional)* SMTP server port (e.g., `587`) |
| `SMTP_USERNAME` | *(Optional)* SMTP auth username/email |
| `SMTP_PASSWORD` | *(Optional)* SMTP app password |
| `SMTP_SENDER` | *(Optional)* Mail sender email header address |

5. Click **Deploy** — Render will automatically build, run database migrations, and launch your app!

### How it works
The app uses a smart **database compatibility layer** in `appcore/db.py`:
- **Locally** (no `DATABASE_URL` set): Uses fast local SQLite (`codebuddy.db`).
- **On Render / Cloud** (`DATABASE_URL` set): Automatically connects to Supabase PostgreSQL via connection pooling (`psycopg2`). All queries (`?` params, `AUTOINCREMENT`, `PRAGMA table_info`, `datetime('now')`) are transparently translated to PostgreSQL on the fly.

---

## 🤖 AI Provider Architecture (Triple Redundancy)

```
User Query
    │
    ▼
┌─────────────────────────────────────────────────┐
│  Priority 1: OLLAMA (Local GPU)                 │  ← FREE, fastest, unlimited
│  Priority 2: GROQ (Cloud - Ultra Fast)          │  ← Free tier, 30 req/min
│  Priority 3: OPENROUTER (Cloud - Fallback Chain)│  ← Free fallback chain
└─────────────────────────────────────────────────┘
```

| Priority | Provider | Models | Cost | Speed |
|---|---|---|---|---|
| 🥇 **1st** | **Ollama** (local) | `qwen2.5-coder:7b` (coding) & `llama3.2:3b` (fast tasks) | **₹0 forever** | ~50ms |
| 🥈 **2nd** | **Groq** (cloud) | `llama-3.1-8b` / `llama-3.3-70b` | Free tier | ~200ms |
| 🥉 **3rd** | **OpenRouter** (cloud) | `nemotron-70b:free` → `llama-3.3-70b:free` → `qwen3-coder:free` → `gemma-3-4b:free` → `openrouter/free` | Free tier | ~500ms |
| 🔧 **4th** | **Local heuristics** | Built-in pattern matching | ₹0 | Instant |

If any provider fails (offline/rate-limited/error) → the next provider is tried automatically. Zero downtime.

---

## 🌍 Languages Supported

**Indian (native script + TTS):** Tamil · Tanglish · Hindi · Telugu · Kannada · Malayalam · Bengali · Marathi · Gujarati · Punjabi

**World:** French · German · Spanish · Japanese · Chinese · Korean · Arabic · Russian · Portuguese · Italian

---

## 🧰 Tech Stack

| Library | Role |
|---|---|
| Flask 3.0+ | Web framework |
| Flask-Login | Authentication management |
| Flask-Bcrypt | Password hashing |
| Flask-SocketIO | Real-time WebSocket collaboration |
| PostgreSQL (Supabase) / SQLite | Cloud database / Local database |
| psycopg2-binary | PostgreSQL driver |
| Ollama | Local GPU AI — zero cost, unlimited, offline capable |
| OpenRouter / Groq | Cloud AI fallback chain (free tier) |
| AI Output Simulator | Predicts and simulates run outputs of 50+ languages via Ollama/Groq/OpenRouter + local compiler fallbacks |
| gTTS / XTTS-v2 | Text-to-speech and voice cloning |
| Gunicorn | Production WSGI server |
| python-dotenv | Load `.env` configuration |
| requests | HTTP requests to external APIs |

---

## 🔒 Security

- Bcrypt password hashing · 30-day sessions · SameSite cookies
- `COOKIE_SECURE=true` enforced in production (HTTPS only)
- Rate limiting: 50 req/min chat · 30 req/min code execution
- 192-bit random share tokens — no ID enumeration
- SQL stat fields use a whitelist — zero raw input in queries
- Security headers: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`

---

### Load Benchmark
Run the built-in concurrent benchmark against the chat and code-run endpoints:

```bash
python scripts/load_benchmark.py --concurrency 6 --chat-requests 6 --code-requests 6
```

To hit the live server:

```bash
python scripts/load_benchmark.py --mode live --base-url https://codebuddy-0slh.onrender.com --concurrency 8 --chat-requests 12 --code-requests 12 --no-stub-upstreams
```

### Automated Tests
```bash
python -m unittest discover -s tests -p "test_*.py"
```

---
<div align="center">
<img src="https://capsule-render.vercel.app/api?type=waving&color=0:4ecdc4,100:0f1117&height=120&section=footer"/>

**Built by [Dharanidharan M](https://github.com/dharani25007-code)**
</div>
