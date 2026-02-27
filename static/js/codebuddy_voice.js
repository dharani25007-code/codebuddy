/* ╔══════════════════════════════════════════════════════════════════════╗
   ║  CODEBUDDY NEURAL VOICE ENGINE v3.0                                 ║
   ║  The World's Most Advanced Programming Voice Assistant              ║
   ║                                                                     ║
   ║  PATENT-WORTHY FEATURES:                                            ║
   ║  1. Voice Command Routing — intent detection for mode switching     ║
   ║  2. Code Dictation Mode — speaks code with symbol pronunciation     ║
   ║  3. Emotion-Adaptive TTS — adjusts voice tone per response type     ║
   ║  4. Multilingual Code-Switching — mid-sentence language detection   ║
   ║  5. Voice Confidence Meter — real-time input quality visualization  ║
   ║  6. Smart Punctuation Injection — auto-adds . , ; : from pauses    ║
   ║  7. Wake Word Listener — "Hey CodeBuddy" always-on activation       ║
   ║  8. Silence Detection — auto-sends after user stops speaking        ║
   ║  9. Speaker Visualization — live waveform + spectrum analyzer       ║
   ║  10. Voice Shortcuts — "run it", "copy that", "clear screen"        ║
   ║  11. TTS Code Filtering — reads explanations, skips raw code        ║
   ║  12. Session Voice Replay — re-read any previous AI response        ║
   ╚══════════════════════════════════════════════════════════════════════╝ */

'use strict';

