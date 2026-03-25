⚡ CODEBUDDY AI

v9.0 · Complete Developer Reference

World's First Tanglish AI Coding Assistant

28 World-First Features · 20+ Languages · 100% Free AI Models

Flask + SQLite + OpenRouter + gTTS + SocketIO

March 2026

📋 Table of Contents
1. Overview - What CodeBuddy is and what makes it unique

2. Quick Start - Install and run in under 5 minutes

3. Tech Stack - All dependencies and their roles

4. Project Structure - File layout and what each file does

5. Environment Variables - Required and optional config

6. All 28 Features - Complete feature reference with API endpoints

7. API Reference - All endpoints, methods, auth requirements

8. AI Models - Which models are used and the fallback chain

9. Languages Supported - 20+ human languages and multilingual TTS

10. Database Schema - All SQLite tables and their purpose

11. Security - Auth, rate limiting, session management

12. Deployment - Local dev and production setup

13. Troubleshooting - Common errors and fixes

1. Overview
CodeBuddy is a full-stack AI-powered programming assistant built with Flask and backed by free AI models via OpenRouter. It is the world's first Tanglish (Tamil + English) voice coding AI, and includes 28 unique features unavailable in any other coding tool.

What makes CodeBuddy unique
Completely free - uses only :free models from OpenRouter (zero API cost)
Tanglish AI - understands and responds in Tamil+English mix (a world first)
9 Indian languages supported - Tamil, Hindi, Telugu, Kannada, Malayalam, Bengali, Marathi, Gujarati, Punjabi
Voice cloning - records your voice and AI speaks back IN YOUR VOICE via XTTS-v2
28 world-first features - none exist in Copilot, ChatGPT, or any other tool
100% local database - SQLite with WAL mode, no cloud dependency
Real-time collaboration - multi-user sessions with SocketIO + WebRTC voice
Core philosophy
Teach, don't just solve - Rubber Duck+ Mode refuses to give answers, forces thinking
Know the user - Code DNA builds your personal style profile, AI matches it
Track growth - Personal Changelog documents every session automatically
Emotional intelligence - Mood Engine adapts tone based on frustration signals
2. Quick Start
Prerequisites
Python 3.10 or higher
pip (Python package manager)
Node.js (optional - only for editing the front-end build)
ffmpeg (optional - required for voice cloning audio conversion)
Step 1 - Clone / copy files
Place all project files in a folder. Ensure you have:

app.py - the main Flask backend
templates/ - all HTML template files
static/ - JavaScript and CSS assets
Step 2 - Install Python dependencies
pip install flask flask-login flask-bcrypt flask-socketio

pip install requests python-dotenv gtts

pip install redis # optional - for production rate limiting

pip install TTS # optional - for real voice cloning (XTTS-v2)

pip install opencv-python # optional - for video frame analysis

Step 3 - Create .env file
OPENROUTER_API_KEY=sk-or-v1-your-key-here

SECRET_KEY=any-long-random-string # optional but recommended

Get a free OpenRouter key at: openrouter.ai/keys

Step 4 - Run
python app.py

Open your browser at: http://127.0.0.1:5000

Step 5 - Register and log in
Click Register - create a username and password (min 3 / 6 chars)
Log in and you land on the dashboard
Click New Chat and choose a mode to begin
3. Tech Stack
LIBRARY	CATEGORY	ROLE
Flask	Python	Web framework - routing, sessions, streaming responses
Flask-Login	Python	User session management and @login_required decorator
Flask-Bcrypt	Python	Password hashing - bcrypt algorithm
Flask-SocketIO	Python	WebSocket server for real-time collaboration
SQLite (WAL)	Database	Primary data store - WAL mode for concurrent reads
OpenRouter API	AI Gateway	Routes requests to 14+ free AI models with fallback
gTTS	TTS	Google Text-to-Speech - 20+ languages including Indic
XTTS-v2 (Coqui)	TTS	Real voice cloning - AI speaks in your recorded voice
Piston API	Execution	Sandboxed code runner - 50+ languages, no install needed
OpenCV	Vision	Video frame extraction for programming video analysis
Redis	Cache	Rate limiting store - falls back to in-memory if absent
python-dotenv	Config	Loads .env variables into os.environ
4. Project Structure
codebuddy/

