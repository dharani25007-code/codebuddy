<div align="center">
<img src="https://capsule-render.vercel.app/api?type=waving&color=0:0f1117,50:7C3AED,100:4ecdc4&height=200&section=header&text=CodeBuddy%20AI&fontSize=52&fontColor=ffffff&fontAlignY=40&desc=World's%20First%20Tanglish%20AI%20Coding%20Assistant&descAlignY=60&descSize=18&animation=fadeIn"/>
</div>

<div align="center">

![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-2.0%2B-000000?style=for-the-badge&logo=flask&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-3%2B-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![Free AI Fallbacks](https://img.shields.io/badge/Free%20AI%20Fallbacks-Open%20Source%20%2B%20Free%20Tier-7C3AED?style=for-the-badge)
![Socket.IO](https://img.shields.io/badge/Socket.IO-4.0%2B-010101?style=for-the-badge&logo=socket.io&logoColor=white)
![Piston](https://img.shields.io/badge/Piston-API-4ecdc4?style=for-the-badge)
![gTTS](https://img.shields.io/badge/gTTS-TTS-4ecdc4?style=for-the-badge)
![Eventlet](https://img.shields.io/badge/Eventlet--Gevent-8A2BE2?style=for-the-badge)

> ⚡ **28 New Features · 5 Themes · 20+ Languages · Free-first AI stack**

</div>

---

## 📌 Overview

CodeBuddy is a full-stack AI-powered programming assistant with **28 New features** — including Tanglish (Tamil + English) voice coding, File Forge upload/edit/run, Video Analyzer, Code DNA fingerprinting, Rubber Duck+ Mode, and a free-first AI fallback chain. The app now uses a 5-theme system across the UI and supports larger file uploads for File Forge and media analysis.

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

---

## 🗂️ Project Structure

```
codebuddy/
├── app.py                          # Main Flask backend (~3500 lines)
├── .env                            # API keys (create this)
├── codebuddy.db                    # SQLite database (auto-created)
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
├── static/js/
│   └── codebuddy_voice.js
└── coqui_profiles/                 # Voice clone samples (auto-created)
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10 or newer
- Pip (bundled with modern Python) and a virtual environment (recommended)
- No paid API keys are required for the default free-only mode
- Optional free-tier API keys if you want higher-quality hosted replies later: OpenRouter and/or Groq
- Optional: a self-hosted Piston instance for code execution if you want to avoid public endpoints entirely
- Recommended system packages: `sqlite3` (usually bundled), `ffmpeg` (for voice/video features)

### Install
```bash
git clone https://github.com/dharani25007-code/codebuddy.git
cd codebuddy
pip install -r requirements.txt
```

### Configure
```bash
# Create .env file
SECRET_KEY=any-long-random-string
CODEBUDDY_DB_PATH=codebuddy.db

```

The app runs without any AI keys in free-only mode. Add optional free-tier keys only if you want better hosted responses.

### Run
```bash
python app.py
```
Open: `http://127.0.0.1:5000` → Register → New Chat → Pick a mode 🚀

### Production Deployment
For a production stack, run the app behind Gunicorn and Nginx. Redis is optional and only needed if you want Socket.IO fan-out across multiple workers:

```bash
pip install -r requirements.txt
set SECRET_KEY=your-long-random-secret
gunicorn -c gunicorn.conf.py app:app
```

Minimal Nginx reverse proxy example:

```nginx
server {
	listen 80;
	server_name codebuddy.example.com;

	location / {
		proxy_pass http://127.0.0.1:8000;
		proxy_http_version 1.1;
		proxy_set_header Host $host;
		proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
		proxy_set_header X-Forwarded-Proto $scheme;
		proxy_set_header Upgrade $http_upgrade;
		proxy_set_header Connection "upgrade";
	}
}
```

The current data layer still uses SQLite. If you want PostgreSQL in production, migrate the `sqlite3` access layer first, then point the app at the new database backend

### Load Benchmark
Run the built-in concurrent benchmark against the chat and code-run endpoints:

```bash
python scripts/load_benchmark.py --concurrency 6 --chat-requests 6 --code-requests 6
```

To hit a live server instead of the in-process test client:

```bash
python scripts/load_benchmark.py --mode live --base-url http://127.0.0.1:5000 --concurrency 8 --chat-requests 12 --code-requests 12 --no-stub-upstreams
```

The benchmark prints p50/p95 latency, max latency, and status counts per endpoint.

### Automated Tests
Run the smoke tests locally with the standard library test runner:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

### Upload Notes
- File Forge accepts larger files than before; the browser-side limit is 2 MB and the Flask server accepts up to 32 MB.
- If you see a "File too large" message, try a smaller file or increase the limit in `templates/index.html` and `app.py` together.
- The SQLite database path is configurable through `CODEBUDDY_DB_PATH` in `.env`.

---

## 🤖 AI Fallback Chain (Free-First)

| Role | Model |
|---|---|
| Code tasks | `deepseek/deepseek-chat-v3-0324:free` |
| Fast / multilingual | `meta-llama/llama-3.3-70b-instruct:free` |
| Classification | `google/gemma-3-4b-it:free` |
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
| Flask | Web framework |
| Flask-Login | Authentication management |
| Flask-Bcrypt | Password hashing |
| Flask-SocketIO | Real-time WebSocket collaboration |
| Eventlet / Gevent | Async workers for SocketIO in production |
| SQLite (WAL) | Local relational database (configurable path) |
| OpenRouter / Groq | Free-tier AI fallback chain |
| Piston API | Sandboxed code execution (50+ languages, free endpoints) |
| gTTS / XTTS-v2 | Text-to-speech and voice cloning |
| python-dotenv | Load `.env` configuration |
| requests | HTTP requests to external APIs |
| ffmpeg | Media processing for voice/video features (external binary) |

---

## 🔒 Security

- Bcrypt password hashing · 30-day sessions · SameSite cookies
- Rate limiting: 50 req/min chat · 30 req/min code execution
- 192-bit random share tokens — no ID enumeration
- SQL stat fields use a whitelist — zero raw input in queries

---


<div align="center">
<img src="https://capsule-render.vercel.app/api?type=waving&color=0:4ecdc4,100:0f1117&height=120&section=footer"/>

**Built by [Dharanidharan M](https://github.com/dharani25007-code) 
</div>


