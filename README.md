# ⚡ CodeBuddy AI

> The world's first Tanglish AI coding assistant — 28 world-first features, 20+ languages, 100% free AI models. Built with Flask, SQLite, OpenRouter, and SocketIO.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-Web%20Framework-black?logo=flask&logoColor=white)
![OpenRouter](https://img.shields.io/badge/OpenRouter-14%20Free%20Models-purple)
![SQLite](https://img.shields.io/badge/Database-SQLite%20WAL-lightgrey?logo=sqlite)
![SocketIO](https://img.shields.io/badge/Realtime-SocketIO-010101?logo=socket.io)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 📌 Overview

CodeBuddy is a full-stack AI-powered programming assistant with **28 features unavailable in any other tool** — including Tanglish (Tamil + English) voice coding, Code DNA fingerprinting, Rubber Duck+ Mode, and a 14-model AI fallback chain. Everything runs 100% free using OpenRouter's free-tier models.

> Built with ⚡ in Coimbatore, India · v9.0 · March 2026

---

## ✨ Core Features

- 🧠 **8 AI Modes** — General, Debug, Optimize, Explain, Interview, ML, DSA, Roadmap
- 🌍 **20+ Languages** — 9 Indian languages including Tamil, Hindi, Telugu, Kannada, Malayalam + world languages
- 🗣️ **Tanglish AI** — world's first Tamil+English mixed language coding assistant
- 🔁 **Streaming Responses** — token-by-token with 14-model fallback chain
- ▶️ **Code Execution** — run 50+ languages via sandboxed Piston API
- 🧬 **Code DNA** — builds your personal coding style profile; AI silently matches it
- 🦆 **Rubber Duck+ Mode** — AI refuses to give answers, only asks Socratic questions
- 🎭 **Mood Engine** — detects frustration/confusion and adapts AI tone in real-time
- 🔮 **Bug Prophecy** — predicts which lines will break based on your past bug history
- 🕰️ **Thought Replay** — watch AI debug step-by-step as a live timeline
- 🎤 **Voice-to-Voice Loop** — speak your bug, hear the fix spoken back (XTTS-v2 / gTTS)
- ⚔️ **Live Code Battle** — 1v1 real-time coding challenges, AI-judged
- 🧪 **Confidence Calibrator** — rate your knowledge, take a quiz, see the gap
- 📓 **Personal Changelog** — auto-generated daily learning diary from your sessions
- 🔒 **Blind Code Review** — anonymous peer review system
- 🏆 **Karma + Leaderboard** — earn points, unlock ranks from NOVICE → GODMODE
- 👥 **Real-time Collaboration** — multi-user rooms with SocketIO + WebRTC voice

---

## 🗂️ Project Structure

```
codebuddy/
│
├── app.py                          # Main Flask backend (~3500 lines)
├── .env                            # API keys (create this)
├── codebuddy.db                    # SQLite database (auto-created)
├── requirements.txt                # Python dependencies
│
├── templates/
│   ├── index.html                  # Main dashboard + chat interface
│   ├── login.html / register.html  # Auth pages
│   ├── profile.html                # User profile + stats
│   ├── leaderboard.html            # Global streak/karma leaderboard
│   ├── collab.html                 # Real-time collaboration room
│   ├── public_chat.html            # Shared chat viewer
│   └── codebuddy_world_first.html  # 28 Features Hub UI
│
├── static/js/
│   └── codebuddy_voice.js          # Voice recording + TTS frontend
│
└── coqui_profiles/                 # Voice clone audio samples (auto-created)
```

---

## 🚀 Getting Started

### Prerequisites

- Python **3.10+**
- A free API key from [openrouter.ai/keys](https://openrouter.ai/keys)

### Installation

```bash
git clone https://github.com/dharani25007-code/codebuddy.git
cd codebuddy
pip install -r requirements.txt
```

### Configuration

Create a `.env` file:
```
OPENROUTER_API_KEY=sk-or-v1-your-key-here
SECRET_KEY=any-long-random-string
```

### Run

```bash
python app.py
```

Open: `http://127.0.0.1:5000` → Register → New Chat → Pick a mode.

### Optional: Voice Cloning

```bash
pip install TTS torch
sudo apt install ffmpeg   # Linux
brew install ffmpeg       # macOS
```

Falls back to gTTS automatically if not installed.

---

## 🧰 Tech Stack

| Library | Role |
|---|---|
| Flask | Web framework — routing, sessions, streaming |
| Flask-Login | User session management |
| Flask-Bcrypt | Password hashing (bcrypt) |
| Flask-SocketIO | WebSocket server for real-time collab |
| SQLite (WAL) | Primary data store — all user data |
| OpenRouter API | Gateway to 14+ free AI models with fallback |
| gTTS | Google Text-to-Speech — 20+ languages |
| XTTS-v2 (Coqui) | Real voice cloning (optional) |
| Piston API | Sandboxed code execution — 50+ languages |
| Redis | Rate limiting store (falls back to in-memory) |

---

## 🤖 AI Models & Fallback Chain

CodeBuddy uses **only free models** from OpenRouter — zero API cost. A 14-model fallback chain ensures availability when individual models are rate-limited.

| Role | Model |
|---|---|
| Code tasks (primary) | `deepseek/deepseek-chat-v3-0324:free` |
| Fast / multilingual | `meta-llama/llama-4-scout:free` |
| Classification | `google/gemma-3-4b-it:free` |
| Last resort | `openrouter/auto` |

If a model returns 429/404/503, the next model is tried automatically with a 1.5s delay.

---

## 🌍 Languages Supported

**Indian Languages** (native script + TTS): Tamil, Tanglish, Hindi, Telugu, Kannada, Malayalam, Bengali, Marathi, Gujarati, Punjabi

**World Languages**: French, German, Spanish, Japanese, Chinese, Korean, Arabic, Russian, Portuguese, Italian

---

## 🔒 Security

- Passwords hashed with **bcrypt**
- 30-day persistent sessions with optional 7-day remember-me cookie
- Rate limiting: 50 req/min (chat), 30 req/min (code execution)
- Share links use 192-bit random tokens — no ID enumeration
- SQL stat fields use a whitelist — no raw user input ever used in queries

---

## 🚀 Production Deployment

```bash
pip install gunicorn
gunicorn -w 1 -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker \
  -b 0.0.0.0:8000 app:app
```

> Use 1 worker only — SQLite does not handle multiple writer processes.  
> Set `COOKIE_SECURE=true` in `.env` when serving over HTTPS.

---

## 🧩 28 World-First Features

| # | Feature | What it does |
|---|---|---|
| 1-10 | Core Platform | Multi-mode chat, streaming, code execution, auth, leaderboard, real-time collab |
| 11 | Thought Replay | Watch AI debug step-by-step as a live timeline |
| 12 | Voice-to-Voice Loop | Speak your bug → AI speaks the fix back |
| 13 | Live Code Battle | 1v1 real-time coding challenge, AI-judged |
| 14 | Code Karma | Earn points for helping others, unlock ranks |
| 15 | Learning Replay | Your full coding journey as a milestone timeline |
| 16 | Blind Code Review | Anonymous peer code review |
| 17 | Mood Engine | Detects frustration/confusion, adapts AI tone |
| 18 | Dead Code Archaeologist | Finds zombie/ghost/fossil code with call graph |
| 19 | Code DNA Fingerprinting | Builds your style profile, AI silently matches it |
| 20 | Bug Prophecy Engine | Predicts which new code lines will break from your history |
| 21 | Pair Programmer Time Machine | Reverse-engineers edit history from final code |
| 22 | Cognitive Load Scorer | Measures brain effort to read code — per-function heatmap |
| 23 | Rubber Duck+ Mode | AI refuses answers, only asks Socratic questions |
| 24 | Personal Changelog | Auto-generates daily learning diary from sessions |
| 25 | Confidence Calibrator | Self-rate → quiz → see the confidence/skill gap |
| 26 | Error Autopsy | Probabilistic root-cause ranking before the fix |
| 27 | Pair Naming Assistant | Suggest names for code / verify if a name matches its body |
| 28 | Focus Zone Detector | Finds when YOU code most productively by hour and day |

---

## 📄 License

This project is licensed under the MIT License.

---

> ⚡ Built by [Dharanidharan M](https://github.com/dharani25007-code) 