├── app.py ← Main Flask backend (~3500 lines)

├── .env ← API keys and config (create this)

├── codebuddy.db ← SQLite database (auto-created)

├── voice_profiles/ ← Voice clone audio samples (auto-created)

│

├── templates/

│ ├── index.html ← Main dashboard + chat interface

│ ├── login.html ← Login page

│ ├── register.html ← Registration page

│ ├── profile.html ← User profile + stats

│ ├── leaderboard.html ← Global streak/karma leaderboard

│ ├── collab.html ← Real-time collaboration room

│ ├── public_chat.html ← Public shared chat viewer

│ └── codebuddy_world_first.html ← Features Hub (28 features UI)

│

└── static/

└── codebuddy_voice.js ← Voice recording + TTS frontend JS

5. Environment Variables
Create a file named .env in the same folder as app.py:

VARIABLE	STATUS	DESCRIPTION
OPENROUTER_API_KEY	required	Your OpenRouter API key - get free at openrouter.ai
SECRET_KEY	optional	Flask session key. Auto-derived from machine if not set
REDIS_URL	optional	Redis for rate limiting. Falls back to in-memory if unset
COOKIE_SECURE	optional	Set to 'true' in production (HTTPS). Default: false
Example .env file:

OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxx

SECRET_KEY=my-super-secret-key-change-this

REDIS_URL=redis://localhost:6379/0

COOKIE_SECURE=false

6. All 28 Features
Features 1-10 are core platform features. Features 11-28 are accessible from the Features Hub (/features).

Core Platform (Features 1-10)
#	Feature	Description	Type
1	Multi-Mode Chat	8 AI modes: general, debug, optimize, explain, interview, ML, DSA, roadmap	AI
2	Streaming Responses	Token-by-token streaming with real-time display and fallback chain	AI
3	20+ Language Support	Responds in Tamil, Hindi, Telugu, Kannada, Malayalam, Bengali + 14 more	AI
4	Code Execution	Run 50+ languages via Piston API - sandboxed, no install needed	AI
5	Persistent Memory	Auto-extracts your language, experience, project from chat and remembers it	AI
6	Code Complexity	Instant Big-O time and space complexity analysis for any snippet	AI
7	PWA Support	Installable as a native app on Android/iOS/Desktop via manifest.json	PWA
8	Secure Auth	Bcrypt passwords, stable sessions, remember-me, CSRF protection	SECURITY
9	Leaderboard + Streaks	Public leaderboard by streak days, shareable SVG streak card	AI
10	Real-time Collab	Multi-user chat rooms with SocketIO + WebRTC voice calling	REAL-TIME
World-First Features (11-28)
#	Feature	Description	Type
11	Thought Replay	Watch AI debug code step-by-step - every hypothesis made visible as a timeline	WORLD-FIRST
12	Voice-to-Voice Loop	Speak your bug → AI speaks the fix back. Full voice coding cycle	WORLD-FIRST
13	Live Code Battle	1v1 real-time coding challenge. AI judges both solutions and declares winner	WORLD-FIRST
14	Code Karma	Earn points for helping others. Karma unlocks ranks from NOVICE → GODMODE	WORLD-FIRST
15	Learning Replay	Your entire coding journey visualised as a milestone timeline with AI insights	WORLD-FIRST
16	Blind Code Review	Submit code anonymously. Peers review without knowing the author	WORLD-FIRST
17	Mood Engine	Detects frustration/confusion from message patterns - adapts AI tone in real-time	WORLD-FIRST
18	Dead Code Archaeologist	Finds zombie/ghost/fossil code and explains WHY each piece is dead with call graph	WORLD-FIRST
19	Code DNA Fingerprinting	Builds your personal style profile. AI silently matches your indentation, naming, patterns	WORLD-FIRST
20	Bug Prophecy Engine	Analyses YOUR historical bugs to predict which lines in new code will break the same way	WORLD-FIRST
21	Pair Programmer Time Machine	Reverse-engineers a full edit history from any final code - no git needed	WORLD-FIRST
22	Cognitive Load Scorer	Measures human brain effort to read code. Per-function heatmap. Not cyclomatic complexity	WORLD-FIRST
23	Rubber Duck+ Mode	AI refuses to give answers - only asks Socratic questions to guide you to the solution	WORLD-FIRST
24	Personal Changelog	Auto-generates a daily learning diary from your sessions. What you learned, built, struggled with	WORLD-FIRST
25	Confidence Calibrator	Rate your knowledge → take a quiz → see the gap between confidence and actual score	WORLD-FIRST
26	Error Autopsy	Probabilistic root-cause ranking BEFORE the fix. Diagnosis tree with cause probabilities	WORLD-FIRST
27	Pair Naming Assistant	Forward: suggest names for code. Reverse: does this name accurately describe the body?	WORLD-FIRST
28	Focus Zone Detector	Analyses message timestamps to find when YOU code most productively by hour and day	WORLD-FIRST
7. API Reference
🔒 = requires login 🌐 = public endpoint

