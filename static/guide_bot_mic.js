// =============================================================
//  guide_bot_mic.js — «Robi» ESHITADI: mikrofon yozuvi (2026-11-03)
//  getUserMedia -> AudioContext -> ScriptProcessor (Telegram WebView'da ham ishlaydi) -> telefonning
//  o'zida 16 kHz, 16-bit, mono WAV ga aylantiriladi -> POST /robi/stt?lang= -> {text}.
//  Serverda ffmpeg kerak emas. Eng uzoq yozuv — GBOT_MIC_MAX_MS (server chegarasidan kam).
//  Telegram ba'zi telefonlarda mikrofonga ruxsat bermasligi mumkin — unda xato qaytadi, yozib so'rash qoladi.
//  Global: API_BASE, APP. guide_bot_ask.js chaqiradi.
// =============================================================

const GBOT_MIC = { stream: null, ctx: null, src: null, proc: null, chunks: [], rate: 0, timer: null, on: false };
const GBOT_MIC_MAX_MS = 12000;      // server ROBI_STT_MAX_SEC (15) dan kam
const GBOT_MIC_OUT_RATE = 16000;
const GBOT_MIC_BUF = 4096;
const GBOT_MIC_SILENCE = 0.012;     // shundan past — hech narsa aytilmagan

function gbotMicSupported() {
  return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia
    && (window.AudioContext || window.webkitAudioContext));
}

// Yozishni boshlaydi. onAutoStop — eng uzoq vaqt tugaganda chaqiriladi.
async function gbotMicStart(onAutoStop) {
  if (GBOT_MIC.on) return;
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true },
  });
  const C = window.AudioContext || window.webkitAudioContext;
  const ctx = new C();
  if (ctx.state === "suspended") await ctx.resume().catch(() => {});
  const src = ctx.createMediaStreamSource(stream);
  const proc = ctx.createScriptProcessor(GBOT_MIC_BUF, 1, 1);
  GBOT_MIC.chunks = [];
  proc.onaudioprocess = (e) => { if (GBOT_MIC.on) GBOT_MIC.chunks.push(new Float32Array(e.inputBuffer.getChannelData(0))); };
  src.connect(proc);
  proc.connect(ctx.destination);                 // ScriptProcessor faqat ulanganda ishlaydi (chiqish — jim)
  Object.assign(GBOT_MIC, { stream, ctx, src, proc, rate: ctx.sampleRate, on: true });
  GBOT_MIC.timer = setTimeout(() => { if (GBOT_MIC.on && onAutoStop) onAutoStop(); }, GBOT_MIC_MAX_MS);
}

function gbotMicRelease() {
  clearTimeout(GBOT_MIC.timer);
  GBOT_MIC.on = false;
  try { GBOT_MIC.proc && GBOT_MIC.proc.disconnect(); } catch (_) { /* yo'q */ }
  try { GBOT_MIC.src && GBOT_MIC.src.disconnect(); } catch (_) { /* yo'q */ }
  try { GBOT_MIC.stream && GBOT_MIC.stream.getTracks().forEach(t => t.stop()); } catch (_) { /* yo'q */ }
  try { GBOT_MIC.ctx && GBOT_MIC.ctx.close(); } catch (_) { /* yo'q */ }
  Object.assign(GBOT_MIC, { stream: null, ctx: null, src: null, proc: null });
}

// Panel yopilganda — yozuvni tashlab yuboradi
function gbotMicCancel() {
  if (GBOT_MIC.on || GBOT_MIC.stream) gbotMicRelease();
  GBOT_MIC.chunks = [];
}

// Yozuvni to'xtatadi -> WAV Blob, yoki null (jimlik / juda qisqa)
function gbotMicStop() {
  const rate = GBOT_MIC.rate;
  const chunks = GBOT_MIC.chunks;
  gbotMicRelease();
  GBOT_MIC.chunks = [];
  const total = chunks.reduce((n, c) => n + c.length, 0);
  if (!total || !rate) return null;
  const all = new Float32Array(total);
  let off = 0, peak = 0;
  chunks.forEach(c => { all.set(c, off); off += c.length; });
  for (let i = 0; i < all.length; i++) peak = Math.max(peak, Math.abs(all[i]));
  if (peak < GBOT_MIC_SILENCE) return null;
  return gbotMicWav(gbotMicDownsample(all, rate, GBOT_MIC_OUT_RATE), GBOT_MIC_OUT_RATE);
}

function gbotMicDownsample(buf, from, to) {
  if (from === to) return buf;
  const ratio = from / to, len = Math.floor(buf.length / ratio), out = new Float32Array(len);
  for (let i = 0; i < len; i++) {
    const a = Math.floor(i * ratio), b = Math.min(buf.length, Math.floor((i + 1) * ratio));
    let s = 0;
    for (let j = a; j < b; j++) s += buf[j];
    out[i] = b > a ? s / (b - a) : 0;
  }
  return out;
}

function gbotMicWav(samples, rate) {
  const view = new DataView(new ArrayBuffer(44 + samples.length * 2));
  const str = (o, s) => { for (let i = 0; i < s.length; i++) view.setUint8(o + i, s.charCodeAt(i)); };
  str(0, "RIFF"); view.setUint32(4, 36 + samples.length * 2, true); str(8, "WAVE");
  str(12, "fmt "); view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, 1, true);
  view.setUint32(24, rate, true); view.setUint32(28, rate * 2, true); view.setUint16(32, 2, true);
  view.setUint16(34, 16, true); str(36, "data"); view.setUint32(40, samples.length * 2, true);
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return new Blob([view], { type: "audio/wav" });
}

// WAV -> matn (server). Qaytaradi: { text } | { error: "mic_fail" | "mic_quota" }
async function gbotMicTranscribe(wav) {
  const lang = (typeof APP !== "undefined" && APP.lang) || "uz";
  try {
    const r = await fetch(`${API_BASE}/robi/stt?lang=${encodeURIComponent(lang)}`, {
      method: "POST", body: wav,
      headers: { "Content-Type": "audio/wav", "X-Telegram-Init-Data": window.Telegram?.WebApp?.initData || "" },
    });
    if (r.status === 429) return { error: "mic_quota" };
    if (!r.ok) return { error: "mic_fail" };
    const js = await r.json();
    return js && js.text ? { text: String(js.text) } : { error: "mic_fail" };
  } catch (_) {
    return { error: "mic_fail" };
  }
}
