// =============================================================
//  guide_bot_voice.js — «Robi» OVOZI (2026-11-03)
//  1) O'z ovozi — robotcha «bip-bup» (WebAudio, fayl kerak emas, hamma tilda ishlaydi):
//     matn yozilayotganda har harfga qisqa ohang, ochilish/yopilish/xursandlik ohanglari.
//  2) Haqiqiy nutq — server ovozi (guide_bot_tts.js, Azure bepul tarif) bo'lsa o'sha, aks holda
//     qurilmadagi shu til ovozi (speechSynthesis). Ikkalasi ham yo'q bo'lsa 🗣 tugma ko'rinmaydi.
//     2026-11-03: haqiqiy nutq standart YOQILGAN (GBOT_VOICE.speak = true).
//  Brauzer tovushni faqat bosishdan keyin ruxsat beradi — birinchi ohang panel ochilganda.
//  Global: APP. guide_bot.js dan OLDIN ulanadi.
// =============================================================

const GBOT_VOICE = { ac: null, muted: false, speak: true };
const GBOT_TONE_BASE = 520;      // Hz — robot «ovozi» asosiy balandligi
const GBOT_TONE_STEP = 38;       // Hz — harfga qarab o'zgarish qadami
const GBOT_TONE_STEPS = 9;       // nechta xil balandlik
const GBOT_TONE_VOWEL = 140;     // Hz — unli harflar biroz balandroq
const GBOT_TONE_SEC = 0.055;     // har «bip» davomiyligi
const GBOT_TONE_VOL = 0.05;      // ovoz balandligi (0..1)
const GBOT_VOWELS = "aeiouyаеёиоуыэюяʻ";
const GBOT_SPEECH_RATE = 1.05;
const GBOT_SPEECH_PITCH = 1.35;  // biroz «robotcha» baland ovoz

function gbotAc() {
  if (GBOT_VOICE.muted) return null;
  if (!GBOT_VOICE.ac) {
    const C = window.AudioContext || window.webkitAudioContext;
    if (!C) return null;
    try { GBOT_VOICE.ac = new C(); } catch (_) { return null; }
  }
  if (GBOT_VOICE.ac.state === "suspended") GBOT_VOICE.ac.resume().catch(() => {});
  return GBOT_VOICE.ac;
}

// Bitta ohang: freq -> slide (Hz), delay soniya keyin boshlanadi
function gbotTone(freq, slide, dur, delay, vol, type) {
  const ac = gbotAc();
  if (!ac) return;
  try {
    const t = ac.currentTime + (delay || 0);
    const o = ac.createOscillator(), g = ac.createGain();
    o.type = type || "triangle";
    o.frequency.setValueAtTime(freq, t);
    if (slide) o.frequency.exponentialRampToValueAtTime(slide, t + dur);
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(vol || GBOT_TONE_VOL, t + 0.012);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.connect(g);
    g.connect(ac.destination);
    o.start(t);
    o.stop(t + dur + 0.03);
  } catch (_) { /* ovoz ishlamasa — jim */ }
}

// Harf «bip»i — matn yozilayotganda (haqiqiy nutq yoqilgan bo'lsa — jim)
function gbotChirp(ch) {
  if (GBOT_VOICE.speak && gbotCanSpeak()) return;
  const c = (ch || "a").toLowerCase();
  const f = GBOT_TONE_BASE + (c.codePointAt(0) % GBOT_TONE_STEPS) * GBOT_TONE_STEP
    + (GBOT_VOWELS.includes(c) ? GBOT_TONE_VOWEL : 0);
  gbotTone(f, f * 1.18, GBOT_TONE_SEC, 0, GBOT_TONE_VOL, "square");
}

const GBOT_SFX = {
  hello: () => { gbotTone(660, 990, 0.12, 0); gbotTone(990, 1320, 0.14, 0.11); },
  next:  () => gbotTone(740, 1040, 0.08, 0),
  happy: () => { [660, 880, 1100, 1320].forEach((f, i) => gbotTone(f, f * 1.05, 0.09, i * 0.08)); },
  bye:   () => { gbotTone(990, 660, 0.14, 0); gbotTone(660, 440, 0.16, 0.13); },
};
function gbotSfx(name) { if (GBOT_SFX[name]) GBOT_SFX[name](); }

// ---- haqiqiy nutq ----
// guide_bot_tts.js server ovozi bilan qayta tayinlaydi (gbotCanSpeak, gbotSpeak, gbotSpeakStop, gbotIsSpeaking)
function gbotCanSpeak() { return !!gbotSpeechVoice(); }
function gbotIsSpeaking() {
  try { return !!(window.speechSynthesis && window.speechSynthesis.speaking); } catch (_) { return false; }
}

function gbotSpeechVoice() {
  const s = window.speechSynthesis;
  if (!s || typeof s.getVoices !== "function") return null;
  const lang = (typeof APP !== "undefined" && APP.lang) || "uz";
  try { return s.getVoices().find(v => (v.lang || "").toLowerCase().startsWith(lang)) || null; }
  catch (_) { return null; }
}

function gbotSpeak(text) {
  gbotSpeakStop();
  const v = GBOT_VOICE.speak && !GBOT_VOICE.muted ? gbotSpeechVoice() : null;
  if (!v) return;
  try {
    const plain = String(text || "").replace(/\*\*/g, "")
      .replace(/[\u{1F000}-\u{1FAFF}\u{2600}-\u{27BF}\u{2B00}-\u{2BFF}\u{FE0F}\u{200D}]/gu, "");
    const u = new SpeechSynthesisUtterance(plain);
    u.voice = v;
    u.lang = v.lang;
    u.rate = GBOT_SPEECH_RATE;
    u.pitch = GBOT_SPEECH_PITCH;
    window.speechSynthesis.speak(u);
  } catch (_) { /* nutq ishlamasa — matn baribir ko'rinadi */ }
}

function gbotSpeakStop() {
  try { if (window.speechSynthesis) window.speechSynthesis.cancel(); } catch (_) { /* yo'q */ }
}

// Ovozlar ro'yxati kech yuklanadi — oldindan so'rab qo'yamiz
try { if (window.speechSynthesis) window.speechSynthesis.getVoices(); } catch (_) { /* yo'q */ }