Authentication
METHOD	ENDPOINT	DESCRIPTION	AUTH
GET	/login	Login page	🌐
POST	/login	Submit credentials. Form: username, password, remember_me	🌐
GET	/register	Registration page	🌐
POST	/register	Create account. Form: username, password	🌐
GET	/logout	Log out and clear session	🔒
Chat
METHOD	ENDPOINT	DESCRIPTION	AUTH
POST	/chat	Main AI chat. Streams response. Form: message, conversation_id, mode, lang	🔒
POST	/new_chat	Create a new conversation. JSON: {mode}	🔒
GET	/load_messages/:id	Load all messages for a chat	🔒
GET	/get_chat_title/:id	Get the auto-generated title	🔒
POST	/rename_chat	Rename a chat. JSON: {chat_id, title}	🔒
POST	/delete_chat	Delete a chat and all its messages	🔒
POST	/pin_chat	Toggle pin on a chat	🔒
POST	/share_chat	Generate a public share link. JSON: {chat_id}	🔒
GET	/public_chat/:token	View a shared chat (no login needed)	🌐
GET	/search_chats	Search chats by title/content. Query: ?q=text	🔒
Code Tools
METHOD	ENDPOINT	DESCRIPTION	AUTH
POST	/run_code	Execute code. JSON: {code, language}	🔒
POST	/analyze_complexity	Get Big-O analysis. JSON: {code}	🔒
POST	/quick_explain	Explain code at beginner/intermediate/expert level	🔒
POST	/edit_file	AI-powered file editor. Streams result	🔒
POST	/autocomplete	Get 3 code completion suggestions	🔒
POST	/analyze_video	Upload and analyse a coding video	🔒
GET	/supported_languages	List all supported execution languages	🌐
World-First Feature Endpoints
METHOD	ENDPOINT	DESCRIPTION	AUTH
POST	/thought_replay	Stream AI debugging steps as JSON. Body: {code}	🔒
POST	/voice_fix	Convert spoken problem to spoken fix. Body: {text, lang}	🔒
POST	/battle/create	Create a 1v1 coding battle	🔒
POST	/battle/join	Join a battle by ID	🔒
POST	/battle/judge	AI-judge both solutions	🔒
GET	/battle/status/:id	Poll battle status and opponent code	🔒
POST	/karma/earn	Award karma for an action	🔒
GET	/karma/me	Get your karma total, level, rank, history	🔒
GET	/learning_replay	Get your full learning timeline	🔒
POST	/learning_insight	Generate AI insight for a milestone	🔒
POST	/blind/submit	Submit code anonymously for review	🔒
GET	/blind/queue	Get open submissions to review	🔒
POST	/blind/review	Submit a review for a submission	🔒
GET	/mood/history	Get recent mood signals and summary	🔒
POST	/dead_code	Scan for dead/zombie/ghost code	🔒
POST	/dna/build	Build your Code DNA profile	🔒
GET	/dna/me	View your current DNA profile	🔒
POST	/prophecy/build	Build your personal bug fingerprint	🔒
POST	/prophecy/predict	Predict bugs in new code from your history	🔒
POST	/time_machine	Reverse-engineer a code edit history	🔒
POST	/cognitive_load	Score the cognitive load of code	🔒
POST	/duck/start	Activate Rubber Duck+ Mode	🔒
POST	/duck/stop	Deactivate Rubber Duck+ Mode	🔒
POST	/changelog/generate	Auto-generate today's learning diary	🔒
GET	/changelog/history	List all past changelog entries	🔒
POST	/calibrate/quiz	Generate a confidence calibration quiz	🔒
POST	/calibrate/submit	Submit answers and get calibration result	🔒
POST	/error_autopsy	Run probabilistic error diagnosis	🔒
POST	/naming/suggest	Get ranked name suggestions for code	🔒
GET	/focus_zone	Analyse your peak coding time windows	🔒
8. AI Models
CodeBuddy uses only :free models from OpenRouter - zero API cost. A fallback chain of 14 models ensures availability even when individual models are rate-limited.

