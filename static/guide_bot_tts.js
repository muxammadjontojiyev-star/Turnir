// =============================================================
//  guide_bot_tts.js — «Robi» HAQIQIY OVOZDA gapiradi (2026-11-03)
//  Server (robi_api.py, Azure bepul tarif): POST /robi/tts {text, lang} -> mp3. Server har matnni bir
//  marta yaratib keshlaydi; bu yerda ham sessiya davomida xotirada saqlanadi va keyingi gap oldindan
//  yuklanadi — gaplar kutishsiz eshitiladi.
//  Ijro — WebAudio orqali (guide_bot_voice.js gbotAc): AudioContext bosish paytida yoqiladi, keyin
//  Telegram WebView'da ham har gapda qayta ruxsat kerak bo'lmaydi.
//  Gap davomiyligi ma'lum bo'lgach yozish tezligi ovozga moslanadi (GBOT._retime, guide_bot_panel.js).
//  Server ovozi bo'lmasa / limit tugasa — qurilma ovozi yoki «bip-bup» (avvalgidek).
//  guide_bot_voice.js dagi gbotCanSpeak / gbotSpeak / gbotSpeakStop / gbotIsSpeaking qayta tayinlanadi.
//  Global: APP, API_BASE, apiFetch, GBOT, GBOT_VOICE, gbotAc. guide_bot_panel.js dan KEYIN ulanadi.
// =============================================================

const GBOT_TTS = { status: null, statusP: null, cache: new Map(), src: null, seq: 0, playing: false };
const GBOT_TTS_CACHE_MAX = 40;          // xotiradagi tayyor ovozlar soni
const GBOT_TTS_STATUS_WAIT_MS = 1500;   // birinchi ochilishda server javobini kutish

// Server ovozi bormi (bir marta so'raladi). Xato bo'lsa — yo'q deb hisoblanadi.
function gbotTtsStatus() {
  if (GBOT_TTS.status) return Promise.resolve(GBOT_TTS.status);
  if (!GBOT_TTS.statusP) {
    GBOT_TTS.statusP = apiFetch("/robi/status")
      .then(s => (GBOT_TTS.status = s || {}))
      .catch(() => (GBOT_TTS.status = {}));
  }
  const wait = new Promise(r => setTimeout(() => r(GBOT_TTS.status || {}), GBOT_TTS_STATUS_WAIT_MS));
  return Promise.race([GBOT_TTS.statusP, wait]);
}

function gbotTtsOn() { return !!(GBOT_TTS.status && GBOT_TTS.status.tts); }

function gbotTtsLang() { return (typeof APP !== "undefined" && APP.lang) || "uz"; }

// mp3 ni yuklaydi (ArrayBuffer) — sessiya keshi bilan
function gbotTtsFetch(text) {
  const key = gbotTtsLang() + "|" + text;
  if (GBOT_TTS.cache.has(key)) return GBOT_TTS.cache.get(key);
  const initData = window.Telegram?.WebApp?.initData || "";
  const p = fetch(API_BASE + "/robi/tts", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Telegram-Init-Data": initData },
    body: JSON.stringify({ text, lang: gbotTtsLang() }),
  }).then(r => {
    if (r.ok) return r.arrayBuffer();
    if (r.status === 429 || r.status === 503) GBOT_TTS.status = { ...(GBOT_TTS.status || {}), tts: false };  // limit / o'chiq
    return null;
  }).catch(() => null);
  p.then(b => { if (!b) GBOT_TTS.cache.delete(key); });   // xato keshda qolmasin
  GBOT_TTS.cache.set(key, p);
  if (GBOT_TTS.cache.size > GBOT_TTS_CACHE_MAX) GBOT_TTS.cache.delete(GBOT_TTS.cache.keys().next().value);
  return p;
}

function gbotTtsTalkOff() {
  if (GBOT.typeT) return;                                  // hali yozilyapti — og'iz to'xtamaydi
  document.getElementById("gbot-big-bot")?.classList.remove("is-talk");
}

const _gbotDeviceSpeak = gbotSpeak;
const _gbotDeviceStop = gbotSpeakStop;
const _gbotDeviceCan = gbotCanSpeak;
const _gbotDeviceSpeaking = gbotIsSpeaking;

gbotCanSpeak = function () { return gbotTtsOn() || _gbotDeviceCan(); };
gbotIsSpeaking = function () { return GBOT_TTS.playing || _gbotDeviceSpeaking(); };

gbotSpeakStop = function () {
  GBOT_TTS.seq += 1;
  if (GBOT_TTS.src) { try { GBOT_TTS.src.stop(); } catch (_) { /* allaqachon to'xtagan */ } GBOT_TTS.src = null; }
  GBOT_TTS.playing = false;
  _gbotDeviceStop();
};

gbotSpeak = function (text) {
  gbotSpeakStop();
  if (GBOT_VOICE.muted || !GBOT_VOICE.speak) return;
  if (!gbotTtsOn()) { _gbotDeviceSpeak(text); return; }
  const ac = gbotAc();
  if (!ac) return;
  const seq = GBOT_TTS.seq;
  gbotTtsFetch(text).then(buf => {
    if (!buf || seq !== GBOT_TTS.seq) return;
    return ac.decodeAudioData(buf.slice(0)).then(audio => {
      if (seq !== GBOT_TTS.seq) return;
      const src = ac.createBufferSource();
      src.buffer = audio;
      src.connect(ac.destination);
      src.onended = () => { if (GBOT_TTS.src === src) { GBOT_TTS.src = null; GBOT_TTS.playing = false; gbotTtsTalkOff(); } };
      GBOT_TTS.src = src;
      GBOT_TTS.playing = true;
      document.getElementById("gbot-big-bot")?.classList.add("is-talk");
      src.start();
      if (typeof GBOT._retime === "function") GBOT._retime(audio.duration * 1000);
    });
  }).catch(() => { GBOT_TTS.playing = false; });
};

// Keyingi gapni oldindan yuklab qo'yish (gbotRender chaqiradi)
function gbotTtsPrefetch(text) {
  if (text && gbotTtsOn() && GBOT_VOICE.speak && !GBOT_VOICE.muted) gbotTtsFetch(text);
}
