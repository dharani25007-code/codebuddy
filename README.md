<div align="center">
<img src="https://capsule-render.vercel.app/api?type=waving&color=0:0f1117,50:7C3AED,100:4ecdc4&height=200&section=header&text=CodeBuddy%20AI&fontSize=52&fontColor=ffffff&fontAlignY=40&desc=World's%20First%20Tanglish%20AI%20Coding%20Assistant&descAlignY=60&descSize=18&animation=fadeIn"/>
</div>

<div align="center">

![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0%2B-000000?style=for-the-badge&logo=flask&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-Local%20Dev-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![Free AI Fallbacks](https://img.shields.io/badge/Free%20AI%20Fallbacks-Open%20Source%20%2B%20Free%20Tier-7C3AED?style=for-the-badge)
![Socket.IO](https://img.shields.io/badge/Socket.IO-4.0%2B-010101?style=for-the-badge&logo=socket.io&logoColor=white)
![Render](https://img.shields.io/badge/Deployed%20on-Render-46E3B7?style=for-the-badge&logo=render&logoColor=white)
![Piston](https://img.shields.io/badge/Piston-API-4ecdc4?style=for-the-badge)
![gTTS](https://img.shields.io/badge/gTTS-TTS-4ecdc4?style=for-the-badge)

> ⚡ **28 World-First Features · 5 Themes · 20+ Languages · Free-first AI stack · Live on Render**

🌐 **[Live Demo → https://codebuddy-0slh.onrender.com](https://codebuddy-0slh.onrender.com)**

</div>

---

## 📌 Overview

CodeBuddy is a full-stack AI-powered programming assistant with **28 world-first features** — including Tanglish (Tamil + English) voice coding, File Forge upload/edit/run, Video Analyzer, Code DNA fingerprinting, Rubber Duck+ Mode, and a free-first AI fallback chain. The app is deployed live on **Render** with a **Neon PostgreSQL** database for permanent, free cloud storage, and also supports SQLite for local development with zero configuration.

---

## ✨ Core Features

| Feature | Description |
|---|---|
| 🧠 **8 AI Modes** | General, Debug, Optimize, Explain, Interview, ML, DSA, Roadmap |
| 🌍 **20+ Languages** | 9 Indian languages + French, German, Spanish, Japanese, Chinese & more |
| 🗣️ **Tanglish AI** |  Tamil+English mixed language coding assistant |
| 🔁 **Streaming** | Token-by-token with free-tier and local fallbacks |
| ▶️ **Code Execution** | Run 50+ languages via sandboxed free Piston endpoints |
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

---

## 🗂️ Project Structure

```
codebuddy/
├── app.py                          # Main Flask backend (~8000 lines)
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
│   ├── index.html                  # Main dashboard + chat interface
│   ├── login.html / register.html
│   ├── profile.html
│   ├── leaderboard.html
│   ├── collab.html
│   └── codebuddy_world_first.html  # 28 Features Hub
├── scripts/
│   └── load_benchmark.py           # Concurrent endpoint benchmark harness
└── coqui_profiles/                 # Voice clone samples (auto-created)
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10 or newer
- Pip (bundled with modern Python) and a virtual environment (recommended)
- No paid API keys are required for the default free-only mode
- Optional free-tier API keys for higher-quality hosted replies: OpenRouter and/or Groq

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
```

The app runs without any AI keys in free-only mode. Add optional free-tier keys only if you want better hosted responses.

### Run Locally
```bash
python app.py
```
Open: `http://127.0.0.1:5000` → Register → New Chat → Pick a mode 🚀

> **Note:** Running locally uses **SQLite** by default (fast, no configuration needed). The cloud deployment uses PostgreSQL.

---

## ☁️ Free Cloud Deployment (Render + Neon)

CodeBuddy is deployed 100% free using:
- **[Render.com](https://render.com)** — Free web hosting (no credit card required)
- **[Neon.tech](https://neon.tech)** — Free PostgreSQL cloud database (no credit card required)

### Deploy Your Own Instance

1. **Fork** this repository to your GitHub account.
2. **Create a free Neon database** at [neon.tech](https://neon.tech) and copy the connection string.
3. **Create a new Web Service** on [render.com](https://render.com) and connect your GitHub repo.
4. **Set the following Environment Variables** in the Render dashboard:

| Key | Value |
|---|---|
| `SECRET_KEY` | Any long random string |
| `DATABASE_URL` | Your Neon `postgresql://...` connection string |
| `OPENROUTER_API_KEY` | Your OpenRouter free API key |
| `GROQ_API_KEY` | Your Groq free API key |
| `FREE_ONLY_MODE` | `false` |
| `COOKIE_SECURE` | `true` |

5. Click **Deploy** — Render will automatically build and launch your app!

### How it works
The app uses a smart **database compatibility wrapper** built into `app.py`:
- **Locally** (no `DATABASE_URL` set): Uses fast local SQLite.
- **On Render** (`DATABASE_URL` set): Automatically connects to Neon PostgreSQL. All SQLite-specific syntax (`?` params, `AUTOINCREMENT`, `PRAGMA`, `datetime('now')`, `ON CONFLICT`) is transparently translated to PostgreSQL on the fly — zero code duplication.

---

## 🤖 AI Fallback Chain (Free-First)

| Role | Model |
|---|---|
| Code tasks | `deepseek/deepseek-chat-v3-0324:free` |
| Fast / multilingual | `meta-llama/llama-3.3-70b-instruct:free` |
| Classification | `nvidia/llama-3.1-nemotron-70b-instruct:free` |
| Last resort | local heuristics / graceful fallback |

If any model returns 429/404/503 → next free model is tried automatically, then the app falls back to local heuristics where possible.

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
| PostgreSQL / SQLite | Cloud database (Neon) / Local database |
| psycopg2-binary | PostgreSQL driver |
| OpenRouter / Groq | Free-tier AI fallback chain |
| Piston API | Sandboxed code execution (50+ languages, free endpoints) |
| gTTS / XTTS-v2 | Text-to-speech and voice cloning |
| Gunicorn (gthread) | Production WSGI server |
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