Primary Models (as of March 2026)
code model: deepseek/deepseek-chat-v3-0324:free - Complex code tasks, DSA, ML, dead code analysis

fast model: meta-llama/llama-4-scout:free - Fast responses, multilingual, most features

classifier: google/gemma-3-4b-it:free - Programming topic detection (fast yes/no)

title: google/gemma-3-4b-it:free - Auto-generate 3-5 word chat title

Fallback Chain (14 models in order)
deepseek/deepseek-chat-v3-0324:free - primary fallback, very stable
meta-llama/llama-4-scout:free
meta-llama/llama-4-maverick:free
meta-llama/llama-3.3-70b-instruct:free
deepseek/deepseek-r1:free
deepseek/deepseek-r1-distill-llama-70b:free
deepseek/deepseek-r1-distill-qwen-32b:free
google/gemma-3-27b-it:free
google/gemma-3-12b-it:free
mistralai/mistral-small-3.1-24b-instruct:free
qwen/qwen3-coder:free
nvidia/llama-3.1-nemotron-70b-instruct:free
microsoft/phi-4:free
openrouter/auto - last resort, lets OpenRouter choose
If a model returns 429 (rate limited), 404 (not found), or 503 (unavailable), the next model in the chain is tried automatically with a 1.5s delay between attempts.

9. Languages Supported
Indian Languages (with native script TTS)
ta-IN	Tamil	தமிழ்	ta	Full native script + TTS
ta-en	Tanglish	Tamil+Eng	ta	Roman-script Tamil - world first
hi-IN	Hindi	हिंदी	hi	Devanagari script + TTS
te-IN	Telugu	తెలుగు	te	Native script + TTS
kn-IN	Kannada	ಕನ್ನಡ	kn	Native script + TTS
ml-IN	Malayalam	മലയാളം	ml	Native script + TTS
bn-IN	Bengali	বাংলা	bn	Native script + TTS
mr-IN	Marathi	मराठी	mr	Devanagari script + TTS
gu-IN	Gujarati	ગુજરાતી	gu	Native script + TTS
pa-IN	Punjabi	ਪੰਜਾਬੀ	en	Gurmukhi script (TTS: English fallback)
World Languages
French, German, Spanish, Japanese, Chinese (Simplified), Korean, Arabic, Russian, Portuguese (Brazil), Italian - all with native TTS support.

10. Database Schema
All data is stored in codebuddy.db (SQLite). The database is auto-created on first run.

users id, username, password, bio, avatar_color, created_at

conversations id, user_id, title, mode, created_at, updated_at, pinned

messages id, conversation_id, role, content, timestamp, tokens_used

user_stats user_id, total_messages, debug_count, code_runs, streak_days, last_active

user_memory user_id, key, value - persistent facts about each user

bookmarks user_id, message_id, note

share_tokens token, conversation_id - unguessable public share links

mood_signals user_id, conversation_id, mood, score - emotion history

code_dna user_id, profile (JSON), sample_count - style fingerprint

duck_sessions user_id, conversation_id, active, problem_statement, turn_count

changelogs user_id, date, entry (markdown), topics (JSON)

confidence_records user_id, topic, self_rating, actual_score, gap

error_autopsies user_id, error_hash, error_text, language, diagnosis (JSON)

naming_history user_id, original_name, suggestions (JSON), mode

focus_sessions user_id, session_date, hour_of_day, day_of_week, message_count

battles id, creator_id, problem, status, winner

battle_entries battle_id, user_id, code, score

karma user_id, total

karma_events user_id, event_type, delta, note

blind_submissions user_id, anon_id, code, language, status

