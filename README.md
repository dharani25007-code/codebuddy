<div align="center">
<img src="https://capsule-render.vercel.app/api?type=waving&color=0:0f1117,50:7C3AED,100:4ecdc4&height=200&section=header&text=CodeBuddy%20AI&fontSize=52&fontColor=ffffff&fontAlignY=40&desc=World's%20First%20Tanglish%20AI%20Coding%20Assistant&descAlignY=60&descSize=18&animation=fadeIn"/>
</div>

<div align="center">

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![OpenRouter](https://img.shields.io/badge/OpenRouter-7C3AED?style=for-the-badge)
![SocketIO](https://img.shields.io/badge/Socket.IO-010101?style=for-the-badge&logo=socket.io&logoColor=white)

> ⚡ **28 New Features · 20+ Languages · 14 Free AI Models · 

</div>

---

## 📌 Overview

CodeBuddy is a full-stack AI-powered programming assistant with **28 features unavailable in any other tool** — including Tanglish (Tamil + English) voice coding, Code DNA fingerprinting, Rubber Duck+ Mode, and a 14-model AI fallback chain. Everything runs 100% free using OpenRouter's free-tier models.

---

## ✨ Core Features

| Feature | Description |
|---|---|
| 🧠 **8 AI Modes** | General, Debug, Optimize, Explain, Interview, ML, DSA, Roadmap |
| 🌍 **20+ Languages** | 9 Indian languages + French, German, Spanish, Japanese, Chinese & more |
| 🗣️ **Tanglish AI** |  Tamil+English mixed language coding assistant |
| 🔁 **Streaming** | Token-by-token with 14-model fallback chain |
| ▶️ **Code Execution** | Run 50+ languages via sandboxed Piston API |
| 🧬 **Code DNA** | Builds your personal coding style — AI silently matches it |
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
├── templates/
│   ├── index.html                  # Main dashboard + chat interface
│   ├── login.html / register.html
│   ├── profile.html
│   ├── leaderboard.html
│   ├── collab.html
│   └── codebuddy_world_first.html  # 28 Features Hub
├── static/js/
│   └── codebuddy_voice.js
└── coqui_profiles/                 # Voice clone samples (auto-created)
```

---

## 🚀 Getting Started

### Prerequisites
- Python **3.10+**
- Free API key from [openrouter.ai/keys](https://openrouter.ai/keys)

### Install
```bash
git clone https://github.com/dharani25007-code/codebuddy.git
cd codebuddy
pip install -r requirements.txt
```

### Configure
```bash
# Create .env file
OPENROUTER_API_KEY=sk-or-v1-your-key-here
SECRET_KEY=any-long-random-string
```

### Run
```bash
python app.py
```
Open: `http://127.0.0.1:5000` → Register → New Chat → Pick a mode 🚀

---

## 🤖 AI Fallback Chain (14 Models)

| Role | Model |
|---|---|
| Code tasks | `deepseek/deepseek-chat-v3-0324:free` |
| Fast / multilingual | `meta-llama/llama-4-scout:free` |
| Classification | `google/gemma-3-4b-it:free` |
| Last resort | `openrouter/auto` |

If any model returns 429/404/503 → next model tried automatically with 1.5s delay.

---

## 🌍 Languages Supported

**Indian (native script + TTS):** Tamil · Tanglish · Hindi · Telugu · Kannada · Malayalam · Bengali · Marathi · Gujarati · Punjabi

**World:** French · German · Spanish · Japanese · Chinese · Korean · Arabic · Russian · Portuguese · Italian

---

## 🧰 Tech Stack

| Library | Role |
|---|---|
| Flask | Web framework |
| Flask-Login + Bcrypt | Auth & password hashing |
| Flask-SocketIO | Real-time WebSocket collab |
| SQLite (WAL) | Primary data store |
| OpenRouter API | 14 free AI models with fallback |
| gTTS / XTTS-v2 | Text-to-speech (20+ languages / voice cloning) |
| Piston API | Sandboxed code execution — 50+ languages |

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


