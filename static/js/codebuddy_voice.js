/**
 * ╔══════════════════════════════════════════════════════════════════╗
 * ║  CODEBUDDY NEURAL VOICE ENGINE v4.0                             ║
 * ║  World's First Programming-Focused Multilingual Voice AI        ║
 * ║  UPGRADED: +10 Indic langs · Memory UI · Leaderboard · PWA     ║
 * ╚══════════════════════════════════════════════════════════════════╝
 */

(function () {
  'use strict';

  /* ═══════════════════════════════════════
     CORE STATE
  ═══════════════════════════════════════ */
  const STATE = {
    isOpen: false,
    isListening: false,
    isSpeaking: false,
    isPaused: false,
    currentLang: 'en-US',
    wakeWordActive: false,
    uploadedFile: null,
    uploadedFileType: null,
    recognition: null,
    synth: window.speechSynthesis,
    voices: [],
    currentUtterance: null,
    transcript: '',
    interimTranscript: '',
    lastCommand: '',
    volume: 0.85,
    rate: 0.95,
    pitch: 1.05,
    autoSpeak: false,
    codeContext: true,
    initialized: false,
    onSpeakEnd: null,   // fired when audio finishes — used by PLAY button to reset UI
    onSpeakStart: null, // fired when audio starts — used by PLAY button to show STOP
  };

  /* ═══════════════════════════════════════════════════════
     CHANGE 3: LANGUAGES — 10 Indic + World Languages
  ═══════════════════════════════════════════════════════ */
  const LANGS = {
    'en-US': {
      name: 'English', short: 'EN', flag: '🇺🇸',
      greet: 'CodeBuddy Neural Voice ready. Say "Hey Buddy" to activate.',
      listening: 'Listening...',
      processing: 'Processing your code query...',
      error: 'Voice recognition error. Please try again.',
      noSupport: 'Speech recognition not supported in this browser.',
      commands: {
        'run code': () => triggerRun(),
        'execute': () => triggerRun(),
        'debug this': () => triggerDebug(),
        'explain code': () => triggerExplain(),
        'optimize': () => triggerOptimize(),
        'clear chat': () => clearConversation(),
        'new session': () => newSession(),
        'stop speaking': () => CBVoice.stop(),
        'pause': () => CBVoice.pause(),
        'resume': () => CBVoice.resume(),
        'hey buddy': () => activateWakeWord(),
        'show memory': () => CBVoice.showMemory(),
        'open leaderboard': () => window.open('/leaderboard', '_blank'),
        'share my streak': () => CBVoice.shareStreak(),
      }
    },
    'ta-IN': {
      name: 'Tamil', short: 'TA', flag: '🇮🇳',
      greet: 'கோட்பட்டி தயார். "ஹே பட்டி" என்று சொல்லுங்கள்.',
      listening: 'கேட்கிறேன்...',
      processing: 'செயலாக்குகிறேன்...',
      error: 'பிழை. மீண்டும் முயற்சிக்கவும்.',
      noSupport: 'இந்த உலாவியில் குரல் ஆதரவு இல்லை.',
      commands: {
        'கோட் இயக்கு': () => triggerRun(),
        'பிழை திருத்து': () => triggerDebug(),
        'விளக்கு': () => triggerExplain(),
        'நிறுத்து': () => CBVoice.stop(),
        'ஹே பட்டி': () => activateWakeWord(),
      }
    },
    'ta-en': {
      name: 'Tanglish', short: 'TA-EN', flag: '🇮🇳',
      greet: 'Tanglish mode ready. "Hey Buddy" nu sollunga.',
      listening: 'Kekuren...',
      processing: 'Process panren...',
      error: 'Voice error. Thirumba try pannunga.',
      noSupport: 'Not supported in this browser.',
      commands: {
        'run code': () => triggerRun(),
        'debug this': () => triggerDebug(),
        'explain code': () => triggerExplain(),
        'stop speaking': () => CBVoice.stop(),
        'hey buddy': () => activateWakeWord(),
      },
      textOutputLang: 'en-US',
      voiceOutputLang: 'ta-IN'
    },
    'hi-IN': {
      name: 'हिन्दी', short: 'HI', flag: '🇮🇳',
      greet: 'कोडबडी न्यूरल वॉयस तैयार है। "हे बडी" कहें।',
      listening: 'सुन रहा हूँ...',
      processing: 'आपकी कोड क्वेरी प्रोसेस हो रही है...',
      error: 'वॉयस पहचान में त्रुटि। कृपया पुनः प्रयास करें।',
      noSupport: 'इस ब्राउज़र में वॉयस पहचान समर्थित नहीं है।',
      commands: {
        'कोड चलाओ': () => triggerRun(),
        'डिबग करो': () => triggerDebug(),
        'समझाओ': () => triggerExplain(),
        'रोको': () => CBVoice.stop(),
        'हे बडी': () => activateWakeWord(),
      }
    },
    // ── NEW INDIC LANGUAGES ──
    'te-IN': {
      name: 'Telugu', short: 'TE', flag: '🇮🇳',
      greet: 'కోడ్‌బడ్డీ సిద్ధంగా ఉంది. "హే బడ్డీ" అని చెప్పండి.',
      listening: 'వింటున్నాను...',
      processing: 'ప్రాసెస్ చేస్తున్నాను...',
      error: 'వాయిస్ లోపం. దయచేసి మళ్ళీ ప్రయత్నించండి.',
      noSupport: 'ఈ బ్రౌజర్‌లో వాయిస్ మద్దతు లేదు.',
      commands: {
        'కోడ్ రన్ చేయి': () => triggerRun(),
        'డీబగ్ చేయి': () => triggerDebug(),
        'వివరించు': () => triggerExplain(),
        'ఆపు': () => CBVoice.stop(),
        'హే బడ్డీ': () => activateWakeWord(),
      }
    },
    'kn-IN': {
      name: 'Kannada', short: 'KN', flag: '🇮🇳',
      greet: 'ಕೋಡ್‌ಬಡ್ಡಿ ಸಿದ್ಧವಾಗಿದೆ. "ಹೇ ಬಡ್ಡಿ" ಎಂದು ಹೇಳಿ.',
      listening: 'ಕೇಳುತ್ತಿದ್ದೇನೆ...',
      processing: 'ಪ್ರಕ್ರಿಯೆಗೊಳಿಸುತ್ತಿದ್ದೇನೆ...',
      error: 'ಧ್ವನಿ ದೋಷ. ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.',
      noSupport: 'ಈ ಬ್ರೌಸರ್‌ನಲ್ಲಿ ಧ್ವನಿ ಬೆಂಬಲ ಇಲ್ಲ.',
      commands: {
        'ಕೋಡ್ ರನ್ ಮಾಡು': () => triggerRun(),
        'ಡೀಬಗ್ ಮಾಡು': () => triggerDebug(),
        'ವಿವರಿಸು': () => triggerExplain(),
        'ನಿಲ್ಲಿಸು': () => CBVoice.stop(),
        'ಹೇ ಬಡ್ಡಿ': () => activateWakeWord(),
      }
    },
    'ml-IN': {
      name: 'Malayalam', short: 'ML', flag: '🇮🇳',
      greet: 'കോഡ്ബഡ്ഡി തയ്യാർ. "ഹേ ബഡ്ഡി" എന്ന് പറയൂ.',
      listening: 'കേൾക്കുന്നു...',
      processing: 'പ്രോസസ്സ് ചെയ്യുന്നു...',
      error: 'വോയ്‌സ് പിശക്. വീണ്ടും ശ്രമിക്കൂ.',
      noSupport: 'ഈ ബ്രൗസറിൽ വോയ്‌സ് പിന്തുണ ഇല്ല.',
      commands: {
        'കോഡ് റൺ ചെയ്യൂ': () => triggerRun(),
        'ഡീബഗ് ചെയ്യൂ': () => triggerDebug(),
        'വിശദീകരിക്കൂ': () => triggerExplain(),
        'നിർത്തൂ': () => CBVoice.stop(),
        'ഹേ ബഡ്ഡി': () => activateWakeWord(),
      }
    },
    'bn-IN': {
      name: 'Bengali', short: 'BN', flag: '🇮🇳',
      greet: 'কোডবাডি প্রস্তুত। "হে বাডি" বলুন।',
      listening: 'শুনছি...',
      processing: 'প্রক্রিয়া করছি...',
      error: 'ভয়েস ত্রুটি। আবার চেষ্টা করুন।',
      noSupport: 'এই ব্রাউজারে ভয়েস সমর্থন নেই।',
      commands: {
        'কোড রান করো': () => triggerRun(),
        'ডিবাগ করো': () => triggerDebug(),
        'ব্যাখ্যা করো': () => triggerExplain(),
        'থামো': () => CBVoice.stop(),
        'হে বাডি': () => activateWakeWord(),
      }
    },
    'mr-IN': {
      name: 'Marathi', short: 'MR', flag: '🇮🇳',
      greet: 'कोडबडी तयार आहे. "हे बडी" म्हणा.',
      listening: 'ऐकत आहे...',
      processing: 'प्रक्रिया करत आहे...',
      error: 'आवाज त्रुटी. पुन्हा प्रयत्न करा.',
      noSupport: 'या ब्राउझरमध्ये आवाज समर्थन नाही.',
      commands: {
        'कोड चालवा': () => triggerRun(),
        'डीबग करा': () => triggerDebug(),
        'समजावून सांगा': () => triggerExplain(),
        'थांबा': () => CBVoice.stop(),
        'हे बडी': () => activateWakeWord(),
      }
    },
  };

  /* ═══════════════════════════════════════
     CODE SYMBOL VOICE DICTATION MAP
  ═══════════════════════════════════════ */
  const CODE_SYMBOLS = {
    'arrow function': ' => ',
    'arrow': ' => ',
    'equals equals': ' === ',
    'not equals': ' !== ',
    'greater than or equal': ' >= ',
    'less than or equal': ' <= ',
    'double pipe': ' || ',
    'double ampersand': ' && ',
    'spread operator': '...',
    'optional chain': '?.',
    'nullish coalescing': ' ?? ',
    'plus equals': ' += ',
    'minus equals': ' -= ',
    'times equals': ' *= ',
    'divide equals': ' /= ',
    'open bracket': '[',
    'close bracket': ']',
    'open brace': '{',
    'close brace': '}',
    'open paren': '(',
    'close paren': ')',
    'open angle': '<',
    'close angle': '>',
    'new line': '\n',
    'tab': '\t',
    'semicolon': ';',
    'colon': ':',
    'double colon': '::',
    'dot': '.',
    'comma': ',',
    'hash': '#',
    'at sign': '@',
    'dollar sign': '$',
    'underscore': '_',
    'backtick': '`',
    'double quote': '"',
    'single quote': "'",
    'console log': 'console.log()',
    'console error': 'console.error()',
    'return statement': 'return ',
    'const variable': 'const ',
    'let variable': 'let ',
    'var variable': 'var ',
    'function definition': 'function ',
    'async function': 'async function ',
    'if statement': 'if () {\n\n}',
    'for loop': 'for (let i = 0; i < ; i++) {\n\n}',
    'while loop': 'while () {\n\n}',
    'try catch': 'try {\n\n} catch (e) {\n\n}',
    'import from': "import  from ''",
    'export default': 'export default ',
    'class definition': 'class  {\n  constructor() {\n\n  }\n}',
    'lambda': ' => ',
    'list comprehension': '[x for x in ]',
    'print statement': 'print()',
    'def function': 'def ():\n    ',
    'self dot': 'self.',
  };

  // CODE_SYMBOLS_WITH_DESC: [symbol, description] for the SYMBOLS tab UI
  const CODE_SYMBOLS_WITH_DESC = {
    'arrow function':        [' => ',  'Arrow function — shorthand for function()'],
    'arrow':                 [' => ',  'Same as arrow function'],
    'equals equals':         [' === ', 'Strict equality — checks value AND type'],
    'not equals':            [' !== ', 'Strict inequality — true if different value or type'],
    'greater than or equal': [' >= ',  'Comparison — true if left is bigger or same'],
    'less than or equal':    [' <= ',  'Comparison — true if left is smaller or same'],
    'double pipe':           [' || ',  'Logical OR — true if either side is true'],
    'double ampersand':      [' && ',  'Logical AND — true only if both sides are true'],
    'spread operator':       ['...',   'Spread — expands array/object into individual items'],
    'optional chain':        ['?.',    'Optional chain — safely access property, null if missing'],
    'nullish coalescing':    [' ?? ',  'Nullish — use right side only if left is null/undefined'],
    'plus equals':           [' += ',  'Add and assign — x += 3 means x = x + 3'],
    'minus equals':          [' -= ',  'Subtract and assign — x -= 3 means x = x - 3'],
    'times equals':          [' *= ',  'Multiply and assign — x *= 2 means x = x * 2'],
    'divide equals':         [' /= ',  'Divide and assign — x /= 2 means x = x / 2'],
    'open bracket':          ['[',     'Start of array or index access'],
    'close bracket':         [']',     'End of array or index access'],
    'open brace':            ['{',     'Start of object, block, or function body'],
    'close brace':           ['}',     'End of object, block, or function body'],
    'open paren':            ['(',     'Start of function call or expression group'],
    'close paren':           [')',     'End of function call or expression group'],
    'semicolon':             [';',     'Statement terminator — ends a line of code'],
    'colon':                 [':',     'Key-value separator in objects'],
    'dot':                   ['.',     'Property accessor — obj.property'],
    'comma':                 [',',     'Separator — between items in list, function args'],
    'hash':                  ['#',     'Private class field prefix, or CSS ID selector'],
    'at sign':               ['@',     'Decorator syntax — @decorator before class/method'],
    'dollar sign':           ['$',     'Variable prefix in template literals: ${var}'],
    'backtick':              ['`',     'Template literal — allows ${expressions} inside'],
    'double quote':          ['"',     'String delimiter'],
    'single quote':          ["'",     'String delimiter'],
    'console log':           ['console.log()', 'Print to browser DevTools console'],
    'console error':         ['console.error()', 'Print error (red) to console'],
    'return statement':      ['return ', 'Return a value from a function'],
    'const variable':        ['const ', 'Declare constant — cannot be reassigned'],
    'let variable':          ['let ',   'Declare block-scoped variable — can be reassigned'],
    'async function':        ['async function ', 'Declare async function — can use await inside'],
  };



  const PROG_LANGS = [
    'python', 'javascript', 'typescript', 'java', 'c', 'cpp', 'c#', 'csharp',
    'go', 'golang', 'rust', 'ruby', 'php', 'swift', 'kotlin', 'scala', 'r',
    'matlab', 'julia', 'haskell', 'erlang', 'elixir', 'clojure', 'lisp',
    'prolog', 'fortran', 'cobol', 'pascal', 'delphi', 'ada', 'groovy',
    'lua', 'perl', 'bash', 'shell', 'powershell', 'sql', 'mysql', 'postgresql',
    'mongodb', 'graphql', 'html', 'css', 'scss', 'sass', 'xml', 'json', 'yaml',
    'toml', 'markdown', 'dart', 'flutter', 'react', 'vue', 'angular', 'svelte',
    'assembly', 'asm', 'vhdl', 'verilog', 'solidity', 'webassembly', 'wasm',
    'brainfuck', 'forth', 'scheme', 'racket', 'ocaml', 'fsharp', 'nim', 'zig',
    'crystal', 'd', 'hack', 'apex', 'vba', 'autohotkey', 'tcl', 'rexx',
    'abap', 'pl/sql', 't-sql', 'nosql', 'redis', 'docker', 'kubernetes',
    'terraform', 'ansible', 'puppet', 'chef', 'nginx', 'apache',
  ];

  function injectStyles() {
    if (document.getElementById('cbv-styles')) return;
    const s = document.createElement('style');
    s.id = 'cbv-styles';
    s.textContent = `
#cbVoiceBar { position: fixed; bottom: 0; left: 280px; right: 0; height: 56px; background: linear-gradient(180deg, rgba(2,5,14,0.96) 0%, rgba(4,8,20,0.99) 100%); backdrop-filter: blur(48px) saturate(200%); border-top: none; display: flex; align-items: center; padding: 0 20px; gap: 10px; z-index: 50; transition: left 0.4s cubic-bezier(0.4,0,0.2,1); overflow: hidden; }
body:has(.sidebar.collapsed) #cbVoiceBar { left: 60px; }
#cbVoiceBar::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px; background: linear-gradient(90deg, transparent 0%, rgba(0,255,224,0.8) 20%, rgba(168,85,247,0.8) 50%, rgba(0,255,224,0.8) 80%, transparent 100%); background-size: 200% 100%; animation: cbBarScan 4s linear infinite; filter: blur(0.3px); }
#cbVoiceBar::after { content: ''; position: absolute; inset: 0; background: repeating-linear-gradient(0deg, transparent, transparent 3px, rgba(0,255,224,0.008) 3px, rgba(0,255,224,0.008) 4px); pointer-events: none; }
@keyframes cbBarScan { 0%{background-position:0%} 100%{background-position:200%} }
#cbMicBtn { width: 40px; height: 40px; border-radius: 50%; border: 1.5px solid rgba(0,255,224,0.4); background: radial-gradient(circle at 40% 35%, rgba(0,255,224,0.18), rgba(0,255,224,0.04) 70%); color: #00ffe0; font-size: 16px; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: all 0.25s; flex-shrink: 0; position: relative; box-shadow: 0 0 12px rgba(0,255,224,0.15), inset 0 1px 0 rgba(0,255,224,0.15); }
#cbMicBtn:hover { border-color: #00ffe0; box-shadow: 0 0 24px rgba(0,255,224,0.5), 0 0 48px rgba(0,255,224,0.15), inset 0 0 12px rgba(0,255,224,0.1); background: radial-gradient(circle at 40% 35%, rgba(0,255,224,0.28), rgba(0,255,224,0.08) 70%); }
#cbMicBtn.active { border-color: #ff6b2b; background: radial-gradient(circle at 40% 35%, rgba(255,107,43,0.25), rgba(255,107,43,0.06) 70%); color: #ff6b2b; animation: cbMicPulse 1s ease infinite; box-shadow: 0 0 24px rgba(255,107,43,0.5), 0 0 48px rgba(255,107,43,0.15); }
@keyframes cbMicPulse { 0%,100%{transform:scale(1);box-shadow:0 0 24px rgba(255,107,43,0.5)} 50%{transform:scale(1.08);box-shadow:0 0 36px rgba(255,107,43,0.7)} }
#cbMicBtn.wake::after { content: ''; position: absolute; inset: -7px; border-radius: 50%; border: 1.5px solid rgba(0,255,224,0.4); animation: cbWakeRing 1.5s ease infinite; }
@keyframes cbWakeRing { 0%{transform:scale(1);opacity:0.9} 100%{transform:scale(1.6);opacity:0} }
#cbWaveform { display: flex; align-items: center; gap: 2.5px; height: 36px; flex-shrink: 0; padding: 0 4px; }
.cbWave { width: 2.5px; border-radius: 2px; background: linear-gradient(180deg, #00ffe0 0%, rgba(168,85,247,0.6) 100%); transition: height 0.08s ease; opacity: 0.5; min-height: 3px; }
#cbVoiceBar.listening .cbWave { animation: cbWaveAnim 0.6s ease infinite; opacity: 0.9; }
#cbVoiceBar.speaking .cbWave { animation: cbWaveSpeak 0.8s ease infinite; opacity: 0.8; }
@keyframes cbWaveAnim { 0%,100% { height: 3px; opacity: 0.3; } 50% { height: 30px; opacity: 1; } }
@keyframes cbWaveSpeak { 0%,100% { height: 5px; opacity: 0.4; } 50% { height: 22px; opacity: 0.9; } }
.cbWave:nth-child(1){animation-delay:0s} .cbWave:nth-child(2){animation-delay:0.07s} .cbWave:nth-child(3){animation-delay:0.14s} .cbWave:nth-child(4){animation-delay:0.21s} .cbWave:nth-child(5){animation-delay:0.28s} .cbWave:nth-child(6){animation-delay:0.35s} .cbWave:nth-child(7){animation-delay:0.42s} .cbWave:nth-child(8){animation-delay:0.35s} .cbWave:nth-child(9){animation-delay:0.28s} .cbWave:nth-child(10){animation-delay:0.21s} .cbWave:nth-child(11){animation-delay:0.14s} .cbWave:nth-child(12){animation-delay:0.07s}
#cbTranscript { flex: 1; font-family: 'IBM Plex Mono', monospace; font-size: 11px; color: rgba(226,244,255,0.4); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; padding: 0 4px; letter-spacing: 0.03em; }
#cbTranscript .interim { color: rgba(0,255,224,0.5); font-style: italic; }
#cbTranscript .final { color: rgba(226,244,255,0.85); }
#cbTranscript .cmd { color: #a855f7; font-weight: 600; }
#cbStatus { font-family: 'Orbitron', monospace; font-size: 7.5px; font-weight: 700; letter-spacing: 2.5px; text-transform: uppercase; padding: 4px 12px; border-radius: 20px; flex-shrink: 0; transition: all 0.3s; }
#cbStatus.idle { color: rgba(226,244,255,0.25); border: 1px solid rgba(226,244,255,0.07); background: rgba(255,255,255,0.02); }
#cbStatus.listening { color: #ff6b2b; border: 1px solid rgba(255,107,43,0.4); background: rgba(255,107,43,0.08); animation: cbBlink 1s ease infinite; box-shadow: 0 0 12px rgba(255,107,43,0.2); }
#cbStatus.speaking { color: #00ffe0; border: 1px solid rgba(0,255,224,0.4); background: rgba(0,255,224,0.08); box-shadow: 0 0 12px rgba(0,255,224,0.2); }
#cbStatus.processing { color: #a855f7; border: 1px solid rgba(168,85,247,0.4); background: rgba(168,85,247,0.08); box-shadow: 0 0 12px rgba(168,85,247,0.2); }
@keyframes cbBlink { 0%,100%{opacity:1} 50%{opacity:0.5} }
.cbCtrl { width: 32px; height: 32px; border-radius: 8px; border: 1px solid rgba(0,255,224,0.1); background: rgba(0,255,224,0.03); color: rgba(226,244,255,0.3); font-size: 12px; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: all 0.2s; flex-shrink: 0; }
.cbCtrl:hover { border-color: rgba(0,255,224,0.4); color: #00ffe0; background: rgba(0,255,224,0.08); box-shadow: 0 0 12px rgba(0,255,224,0.15); }
.cbCtrl.active { color: #00ffe0; border-color: rgba(0,255,224,0.5); background: rgba(0,255,224,0.1); }
#cbLangSel { appearance: none; -webkit-appearance: none; background: rgba(0,255,224,0.03); border: 1px solid rgba(0,255,224,0.12); color: rgba(0,255,224,0.7); padding: 5px 12px; font-family: 'Orbitron', monospace; font-size: 8px; font-weight: 700; letter-spacing: 1px; border-radius: 8px; cursor: pointer; outline: none; flex-shrink: 0; transition: all 0.2s; height: 32px; min-width: 160px; max-width: 200px; }
#cbLangSel:hover { border-color: rgba(0,255,224,0.4); background: rgba(0,255,224,0.07); box-shadow: 0 0 12px rgba(0,255,224,0.15); }
#cbLangSel option { background: #060d1a; color: #e2f4ff; }
#cbUploadBtn { width: 32px; height: 32px; border-radius: 8px; border: 1px solid rgba(168,85,247,0.2); background: rgba(168,85,247,0.04); color: rgba(168,85,247,0.6); font-size: 13px; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: all 0.2s; flex-shrink: 0; position: relative; }
#cbUploadBtn:hover { border-color: #a855f7; background: rgba(168,85,247,0.1); box-shadow: 0 0 14px rgba(168,85,247,0.3); color: #a855f7; }
#cbUploadBtn.has-file { border-color: #4ade80; color: #4ade80; background: rgba(74,222,128,0.08); }
#cbFileInput { display: none; }
#cbFileBadge { display: none; align-items: center; gap: 5px; padding: 3px 10px; border-radius: 20px; border: 1px solid rgba(74,222,128,0.3); background: rgba(74,222,128,0.06); font-family: 'IBM Plex Mono', monospace; font-size: 9px; color: #4ade80; max-width: 120px; flex-shrink: 0; }
#cbFileBadge.visible { display: flex; }
#cbFileBadge .cb-fname { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
#cbFileBadge .cb-fclose { cursor: pointer; opacity: 0.6; flex-shrink: 0; }
#cbFileBadge .cb-fclose:hover { opacity: 1; color: #ff6b2b; }
#cbAutoSpeak { display: flex; align-items: center; gap: 6px; font-family: 'Orbitron', monospace; font-size: 7px; font-weight: 600; letter-spacing: 1.5px; color: rgba(226,244,255,0.25); cursor: pointer; flex-shrink: 0; text-transform: uppercase; transition: color 0.2s; padding: 0 4px; }
#cbAutoSpeak.on { color: rgba(0,255,224,0.8); }
#cbAutoSpeak .cb-toggle { width: 28px; height: 14px; border-radius: 7px; border: 1px solid rgba(0,255,224,0.15); background: rgba(0,0,0,0.4); position: relative; transition: all 0.3s; }
#cbAutoSpeak.on .cb-toggle { background: rgba(0,255,224,0.15); border-color: rgba(0,255,224,0.5); box-shadow: 0 0 8px rgba(0,255,224,0.2); }
#cbAutoSpeak .cb-knob { width: 9px; height: 9px; border-radius: 50%; background: rgba(226,244,255,0.25); position: absolute; top: 1.5px; left: 1.5px; transition: all 0.3s; }
#cbAutoSpeak.on .cb-knob { background: #00ffe0; transform: translateX(13px); box-shadow: 0 0 8px #00ffe0; }
#cbLabBtn { font-size: 8px; font-family: 'Orbitron', monospace; font-weight: 700; letter-spacing: 1.5px; padding: 0 12px; height: 32px; border-radius: 8px; border: 1px solid rgba(168,85,247,0.25); background: rgba(168,85,247,0.06); color: rgba(168,85,247,0.7); cursor: pointer; transition: all 0.2s; display: flex; align-items: center; gap: 5px; flex-shrink: 0; white-space: nowrap; }
#cbLabBtn:hover { border-color: rgba(168,85,247,0.6); background: rgba(168,85,247,0.12); color: #a855f7; box-shadow: 0 0 16px rgba(168,85,247,0.25); }
.cb-divider { width: 1px; height: 24px; background: rgba(0,255,224,0.08); flex-shrink: 0; margin: 0 2px; }
#cbVolSlider { -webkit-appearance: none; appearance: none; width: 60px; height: 2px; border-radius: 1px; background: rgba(0,255,224,0.15); outline: none; flex-shrink: 0; cursor: pointer; }
#cbVolSlider::-webkit-slider-thumb { -webkit-appearance: none; width: 10px; height: 10px; border-radius: 50%; background: #00ffe0; box-shadow: 0 0 6px #00ffe0; cursor: pointer; }
#cbVoicePanel { position: fixed; bottom: 60px; left: 280px; width: 380px; background: rgba(4,8,16,0.98); backdrop-filter: blur(40px) saturate(200%); border: 1px solid rgba(0,255,224,0.15); border-radius: 4px 4px 0 0; z-index: 100; box-shadow: 0 -8px 40px rgba(0,0,0,0.6), 0 0 30px rgba(0,255,224,0.05); transition: transform 0.3s cubic-bezier(0.4,0,0.2,1), opacity 0.3s; transform-origin: bottom left; display: flex; flex-direction: column; max-height: 520px; }
#cbVoicePanel.hidden { transform: translateY(20px) scale(0.97); opacity: 0; pointer-events: none; }
body:has(.sidebar.collapsed) #cbVoicePanel { left: 60px; }
#cbPanelHeader { display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; border-bottom: 1px solid rgba(0,255,224,0.08); flex-shrink: 0; }
.cbPanelTitle { font-family: 'Orbitron', monospace; font-size: 9px; font-weight: 700; letter-spacing: 3px; text-transform: uppercase; color: #00ffe0; display: flex; align-items: center; gap: 8px; }
.cbPanelDot { width: 5px; height: 5px; border-radius: 50%; background: #00ffe0; box-shadow: 0 0 6px #00ffe0; animation: cbBlink 1.4s ease infinite; }
#cbPanelClose { background: none; border: none; color: rgba(226,244,255,0.3); cursor: pointer; font-size: 14px; transition: color 0.15s; }
#cbPanelClose:hover { color: #ff6b2b; }
#cbPanelTabs { display: flex; border-bottom: 1px solid rgba(0,255,224,0.08); flex-shrink: 0; }
.cbPTab { flex: 1; padding: 8px; text-align: center; font-family: 'Orbitron', monospace; font-size: 7px; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; color: rgba(226,244,255,0.3); cursor: pointer; border-bottom: 2px solid transparent; transition: all 0.15s; }
.cbPTab.active { color: #00ffe0; border-color: #00ffe0; }
.cbPTab:hover:not(.active) { color: rgba(226,244,255,0.6); }
#cbPanelBody { flex: 1; overflow-y: auto; padding: 14px; }
#cbPanelBody::-webkit-scrollbar { width: 2px; }
#cbPanelBody::-webkit-scrollbar-thumb { background: rgba(0,255,224,0.2); }
.cbPanelSection { display: none; }
.cbPanelSection.active { display: block; }
.cbCmdGrid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-bottom: 12px; }
.cbCmd { padding: 8px 10px; border-radius: 2px; border: 1px solid rgba(0,255,224,0.1); background: rgba(0,255,224,0.03); font-family: 'IBM Plex Mono', monospace; font-size: 10px; color: rgba(226,244,255,0.5); cursor: pointer; transition: all 0.15s; text-align: center; display: flex; flex-direction: column; align-items: center; gap: 3px; }
.cbCmd:hover { border-color: rgba(0,255,224,0.3); color: #00ffe0; background: rgba(0,255,224,0.06); }
.cbCmd .cbCmdIcon { font-size: 14px; }
.cbCmd .cbCmdLabel { font-size: 8px; font-family: 'Orbitron',monospace; letter-spacing: 1px; }
.cbSymLabel { font-family: 'Orbitron', monospace; font-size: 7px; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; color: rgba(226,244,255,0.3); margin: 10px 0 6px; }
.cbSymRow { display: flex; justify-content: space-between; align-items: center; padding: 5px 8px; border-radius: 2px; font-family: 'IBM Plex Mono', monospace; font-size: 10px; transition: background 0.12s; margin-bottom: 2px; }
.cbSymRow:hover { background: rgba(0,255,224,0.04); }
.cbSymPhrase { color: rgba(226,244,255,0.5); }
.cbSymResult { color: #00ffe0; background: rgba(0,255,224,0.06); padding: 1px 6px; border-radius: 2px; font-size: 11px; }
.cbSettingRow { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid rgba(0,255,224,0.05); }
.cbSettingRow:last-child { border-bottom: none; }
.cbSettingLabel { font-family: 'Orbitron', monospace; font-size: 8px; font-weight: 600; letter-spacing: 1px; color: rgba(226,244,255,0.4); text-transform: uppercase; }
.cbSettingCtrl input[type=range] { -webkit-appearance: none; width: 90px; height: 2px; border-radius: 1px; background: rgba(0,255,224,0.15); outline: none; cursor: pointer; }
.cbSettingCtrl input[type=range]::-webkit-slider-thumb { -webkit-appearance: none; width: 10px; height: 10px; border-radius: 50%; background: #00ffe0; box-shadow: 0 0 6px #00ffe0; cursor: pointer; }
.cbHistEntry { display: flex; gap: 8px; padding: 6px 0; border-bottom: 1px solid rgba(0,255,224,0.05); font-family: 'IBM Plex Mono', monospace; font-size: 10px; }
.cbHistEntry:last-child { border-bottom: none; }
.cbHistRole { font-family: 'Orbitron', monospace; font-size: 7px; font-weight: 700; letter-spacing: 1px; color: #a855f7; flex-shrink: 0; margin-top: 1px; }
.cbHistText { color: rgba(226,244,255,0.6); line-height: 1.5; word-break: break-word; }
#cbImgPreview { display: none; max-width: 100%; max-height: 120px; border: 1px solid rgba(74,222,128,0.2); border-radius: 2px; margin-top: 8px; object-fit: contain; }
#cbImgPreview.visible { display: block; }
#cbWakeIndicator { position: fixed; top: 70px; right: 20px; background: rgba(0,255,224,0.08); border: 1px solid rgba(0,255,224,0.2); padding: 6px 12px; border-radius: 2px; font-family: 'Orbitron', monospace; font-size: 8px; font-weight: 700; letter-spacing: 2px; color: #00ffe0; display: none; z-index: 9000; animation: cbFadeIn 0.3s ease; }
@keyframes cbFadeIn { from{opacity:0;transform:translateY(-6px)} to{opacity:1;transform:none} }
#cbDropOverlay { display: none; position: fixed; inset: 0; z-index: 9999; background: rgba(0,255,224,0.04); border: 3px dashed rgba(0,255,224,0.4); align-items: center; justify-content: center; flex-direction: column; gap: 12px; font-family: 'Orbitron', monospace; font-size: 14px; font-weight: 700; letter-spacing: 4px; color: #00ffe0; text-shadow: 0 0 20px #00ffe0; backdrop-filter: blur(4px); }
#cbDropOverlay.active { display: flex; }
#cbDropOverlay .cbDropIcon { font-size: 48px; filter: drop-shadow(0 0 20px #00ffe0); animation: cbFloat 2s ease infinite; }
@keyframes cbFloat { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-10px)} }
`;
    document.head.appendChild(s);
  }

  function buildUI() {
    const dropOverlay = document.createElement('div');
    dropOverlay.id = 'cbDropOverlay';
    dropOverlay.innerHTML = `<div class="cbDropIcon">📁</div><div>DROP FILE TO ANALYZE</div><div style="font-size:9px;letter-spacing:2px;opacity:0.6;margin-top:-4px">CODE · IMAGE · SCREENSHOT · DOCUMENT</div>`;
    document.body.appendChild(dropOverlay);

    const wakeInd = document.createElement('div');
    wakeInd.id = 'cbWakeIndicator';
    wakeInd.textContent = '● WAKE WORD ACTIVE';
    document.body.appendChild(wakeInd);

    const bar = document.createElement('div');
    bar.id = 'cbVoiceBar';
    bar.innerHTML = `
    <button id="cbMicBtn" title="Start/Stop voice input">🎤</button>
    <div id="cbWaveform">
      ${Array(14).fill('<div class="cbWave" style="height:3px"></div>').join('')}
    </div>
    <div id="cbTranscript"><span style="opacity:0.25;font-family:Orbitron,monospace;font-size:8px;letter-spacing:2px">SAY "HEY BUDDY" TO ACTIVATE · NEURAL VOICE ENGINE</span></div>
    <div id="cbFileBadge">
      <span>📎</span>
      <span class="cb-fname" id="cbFName"></span>
      <span class="cb-fclose" onclick="CBVoice.clearFile()">✕</span>
    </div>
    <div class="cb-divider"></div>
    <div id="cbStatus" class="idle">IDLE</div>
    <div class="cb-divider"></div>
    <button class="cbCtrl" id="cbPauseBtn" onclick="CBVoice.togglePause()" title="Pause speech">⏸</button>
    <button class="cbCtrl" id="cbStopBtn" onclick="CBVoice.stop()" title="Stop speech">⏹</button>
    <div class="cb-divider"></div>
    <button id="cbUploadBtn" title="Upload file for AI analysis" onclick="document.getElementById('cbFileInput').click()">📎</button>
    <input type="file" id="cbFileInput" accept="image/*,.pdf,.txt,.py,.js,.ts,.java,.cpp,.c,.cs,.go,.rs,.rb,.php,.swift,.kt,.html,.css,.json,.xml,.yaml,.md,.sql,.sh,.r,.m">
    <select id="cbLangSel" onchange="if(typeof onLangChange==='function')onLangChange(this)">
      <optgroup label="── English ──">
        <option value="en-US">🇺🇸 EN — English</option>
      </optgroup>
      <optgroup label="── Indic ──">
        <option value="ta-IN">🇮🇳 TA — Tamil · தமிழ்</option>
        <option value="ta-en">🇮🇳 TA+EN — Tanglish</option>
        <option value="hi-IN">🇮🇳 HI — हिंदी</option>
        <option value="te-IN">🇮🇳 TE — Telugu · తెలుగు</option>
        <option value="kn-IN">🇮🇳 KN — Kannada · ಕನ್ನಡ</option>
        <option value="ml-IN">🇮🇳 ML — Malayalam · മലയാളം</option>
        <option value="bn-IN">🇮🇳 BN — Bengali · বাংলা</option>
        <option value="mr-IN">🇮🇳 MR — Marathi · मराठी</option>
      </optgroup>
      <optgroup label="── World ──">
        <option value="fr-FR">🇫🇷 FR — Français</option>
        <option value="de-DE">🇩🇪 DE — Deutsch</option>
        <option value="es-ES">🇪🇸 ES — Español</option>
        <option value="ja-JP">🇯🇵 JA — 日本語</option>
        <option value="zh-CN">🇨🇳 ZH — 中文</option>
        <option value="ko-KR">🇰🇷 KO — 한국어</option>
        <option value="ar-SA">🇸🇦 AR — العربية</option>
        <option value="ru-RU">🇷🇺 RU — Русский</option>
        <option value="pt-BR">🇧🇷 PT — Português</option>
      </optgroup>
    </select>
    <div id="cbAutoSpeak" onclick="CBVoice.toggleAutoSpeak()" title="Auto-speak AI responses">
      <div class="cb-toggle"><div class="cb-knob"></div></div>
      <span>AUTO</span>
    </div>
    <button id="cbLabBtn" onclick="CBVoice.togglePanel()" title="Voice Lab Panel">⚡ LAB</button>
  `;
    document.body.appendChild(bar);

    const panel = document.createElement('div');
    panel.id = 'cbVoicePanel';
    panel.className = 'hidden';
    panel.innerHTML = `
    <div id="cbPanelHeader">
      <div class="cbPanelTitle">
        <div class="cbPanelDot"></div>
        NEURAL VOICE LAB
      </div>
      <button id="cbPanelClose" onclick="CBVoice.togglePanel()">✕</button>
    </div>
    <div id="cbPanelTabs">
      <div class="cbPTab active" onclick="switchPTab('commands',this)">COMMANDS</div>
      <div class="cbPTab" onclick="switchPTab('symbols',this)">SYMBOLS</div>
      <div class="cbPTab" onclick="switchPTab('history',this)">HISTORY</div>
      <div class="cbPTab" onclick="switchPTab('settings',this)">SETTINGS</div>
    </div>
    <div id="cbPanelBody">
      <div class="cbPanelSection active" id="cbTab-commands">
        <div class="cbCmdGrid">
          <div class="cbCmd" onclick="triggerRun()"><div class="cbCmdIcon">▶</div><div class="cbCmdLabel">RUN CODE</div></div>
          <div class="cbCmd" onclick="triggerDebug()"><div class="cbCmdIcon">🐛</div><div class="cbCmdLabel">DEBUG</div></div>
          <div class="cbCmd" onclick="triggerExplain()"><div class="cbCmdIcon">💡</div><div class="cbCmdLabel">EXPLAIN</div></div>
          <div class="cbCmd" onclick="triggerOptimize()"><div class="cbCmdIcon">⚡</div><div class="cbCmdLabel">OPTIMIZE</div></div>
          <div class="cbCmd" onclick="triggerComplexity()"><div class="cbCmdIcon">📊</div><div class="cbCmdLabel">COMPLEXITY</div></div>
          <div class="cbCmd" onclick="triggerTest()"><div class="cbCmdIcon">🧪</div><div class="cbCmdLabel">WRITE TESTS</div></div>
          <div class="cbCmd" onclick="triggerDocument()"><div class="cbCmdIcon">📝</div><div class="cbCmdLabel">DOCUMENT</div></div>
          <div class="cbCmd" onclick="triggerConvert()"><div class="cbCmdIcon">🔄</div><div class="cbCmdLabel">CONVERT LANG</div></div>
          <div class="cbCmd" onclick="analyzeUploadedFile()"><div class="cbCmdIcon">📁</div><div class="cbCmdLabel">ANALYZE FILE</div></div>
          <div class="cbCmd" onclick="CBVoice.startListening()"><div class="cbCmdIcon">🎤</div><div class="cbCmdLabel">SPEAK QUERY</div></div>
        </div>
        <div class="cbSymLabel">VOICE COMMAND REFERENCE</div>
        <div class="cbSymRow"><span class="cbSymPhrase">"Hey Buddy"</span><span class="cbSymResult">Wake Up</span></div>
        <div class="cbSymRow"><span class="cbSymPhrase">"Run code"</span><span class="cbSymResult">Execute</span></div>
        <div class="cbSymRow"><span class="cbSymPhrase">"Debug this"</span><span class="cbSymResult">Find bugs</span></div>
        <div class="cbSymRow"><span class="cbSymPhrase">"Explain code"</span><span class="cbSymResult">Narrate</span></div>
        <div class="cbSymRow"><span class="cbSymPhrase">"Write tests"</span><span class="cbSymResult">Unit tests</span></div>
        <div class="cbSymRow"><span class="cbSymPhrase">"Optimize"</span><span class="cbSymResult">Refactor</span></div>
        <div class="cbSymRow"><span class="cbSymPhrase">"Stop speaking"</span><span class="cbSymResult">Silence TTS</span></div>
      </div>
      <div class="cbPanelSection" id="cbTab-symbols">
        <div class="cbSymLabel">🎙 SAY THIS → GET CODE SYMBOL</div>
        <div style="font-family:IBM Plex Mono,monospace;font-size:9px;color:rgba(226,244,255,0.3);margin-bottom:10px;line-height:1.6">
          Speak these phrases while coding by voice. They are replaced with the exact symbol in your code editor.
        </div>
        ${Object.entries(CODE_SYMBOLS_WITH_DESC).map(([k, [sym, desc]]) => `
          <div class="cbSymRow" style="flex-direction:column;align-items:flex-start;gap:2px;padding:7px 0;border-bottom:1px solid rgba(255,255,255,0.04)">
            <div style="display:flex;justify-content:space-between;width:100%;align-items:center">
              <span class="cbSymPhrase" style="font-size:10px">"${k}"</span>
              <span class="cbSymResult" style="font-size:13px;min-width:36px;text-align:center">${sym.replace(/\n/g,'↵').replace(/\t/g,'→')}</span>
            </div>
            <span style="font-family:IBM Plex Mono,monospace;font-size:9px;color:rgba(0,255,224,0.4);margin-top:2px">${desc}</span>
          </div>
        `).join('')}
      </div>
      <div class="cbPanelSection" id="cbTab-history">
        <div id="cbHistoryList" style="font-family:IBM Plex Mono,monospace;font-size:10px;color:rgba(226,244,255,0.3)">No voice interactions yet.</div>
        <img id="cbImgPreview" />
      </div>
      <div class="cbPanelSection" id="cbTab-settings">
        <div class="cbSettingRow">
          <div class="cbSettingLabel">SPEECH RATE</div>
          <div class="cbSettingCtrl"><input type="range" min="0.5" max="2" step="0.05" value="0.95" id="cbRateSlider" oninput="CBVoice.setRate(+this.value)"></div>
        </div>
        <div class="cbSettingRow">
          <div class="cbSettingLabel">PITCH</div>
          <div class="cbSettingCtrl"><input type="range" min="0.5" max="2" step="0.05" value="1.05" id="cbPitchSlider" oninput="CBVoice.setPitch(+this.value)"></div>
        </div>
        <div class="cbSettingRow">
          <div class="cbSettingLabel">VOLUME</div>
          <div class="cbSettingCtrl"><input type="range" min="0" max="1" step="0.05" value="0.85" id="cbVolSlider2" oninput="CBVoice.setVolume(+this.value)"></div>
        </div>
        <div class="cbSettingRow">
          <div class="cbSettingLabel">CODE CONTEXT</div>
          <div class="cbSettingCtrl">
            <div id="cbCodeCtxToggle" onclick="toggleCodeContext()" style="cursor:pointer;font-family:Orbitron,monospace;font-size:8px;font-weight:700;letter-spacing:1px;color:#00ffe0;">ON</div>
          </div>
        </div>
        <div class="cbSettingRow">
          <div class="cbSettingLabel">LANGUAGE</div>
          <div class="cbSettingCtrl">
            <select id="cbLangSel2" onchange="CBVoice.setLang(this.value)" style="background:rgba(0,255,224,0.04);border:1px solid rgba(0,255,224,0.15);color:#00ffe0;padding:4px 8px;font-family:Orbitron,monospace;font-size:8px;border-radius:2px;outline:none;cursor:pointer;">
              <optgroup label="── English ──">
                <option value="en-US">🇺🇸 English</option>
              </optgroup>
              <optgroup label="── Indic ──">
                <option value="ta-IN">🇮🇳 Tamil — தமிழ்</option>
                <option value="ta-en">🇮🇳 Tanglish — தமிழ் + EN</option>
                <option value="hi-IN">🇮🇳 Hindi — हिंदी</option>
                <option value="te-IN">🇮🇳 Telugu — తెలుగు</option>
                <option value="kn-IN">🇮🇳 Kannada — ಕನ್ನಡ</option>
                <option value="ml-IN">🇮🇳 Malayalam — മലയാളം</option>
                <option value="bn-IN">🇮🇳 Bengali — বাংলা</option>
                <option value="mr-IN">🇮🇳 Marathi — मराठी</option>
              </optgroup>
              <optgroup label="── World ──">
                <option value="fr-FR">🇫🇷 Français</option>
                <option value="de-DE">🇩🇪 Deutsch</option>
                <option value="es-ES">🇪🇸 Español</option>
                <option value="ja-JP">🇯🇵 日本語</option>
                <option value="zh-CN">🇨🇳 中文</option>
                <option value="ko-KR">🇰🇷 한국어</option>
                <option value="ar-SA">🇸🇦 العربية</option>
                <option value="ru-RU">🇷🇺 Русский</option>
                <option value="pt-BR">🇧🇷 Português</option>
              </optgroup>
            </select>
          </div>
        </div>
        <div style="margin-top:12px;padding:10px;border:1px solid rgba(0,255,224,0.08);border-radius:2px;background:rgba(0,255,224,0.02);">
          <div style="font-family:Orbitron,monospace;font-size:7px;font-weight:700;letter-spacing:2px;color:rgba(226,244,255,0.3);margin-bottom:6px;">TEST VOICE</div>
          <button onclick="CBVoice.testVoice()" style="width:100%;padding:7px;background:rgba(0,255,224,0.06);border:1px solid rgba(0,255,224,0.2);color:#00ffe0;font-family:Orbitron,monospace;font-size:8px;font-weight:700;letter-spacing:2px;cursor:pointer;border-radius:2px;transition:all 0.2s;" onmouseover="this.style.background='rgba(0,255,224,0.12)'" onmouseout="this.style.background='rgba(0,255,224,0.06)'">▶ SPEAK TEST PHRASE</button>
        </div>
      </div>
    </div>
  `;
    document.body.appendChild(panel);

    document.getElementById('cbFileInput').addEventListener('change', handleFileSelect);
    document.getElementById('cbLangSel').addEventListener('change', e => CBVoice.setLang(e.target.value));
    document.getElementById('cbMicBtn').addEventListener('click', () => {
      if (STATE.isListening) CBVoice.stopListening();
      else CBVoice.startListening();
    });
    setupDragDrop();
  }

  function switchPTab(name, el) {
    document.querySelectorAll('.cbPTab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.cbPanelSection').forEach(s => s.classList.remove('active'));
    el.classList.add('active');
    const sec = document.getElementById('cbTab-' + name);
    if (sec) sec.classList.add('active');
  }

  function initRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) { setStatus('NO BROWSER SUPPORT', 'idle'); return null; }
    const r = new SpeechRecognition();
    r.continuous = true;
    r.interimResults = true;
    r.lang = STATE.currentLang;
    r.maxAlternatives = 3;

    r.onstart = () => {
      STATE.isListening = true;
      setStatus('LISTENING', 'listening');
      document.getElementById('cbMicBtn').classList.add('active');
      document.getElementById('cbVoiceBar').classList.add('listening');
      setTranscript(LANGS[STATE.currentLang]?.listening || 'Listening...', 'interim');
    };

    r.onresult = (e) => {
      let interim = '', final = '';
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const t = e.results[i][0].transcript;
        if (e.results[i].isFinal) final += t;
        else interim += t;
      }
      if (interim) setTranscript(interim, 'interim');
      if (final) {
        const processed = processTranscript(final.trim());
        setTranscript(processed, 'final');
        STATE.transcript = processed;
        handleVoiceInput(processed);
      }
    };

    r.onerror = (e) => {
      if (e.error !== 'no-speech') {
        setStatus('ERROR', 'idle');
        setTranscript('Recognition error: ' + e.error, 'final');
      }
      STATE.isListening = false;
      document.getElementById('cbMicBtn').classList.remove('active');
      document.getElementById('cbVoiceBar').classList.remove('listening');
    };

    r.onend = () => {
      STATE.isListening = false;
      document.getElementById('cbMicBtn').classList.remove('active');
      document.getElementById('cbVoiceBar').classList.remove('listening');
      setStatus('IDLE', 'idle');
      if (STATE.wakeWordActive && STATE.recognition) {
        setTimeout(() => { try { STATE.recognition.start(); } catch (e) { } }, 300);
      }
    };

    return r;
  }

  function processTranscript(text) {
    if (!STATE.codeContext) return text;
    let result = text.toLowerCase();
    for (const [phrase, symbol] of Object.entries(CODE_SYMBOLS)) {
      const regex = new RegExp('\\b' + phrase.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '\\b', 'gi');
      result = result.replace(regex, symbol);
    }
    return result;
  }

  function handleVoiceInput(text) {
    const lower = text.toLowerCase().trim();
    if (lower.includes('hey buddy') || lower.includes('ஹே பட்டி') || lower.includes('हे बडी')) {
      activateWakeWord(); return;
    }
    const cmds = LANGS[STATE.currentLang]?.commands || {};
    for (const [phrase, action] of Object.entries(cmds)) {
      if (lower.includes(phrase.toLowerCase())) { action(); return; }
    }
    const enCmds = LANGS['en-US'].commands;
    for (const [phrase, action] of Object.entries(enCmds)) {
      if (lower.includes(phrase.toLowerCase())) { action(); return; }
    }
    const detectedLang = PROG_LANGS.find(l => lower.includes(l));
    let query = text;
    if (lower.startsWith('explain') || lower.startsWith('what is') || lower.startsWith('how to')) {
      query = text + (detectedLang ? ` in ${detectedLang}` : ' in the context of programming');
    }
    sendVoiceQuery(query);
  }

  function sendVoiceQuery(text) {
    const msgEl = document.getElementById('message');
    const sendBtn = document.getElementById('sendBtn');
    if (!msgEl || !sendBtn) return;
    setStatus('PROCESSING', 'processing');
    msgEl.value = text;
    if (msgEl.oninput) msgEl.oninput.call(msgEl);
    setTimeout(() => {
      sendBtn.click();
      setStatus('IDLE', 'idle');
    }, 200);
  }

  let _currentAudio = null;
  let _pendingController = null;  // AbortController for in-flight TTS fetch


  // Maps UI lang code → backend /tts lang param
  // ta-en (Tanglish) sends 'ta-en' so backend uses Tamil voice for whole response
  const LANG_TO_TTS = {
    'en-US': 'en-US', 'ta-IN': 'ta-IN', 'ta-en': 'ta-en',
    'hi-IN': 'hi-IN', 'te-IN': 'te-IN', 'kn-IN': 'kn-IN',
    'ml-IN': 'ml-IN', 'bn-IN': 'bn-IN', 'mr-IN': 'mr-IN',
    'pa-IN': 'pa-IN', 'gu-IN': 'gu-IN',
    'fr-FR': 'fr-FR', 'de-DE': 'de-DE', 'es-ES': 'es-ES',
    'ja-JP': 'ja-JP', 'ko-KR': 'ko-KR', 'ar-SA': 'ar-SA',
    'zh-CN': 'zh-CN', 'ru-RU': 'ru-RU', 'pt-BR': 'pt-BR',
  };

  // Maps UI lang → browser Web Speech API lang code (for fallback when gTTS fails)
  // ta-en (Tanglish) must use Tamil voice in browser too
  const LANG_TO_BROWSER = {
    'ta-en': 'ta-IN',
    'ta-IN': 'ta-IN', 'hi-IN': 'hi-IN', 'te-IN': 'te-IN',
    'kn-IN': 'kn-IN', 'ml-IN': 'ml-IN', 'bn-IN': 'bn-IN',
    'mr-IN': 'mr-IN', 'pa-IN': 'pa-IN', 'gu-IN': 'gu-IN',
    'fr-FR': 'fr-FR', 'de-DE': 'de-DE', 'es-ES': 'es-ES',
    'ja-JP': 'ja-JP', 'ko-KR': 'ko-KR', 'ar-SA': 'ar-SA',
    'zh-CN': 'zh-CN', 'ru-RU': 'ru-RU', 'pt-BR': 'pt-BR',
    'en-US': 'en-US',
  };

  // ── _speakViaGTTS: internal helper — sends text+lang to gTTS backend ────────
  // Called by speak() for normal path AND by auto-translate callback.
  function _speakViaGTTS(text, activeLang) {
    // ── If voice clone is active, use the detected language from the profile ──
    // window._vcDetectedLang is set by VoiceClone after upload/checkStatus.
    // The backend also reads it from the JSON profile as a safety net,
    // but we send it explicitly here so it's always correct.
    const effectiveLang = (window._hasVoiceClone && window._vcDetectedLang)
      ? window._vcDetectedLang
      : activeLang;

    const ttsLang = LANG_TO_TTS[effectiveLang] || effectiveLang;

    // ── CRITICAL: kill browser TTS immediately before starting gTTS ──────────
    // Without this, any queued/running speechSynthesis utterance keeps playing
    // alongside the gTTS audio, causing the double-voice (male+female) bug.
    if (STATE.synth) STATE.synth.cancel();
    STATE.currentUtterance = null;

    setStatus('SPEAKING', 'speaking');
    animateWaveformSpeak(true);
    STATE.isSpeaking = true;
    addHistory('TTS', '[' + effectiveLang + '] ' + text.slice(0, 80) + '...');

    const isTanglish = (effectiveLang === 'ta-en');
    const effectiveRate = isTanglish ? Math.min(STATE.rate, 0.85) : Math.min(Math.max(STATE.rate, 0.5), 2.0);

    if (_pendingController) { try { _pendingController.abort(); } catch(e){} }
    _pendingController = new AbortController();
    fetch(window._hasVoiceClone ? '/voice_clone/tts' : '/tts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: text, lang: ttsLang }),
      signal: _pendingController.signal
    })
    .then(res => {
      if (!res.ok) return res.json().catch(() => ({})).then(err => { throw new Error(err.error || 'TTS error ' + res.status); });
      return res.blob();
    })
    .then(blob => {
      // Cancel browser TTS again in case it started while fetch was in flight
      if (STATE.synth) STATE.synth.cancel();
      const url = URL.createObjectURL(blob);
      if (_currentAudio) { _currentAudio.pause(); _currentAudio = null; }
      _currentAudio = new Audio(url);
      _currentAudio.volume = STATE.volume;
      _currentAudio.playbackRate = effectiveRate;
      _currentAudio.onended = () => {
        STATE.isSpeaking = false; setStatus('IDLE', 'idle');
        animateWaveformSpeak(false); URL.revokeObjectURL(url); _currentAudio = null;
        if (typeof STATE.onSpeakEnd === 'function') { STATE.onSpeakEnd(); STATE.onSpeakEnd = null; }
      };
      _currentAudio.onerror = () => {
        STATE.isSpeaking = false; setStatus('IDLE', 'idle');
        animateWaveformSpeak(false); _currentAudio = null;
        if (typeof STATE.onSpeakEnd === 'function') { STATE.onSpeakEnd(); STATE.onSpeakEnd = null; }
      };
      _pendingController = null;
      _currentAudio.play().then(() => {
        if (typeof STATE.onSpeakStart === 'function') { STATE.onSpeakStart(); STATE.onSpeakStart = null; }
      }).catch(() => {});
    })
    .catch(err => {
      if (err && err.name === 'AbortError') return; // intentionally cancelled, don't fall back
      console.warn('CBVoice: gTTS failed (' + err.message + ') — no browser TTS fallback (prevents double voice)');
      STATE.isSpeaking = false; setStatus('IDLE', 'idle');
      animateWaveformSpeak(false);
      // Do NOT call speakBrowser() here — it plays female voice over gTTS = double voice bug
    });
  }

    function speak(text, forceLang) {
    if (!text) return;

    // ── Stop EVERYTHING first — prevents any double-voice overlap ────────────
    if (_currentAudio) { _currentAudio.pause(); _currentAudio = null; }
    if (_pendingController) { try { _pendingController.abort(); } catch(e){} _pendingController = null; }
    if (STATE.synth) { STATE.synth.cancel(); }
    STATE.currentUtterance = null;
    STATE.isSpeaking = false;

    // If voice clone profile exists, always use the detected language
    // so the AI answer is spoken in the user's own language regardless of UI selector
    const activeLang = (window._hasVoiceClone && window._vcDetectedLang)
      ? window._vcDetectedLang
      : (forceLang || STATE.currentLang);

    let clean = text
      .replace(/```[\s\S]*?```/g, ' code block. ')
      .replace(/`[^`]+`/g, ' code ')
      .replace(/#{1,6}\s/g, '')
      .replace(/\*\*([^*]+)\*\*/g, '$1')
      .replace(/\*([^*]+)\*/g, '$1')
      .replace(/[<>]/g, '')
      .replace(/https?:\/\/\S+/g, 'link')
      .replace(/\s{2,}/g, ' ')
      .trim()
      .slice(0, 1000);

    if (!clean) return;

    // ── Indic language guard ─────────────────────────────────────────────────
    // The backend now uses WORD-LEVEL engine splitting:
    //   - Native script words (Tamil/Hindi/Telugu/etc) → native gTTS engine (correct accent)
    //   - Embedded English tech words ("Python", "function", "loop") → English gTTS (natural)
    //
    // So we ALWAYS send text to the backend — no need to block playback.
    // If AI responded entirely in English despite native-lang instruction, we show a soft hint
    // but still play it back using the English gTTS segments (audible, just not in target lang).
    const NATIVE_SCRIPT = {
      'ta-IN': /[\u0B80-\u0BFF]/,
      'te-IN': /[\u0C00-\u0C7F]/,
      'kn-IN': /[\u0C80-\u0CFF]/,
      'ml-IN': /[\u0D00-\u0D7F]/,
      'bn-IN': /[\u0980-\u09FF]/,
      'mr-IN': /[\u0900-\u097F]/,
      'hi-IN': /[\u0900-\u097F]/,
    };
    const nativePattern = NATIVE_SCRIPT[activeLang];
    if (nativePattern && !nativePattern.test(clean)) {
      // AI replied in English despite non-English language being selected.
      // Auto-translate via /translate endpoint, then speak the translation.
      setTranscript('\u23f3 Translating response to ' + activeLang + '...', 'cmd');
      setStatus('PROCESSING', 'processing');
      fetch('/translate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: clean, lang: activeLang })
      })
      .then(r => r.json())
      .then(data => {
        const translated = (data.translated || clean).trim();
        setTranscript('\ud83c\udf10 Translated \u2192 ' + activeLang, 'cmd');
        _speakViaGTTS(translated, activeLang);
      })
      .catch(() => {
        setTranscript('\u26a0 Translation failed \u2014 reading English', 'cmd');
        _speakViaGTTS(clean, 'en-US');
      });
      return; // async: wait for translation
    }
    if (!clean) return;

    _speakViaGTTS(clean, activeLang);
  }
    function speakBrowser(clean, lang) {
    if (!STATE.synth) return;

    // Stop gTTS audio if somehow still playing
    if (_currentAudio) { _currentAudio.pause(); _currentAudio = null; }
    STATE.synth.cancel();

    // lang is already the correct BCP-47 code (ta-IN, hi-IN etc.)
    // passed by speak() via LANG_TO_BROWSER — never 'ta-en' here
    const utter = new SpeechSynthesisUtterance(clean);
    utter.rate   = STATE.rate;
    utter.pitch  = STATE.pitch;
    utter.volume = STATE.volume;

    // Try to find a matching FEMALE voice — always prefer female
    const voice = getBestVoice(lang, true); // true = prefer female
    if (voice) {
      utter.voice = voice;
      utter.lang  = voice.lang;
    } else {
      utter.lang = lang;
    }

    utter.onstart = () => { STATE.isSpeaking = true; setStatus('SPEAKING', 'speaking'); animateWaveformSpeak(true); };
    utter.onend   = () => { STATE.isSpeaking = false; setStatus('IDLE', 'idle'); animateWaveformSpeak(false); };
    utter.onerror = (e) => {
      STATE.isSpeaking = false;
      setStatus('IDLE', 'idle');
      animateWaveformSpeak(false);
      if (e.error !== 'canceled' && e.error !== 'interrupted') {
        const langName = lang.split('-')[0].toUpperCase();
        setTranscript(
          '⚠ No ' + langName + ' voice on this device. Go to Settings → Accessibility → TTS and install ' + langName + ' language pack.',
          'cmd'
        );
        console.warn('CBVoice browser TTS error for', lang, ':', e.error);
      }
    };
    STATE.currentUtterance = utter;
    STATE.synth.speak(utter);
  }
  function detectLanguage(text) {
    if (/[\u0B80-\u0BFF]/.test(text)) return 'ta-IN';
    if (/[\u0900-\u097F]/.test(text)) return 'hi-IN';
    if (/[\u0C00-\u0C7F]/.test(text)) return 'te-IN';
    if (/[\u0C80-\u0CFF]/.test(text)) return 'kn-IN';
    if (/[\u0D00-\u0D7F]/.test(text)) return 'ml-IN';
    if (/[\u0980-\u09FF]/.test(text)) return 'bn-IN';
    return 'en-US';
  }

  function getBestVoice(lang, preferFemale) {
    const latest = STATE.synth ? STATE.synth.getVoices() : [];
    if (latest.length) STATE.voices = latest;
    const voices = STATE.voices;
    if (!voices.length) return null;

    const searchLang = (lang === 'ta-en') ? 'ta-IN' : lang;
    const base = searchLang.split('-')[0].toLowerCase();

    // Detect female voices — used to prefer them when preferFemale=true
    const isFemale = v => {
      const n = v.name.toLowerCase();
      const femaleWords = ['female','woman','girl','fiona','samantha','karen','victoria','moira',
        'veena','tessa','alice','amelie','anna','aurelie','claire','joana','lekha','heera',
        'kalpana','meijia','sin-ji','tingting','yuna','milena','luciana','paulina','monica',
        'chitra','zira','susan','hazel','linda','eva','julia','natasha','kate','aria','jenny',
        'aditi','raveena','priya','asha','pallavi'];
      const maleWords = ['male','man','david','daniel','alex','jorge','thomas','markus',
        'stefan','otoya','maged','yuri','ravi','hemant','reed','fred','bruce','tarik','felix'];
      if (femaleWords.some(w => n.includes(w))) return true;
      if (maleWords.some(w => n.includes(w))) return false;
      return null; // unknown gender — acceptable
    };

    const VOICE_NAMES = {
      'ta': ['lekha','tamil'], 'hi': ['kalpana','heera','hindi'],
      'te': ['chitra','telugu'], 'kn': ['kannada'], 'ml': ['malayalam'],
      'bn': ['bengali'], 'mr': ['marathi'], 'pa': ['punjabi'], 'gu': ['gujarati'],
      'fr': ['amelie','aurelie','french'], 'de': ['anna','german'],
      'es': ['monica','paulina','spanish'], 'ja': ['kyoko','japanese'],
      'zh': ['tingting','meijia','chinese'], 'ko': ['yuna','korean'],
      'ar': ['arabic'], 'ru': ['milena','russian'],
      'pt': ['joana','luciana','portuguese'],
      'en': ['samantha','karen','zira','moira','tessa','aria','jenny','victoria'],
    };
    const keywords = VOICE_NAMES[base] || [];

    const tryFind = arr => {
      let v = arr.find(x => x.lang === searchLang && x.localService);
      if (!v) v = arr.find(x => x.lang === searchLang);
      if (!v) v = arr.find(x => x.lang.toLowerCase().startsWith(base + '-'));
      if (!v) v = arr.find(x => x.lang.toLowerCase().startsWith(base));
      if (!v && keywords.length) v = arr.find(x => keywords.some(kw => x.name.toLowerCase().includes(kw)));
      return v || null;
    };

    if (preferFemale) {
      // Try female voices first, fall back to any voice if no female found
      const femalePool = voices.filter(v => isFemale(v) !== false);
      return tryFind(femalePool) || tryFind(voices);
    }
    return tryFind(voices);
  }
  function waitForVoices() {
    return new Promise(resolve => {
      const voices = STATE.synth.getVoices();
      if (voices.length > 0) { STATE.voices = voices; resolve(voices); return; }
      const handler = () => {
        STATE.voices = STATE.synth.getVoices();
        resolve(STATE.voices);
      };
      STATE.synth.addEventListener('voiceschanged', handler, { once: true });
      setTimeout(() => { STATE.voices = STATE.synth.getVoices(); resolve(STATE.voices); }, 2000);
    });
  }

  function handleFileSelect(e) {
    const file = e.target.files[0];
    if (!file) return;
    processFile(file);
  }

  function processFile(file) {
    STATE.uploadedFile = file;
    STATE.uploadedFileType = file.type;

    const badge = document.getElementById('cbFileBadge');
    const fname = document.getElementById('cbFName');
    const uploadBtn = document.getElementById('cbUploadBtn');
    const imgPreview = document.getElementById('cbImgPreview');

    fname.textContent = file.name.length > 14 ? file.name.slice(0, 12) + '…' : file.name;
    badge.classList.add('visible');
    uploadBtn.classList.add('has-file');

    if (file.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = (ev) => {
        imgPreview.src = ev.target.result;
        imgPreview.classList.add('visible');
        speak(`Image loaded: ${file.name}. Click Analyze File or say "analyze this" to process it.`);
      };
      reader.readAsDataURL(file);
    } else {
      imgPreview.classList.remove('visible');
      imgPreview.src = '';
      speak(`File loaded: ${file.name}. Ready for analysis.`);
    }
    setTranscript(`📎 ${file.name} loaded — say "analyze this" or click Analyze File`, 'cmd');
    addHistory('FILE', file.name + ' (' + formatBytes(file.size) + ')');
  }

  function analyzeUploadedFile() {
    if (!STATE.uploadedFile) {
      speak('Please upload a file first.');
      return;
    }
    const file = STATE.uploadedFile;
    if (file.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = (ev) => {
        sendVoiceQuery(`I uploaded an image called "${file.name}". Please help me analyze code or errors shown in this screenshot. Ask me to describe what you see.`);
      };
      reader.readAsDataURL(file);
    } else {
      const reader = new FileReader();
      reader.onload = (ev) => {
        const content = ev.target.result.slice(0, 4000);
        const ext = file.name.split('.').pop().toLowerCase();
        const query = `Please analyze this ${ext.toUpperCase()} file named "${file.name}":\n\n\`\`\`${ext}\n${content}\n\`\`\`\n\nExplain what this code does, identify any bugs, and suggest improvements.`;
        sendVoiceQuery(query);
      };
      reader.readAsText(file);
    }
  }

  function formatBytes(bytes) {
    if (bytes < 1024) return bytes + 'B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + 'KB';
    return (bytes / 1048576).toFixed(1) + 'MB';
  }

  function setupDragDrop() {
    const overlay = document.getElementById('cbDropOverlay');
    let dragCounter = 0;
    document.addEventListener('dragenter', e => { e.preventDefault(); dragCounter++; overlay.classList.add('active'); });
    document.addEventListener('dragleave', e => { dragCounter--; if (dragCounter === 0) overlay.classList.remove('active'); });
    document.addEventListener('dragover', e => { e.preventDefault(); });
    document.addEventListener('drop', e => {
      e.preventDefault(); dragCounter = 0; overlay.classList.remove('active');
      const file = e.dataTransfer?.files[0];
      if (file) processFile(file);
    });
  }

  function activateWakeWord() {
    STATE.wakeWordActive = true;
    const indicator = document.getElementById('cbWakeIndicator');
    const micBtn = document.getElementById('cbMicBtn');
    indicator.style.display = 'block';
    micBtn.classList.add('wake');
    speak('CodeBuddy activated. What would you like to code?');
    setTranscript('🎯 Wake word detected — I\'m listening!', 'cmd');
    setTimeout(() => {
      STATE.wakeWordActive = false;
      indicator.style.display = 'none';
      micBtn.classList.remove('wake');
    }, 30000);
  }

  function triggerRun() {
    const runBtn = document.querySelector('.run-btn.run-active') || document.querySelector('.run-btn');
    if (runBtn) { runBtn.click(); speak('Running your code.'); }
    else speak('No code block found to run. Please ask CodeBuddy to write some code first.');
  }

  function triggerDebug() {
    const lastCode = window.lastCodeBlock || '';
    if (lastCode) {
      sendVoiceQuery(`Debug this code and explain every bug and fix:\n\`\`\`\n${lastCode}\n\`\`\``);
    } else {
      sendVoiceQuery('Please debug the last code we discussed and explain any issues found.');
    }
    speak('Analyzing code for bugs.');
  }

  function triggerExplain() {
    const lastCode = window.lastCodeBlock || '';
    if (lastCode) {
      sendVoiceQuery(`Explain this code line by line in simple terms:\n\`\`\`\n${lastCode}\n\`\`\``);
    } else {
      sendVoiceQuery('Please explain the last code block in simple terms, line by line.');
    }
    speak('Generating explanation.');
  }

  function triggerOptimize() {
    const lastCode = window.lastCodeBlock || '';
    if (lastCode) {
      sendVoiceQuery(`Optimize this code for maximum performance and readability:\n\`\`\`\n${lastCode}\n\`\`\``);
    } else {
      sendVoiceQuery('Please optimize the last code block for performance and clean code principles.');
    }
    speak('Optimizing code.');
  }

  function triggerComplexity() {
    const lastCode = window.lastCodeBlock || '';
    if (lastCode) {
      sendVoiceQuery(`Analyze the Big O time and space complexity of this code with full explanation:\n\`\`\`\n${lastCode}\n\`\`\``);
    } else {
      sendVoiceQuery('Analyze the time and space complexity of the last code block.');
    }
    speak('Calculating complexity.');
  }

  function triggerTest() {
    const lastCode = window.lastCodeBlock || '';
    if (lastCode) {
      sendVoiceQuery(`Write comprehensive unit tests for this code covering edge cases:\n\`\`\`\n${lastCode}\n\`\`\``);
    } else {
      sendVoiceQuery('Write comprehensive unit tests for the last code block.');
    }
    speak('Writing unit tests.');
  }

  function triggerDocument() {
    const lastCode = window.lastCodeBlock || '';
    if (lastCode) {
      sendVoiceQuery(`Add professional documentation, docstrings, and JSDoc comments to this code:\n\`\`\`\n${lastCode}\n\`\`\``);
    } else {
      sendVoiceQuery('Add professional documentation and comments to the last code block.');
    }
    speak('Generating documentation.');
  }

  function triggerConvert() {
    speak('Which programming language would you like to convert this code to?');
    setTranscript('Say the target language name...', 'interim');
    setTimeout(() => CBVoice.startListening(), 1500);
  }

  function clearConversation() {
    if (confirm('Clear chat history?')) {
      const chatBox = document.getElementById('chatBox');
      if (chatBox) chatBox.innerHTML = '';
      speak('Conversation cleared.');
    }
  }

  function newSession() {
    if (typeof newChat === 'function') newChat();
    speak('Starting new session.');
  }

  function toggleCodeContext() {
    STATE.codeContext = !STATE.codeContext;
    const el = document.getElementById('cbCodeCtxToggle');
    if (el) el.textContent = STATE.codeContext ? 'ON' : 'OFF';
    speak('Code context ' + (STATE.codeContext ? 'enabled' : 'disabled'));
  }

  function setStatus(text, type) {
    const el = document.getElementById('cbStatus');
    if (!el) return;
    el.textContent = text;
    el.className = type || 'idle';
  }

  function setTranscript(text, type) {
    const el = document.getElementById('cbTranscript');
    if (!el) return;
    el.innerHTML = `<span class="${type || 'final'}">${text}</span>`;
  }

  function animateWaveformSpeak(active) {
    const bar = document.getElementById('cbVoiceBar');
    const waves = document.querySelectorAll('.cbWave');
    if (bar) bar.classList.toggle('speaking', active);
    waves.forEach((w) => {
      if (active) {
        const h = Math.random() * 24 + 4;
        w.style.height = h + 'px';
        w.style.opacity = '0.85';
      } else {
        w.style.height = '3px';
        w.style.opacity = '0.5';
      }
    });
    if (active && STATE.isSpeaking) {
      setTimeout(() => animateWaveformSpeak(true), 100);
    }
  }

  function addHistory(role, text) {
    const list = document.getElementById('cbHistoryList');
    if (!list) return;
    if (list.textContent === 'No voice interactions yet.') list.innerHTML = '';
    const entry = document.createElement('div');
    entry.className = 'cbHistEntry';
    const roleEl = document.createElement('div');
    roleEl.className = 'cbHistRole';
    roleEl.textContent = role;
    const textEl = document.createElement('div');
    textEl.className = 'cbHistText';
    textEl.textContent = text;
    entry.appendChild(roleEl);
    entry.appendChild(textEl);
    list.insertBefore(entry, list.firstChild);
    while (list.children.length > 20) list.removeChild(list.lastChild);
  }

  function hookAutoSpeak() {
    // hookAutoSpeak is intentionally disabled.
    // Auto-speak is handled directly in index.html after streaming completes
    // (speakText(full) is called once when the full response is ready).
    // Using a MutationObserver here caused two bugs:
    //   1. Timer reset on every streaming token → 2+ minute delay before audio
    //   2. Double-trigger (observer + speakText) → audio restarts from beginning
    // Solution: index.html calls speakText(full) → CBVoice.speak() → gTTS once, correctly.
  }

  window.CBVoice = {
    get autoSpeak() { return STATE.autoSpeak; },
    startListening() {
      if (!STATE.recognition) {
        STATE.recognition = initRecognition();
      }
      if (!STATE.recognition) { speak(LANGS[STATE.currentLang]?.noSupport || 'Not supported.'); return; }
      STATE.recognition.lang = STATE.currentLang;
      try { STATE.recognition.start(); }
      catch (e) { console.warn('Recognition start error:', e); }
      addHistory('MIC', 'Started listening in ' + (LANGS[STATE.currentLang]?.name || STATE.currentLang));
    },
    stopListening() {
      if (STATE.recognition) try { STATE.recognition.stop(); } catch (e) { }
      STATE.isListening = false;
      document.getElementById('cbMicBtn')?.classList.remove('active');
      document.getElementById('cbVoiceBar')?.classList.remove('listening');
      setStatus('IDLE', 'idle');
    },
    speak(text, lang) { speak(text, lang); },
    // Stop any running SpeechRecognition — Chrome allows only ONE at a time.
    // If voice-clone STT is still running when PLAY is clicked, it blocks
    // audio playback for up to 20 seconds until the STT session times out.
    stopSTT() {
      if (STATE.recognition) { try { STATE.recognition.stop(); } catch(e){} }
      if (window._vcSttRec) { try { window._vcSttRec.stop(); } catch(e){} window._vcSttRec = null; }
    },
    // Register callbacks for when audio actually starts/ends.
    // More reliable than polling getCurrentAudio() in a setInterval.
    setSpeakCallbacks(onStart, onEnd) {
      STATE.onSpeakStart = onStart || null;
      STATE.onSpeakEnd = onEnd || null;
    },
    stop() {
      if (_pendingController) { try { _pendingController.abort(); } catch(e){} _pendingController = null; }
      if (_currentAudio) { _currentAudio.pause(); _currentAudio = null; }
      STATE.synth?.cancel();
      STATE.isSpeaking = false;
      STATE.isPaused = false;
      animateWaveformSpeak(false);
      setStatus('IDLE', 'idle');
      const pb = document.getElementById('cbPauseBtn');
      if (pb) pb.textContent = '⏸';
      // Fire onSpeakEnd so PLAY button resets even on manual stop
      if (typeof STATE.onSpeakEnd === 'function') { STATE.onSpeakEnd(); STATE.onSpeakEnd = null; }
    },
    togglePause() {
      if (STATE.isPaused) { this.resume(); } else { this.pause(); }
    },
    pause() {
      // Abort any in-flight TTS fetch (user paused before audio loaded)
      if (_pendingController) { try { _pendingController.abort(); } catch(e){} _pendingController = null; }
      // Pause the gTTS <audio> element (primary audio source)
      if (_currentAudio && !_currentAudio.paused) _currentAudio.pause();
      // Also pause Web Speech API fallback
      STATE.synth?.pause();
      STATE.isPaused = true;
      STATE.isSpeaking = false;
      animateWaveformSpeak(false);
      setStatus('PAUSED', 'idle');
      const pb = document.getElementById('cbPauseBtn');
      if (pb) pb.textContent = '▶';
    },
    resume() {
      // Resume the gTTS <audio> element
      if (_currentAudio && _currentAudio.paused) _currentAudio.play();
      STATE.synth?.resume();
      STATE.isPaused = false;
      setStatus('SPEAKING', 'speaking');
      const pb = document.getElementById('cbPauseBtn');
      if (pb) pb.textContent = '⏸';
    },
    togglePanel() {
      STATE.isOpen = !STATE.isOpen;
      document.getElementById('cbVoicePanel')?.classList.toggle('hidden', !STATE.isOpen);
    },
    toggleAutoSpeak() {
      STATE.autoSpeak = !STATE.autoSpeak;
      const el = document.getElementById('cbAutoSpeak');
      if (el) el.classList.toggle('on', STATE.autoSpeak);
      speak('Auto speak ' + (STATE.autoSpeak ? 'enabled' : 'disabled'));
    },
    setLang(lang) {
      if (!LANG_TO_TTS[lang] && !LANGS[lang]) return;
      STATE.currentLang = lang;
      // Sync all language selectors
      ['cbLangSel', 'cbLangSel2', 'voiceLang'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = lang;
      });
      // Recognition uses Tamil for Tanglish (user speaks Tamil, AI replies in Tanglish)
      const recogLang = (lang === 'ta-en') ? 'ta-IN' : lang;
      if (STATE.recognition) STATE.recognition.lang = recogLang;
      // Speak greeting in the new language
      const greeting = LANGS[lang] ? LANGS[lang].greet : 'Language changed.';
      speak(greeting, lang);
      addHistory('LANG', (LANGS[lang] ? LANGS[lang].name : lang) + ' selected');
      // Show hint in transcript
      const hints = {
        'ta-IN': '🇮🇳 Tamil mode — text and voice fully in Tamil',
        'ta-en': '🇮🇳 Tanglish mode — text in English letters, voice in Tamil',
        'hi-IN': '🇮🇳 Hindi mode — text and voice in Hindi',
        'te-IN': '🇮🇳 Telugu mode — text and voice in Telugu',
        'kn-IN': '🇮🇳 Kannada mode — text and voice in Kannada',
        'ml-IN': '🇮🇳 Malayalam mode — text and voice in Malayalam',
        'en-US': '🇺🇸 English mode',
      };
      setTranscript(hints[lang] || ('🌐 ' + (LANGS[lang] ? LANGS[lang].name : lang) + ' mode active'), 'cmd');
    },
    // Called by VoiceClone after voice is uploaded and language detected.
    // Pass null to RESET (after delete) — restores UI language selector.
    setDetectedLang(lang, langName) {
      if (!lang) {
        // RESET — profile was deleted
        window._vcDetectedLang = null;
        window._hasVoiceClone = false;
        // Restore to whatever the UI selector shows
        const sel = document.getElementById('cbLangSel') || document.getElementById('cbLangSel2');
        const uiLang = (sel && sel.value) ? sel.value : 'en-US';
        STATE.currentLang = uiLang;
        const recogLang = (uiLang === 'ta-en') ? 'ta-IN' : uiLang;
        if (STATE.recognition) STATE.recognition.lang = recogLang;
        setTranscript('🎙 Voice profile deleted — using language selector', 'cmd');
        return;
      }
      window._vcDetectedLang = lang;
      window._hasVoiceClone = true;
      STATE.currentLang = lang;
      ['cbLangSel', 'cbLangSel2', 'voiceLang'].forEach(id => {
        const el = document.getElementById(id);
        if (el) { const opt = [...el.options].find(o => o.value === lang); if (opt) el.value = lang; }
      });
      const recogLang = (lang === 'ta-en') ? 'ta-IN' : lang;
      if (STATE.recognition) STATE.recognition.lang = recogLang;
      setTranscript('🎙 Voice profile active — speaking in ' + (langName || lang), 'cmd');
      addHistory('VC', 'Voice language locked: ' + (langName || lang));
    },
    setRate(v) { STATE.rate = v; },
    setPitch(v) { STATE.pitch = v; },
    setVolume(v) { STATE.volume = v; },
    clearFile() {
      STATE.uploadedFile = null;
      STATE.uploadedFileType = null;
      document.getElementById('cbFileBadge')?.classList.remove('visible');
      document.getElementById('cbUploadBtn')?.classList.remove('has-file');
      document.getElementById('cbImgPreview')?.classList.remove('visible');
      document.getElementById('cbFileInput').value = '';
    },
    testVoice() {
      const msgs = {
        'en-US': 'CodeBuddy Neural Voice is working. Ready to help with Python, JavaScript, and any programming language.',
        'ta-IN': 'கோட்பட்டி தயார். Python, JavaScript மற்றும் எந்த programming language-லும் உதவ முடியும்.',
        'ta-en': 'Dei CodeBuddy ready bro! Python yaandral enna, function yaandral enna, ellame solluven. Type pannu, autocomplete varum!',
        'hi-IN': 'CodeBuddy Neural Voice sahi kaam kar raha hai. Python, JavaScript aur kisi bhi programming language mein help kar sakta hoon.',
        'te-IN': 'కోడ్‌బడ్డీ సిద్ధంగా ఉంది. Python, JavaScript మరియు ఏ programming language లోనైనా సహాయపడగలను.',
        'kn-IN': 'ಕೋಡ್‌ಬಡ್ಡಿ ಸಿದ್ಧವಾಗಿದೆ. Python, JavaScript ಮತ್ತು ಯಾವುದೇ programming language ನಲ್ಲಿ ಸಹಾಯ ಮಾಡಬಲ್ಲೆ.',
        'ml-IN': 'കോഡ്ബഡ്ഡി തയ്യാർ. Python, JavaScript, ഏത് programming language ലും സഹായിക്കാം.',
        'bn-IN': 'কোডবাডি প্রস্তুত। Python, JavaScript এবং যেকোনো programming language এ সাহায্য করতে পারি।',
        'mr-IN': 'कोडबडी तयार आहे. Python, JavaScript आणि कोणत्याही programming language मध्ये मदत करू शकतो.',
      };
      const lang = STATE.currentLang;
      speak(msgs[lang] || msgs['en-US'], lang);
    },
    analyzeFile() { analyzeUploadedFile(); },

    // CHANGE 5: Memory UI — show stored memory as voice readout
    showMemory() {
      fetch('/get_memory')
        .then(r => r.json())
        .then(data => {
          const mem = data.memory || {};
          const keys = Object.keys(mem);
          if (!keys.length) {
            speak("No memory stored yet. I'll learn your preferences as we code together.");
            return;
          }
          const summary = keys.map(k => `${k}: ${mem[k]}`).join('. ');
          speak('Here is what I remember about you: ' + summary);
          setTranscript('🧠 Memory: ' + summary, 'cmd');
        })
        .catch(() => speak('Could not load memory.'));
    },

    // CHANGE 9: Share streak as SVG card
    shareStreak() {
      const username = document.querySelector('[data-username]')?.dataset?.username
                    || document.title.replace('CodeBuddy - ', '') || 'coder';
      const url = `/streak_card/${username}.svg`;
      window.open(url, '_blank');
      speak(`Opening your streak card for ${username}. Share it on social media!`);
    },

    // CHANGE 7: Install PWA
    installPWA() {
      if (STATE._deferredInstall) {
        STATE._deferredInstall.prompt();
        STATE._deferredInstall.userChoice.then(choice => {
          if (choice.outcome === 'accepted') speak('CodeBuddy installed! You can now use it offline.');
          STATE._deferredInstall = null;
        });
      } else {
        speak('Open this page in Chrome and tap the install button in the address bar.');
      }
    },
  };

  function init() {
    if (STATE.initialized) return;
    STATE.initialized = true;
    injectStyles();
    buildUI();
    waitForVoices().then(voices => {
      STATE.voices = voices;
    });
    hookAutoSpeak();
    STATE.recognition = initRecognition();
    const mainLang = document.getElementById('voiceLang');
    if (mainLang) {
      mainLang.addEventListener('change', e => CBVoice.setLang(e.target.value));
    }

    // CHANGE 7: Register service worker for PWA
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js')
        .then(() => console.log('[CBVoice] SW registered'))
        .catch(e => console.warn('[CBVoice] SW registration failed:', e));
    }

    // CHANGE 7: Capture install prompt for later
    window.addEventListener('beforeinstallprompt', e => {
      e.preventDefault();
      STATE._deferredInstall = e;
      // Show a subtle install hint in transcript
      setTimeout(() => {
        setTranscript('📱 Install CodeBuddy as app — say "install app" or click ⊕', 'cmd');
      }, 3000);
    });

    // CHANGE 9: Load leaderboard rank into state
    fetch('/api/leaderboard')
      .then(r => r.json())
      .then(data => {
        STATE._leaderboard = data.leaderboard || [];
      })
      .catch(() => {});

    setTimeout(() => {
      setTranscript('⚡ CodeBuddy Neural Voice Engine v4.0 ready — Click 🎤 or say "Hey Buddy"', 'cmd');
    }, 800);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  window.switchPTab = switchPTab;
  window.triggerRun = triggerRun;
  window.triggerDebug = triggerDebug;
  window.triggerExplain = triggerExplain;
  window.triggerOptimize = triggerOptimize;
  window.triggerComplexity = triggerComplexity;
  window.triggerTest = triggerTest;
  window.triggerDocument = triggerDocument;
  window.triggerConvert = triggerConvert;
  window.toggleCodeContext = toggleCodeContext;
  window.analyzeUploadedFile = analyzeUploadedFile;
  window.activateWakeWord = activateWakeWord;
  window.clearConversation = clearConversation;
  window.newSession = newSession;
  window.sendVoiceQuery = sendVoiceQuery;
  window.speak = speak;

})(); // end IIFE