window.CBVoice = (function () {

  // ═══════════════ CONFIG ═══════════════
  const CFG = {
    WAKE_WORD: 'hey codebuddy',
    SILENCE_TIMEOUT_MS: 1800,   // auto-send after 1.8s silence
    MAX_RECORD_MS: 60000,
    CONFIDENCE_THRESHOLD: 0.55, // min confidence to auto-send
    WAVEFORM_BARS: 48,
    SPECTRUM_BARS: 32,
    SUPPORTED_LANGS: [
      { code: 'en-US', label: 'EN', name: 'English' },
      { code: 'ta-IN', label: 'TA', name: 'Tamil' },
      { code: 'hi-IN', label: 'HI', name: 'Hindi' },
      { code: 'zh-CN', label: 'ZH', name: 'Chinese' },
      { code: 'fr-FR', label: 'FR', name: 'French' },
      { code: 'de-DE', label: 'DE', name: 'German' },
      { code: 'ja-JP', label: 'JA', name: 'Japanese' },
      { code: 'es-ES', label: 'ES', name: 'Spanish' },
    ],
    TTS_VOICES: {
      mentor: { pitch: 1.05, rate: 0.92, volume: 1.0 },
      strict: { pitch: 0.88, rate: 0.82, volume: 1.0 },
      excited: { pitch: 1.2,  rate: 1.05, volume: 1.0 },
      calm:    { pitch: 0.95, rate: 0.78, volume: 0.9 },
    },
    CODE_SYMBOLS: {
      '===': 'triple equals',  '!==': 'strict not equals',
      '==': 'equals',          '!=': 'not equals',
      '>=': 'greater or equal','<=': 'less or equal',
      '=>': 'arrow',           '->': 'pointer arrow',
      '++': 'increment',       '--': 'decrement',
      '&&': 'and',             '||': 'or',
      '**': 'power',           '//': 'comment',
      '/*': 'block comment start', '*/': 'block comment end',
      '<<<': 'triple less than', '>>>': 'triple right shift',
      '{': 'open brace',       '}': 'close brace',
      '[': 'open bracket',     ']': 'close bracket',
      '(': 'open paren',       ')': 'close paren',
      '<': 'less than',        '>': 'greater than',
      '!': 'exclamation',      '@': 'at',
      '#': 'hash',             '$': 'dollar',
      '%': 'percent',          '^': 'caret',
      '&': 'ampersand',        '*': 'star',
      '-': 'dash',             '_': 'underscore',
      '=': 'equals',           '+': 'plus',
      '|': 'pipe',             '~': 'tilde',
      '`': 'backtick',         '\\': 'backslash',
      '/': 'slash',            ':': 'colon',
      ';': 'semicolon',        ',': 'comma',
      '.': 'dot',              '?': 'question mark',
    },
    VOICE_COMMANDS: {
      // Navigation
      'new chat': () => document.querySelector('.new-chat-btn')?.click(),
      'clear chat': () => _clearScreen(),
      'scroll down': () => document.getElementById('chatBox')?.scrollTo({ top: 99999, behavior: 'smooth' }),
      'scroll up': () => document.getElementById('chatBox')?.scrollTo({ top: 0, behavior: 'smooth' }),
      // Mode switching
      'switch to debug': () => _setMode('debug'),
      'debug mode': () => _setMode('debug'),
      'interview mode': () => _setMode('interview'),
      'optimize mode': () => _setMode('optimize'),
      'machine learning mode': () => _setMode('ml'),
      'general mode': () => _setMode('general'),
      // Actions
      'run it': () => document.querySelector('.run-btn')?.click(),
      'run code': () => document.querySelector('.run-btn')?.click(),
      'copy that': () => _copyLastResponse(),
      'copy code': () => document.querySelector('.code-btn')?.click(),
      'read that': () => CBVoice.speakLast(),
      'stop reading': () => CBVoice.stopSpeaking(),
      'repeat that': () => CBVoice.speakLast(),
      'pause': () => CBVoice.pauseSpeaking(),
      'resume': () => CBVoice.resumeSpeaking(),
      // Theme
      'dark mode': () => { document.body.classList.remove('light'); },
      'light mode': () => { document.body.classList.add('light'); },
      'toggle theme': () => document.querySelector('.theme-morph')?.click(),
      // Panel
      'show live': () => document.getElementById('liveBtn')?.click(),
      'hide live': () => { if (!document.getElementById('liveOverlay')?.classList.contains('hidden')) document.getElementById('liveBtn')?.click(); },
    },
  };

  // ═══════════════ STATE ═══════════════
  const S = {
    recognition: null,
    isListening: false,
    isWakeListening: false,
    isSpeaking: false,
    currentLang: 'en-US',
    silenceTimer: null,
    audioCtx: null,
    analyser: null,
    mediaStream: null,
    animFrame: null,
    waveformData: new Uint8Array(CFG.WAVEFORM_BARS),
    spectrumData: new Uint8Array(CFG.SPECTRUM_BARS),
    lastTranscript: '',
    commandMode: false,
    ttsPersonality: 'mentor',
    voiceHistory: [],        // array of {text, role, ts}
    historyIndex: -1,
    autoSend: true,
    codeDictation: false,
    wakeEnabled: false,
    wakeRecognition: null,
    uiMounted: false,
  };

  // ═══════════════ DOM REFS ═══════════════
  let UI = {};

  // ═══════════════════════════════════════════
  // FEATURE 1: VOICE PANEL UI CONSTRUCTION
  // ═══════════════════════════════════════════
  function mountUI() {
    if (S.uiMounted) return;
    S.uiMounted = true;

    // Inject CSS
    const style = document.createElement('style');
    style.textContent = getVoiceCSS();
    document.head.appendChild(style);

    // Create the floating voice panel
    const panel = document.createElement('div');
    panel.id = 'cbVoicePanel';
    panel.className = 'cbv-panel cbv-hidden';
    panel.innerHTML = getPanelHTML();
    document.body.appendChild(panel);

    // Create the always-visible voice bar (replaces the simple cluster)
    const bar = document.createElement('div');
    bar.id = 'cbVoiceBar';
    bar.className = 'cbv-bar';
    bar.innerHTML = getBarHTML();
    document.body.appendChild(bar);

    // Create the speaking overlay (floating waveform when AI talks)
    const speakOv = document.createElement('div');
    speakOv.id = 'cbSpeakOverlay';
    speakOv.className = 'cbv-speak-overlay cbv-hidden';
    speakOv.innerHTML = getSpeakOverlayHTML();
    document.body.appendChild(speakOv);

    // Cache refs
    UI = {
      panel: panel,
      bar: bar,
      speakOverlay: speakOv,
      waveCanvas: panel.querySelector('#cbvWaveCanvas'),
      specCanvas: panel.querySelector('#cbvSpecCanvas'),
      transcript: panel.querySelector('#cbvTranscript'),
      confidence: panel.querySelector('#cbvConfidence'),
      confidenceFill: panel.querySelector('#cbvConfidenceFill'),
      status: panel.querySelector('#cbvStatus'),
      langSelect: panel.querySelector('#cbvLang'),
      autoSendToggle: panel.querySelector('#cbvAutoSend'),
      wakeToggle: panel.querySelector('#cbvWakeToggle'),
      codeDictToggle: panel.querySelector('#cbvCodeDict'),
      historyList: panel.querySelector('#cbvHistoryList'),
      ttsPersonality: panel.querySelector('#cbvTTSPersonality'),
      ttsProgress: panel.querySelector('#cbvTTSProgress'),
      ttsFill: panel.querySelector('#cbvTTSFill'),
      barMicBtn: bar.querySelector('#cbvBarMic'),
      barSpeakBtn: bar.querySelector('#cbvBarSpeak'),
      barPanelBtn: bar.querySelector('#cbvBarPanel'),
      barWake: bar.querySelector('#cbvBarWake'),
      barLangLabel: bar.querySelector('#cbvBarLang'),
    };

    bindEvents();
    startAudioContext();
    log('VOICE ENGINE INITIALIZED');
  }

  // ═══════════════════════════════════════════
  // FEATURE 2: VOICE BAR HTML
  // ═══════════════════════════════════════════
  function getBarHTML() {
    return `
      <div class="cbv-bar-inner">
        <div class="cbv-bar-waveform" id="cbvBarWave">
          <canvas id="cbvMiniWave" width="80" height="28"></canvas>
        </div>
        <div class="cbv-bar-controls">
          <button class="cbv-bar-btn" id="cbvBarMic" title="Voice Input (V)" onclick="CBVoice.toggleListening()">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="9" y="2" width="6" height="11" rx="3"/>
              <path d="M5 10a7 7 0 0 0 14 0M12 19v3M8 22h8"/>
            </svg>
          </button>
          <button class="cbv-bar-btn cbv-bar-btn--speak" id="cbvBarSpeak" title="Read Last Response (R)" onclick="CBVoice.speakLast()">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
              <path d="M15.54 8.46a5 5 0 0 1 0 7.07M19.07 4.93a10 10 0 0 1 0 14.14"/>
            </svg>
          </button>
          <div class="cbv-bar-sep"></div>
          <button class="cbv-bar-btn cbv-bar-btn--sm" id="cbvBarPause" title="Pause/Resume" onclick="CBVoice.togglePause()">⏸</button>
          <button class="cbv-bar-btn cbv-bar-btn--sm" id="cbvBarStop" title="Stop Speaking" onclick="CBVoice.stopSpeaking()">⏹</button>
          <div class="cbv-bar-sep"></div>
          <div class="cbv-bar-lang-wrap">
            <span class="cbv-bar-lang-label" id="cbvBarLang">EN</span>
          </div>
          <div class="cbv-wake-indicator" id="cbvBarWake" title="Wake Word Status">
            <span class="cbv-wake-dot"></span>
          </div>
          <div class="cbv-bar-sep"></div>
          <button class="cbv-bar-btn cbv-bar-btn--panel" id="cbvBarPanel" title="Open Voice Lab" onclick="CBVoice.togglePanel()">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="3"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M4.93 4.93a10 10 0 0 0 0 14.14"/>
            </svg>
          </button>
        </div>
      </div>`;
  }

  // ═══════════════════════════════════════════
  // FEATURE 3: FULL VOICE LAB PANEL HTML
  // ═══════════════════════════════════════════
  function getPanelHTML() {
    return `
      <div class="cbv-panel-header">
        <div class="cbv-panel-title">
          <span class="cbv-panel-dot"></span>
          NEURAL VOICE LAB
        </div>
        <div class="cbv-panel-controls">
          <button class="cbv-ph-btn" onclick="CBVoice.togglePanel()">✕</button>
        </div>
      </div>

      <div class="cbv-tabs">
        <div class="cbv-tab active" data-tab="record" onclick="CBVoice._switchTab('record',this)">RECORD</div>
        <div class="cbv-tab" data-tab="speak" onclick="CBVoice._switchTab('speak',this)">SPEAK</div>
        <div class="cbv-tab" data-tab="cmds" onclick="CBVoice._switchTab('cmds',this)">COMMANDS</div>
        <div class="cbv-tab" data-tab="history" onclick="CBVoice._switchTab('history',this)">HISTORY</div>
        <div class="cbv-tab" data-tab="settings" onclick="CBVoice._switchTab('settings',this)">SETTINGS</div>
      </div>

      <!-- ── RECORD TAB ── -->
      <div class="cbv-tabpanel active" id="cbvTab-record">
        <!-- WAVEFORM VISUALIZER -->
        <div class="cbv-visualizer-wrap">
          <canvas id="cbvWaveCanvas" class="cbv-wave-canvas" width="360" height="80"></canvas>
          <canvas id="cbvSpecCanvas" class="cbv-spec-canvas" width="360" height="40"></canvas>
          <div class="cbv-vis-overlay">
            <div class="cbv-vis-label" id="cbvStatus">STANDBY</div>
          </div>
        </div>

        <!-- TRANSCRIPT DISPLAY -->
        <div class="cbv-transcript-wrap">
          <div class="cbv-tr-label">LIVE TRANSCRIPT</div>
          <div class="cbv-transcript" id="cbvTranscript">Waiting for voice input…</div>
        </div>

        <!-- CONFIDENCE METER -->
        <div class="cbv-confidence-wrap">
          <div class="cbv-conf-label">
            <span>CONFIDENCE</span>
            <span id="cbvConfidence">0%</span>
          </div>
          <div class="cbv-conf-track">
            <div class="cbv-conf-fill" id="cbvConfidenceFill" style="width:0%"></div>
          </div>
        </div>

        <!-- RECORD CONTROLS -->
        <div class="cbv-rec-controls">
          <button class="cbv-big-mic" id="cbvBigMic" onclick="CBVoice.toggleListening()">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <rect x="9" y="2" width="6" height="11" rx="3"/>
              <path d="M5 10a7 7 0 0 0 14 0M12 19v3M8 22h8"/>
            </svg>
            <span id="cbvBigMicLabel">PRESS TO SPEAK</span>
          </button>
          <div class="cbv-rec-sub">
            <button class="cbv-sub-btn" onclick="CBVoice._sendTranscript()">SEND NOW</button>
            <button class="cbv-sub-btn" onclick="CBVoice._clearTranscript()">CLEAR</button>
          </div>
        </div>

        <!-- LANG SELECT -->
        <div class="cbv-lang-grid">
          ${CFG.SUPPORTED_LANGS.map(l => `
            <div class="cbv-lang-chip ${l.code === 'en-US' ? 'active' : ''}"
                 data-lang="${l.code}"
                 onclick="CBVoice.setLang('${l.code}',this)">
              ${l.label}<span>${l.name}</span>
            </div>`).join('')}
        </div>

        <!-- AUTO SEND + CODE DICT TOGGLES -->
        <div class="cbv-toggle-row">
          <div class="cbv-toggle-item">
            <div class="cbv-toggle-info">
              <div class="cbv-toggle-name">AUTO-SEND</div>
              <div class="cbv-toggle-desc">Send automatically after silence</div>
            </div>
            <div class="cbv-switch active" id="cbvAutoSend" onclick="CBVoice._toggleAutoSend(this)">
              <div class="cbv-switch-knob"></div>
            </div>
          </div>
          <div class="cbv-toggle-item">
            <div class="cbv-toggle-info">
              <div class="cbv-toggle-name">CODE DICTATION</div>
              <div class="cbv-toggle-desc">Pronounce symbols while reading</div>
            </div>
            <div class="cbv-switch" id="cbvCodeDict" onclick="CBVoice._toggleCodeDict(this)">
              <div class="cbv-switch-knob"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- ── SPEAK TAB ── -->
      <div class="cbv-tabpanel" id="cbvTab-speak">
        <div class="cbv-speak-section">
          <div class="cbv-sec-title">TTS PERSONALITY</div>
          <div class="cbv-personality-grid">
            <div class="cbv-persona active" data-persona="mentor" onclick="CBVoice.setPersonality('mentor',this)">
              <div class="cbv-persona-icon">🎓</div>
              <div class="cbv-persona-name">MENTOR</div>
              <div class="cbv-persona-desc">Warm & supportive</div>
            </div>
            <div class="cbv-persona" data-persona="strict" onclick="CBVoice.setPersonality('strict',this)">
              <div class="cbv-persona-icon">⚡</div>
              <div class="cbv-persona-name">STRICT</div>
              <div class="cbv-persona-desc">Deep & authoritative</div>
            </div>
            <div class="cbv-persona" data-persona="excited" onclick="CBVoice.setPersonality('excited',this)">
              <div class="cbv-persona-icon">🚀</div>
              <div class="cbv-persona-name">EXCITED</div>
              <div class="cbv-persona-desc">Fast & energetic</div>
            </div>
            <div class="cbv-persona" data-persona="calm" onclick="CBVoice.setPersonality('calm',this)">
              <div class="cbv-persona-icon">🌊</div>
              <div class="cbv-persona-name">CALM</div>
              <div class="cbv-persona-desc">Slow & meditative</div>
            </div>
          </div>

          <div class="cbv-tts-progress-wrap">
            <div class="cbv-conf-label"><span>SPEAKING PROGRESS</span><span id="cbvTTSPct">0%</span></div>
            <div class="cbv-conf-track">
              <div class="cbv-conf-fill" id="cbvTTSFill" style="width:0%; background: linear-gradient(90deg,var(--nova),var(--plasma))"></div>
            </div>
          </div>

          <div class="cbv-speak-controls">
            <button class="cbv-speak-btn" onclick="CBVoice.speakLast()">▶ READ LAST</button>
            <button class="cbv-speak-btn" onclick="CBVoice.togglePause()">⏸ PAUSE</button>
            <button class="cbv-speak-btn cbv-speak-btn--stop" onclick="CBVoice.stopSpeaking()">⏹ STOP</button>
          </div>

          <div class="cbv-custom-speak">
            <div class="cbv-sec-title">SPEAK CUSTOM TEXT</div>
            <textarea class="cbv-custom-input" id="cbvCustomSpeak" placeholder="Type text to speak…" rows="3"></textarea>
            <button class="cbv-speak-btn" onclick="CBVoice.speakCustom()">▶ SPEAK TEXT</button>
          </div>

          <div class="cbv-toggle-item" style="margin-top:12px">
            <div class="cbv-toggle-info">
              <div class="cbv-toggle-name">AUTO-READ RESPONSES</div>
              <div class="cbv-toggle-desc">Read AI answers automatically</div>
            </div>
            <div class="cbv-switch" id="cbvAutoRead" onclick="CBVoice._toggleAutoRead(this)">
              <div class="cbv-switch-knob"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- ── COMMANDS TAB ── -->
      <div class="cbv-tabpanel" id="cbvTab-cmds">
        <div class="cbv-sec-title">VOICE COMMANDS</div>
        <div class="cbv-cmd-list">
          ${Object.keys(CFG.VOICE_COMMANDS).map(cmd => `
            <div class="cbv-cmd-row" onclick="CBVoice._runCommand('${cmd}')">
              <div class="cbv-cmd-text">"${cmd}"</div>
              <div class="cbv-cmd-run">▶</div>
            </div>`).join('')}
        </div>
        <div class="cbv-sec-title" style="margin-top:16px">HOTKEYS</div>
        <div class="cbv-hotkey-list">
          <div class="cbv-hk"><kbd>V</kbd><span>Toggle voice recording</span></div>
          <div class="cbv-hk"><kbd>R</kbd><span>Read last AI response</span></div>
          <div class="cbv-hk"><kbd>Space</kbd><span>Stop speaking (when panel open)</span></div>
          <div class="cbv-hk"><kbd>Esc</kbd><span>Cancel & clear transcript</span></div>
        </div>
      </div>

      <!-- ── HISTORY TAB ── -->
      <div class="cbv-tabpanel" id="cbvTab-history">
        <div class="cbv-sec-title">VOICE SESSION HISTORY</div>
        <div class="cbv-history-list" id="cbvHistoryList">
          <div class="cbv-hist-empty">No voice interactions yet.</div>
        </div>
      </div>

      <!-- ── SETTINGS TAB ── -->
      <div class="cbv-tabpanel" id="cbvTab-settings">
        <div class="cbv-sec-title">WAKE WORD</div>
        <div class="cbv-toggle-item">
          <div class="cbv-toggle-info">
            <div class="cbv-toggle-name">ALWAYS-ON LISTENER</div>
            <div class="cbv-toggle-desc">"Hey CodeBuddy" to start recording</div>
          </div>
          <div class="cbv-switch" id="cbvWakeToggle" onclick="CBVoice.toggleWakeWord(this)">
            <div class="cbv-switch-knob"></div>
          </div>
        </div>
        <div class="cbv-wake-status" id="cbvWakeStatus">Wake word detection is OFF</div>

        <div class="cbv-sec-title" style="margin-top:16px">TTS ENGINE</div>
        <div class="cbv-toggle-item">
          <div class="cbv-toggle-info">
            <div class="cbv-toggle-name">FILTER CODE FROM SPEECH</div>
            <div class="cbv-toggle-desc">Skip raw code blocks, read explanations only</div>
          </div>
          <div class="cbv-switch active" id="cbvCodeFilter" onclick="CBVoice._toggleSwitch(this, 'codeFilter')">
            <div class="cbv-switch-knob"></div>
          </div>
        </div>
        <div class="cbv-toggle-item">
          <div class="cbv-toggle-info">
            <div class="cbv-toggle-name">SMART PUNCTUATION</div>
            <div class="cbv-toggle-desc">Auto-inject . , ; based on speech pauses</div>
          </div>
          <div class="cbv-switch active" id="cbvSmartPunct" onclick="CBVoice._toggleSwitch(this, 'smartPunct')">
            <div class="cbv-switch-knob"></div>
          </div>
        </div>
        <div class="cbv-toggle-item">
          <div class="cbv-toggle-info">
            <div class="cbv-toggle-name">CONTINUOUS LISTEN</div>
            <div class="cbv-toggle-desc">Don't stop listening between messages</div>
          </div>
          <div class="cbv-switch" id="cbvContinuous" onclick="CBVoice._toggleSwitch(this, 'continuous')">
            <div class="cbv-switch-knob"></div>
          </div>
        </div>

        <div class="cbv-sec-title" style="margin-top:16px">VOICE SHORTCUTS KEY</div>
        <div class="cbv-shortcut-key">
          <div class="cbv-sk-item"><span class="cbv-sk-badge">🔴</span> Recording</div>
          <div class="cbv-sk-item"><span class="cbv-sk-badge">🔵</span> Confident (auto-send)</div>
          <div class="cbv-sk-item"><span class="cbv-sk-badge">🟡</span> Low confidence (manual)</div>
          <div class="cbv-sk-item"><span class="cbv-sk-badge">🟢</span> Sent successfully</div>
        </div>
      </div>`;
  }

  // ═══════════════════════════════════════════
  // FEATURE 4: SPEAKING OVERLAY
  // ═══════════════════════════════════════════
  function getSpeakOverlayHTML() {
    return `
      <div class="cbv-so-inner">
        <canvas id="cbvSpeakWave" width="280" height="56"></canvas>
        <div class="cbv-so-label" id="cbvSoLabel">AI SPEAKING…</div>
        <div class="cbv-so-controls">
          <button onclick="CBVoice.togglePause()">⏸</button>
          <button onclick="CBVoice.stopSpeaking()">⏹</button>
        </div>
      </div>`;
  }

  // ═══════════════════════════════════════════
  // CSS
  // ═══════════════════════════════════════════
  function getVoiceCSS() {
    return `
/* ═══ CODEBUDDY VOICE ENGINE CSS ═══ */
:root {
  --cbv-plasma: #00ffe0;
  --cbv-nova: #a855f7;
  --cbv-fire: #ff6b2b;
  --cbv-gold: #fbbf24;
  --cbv-deep: #060d1a;
  --cbv-border: rgba(0,255,224,0.18);
  --cbv-surface: rgba(0,255,224,0.04);
  --cbv-glow: rgba(0,255,224,0.2);
  --cbv-text: #e2f4ff;
  --cbv-text2: rgba(226,244,255,0.45);
  --cbv-text3: rgba(226,244,255,0.2);
  --cbv-mono: 'IBM Plex Mono', monospace;
  --cbv-display: 'Orbitron', monospace;
}
body.light {
  --cbv-plasma: #0891b2;
  --cbv-nova: #6d28d9;
  --cbv-deep: #e8f4f8;
  --cbv-border: rgba(8,145,178,0.25);
  --cbv-surface: rgba(8,145,178,0.05);
  --cbv-glow: rgba(8,145,178,0.15);
  --cbv-text: #0c2a3a;
  --cbv-text2: rgba(12,42,58,0.6);
  --cbv-text3: rgba(12,42,58,0.3);
}

/* ── VOICE BAR ── */
.cbv-bar {
  position: fixed;
  bottom: 0; left: 280px; right: 0;
  height: 52px;
  background: rgba(4,8,16,0.92);
  backdrop-filter: blur(32px) saturate(200%);
  border-top: 1px solid var(--cbv-border);
  z-index: 50;
  transition: left 0.4s cubic-bezier(0.4,0,0.2,1);
  box-shadow: 0 -4px 30px rgba(0,255,224,0.04);
}
body.light .cbv-bar { background: rgba(228,243,249,0.95); }
.sidebar.collapsed ~ .cbv-bar, .sidebar.collapsed + .main ~ .cbv-bar { left: 60px; }
.cbv-bar-inner { display: flex; align-items: center; height: 100%; padding: 0 18px; gap: 10px; }
.cbv-bar-waveform { flex: 1; max-width: 100px; height: 28px; position: relative; }
.cbv-bar-controls { display: flex; align-items: center; gap: 6px; }
.cbv-bar-btn {
  width: 36px; height: 36px; border-radius: 2px;
  border: 1px solid var(--cbv-border);
  background: var(--cbv-surface);
  color: var(--cbv-text2);
  display: flex; align-items: center; justify-content: center;
  cursor: none; transition: all 0.15s; flex-shrink: 0;
}
.cbv-bar-btn svg { width: 16px; height: 16px; }
.cbv-bar-btn:hover { border-color: var(--cbv-plasma); color: var(--cbv-plasma); box-shadow: 0 0 12px var(--cbv-glow); }
.cbv-bar-btn.cbv-active { background: rgba(0,255,224,0.12); color: var(--cbv-plasma); border-color: var(--cbv-plasma); box-shadow: 0 0 16px var(--cbv-glow); }
.cbv-bar-btn.cbv-recording { background: rgba(255,107,43,0.12); color: var(--cbv-fire); border-color: rgba(255,107,43,0.4); animation: cbvRecPulse 1s ease infinite; }
@keyframes cbvRecPulse { 0%,100%{opacity:1;box-shadow:0 0 8px rgba(255,107,43,0.3)} 50%{opacity:0.7;box-shadow:0 0 20px rgba(255,107,43,0.6)} }
.cbv-bar-btn--sm { width: 28px; height: 28px; font-size: 11px; }
.cbv-bar-btn--speak:hover { color: var(--cbv-nova); border-color: var(--cbv-nova); box-shadow: 0 0 12px rgba(168,85,247,0.25); }
.cbv-bar-btn--panel { border-color: rgba(168,85,247,0.3); color: var(--cbv-nova); }
.cbv-bar-btn--panel:hover { border-color: var(--cbv-nova); box-shadow: 0 0 14px rgba(168,85,247,0.3); }
.cbv-bar-sep { width: 1px; height: 22px; background: var(--cbv-border); margin: 0 2px; }
.cbv-bar-lang-wrap { padding: 0 8px; }
.cbv-bar-lang-label { font-family: var(--cbv-display); font-size: 9px; font-weight: 700; letter-spacing: 2px; color: var(--cbv-plasma); }
.cbv-wake-indicator { display: flex; align-items: center; padding: 0 6px; }
.cbv-wake-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--cbv-text3); transition: all 0.3s; }
.cbv-wake-indicator.active .cbv-wake-dot { background: #4ade80; box-shadow: 0 0 8px rgba(74,222,128,0.6); animation: cbvWakeBlink 2s ease infinite; }
@keyframes cbvWakeBlink { 0%,100%{opacity:1} 50%{opacity:0.4} }

/* ── VOICE PANEL ── */
.cbv-panel {
  position: fixed;
  bottom: 64px; right: 20px;
  width: 400px;
  max-height: calc(100vh - 90px);
  background: rgba(4,8,18,0.97);
  backdrop-filter: blur(48px) saturate(220%);
  border: 1px solid var(--cbv-border);
  border-radius: 3px;
  z-index: 300;
  display: flex; flex-direction: column;
  overflow: hidden;
  box-shadow: 0 -8px 60px rgba(0,0,0,0.8), 0 0 40px var(--cbv-glow), 0 0 0 1px rgba(0,255,224,0.02);
  transition: opacity 0.25s, transform 0.25s;
}
body.light .cbv-panel { background: rgba(228,243,249,0.97); }
.cbv-panel.cbv-hidden { opacity: 0; transform: translateY(16px) scale(0.97); pointer-events: none; }
/* corner accents */
.cbv-panel::before, .cbv-panel::after { content: ''; position: absolute; width: 14px; height: 14px; border-color: var(--cbv-plasma); border-style: solid; opacity: 0.5; z-index: 1; pointer-events: none; }
.cbv-panel::before { top: -1px; left: -1px; border-width: 2px 0 0 2px; }
.cbv-panel::after  { bottom: -1px; right: -1px; border-width: 0 2px 2px 0; }

.cbv-panel-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--cbv-border);
  background: rgba(0,255,224,0.02);
  flex-shrink: 0;
}
.cbv-panel-title {
  display: flex; align-items: center; gap: 8px;
  font-family: var(--cbv-display); font-size: 10px; font-weight: 700;
  letter-spacing: 3px; color: var(--cbv-plasma); text-transform: uppercase;
}
.cbv-panel-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--cbv-plasma); box-shadow: 0 0 8px var(--cbv-plasma);
  animation: cbvWakeBlink 1.6s ease infinite;
}
.cbv-panel-controls { display: flex; gap: 6px; }
.cbv-ph-btn { background: none; border: none; color: var(--cbv-text3); cursor: none; font-size: 13px; padding: 2px 6px; border-radius: 2px; transition: color 0.15s; }
.cbv-ph-btn:hover { color: var(--cbv-fire); }

/* ── TABS ── */
.cbv-tabs { display: flex; border-bottom: 1px solid var(--cbv-border); flex-shrink: 0; }
.cbv-tab {
  flex: 1; padding: 9px 4px; text-align: center;
  font-family: var(--cbv-display); font-size: 8px; font-weight: 700;
  letter-spacing: 1.5px; text-transform: uppercase;
  color: var(--cbv-text3); cursor: none;
  border-bottom: 2px solid transparent; transition: all 0.15s;
}
.cbv-tab.active { color: var(--cbv-plasma); border-color: var(--cbv-plasma); }
.cbv-tab:hover:not(.active) { color: var(--cbv-text2); }

/* ── TAB PANELS ── */
.cbv-tabpanel { display: none; overflow-y: auto; max-height: 60vh; padding: 14px; animation: cbvFadeUp 0.2s ease; }
.cbv-tabpanel.active { display: block; }
.cbv-tabpanel::-webkit-scrollbar { width: 2px; }
.cbv-tabpanel::-webkit-scrollbar-thumb { background: var(--cbv-border); }
@keyframes cbvFadeUp { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:none} }

/* ── VISUALIZER ── */
.cbv-visualizer-wrap {
  position: relative; border: 1px solid var(--cbv-border);
  border-radius: 2px; overflow: hidden;
  background: rgba(2,4,8,0.8);
  margin-bottom: 12px;
}
.cbv-wave-canvas { display: block; width: 100%; }
.cbv-spec-canvas { display: block; width: 100%; }
.cbv-vis-overlay {
  position: absolute; top: 8px; right: 10px;
  display: flex; align-items: center; gap: 6px;
}
.cbv-vis-label {
  font-family: var(--cbv-display); font-size: 8px; font-weight: 700;
  letter-spacing: 2.5px; color: var(--cbv-plasma); text-transform: uppercase;
  text-shadow: 0 0 10px var(--cbv-plasma);
}

/* ── TRANSCRIPT ── */
.cbv-transcript-wrap { margin-bottom: 12px; }
.cbv-tr-label { font-family: var(--cbv-display); font-size: 8px; letter-spacing: 2px; color: var(--cbv-text3); margin-bottom: 5px; text-transform: uppercase; }
.cbv-transcript {
  min-height: 44px; padding: 10px 12px;
  border: 1px solid var(--cbv-border);
  background: var(--cbv-surface);
  border-radius: 2px;
  font-family: var(--cbv-mono); font-size: 12px; color: var(--cbv-text);
  line-height: 1.6; letter-spacing: 0.3px;
  transition: border-color 0.2s;
}
.cbv-transcript.active { border-color: var(--cbv-plasma); box-shadow: 0 0 12px var(--cbv-glow); }

/* ── CONFIDENCE ── */
.cbv-confidence-wrap { margin-bottom: 14px; }
.cbv-conf-label { display: flex; justify-content: space-between; font-family: var(--cbv-display); font-size: 8px; color: var(--cbv-text3); margin-bottom: 5px; letter-spacing: 1px; }
.cbv-conf-track { height: 3px; background: rgba(255,255,255,0.06); border-radius: 2px; overflow: hidden; }
.cbv-conf-fill { height: 100%; border-radius: 2px; transition: width 0.3s ease, background 0.3s; background: linear-gradient(90deg, var(--cbv-fire), var(--cbv-gold)); }
.cbv-conf-fill.high { background: linear-gradient(90deg, var(--cbv-plasma), #00bfa5); box-shadow: 0 0 6px var(--cbv-glow); }

/* ── RECORD CONTROLS ── */
.cbv-rec-controls { display: flex; flex-direction: column; align-items: center; gap: 10px; margin-bottom: 14px; }
.cbv-big-mic {
  width: 80px; height: 80px; border-radius: 50%;
  border: 2px solid var(--cbv-border);
  background: var(--cbv-surface);
  color: var(--cbv-text2); cursor: none;
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 4px;
  transition: all 0.2s;
  box-shadow: 0 0 20px rgba(0,255,224,0.05);
}
.cbv-big-mic svg { width: 28px; height: 28px; }
.cbv-big-mic span { font-family: var(--cbv-display); font-size: 7px; font-weight: 700; letter-spacing: 1.5px; color: var(--cbv-text3); text-transform: uppercase; }
.cbv-big-mic:hover { border-color: var(--cbv-plasma); color: var(--cbv-plasma); box-shadow: 0 0 30px var(--cbv-glow); }
.cbv-big-mic.recording { border-color: var(--cbv-fire); color: var(--cbv-fire); background: rgba(255,107,43,0.08); animation: cbvMicPulse 1s ease infinite; }
.cbv-big-mic.recording span { color: var(--cbv-fire); }
@keyframes cbvMicPulse {
  0%,100% { box-shadow: 0 0 20px rgba(255,107,43,0.2); transform: scale(1); }
  50%      { box-shadow: 0 0 40px rgba(255,107,43,0.5); transform: scale(1.04); }
}
.cbv-rec-sub { display: flex; gap: 8px; }
.cbv-sub-btn {
  padding: 7px 16px; border-radius: 2px;
  border: 1px solid var(--cbv-border); background: var(--cbv-surface);
  font-family: var(--cbv-display); font-size: 8px; font-weight: 700;
  letter-spacing: 2px; color: var(--cbv-text2); cursor: none;
  text-transform: uppercase; transition: all 0.15s;
}
.cbv-sub-btn:hover { border-color: var(--cbv-plasma); color: var(--cbv-plasma); background: rgba(0,255,224,0.06); }

/* ── LANG GRID ── */
.cbv-lang-grid { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 14px; }
.cbv-lang-chip {
  padding: 5px 10px; border-radius: 2px;
  border: 1px solid var(--cbv-border); background: var(--cbv-surface);
  font-family: var(--cbv-display); font-size: 9px; font-weight: 700;
  letter-spacing: 1px; color: var(--cbv-text3); cursor: none;
  transition: all 0.15s; display: flex; gap: 5px; align-items: center;
}
.cbv-lang-chip span { font-size: 7px; font-weight: 400; color: var(--cbv-text3); }
.cbv-lang-chip.active, .cbv-lang-chip:hover { border-color: var(--cbv-plasma); color: var(--cbv-plasma); background: rgba(0,255,224,0.06); }
.cbv-lang-chip.active span { color: var(--cbv-text2); }

/* ── TOGGLES ── */
.cbv-toggle-row { display: flex; flex-direction: column; gap: 10px; }
.cbv-toggle-item { display: flex; align-items: center; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.04); }
.cbv-toggle-name { font-family: var(--cbv-display); font-size: 9px; font-weight: 700; letter-spacing: 1.5px; color: var(--cbv-text); text-transform: uppercase; }
.cbv-toggle-desc { font-family: var(--cbv-mono); font-size: 9.5px; color: var(--cbv-text3); margin-top: 2px; }
.cbv-switch { width: 40px; height: 22px; border-radius: 11px; border: 1px solid var(--cbv-border); background: rgba(255,255,255,0.04); cursor: none; position: relative; transition: all 0.25s; flex-shrink: 0; }
.cbv-switch.active { background: rgba(0,255,224,0.12); border-color: var(--cbv-plasma); box-shadow: 0 0 8px var(--cbv-glow); }
.cbv-switch-knob { position: absolute; top: 3px; left: 3px; width: 14px; height: 14px; border-radius: 50%; background: var(--cbv-text3); transition: all 0.25s; }
.cbv-switch.active .cbv-switch-knob { left: 21px; background: var(--cbv-plasma); box-shadow: 0 0 6px var(--cbv-plasma); }

/* ── SPEAK TAB ── */
.cbv-speak-section { display: flex; flex-direction: column; gap: 14px; }
.cbv-sec-title { font-family: var(--cbv-display); font-size: 8px; font-weight: 700; letter-spacing: 3px; color: var(--cbv-text3); text-transform: uppercase; margin-bottom: 8px; }
.cbv-personality-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.cbv-persona {
  padding: 12px 10px; border-radius: 2px;
  border: 1px solid var(--cbv-border); background: var(--cbv-surface);
  cursor: none; text-align: center; transition: all 0.15s;
}
.cbv-persona.active, .cbv-persona:hover { border-color: var(--cbv-nova); background: rgba(168,85,247,0.06); box-shadow: 0 0 12px rgba(168,85,247,0.15); }
.cbv-persona-icon { font-size: 20px; margin-bottom: 4px; }
.cbv-persona-name { font-family: var(--cbv-display); font-size: 9px; font-weight: 700; letter-spacing: 2px; color: var(--cbv-text); text-transform: uppercase; }
.cbv-persona-desc { font-family: var(--cbv-mono); font-size: 9px; color: var(--cbv-text3); margin-top: 3px; }
.cbv-speak-controls { display: flex; gap: 8px; flex-wrap: wrap; }
.cbv-speak-btn {
  padding: 8px 14px; border-radius: 2px; cursor: none;
  border: 1px solid var(--cbv-border); background: var(--cbv-surface);
  font-family: var(--cbv-display); font-size: 8px; font-weight: 700;
  letter-spacing: 2px; color: var(--cbv-text2); text-transform: uppercase;
  transition: all 0.15s;
}
.cbv-speak-btn:hover { border-color: var(--cbv-nova); color: var(--cbv-nova); background: rgba(168,85,247,0.06); }
.cbv-speak-btn--stop:hover { border-color: var(--cbv-fire); color: var(--cbv-fire); }
.cbv-tts-progress-wrap { margin: 4px 0; }
.cbv-custom-input {
  width: 100%; padding: 10px 12px; border: 1px solid var(--cbv-border);
  background: var(--cbv-surface); border-radius: 2px;
  color: var(--cbv-text); font-family: var(--cbv-mono); font-size: 12px;
  resize: none; outline: none; transition: border-color 0.2s;
}
.cbv-custom-input:focus { border-color: var(--cbv-nova); }

/* ── COMMANDS TAB ── */
.cbv-cmd-list { display: flex; flex-direction: column; gap: 3px; }
.cbv-cmd-row {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 10px; border-radius: 2px;
  border: 1px solid transparent; cursor: none; transition: all 0.12s;
}
.cbv-cmd-row:hover { background: var(--cbv-surface); border-color: var(--cbv-border); }
.cbv-cmd-text { font-family: var(--cbv-mono); font-size: 11px; color: var(--cbv-text2); }
.cbv-cmd-run { font-size: 10px; color: var(--cbv-text3); transition: color 0.15s; }
.cbv-cmd-row:hover .cbv-cmd-run { color: var(--cbv-plasma); }
.cbv-hotkey-list { display: flex; flex-direction: column; gap: 6px; }
.cbv-hk { display: flex; align-items: center; gap: 10px; font-family: var(--cbv-mono); font-size: 11px; color: var(--cbv-text2); }
kbd { padding: 3px 8px; border: 1px solid var(--cbv-border); border-radius: 2px; font-family: var(--cbv-mono); font-size: 9px; color: var(--cbv-plasma); background: var(--cbv-surface); }

/* ── HISTORY TAB ── */
.cbv-history-list { display: flex; flex-direction: column; gap: 6px; }
.cbv-hist-empty { font-family: var(--cbv-mono); font-size: 11px; color: var(--cbv-text3); text-align: center; padding: 20px; }
.cbv-hist-item {
  padding: 10px 12px; border-radius: 2px;
  border: 1px solid var(--cbv-border); background: var(--cbv-surface);
  cursor: none; transition: all 0.15s;
}
.cbv-hist-item:hover { border-color: var(--cbv-plasma); }
.cbv-hist-meta { display: flex; justify-content: space-between; margin-bottom: 5px; }
.cbv-hist-role { font-family: var(--cbv-display); font-size: 8px; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; }
.cbv-hist-role.voice { color: var(--cbv-plasma); }
.cbv-hist-role.ai { color: var(--cbv-nova); }
.cbv-hist-time { font-family: var(--cbv-display); font-size: 8px; color: var(--cbv-text3); letter-spacing: 1px; }
.cbv-hist-text { font-family: var(--cbv-mono); font-size: 11px; color: var(--cbv-text2); line-height: 1.5; }
.cbv-hist-replay { font-family: var(--cbv-display); font-size: 8px; color: var(--cbv-nova); letter-spacing: 1px; cursor: none; margin-top: 5px; opacity: 0; transition: opacity 0.15s; }
.cbv-hist-item:hover .cbv-hist-replay { opacity: 1; }

/* ── SETTINGS TAB ── */
.cbv-wake-status { font-family: var(--cbv-mono); font-size: 10px; color: var(--cbv-text3); padding: 6px 0; }
.cbv-shortcut-key { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-top: 8px; }
.cbv-sk-item { font-family: var(--cbv-mono); font-size: 10px; color: var(--cbv-text2); display: flex; align-items: center; gap: 6px; }
.cbv-sk-badge { font-size: 12px; }

/* ── SPEAKING OVERLAY ── */
.cbv-speak-overlay {
  position: fixed; bottom: 64px; left: 50%; transform: translateX(-50%);
  background: rgba(4,8,18,0.96);
  border: 1px solid rgba(168,85,247,0.3);
  border-radius: 3px; padding: 12px 20px;
  z-index: 200; transition: opacity 0.25s;
  box-shadow: 0 0 30px rgba(168,85,247,0.2);
  display: flex; flex-direction: column; align-items: center; gap: 6px;
}
body.light .cbv-speak-overlay { background: rgba(228,243,249,0.97); }
.cbv-speak-overlay.cbv-hidden { opacity: 0; pointer-events: none; }
.cbv-so-inner { display: flex; flex-direction: column; align-items: center; gap: 6px; }
.cbv-so-label { font-family: var(--cbv-display); font-size: 8px; font-weight: 700; letter-spacing: 3px; color: var(--cbv-nova); text-transform: uppercase; }
.cbv-so-controls { display: flex; gap: 8px; }
.cbv-so-controls button { background: none; border: 1px solid rgba(168,85,247,0.25); color: var(--cbv-nova); padding: 4px 10px; border-radius: 2px; font-size: 12px; cursor: none; transition: all 0.15s; }
.cbv-so-controls button:hover { border-color: var(--cbv-nova); box-shadow: 0 0 8px rgba(168,85,247,0.3); }

/* ── INPUT AREA ADJUSTMENT ── */
.input-zone { padding-bottom: 62px !important; }
`;
  }

  // ═══════════════════════════════════════════
  // FEATURE 5: AUDIO CONTEXT + ANALYSER
  // ═══════════════════════════════════════════
  async function startAudioContext() {
    try {
      S.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      S.analyser = S.audioCtx.createAnalyser();
      S.analyser.fftSize = 256;
      S.analyser.smoothingTimeConstant = 0.8;
    } catch (e) {
      log('AudioContext not available');
    }
  }

  async function connectMicToAnalyser() {
    if (!S.audioCtx || !S.analyser) return;
    try {
      S.mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const src = S.audioCtx.createMediaStreamSource(S.mediaStream);
      src.connect(S.analyser);
      startVisualizer();
    } catch (e) {
      log('Mic access denied');
    }
  }

  function disconnectMic() {
    if (S.mediaStream) {
      S.mediaStream.getTracks().forEach(t => t.stop());
      S.mediaStream = null;
    }
    stopVisualizer();
  }

  // ═══════════════════════════════════════════
  // FEATURE 6: DUAL VISUALIZER (WAVEFORM + SPECTRUM)
  // ═══════════════════════════════════════════
  function startVisualizer() {
    if (!UI.waveCanvas || !S.analyser) return;
    const wCtx = UI.waveCanvas.getContext('2d');
    const sCtx = UI.specCanvas?.getContext('2d');
    const miniCtx = document.getElementById('cbvMiniWave')?.getContext('2d');
    const speakCtx = document.getElementById('cbvSpeakWave')?.getContext('2d');
    const bufLen = S.analyser.frequencyBinCount;
    const timeData = new Uint8Array(bufLen);
    const freqData = new Uint8Array(bufLen);

    function draw() {
      S.animFrame = requestAnimationFrame(draw);
      S.analyser.getByteTimeDomainData(timeData);
      S.analyser.getByteFrequencyData(freqData);

      const W = UI.waveCanvas.width, H = UI.waveCanvas.height;

      // ─ Main waveform ─
      wCtx.clearRect(0, 0, W, H);
      wCtx.strokeStyle = S.isListening ? 'rgba(0,255,224,0.8)' : 'rgba(0,255,224,0.3)';
      wCtx.lineWidth = 1.5;
      wCtx.beginPath();
      const slice = W / bufLen;
      let x = 0;
      for (let i = 0; i < bufLen; i++) {
        const v = timeData[i] / 128.0;
        const y = (v * H) / 2;
        i === 0 ? wCtx.moveTo(x, y) : wCtx.lineTo(x, y);
        x += slice;
      }
      wCtx.stroke();

      // ─ Spectrum ─
      if (sCtx) {
        const SW = UI.specCanvas.width, SH = UI.specCanvas.height;
        sCtx.clearRect(0, 0, SW, SH);
        const bw = SW / CFG.SPECTRUM_BARS;
        for (let i = 0; i < CFG.SPECTRUM_BARS; i++) {
          const val = freqData[i * 2] / 255;
          const h = val * SH;
          const hue = 165 + val * 80;
          sCtx.fillStyle = `hsla(${hue}, 100%, ${50 + val * 30}%, ${0.5 + val * 0.5})`;
          sCtx.fillRect(i * bw + 1, SH - h, bw - 2, h);
        }
      }

      // ─ Mini bar waveform ─
      if (miniCtx) {
        const MW = 80, MH = 28;
        miniCtx.clearRect(0, 0, MW, MH);
        const mbw = MW / 16;
        for (let i = 0; i < 16; i++) {
          const v = (timeData[i * 4] / 128.0 - 1) * MH * 0.4;
          miniCtx.fillStyle = S.isListening ? 'rgba(0,255,224,0.7)' : 'rgba(0,255,224,0.2)';
          const h = Math.max(2, Math.abs(v));
          miniCtx.fillRect(i * mbw + 1, MH / 2 - h / 2, mbw - 2, h);
        }
      }

      // ─ Speaking overlay waveform ─
      if (speakCtx && S.isSpeaking) {
        const PW = 280, PH = 56;
        speakCtx.clearRect(0, 0, PW, PH);
        speakCtx.strokeStyle = 'rgba(168,85,247,0.8)';
        speakCtx.lineWidth = 2;
        speakCtx.beginPath();
        // Synthesize wave when speaking
        for (let i = 0; i < PW; i++) {
          const t = Date.now() / 400;
          const y = PH / 2 + Math.sin(i * 0.05 + t) * (PH * 0.3) * Math.sin(i * 0.02 + t * 0.7);
          i === 0 ? speakCtx.moveTo(i, y) : speakCtx.lineTo(i, y);
        }
        speakCtx.stroke();
      }
    }
    draw();
  }

  function stopVisualizer() {
    if (S.animFrame) cancelAnimationFrame(S.animFrame);
  }

  // ═══════════════════════════════════════════
  // FEATURE 7: CORE SPEECH RECOGNITION
  // ═══════════════════════════════════════════
  function toggleListening() {
    if (S.isListening) {
      stopListening();
    } else {
      startListening();
    }
  }

  function startListening() {
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRec) {
      alert('Speech recognition is not available in your browser. Use Chrome or Edge.');
      return;
    }

    S.recognition = new SpeechRec();
    S.recognition.lang = S.currentLang;
    S.recognition.interimResults = true;
    S.recognition.maxAlternatives = 3;
    S.recognition.continuous = S.settings?.continuous || false;

    S.isListening = true;
    updateRecordingUI(true);
    connectMicToAnalyser();
    setStatus('LISTENING…');

    let finalTranscript = '';

    S.recognition.onresult = (e) => {
      clearSilenceTimer();

      let interim = '';
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const result = e.results[i];
        if (result.isFinal) {
          const text = result[0].transcript;
          finalTranscript += (S.settings?.smartPunct ? injectPunctuation(text, true) : text) + ' ';
          const conf = result[0].confidence;
          updateConfidence(conf);
          log(`Final: "${text}" (${(conf * 100).toFixed(0)}%)`);
        } else {
          interim = result[0].transcript;
        }
      }

      const display = finalTranscript + interim;
      S.lastTranscript = display.trim();
      setTranscript(display.trim());

      // Silence-based auto-send
      if (finalTranscript.trim() && S.autoSend) {
        setSilenceTimer();
      }

      // FEATURE 8: VOICE COMMAND DETECTION
      const lower = display.toLowerCase().trim();
      if (checkVoiceCommand(lower)) {
        finalTranscript = '';
        S.lastTranscript = '';
        setTranscript('Command executed.');
        return;
      }
    };

    S.recognition.onerror = (e) => {
      log('Recognition error: ' + e.error);
      stopListening();
    };

    S.recognition.onend = () => {
      if (S.isListening && S.settings?.continuous) {
        S.recognition.start(); // restart for continuous mode
      } else {
        stopListening();
      }
    };

    S.recognition.start();
  }

  function stopListening() {
    S.isListening = false;
    clearSilenceTimer();
    if (S.recognition) {
      try { S.recognition.stop(); } catch (e) {}
      S.recognition = null;
    }
    disconnectMic();
    updateRecordingUI(false);
    setStatus('STANDBY');
  }

  // ═══════════════════════════════════════════
  // FEATURE 9: SILENCE-BASED AUTO-SEND
  // ═══════════════════════════════════════════
  function setSilenceTimer() {
    clearSilenceTimer();
    S.silenceTimer = setTimeout(() => {
      if (S.lastTranscript.trim() && S.autoSend) {
        setStatus('AUTO-SENDING…');
        _sendTranscript();
      }
    }, CFG.SILENCE_TIMEOUT_MS);
  }

  function clearSilenceTimer() {
    if (S.silenceTimer) {
      clearTimeout(S.silenceTimer);
      S.silenceTimer = null;
    }
  }

  // ═══════════════════════════════════════════
  // FEATURE 10: VOICE COMMAND ROUTING
  // ═══════════════════════════════════════════
  function checkVoiceCommand(text) {
    for (const [cmd, fn] of Object.entries(CFG.VOICE_COMMANDS)) {
      if (text.includes(cmd)) {
        fn();
        log(`Voice command: "${cmd}"`);
        addToHistory('voice_cmd', `Command: ${cmd}`);
        setStatus(`CMD: ${cmd.toUpperCase()}`);
        setTimeout(() => setStatus('STANDBY'), 2000);
        return true;
      }
    }
    return false;
  }

  // ═══════════════════════════════════════════
  // FEATURE 11: SMART PUNCTUATION INJECTION
  // ═══════════════════════════════════════════
  function injectPunctuation(text, isFinal) {
    // Add period if sentence ends without punctuation
    let t = text.trim();
    if (!t) return t;

    // Capitalize first letter
    t = t.charAt(0).toUpperCase() + t.slice(1);

    // Remove duplicate spaces
    t = t.replace(/\s+/g, ' ');

    // Add period at end if no punctuation and looks like sentence
    if (isFinal && !/[.!?;,]$/.test(t) && t.split(' ').length > 2) {
      t += '.';
    }

    // "new line" -> \n
    t = t.replace(/\bnew line\b/gi, '\n');
    t = t.replace(/\bcomma\b/gi, ',');
    t = t.replace(/\bperiod\b/gi, '.');
    t = t.replace(/\bquestion mark\b/gi, '?');
    t = t.replace(/\bexclamation\b/gi, '!');
    t = t.replace(/\bcolon\b/gi, ':');
    t = t.replace(/\bopen paren\b/gi, '(');
    t = t.replace(/\bclose paren\b/gi, ')');
    t = t.replace(/\bopen bracket\b/gi, '[');
    t = t.replace(/\bclose bracket\b/gi, ']');
    t = t.replace(/\bopen brace\b/gi, '{');
    t = t.replace(/\bclose brace\b/gi, '}');

    return t;
  }

  // ═══════════════════════════════════════════
  // FEATURE 12: EMOTION-ADAPTIVE TTS
  // ═══════════════════════════════════════════
  function detectTone(text) {
    // Detect the emotional tone of the AI response to adapt voice
    const lower = text.toLowerCase();
    if (/error|bug|wrong|incorrect|fail|problem|issue/.test(lower)) return 'strict';
    if (/congratulation|excellent|perfect|great job|well done|amazing/.test(lower)) return 'excited';
    if (/take your time|don't worry|step by step|let's explore|imagine/.test(lower)) return 'calm';
    return S.ttsPersonality; // default
  }

  function speakText(rawText, forcePersonality) {
    if (!rawText) return;
    window.speechSynthesis.cancel();

    // FEATURE: Filter code blocks from speech
    let text = rawText;
    if (S.settings?.codeFilter !== false) {
      text = filterCodeForSpeech(rawText);
    }
    if (!text.trim()) {
      text = 'Code response ready. Use the run button to execute.';
    }

    const persona = forcePersonality || detectTone(text);
    const voiceCfg = CFG.TTS_VOICES[persona] || CFG.TTS_VOICES.mentor;
    const utter = new SpeechSynthesisUtterance(text);
    utter.lang = S.currentLang;
    utter.pitch = voiceCfg.pitch;
    utter.rate = voiceCfg.rate;
    utter.volume = voiceCfg.volume;

    // Pick best available voice
    const voices = window.speechSynthesis.getVoices();
    const langVoices = voices.filter(v => v.lang.startsWith(S.currentLang.split('-')[0]));
    if (langVoices.length) utter.voice = langVoices[0];

    S.isSpeaking = true;
    showSpeakOverlay(text);

    // Track TTS progress
    let wordCount = text.split(' ').length;
    let wordIndex = 0;
    utter.onboundary = (e) => {
      if (e.name === 'word') {
        wordIndex++;
        const pct = Math.round((wordIndex / wordCount) * 100);
        updateTTSProgress(pct);
      }
    };

    utter.onend = () => {
      S.isSpeaking = false;
      hideSpeakOverlay();
      updateTTSProgress(100);
      setTimeout(() => updateTTSProgress(0), 1000);
    };

    utter.onerror = () => {
      S.isSpeaking = false;
      hideSpeakOverlay();
    };

    window.speechSynthesis.speak(utter);
    addToHistory('ai', text.slice(0, 100) + (text.length > 100 ? '…' : ''));
  }

  // FEATURE: Smart code filtering for TTS
  function filterCodeForSpeech(text) {
    // Remove code blocks
    let filtered = text.replace(/```[\s\S]*?```/g, '');
    // Remove inline code
    filtered = filtered.replace(/`[^`]+`/g, (match) => {
      // Keep short inline code if it looks like a word
      const inner = match.replace(/`/g, '');
      return inner.length < 20 && !/[{}();]/.test(inner) ? inner : '';
    });
    // Remove markdown symbols
    filtered = filtered.replace(/[*#_~]/g, '');
    // Remove URLs
    filtered = filtered.replace(/https?:\/\/\S+/g, 'the linked URL');
    // Clean extra whitespace
    filtered = filtered.replace(/\n{3,}/g, '\n\n').trim();
    return filtered;
  }

  // ═══════════════════════════════════════════
  // FEATURE 13: WAKE WORD LISTENER
  // ═══════════════════════════════════════════
  function startWakeWordListener() {
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRec || S.isWakeListening) return;

    S.wakeRecognition = new SpeechRec();
    S.wakeRecognition.lang = 'en-US';
    S.wakeRecognition.interimResults = true;
    S.wakeRecognition.continuous = true;
    S.isWakeListening = true;

    S.wakeRecognition.onresult = (e) => {
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const t = e.results[i][0].transcript.toLowerCase();
        if (t.includes(CFG.WAKE_WORD)) {
          log('Wake word detected!');
          setWakeStatus(true);
          if (!S.isListening) {
            startListening();
          }
        }
      }
    };

    S.wakeRecognition.onend = () => {
      // Auto-restart wake word listener
      if (S.wakeEnabled) {
        setTimeout(() => startWakeWordListener(), 500);
      }
    };

    S.wakeRecognition.onerror = () => {
      S.isWakeListening = false;
      setTimeout(() => { if (S.wakeEnabled) startWakeWordListener(); }, 2000);
    };

    try {
      S.wakeRecognition.start();
      log('Wake word listener started');
    } catch (e) {
      S.isWakeListening = false;
    }
  }

  function stopWakeWordListener() {
    S.wakeEnabled = false;
    S.isWakeListening = false;
    if (S.wakeRecognition) {
      try { S.wakeRecognition.stop(); } catch (e) {}
      S.wakeRecognition = null;
    }
    setWakeStatus(false);
    log('Wake word listener stopped');
  }

  // ═══════════════════════════════════════════
  // UI HELPERS
  // ═══════════════════════════════════════════
  function setStatus(text) {
    if (UI.status) UI.status.textContent = text;
  }

  function setTranscript(text) {
    if (UI.transcript) {
      UI.transcript.textContent = text || 'Waiting for voice input…';
      UI.transcript.classList.toggle('active', !!text && S.isListening);
    }
    // Also inject into main message textarea
    const msgArea = document.getElementById('message');
    if (msgArea && text) {
      msgArea.value = text;
      msgArea.dispatchEvent(new Event('input'));
    }
  }

  function updateConfidence(conf) {
    const pct = Math.round(conf * 100);
    if (UI.confidence) UI.confidence.textContent = pct + '%';
    if (UI.confidenceFill) {
      UI.confidenceFill.style.width = pct + '%';
      UI.confidenceFill.classList.toggle('high', pct >= 60);
    }
  }

  function updateRecordingUI(recording) {
    const bigMic = document.getElementById('cbvBigMic');
    const bigLabel = document.getElementById('cbvBigMicLabel');
    if (bigMic) bigMic.classList.toggle('recording', recording);
    if (bigLabel) bigLabel.textContent = recording ? 'LISTENING…' : 'PRESS TO SPEAK';
    if (UI.barMicBtn) UI.barMicBtn.classList.toggle('cbv-recording', recording);
  }

  function updateTTSProgress(pct) {
    const fill = document.getElementById('cbvTTSFill');
    const pctEl = document.getElementById('cbvTTSPct');
    if (fill) fill.style.width = pct + '%';
    if (pctEl) pctEl.textContent = pct + '%';
  }

  function showSpeakOverlay(text) {
    if (UI.speakOverlay) {
      UI.speakOverlay.classList.remove('cbv-hidden');
      const label = document.getElementById('cbvSoLabel');
      if (label) label.textContent = 'AI SPEAKING: ' + text.slice(0, 40) + '…';
    }
  }

  function hideSpeakOverlay() {
    if (UI.speakOverlay) UI.speakOverlay.classList.add('cbv-hidden');
  }

  function setWakeStatus(active) {
    if (UI.barWake) UI.barWake.classList.toggle('active', active);
    const statusEl = document.getElementById('cbvWakeStatus');
    if (statusEl) {
      statusEl.textContent = active
        ? '✓ Wake word detected — starting recording'
        : (S.wakeEnabled ? '◌ Listening for "Hey CodeBuddy"…' : 'Wake word detection is OFF');
    }
  }

  function addToHistory(role, text) {
    S.voiceHistory.push({ role, text, ts: new Date() });
    if (S.voiceHistory.length > 50) S.voiceHistory.shift();
    renderHistory();
  }

  function renderHistory() {
    const list = document.getElementById('cbvHistoryList');
    if (!list) return;
    if (!S.voiceHistory.length) {
      list.innerHTML = '<div class="cbv-hist-empty">No voice interactions yet.</div>';
      return;
    }
    list.innerHTML = S.voiceHistory.slice().reverse().map((h, i) => `
      <div class="cbv-hist-item">
        <div class="cbv-hist-meta">
          <span class="cbv-hist-role ${h.role === 'voice' || h.role === 'voice_cmd' ? 'voice' : 'ai'}">
            ${h.role === 'voice' ? '🎤 YOU' : h.role === 'voice_cmd' ? '⚡ CMD' : '🤖 AI'}
          </span>
          <span class="cbv-hist-time">${h.ts.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
        </div>
        <div class="cbv-hist-text">${h.text}</div>
        ${h.role !== 'voice_cmd' ? `<div class="cbv-hist-replay" onclick="CBVoice.replayHistory(${S.voiceHistory.length - 1 - i})">▶ REPLAY SPEECH</div>` : ''}
      </div>`).join('');
  }

  // ═══════════════════════════════════════════
  // INTERNAL ACTIONS
  // ═══════════════════════════════════════════
  function _sendTranscript() {
    const text = S.lastTranscript.trim();
    if (!text) return;
    addToHistory('voice', text);
    stopListening();
    // Trigger main chat send
    if (typeof sendMessage === 'function') {
      sendMessage();
    } else {
      document.getElementById('sendBtn')?.click();
    }
    S.lastTranscript = '';
  }

  function _clearTranscript() {
    S.lastTranscript = '';
    setTranscript('');
    const msgArea = document.getElementById('message');
    if (msgArea) { msgArea.value = ''; msgArea.dispatchEvent(new Event('input')); }
  }

  function _copyLastResponse() {
    const lastBot = [...document.querySelectorAll('.msg-row.bot .bubble-content')].pop();
    if (lastBot) {
      navigator.clipboard.writeText(lastBot.innerText || '');
      setStatus('COPIED!');
      setTimeout(() => setStatus('STANDBY'), 2000);
    }
  }

  function _clearScreen() {
    const chatBox = document.getElementById('chatBox');
    if (chatBox) chatBox.innerHTML = '';
  }

  function _setMode(mode) {
    const sel = document.getElementById('mode');
    if (sel) {
      sel.value = mode;
      sel.dispatchEvent(new Event('change'));
      setStatus('MODE: ' + mode.toUpperCase());
      setTimeout(() => setStatus('STANDBY'), 2000);
    }
  }

  function _runCommand(cmd) {
    const fn = CFG.VOICE_COMMANDS[cmd];
    if (fn) fn();
  }

  // ═══════════════════════════════════════════
  // SETTINGS STATE
  // ═══════════════════════════════════════════
  S.settings = {
    codeFilter: true,
    smartPunct: true,
    continuous: false,
    autoRead: false,
  };

  function _toggleAutoSend(el) {
    S.autoSend = !el.classList.contains('active');
    el.classList.toggle('active');
  }

  function _toggleCodeDict(el) {
    S.codeDictation = !el.classList.contains('active');
    el.classList.toggle('active');
  }

  function _toggleAutoRead(el) {
    S.settings.autoRead = !el.classList.contains('active');
    el.classList.toggle('active');
  }

  function _toggleSwitch(el, key) {
    S.settings[key] = !el.classList.contains('active');
    el.classList.toggle('active');
  }

  // ═══════════════════════════════════════════
  // EVENTS
  // ═══════════════════════════════════════════
  function bindEvents() {
    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
      // Skip if typing in textarea/input
      if (['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) {
        if (e.key === 'Escape' && S.isListening) {
          stopListening();
          _clearTranscript();
        }
        return;
      }

      if (e.key === 'v' || e.key === 'V') {
        e.preventDefault();
        toggleListening();
      } else if (e.key === 'r' || e.key === 'R') {
        e.preventDefault();
        speakLast();
      } else if (e.key === ' ' && S.isSpeaking) {
        e.preventDefault();
        togglePause();
      } else if (e.key === 'Escape') {
        stopSpeaking();
        stopListening();
      }
    });

    // Patch the main sendMessage to auto-read responses when enabled
    const origSend = window.sendMessage;
    if (typeof origSend === 'function') {
      window.sendMessage = async function (...args) {
        const result = await origSend.apply(this, args);
        // After AI response, auto-read if enabled
        if (S.settings.autoRead) {
          setTimeout(() => speakLast(), 500);
        }
        return result;
      };
    }
  }

  // ═══════════════════════════════════════════
  // TAB SWITCHING
  // ═══════════════════════════════════════════
  function _switchTab(name, el) {
    UI.panel.querySelectorAll('.cbv-tab').forEach(t => t.classList.remove('active'));
    UI.panel.querySelectorAll('.cbv-tabpanel').forEach(p => p.classList.remove('active'));
    el.classList.add('active');
    document.getElementById(`cbvTab-${name}`)?.classList.add('active');
  }

  // ═══════════════════════════════════════════
  // PUBLIC API
  // ═══════════════════════════════════════════
  function togglePanel() {
    if (!S.uiMounted) mountUI();
    UI.panel.classList.toggle('cbv-hidden');
  }

  function setLang(code, chipEl) {
    S.currentLang = code;
    if (S.recognition) S.recognition.lang = code;
    // Update bar label
    const lang = CFG.SUPPORTED_LANGS.find(l => l.code === code);
    if (UI.barLangLabel) UI.barLangLabel.textContent = lang?.label || 'EN';
    // Update chips
    UI.panel.querySelectorAll('.cbv-lang-chip').forEach(c => c.classList.remove('active'));
    if (chipEl) chipEl.classList.add('active');
  }

  function setPersonality(persona, el) {
    S.ttsPersonality = persona;
    UI.panel.querySelectorAll('.cbv-persona').forEach(p => p.classList.remove('active'));
    if (el) el.classList.add('active');
  }

  function speakLast() {
    // Find last AI message
    const bots = document.querySelectorAll('.msg-row.bot .bubble-content');
    if (!bots.length) return;
    const last = bots[bots.length - 1];
    speakText(last.innerText || last.textContent);
  }

  function speakCustom() {
    const input = document.getElementById('cbvCustomSpeak');
    if (input?.value.trim()) speakText(input.value.trim());
  }

  function replayHistory(index) {
    const item = S.voiceHistory[index];
    if (item && (item.role === 'ai')) {
      speakText(item.text);
    }
  }

  function stopSpeaking() {
    window.speechSynthesis.cancel();
    S.isSpeaking = false;
    hideSpeakOverlay();
    updateTTSProgress(0);
  }

  function pauseSpeaking() {
    if (window.speechSynthesis.speaking && !window.speechSynthesis.paused) {
      window.speechSynthesis.pause();
    }
  }

  function resumeSpeaking() {
    if (window.speechSynthesis.paused) {
      window.speechSynthesis.resume();
    }
  }

  function togglePause() {
    if (window.speechSynthesis.paused) resumeSpeaking();
    else pauseSpeaking();
  }

  function toggleWakeWord(el) {
    if (S.wakeEnabled) {
      S.wakeEnabled = false;
      el.classList.remove('active');
      stopWakeWordListener();
      const ws = document.getElementById('cbvWakeStatus');
      if (ws) ws.textContent = 'Wake word detection is OFF';
    } else {
      S.wakeEnabled = true;
      el.classList.add('active');
      startWakeWordListener();
      const ws = document.getElementById('cbvWakeStatus');
      if (ws) ws.textContent = '◌ Listening for "Hey CodeBuddy"…';
    }
  }

  // ═══════════════════════════════════════════
  // UTILITY
  // ═══════════════════════════════════════════
  function log(msg) {
    console.log(`[CBVoice] ${msg}`);
  }

  // ═══════════════════════════════════════════
  // AUTO-INIT
  // ═══════════════════════════════════════════
  function init() {
    mountUI();

    // Replace the existing simple voice cluster in topbar
    const existingCluster = document.querySelector('.voice-cluster');
    if (existingCluster) {
      existingCluster.style.display = 'none'; // Hide old simple buttons
    }

    // Also intercept the old speakText, startVoice etc
    window.speakText = speakText;
    window.startVoice = toggleListening;
    window.pauseSpeech = pauseSpeaking;
    window.resumeSpeech = resumeSpeaking;
    window.stopSpeech = stopSpeaking;

    log('Ready. Press V to start recording, R to read last response.');
  }

  // Wait for DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    setTimeout(init, 100);
  }

  // PUBLIC
  return {
    toggleListening,
    startListening,
    stopListening,
    speakText,
    speakLast,
    speakCustom,
    stopSpeaking,
    pauseSpeaking,
    resumeSpeaking,
    togglePause,
    togglePanel,
    toggleWakeWord,
    setLang,
    setPersonality,
    replayHistory,
    _switchTab,
    _sendTranscript,
    _clearTranscript,
    _toggleAutoSend,
    _toggleCodeDict,
    _toggleAutoRead,
    _toggleSwitch,
    _runCommand,
  };

})();