blind_reviews submission_id, reviewer_id, stars, comment

blind_ai_reports submission_id, report, scores (JSON)

collab_rooms room_code, chat_id, host, members (JSON) - SQLite-persisted

bug_fingerprints user_id, fingerprint (JSON) - recurring bug patterns

11. Security
Authentication
Passwords hashed with bcrypt (cost factor default ~12)
Sessions use a stable secret key derived from machine fingerprint (or SECRET_KEY env var)
30-day persistent sessions; optional 7-day remember-me cookie
Session cookie: HttpOnly, SameSite=Lax, Secure=true in production
Rate Limiting
Chat endpoint: 50 requests per minute per user
Code execution: 30 requests per minute
TTS: 120 requests per minute
Heavy AI features (DNA build, prophecy, etc.): 5-15 per minute
Uses Redis if available, falls back to in-memory dict
429 response includes retry_after seconds
Other Security Measures
SQL injection: stat field updates use a whitelist (frozenset) - never raw user input
Share links: 192-bit random token (secrets.token_urlsafe(24)) - no ID enumeration
Security headers on all responses: X-Content-Type-Options, X-Frame-Options, Referrer-Policy
Ownership verified before every chat/message operation
Blind review: own submissions cannot be reviewed by the author
12. Deployment
Local Development
python app.py

Runs on http://127.0.0.1:5000 with debug=True and use_reloader=False.

use_reloader=False is critical - it prevents Flask from restarting with a new secret key that would invalidate all session cookies.

Production (Linux VPS)
pip install gunicorn

gunicorn -w 1 -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker \

-b 0.0.0.0:8000 app:app

Use 1 worker only - SQLite does not handle multiple writer processes well.

Set COOKIE_SECURE=true in .env when serving over HTTPS.

Nginx (reverse proxy)
location / {

proxy_pass http://127.0.0.1:8000;

proxy_http_version 1.1;

proxy_set_header Upgrade $http_upgrade;

proxy_set_header Connection 'upgrade';

proxy_set_header Host $host;

}

Voice Cloning (optional, GPU recommended)
pip install TTS torch

XTTS-v2 downloads ~1.8GB model on first use. GPU (CUDA) gives 10x faster synthesis. Falls back to gTTS if not installed.

13. Troubleshooting
503 / AI unavailable

Cause: All free models on OpenRouter are rate-limited simultaneously.

Fix: Wait 1-2 minutes and retry - free models reset quickly
Fix: Check openrouter.ai/models to see which :free models are online
Fix: Update FREE_FALLBACKS in app.py if models have been removed
400 on Code DNA / Bug Prophecy

Cause: Not enough code history to analyse - the AI needs samples to work from.

Fix: Paste several code snippets in the main chat using Debug or General mode
Fix: Then return to the feature and click Build
ERROR LOADING SESSION on every click

Cause: Flask restarted with a new random secret key, invalidating all cookies.

Fix: Make sure use_reloader=False is set in app.run() - it is by default in this codebase
Fix: Set a stable SECRET_KEY in your .env file
TTS produces no audio / choppy audio

Cause: gTTS version conflict or network issue.

Fix: Run /tts/diagnose endpoint to see full diagnostic report
Fix: Upgrade: pip install --upgrade gtts
Fix: Check click version: pip install click==8.0.4 (gTTS requires click < 8.1)
Voice clone not working

Cause: XTTS-v2 not installed or ffmpeg missing for audio conversion.

Fix: pip install TTS torch
Fix: Install ffmpeg: sudo apt install ffmpeg (Linux) / brew install ffmpeg (Mac)
Fix: Falls back to gTTS automatically if XTTS not available
Code execution fails

Cause: Piston API endpoint is down or returned an error.

Fix: The code tries 3 Piston endpoints automatically
Fix: Check https://emkc.org/api/v2/piston/execute is reachable
Fix: Unsupported language - check /supported_languages for the full list
WebSocket / collaboration not working

Cause: flask-socketio or eventlet not properly installed.

Fix: pip install flask-socketio
Fix: Use async_mode='threading' (already set in this codebase - do not change to eventlet)
CodeBuddy AI v9.0 · Built with ⚡ in Coimbatore, India · March 2026

28 World-First Features · Free Forever · Open for the World
