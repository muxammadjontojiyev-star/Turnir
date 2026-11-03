// =============================================================
//  guide_bot_ask.js — «Robi»GA SAVOL BERISH oynasi (2026-11-03)
//  Gaplashish oynasida «💬 Robiga savol berish» -> savol yoziladi yoki 🎤 bilan aytiladi -> javob
//  bilimlar bazasidan (guide_bot_faq.js, BEPUL, faqat bot mavzusi) topiladi va Robi uni yozib, ovoz
//  chiqarib aytadi. Topilmasa — «faqat bot haqida javob beraman» va savol namunalari (tugmalar).
//  Mikrofon tugmasi — server STT yoqilgan (/robi/status stt) va telefon qo'llasa (guide_bot_mic.js).
//  Foydalanuvchi matni faqat escHtml bilan chiqariladi (qoida: XSS). guide_bot_panel.js dan KEYIN ulanadi.
//  Global: APP, GBOT, GBOT_TTS, escHtml, gbotType, gbotSpeakStop, gbotAct, gbotHaptic, gbotSfx, gbotFaq*.
// =============================================================

const GBOT_ASK = { on: false, busy: false };
const GBOT_ASK_MAX = 200;           // savol uzunligi
const GBOT_ASK_CHIPS = 3;           // namuna savollar soni
const GBOT_ASK_CHIPS_AFTER = 2;     // javobdan keyingi namunalar

function gbotAskLang() { return (typeof APP !== "undefined" && APP.lang) || "uz"; }
function gbotAskUi() { return gbotFaqData(gbotAskLang()).ui; }

function gbotAskButtonHtml() {
  if (typeof GBOT_FAQ === "undefined" || !GBOT_FAQ.uz) return "";
  return `<button class="gbot-ask-open" data-gbask="open">${escHtml(gbotAskUi().ask_btn)}</button>`;
}

function gbotAskMicOk() {
  return typeof gbotMicSupported === "function" && gbotMicSupported()
    && typeof GBOT_TTS !== "undefined" && GBOT_TTS.status && GBOT_TTS.status.stt;
}

function gbotAskReset() {
  GBOT_ASK.on = false;
  GBOT_ASK.busy = false;
  document.getElementById("gbot-you")?.remove();
  document.getElementById("gbot-dots")?.classList.remove("hidden");
  document.getElementById("gbot-big-bot")?.classList.remove("is-listen");
}

function gbotAskYou(text) {
  let you = document.getElementById("gbot-you");
  if (!you) {
    you = document.createElement("div");
    you.id = "gbot-you";
    you.className = "gbot-you";
    document.getElementById("gbot-bubble").before(you);
  }
  you.innerHTML = `<small>${escHtml(gbotAskUi().you)}</small>${escHtml(text)}`;
}

function gbotAskControls(items) {
  const u = gbotAskUi();
  const chips = items.map(it => `<button class="gbot-chip" data-gbask="q" data-q="${escHtml(it.q)}">${escHtml(it.q)}</button>`).join("");
  document.getElementById("gbot-actions").innerHTML = `<div class="gbot-chips">${chips}</div>
    <div class="gbot-ask-row">
      <input class="gbot-ask-in" id="gbot-ask-in" type="text" maxlength="${GBOT_ASK_MAX}" placeholder="${escHtml(u.ph)}" enterkeyhint="send">
      ${gbotAskMicOk() ? `<button class="gbot-ask-btn gbot-ask-mic" id="gbot-ask-mic" data-gbask="mic" aria-label="${escHtml(u.mic)}">🎤</button>` : ""}
      <button class="gbot-ask-btn gbot-ask-send" data-gbask="send" aria-label="${escHtml(u.send)}">➤</button>
    </div>
    <button class="gbot-act gbot-ask-back" data-gbask="back">${escHtml(u.back)}</button>`;
}

// Robi gapiradi (speak=false — faqat yozuv, masalan «Eshityapman…»)
function gbotAskSay(text, speak) {
  if (speak) { gbotType(text, false); return; }
  clearInterval(GBOT.typeT);
  GBOT.typeT = null;
  gbotSpeakStop();
  document.getElementById("gbot-text").innerHTML = gbotFmt(text);
  document.getElementById("gbot-big-bot")?.classList.remove("is-talk");
}

function gbotAskOpen() {
  GBOT_ASK.on = true;
  gbotSpeakStop();
  document.getElementById("gbot-dots")?.classList.add("hidden");
  gbotAct(document.getElementById("gbot-big-bot"), "is-hop");
  gbotSfx("next");
  gbotAskControls(gbotFaqSuggest(gbotAskLang(), GBOT.ctx, GBOT_ASK_CHIPS));
  gbotAskSay(gbotAskUi().hello, true);
}

function gbotAskSend(raw) {
  const text = String(raw || "").replace(/\s+/g, " ").trim().slice(0, GBOT_ASK_MAX);
  if (!text || GBOT_ASK.busy) return;
  gbotHaptic("light");
  gbotAskYou(text);
  const lang = gbotAskLang();
  const hit = gbotFaqFind(text, lang, GBOT.ctx);
  const bot = document.getElementById("gbot-big-bot");
  if (hit) {
    gbotAct(bot, "is-happy");
    gbotAskSay(hit.a, true);
    gbotAskControls(gbotFaqSuggest(lang, GBOT.ctx, GBOT_ASK_CHIPS_AFTER, hit.id));
  } else {
    gbotAct(bot, "is-look");
    gbotAskSay(gbotAskUi().not_found, true);
    gbotAskControls(gbotFaqSuggest(lang, GBOT.ctx, GBOT_ASK_CHIPS));
  }
  document.getElementById("gbot-ask-in")?.blur();
}

async function gbotAskMic() {
  const u = gbotAskUi();
  const btn = document.getElementById("gbot-ask-mic");
  const bot = document.getElementById("gbot-big-bot");
  if (GBOT_ASK.busy) return;
  if (typeof GBOT_MIC !== "undefined" && GBOT_MIC.on) { await gbotAskMicFinish(); return; }
  try {
    gbotSpeakStop();
    await gbotMicStart(() => gbotAskMicFinish());
  } catch (_) {
    gbotAskSay(u.mic_denied, false);
    return;
  }
  gbotHaptic("medium");
  btn?.classList.add("is-rec");
  bot?.classList.add("is-listen");
  gbotAskSay(u.listening, false);
}

async function gbotAskMicFinish() {
  const u = gbotAskUi();
  document.getElementById("gbot-ask-mic")?.classList.remove("is-rec");
  document.getElementById("gbot-big-bot")?.classList.remove("is-listen");
  const wav = gbotMicStop();
  if (!wav) { gbotAskSay(u.mic_fail, false); return; }
  GBOT_ASK.busy = true;
  gbotAskSay(u.thinking, false);
  const res = await gbotMicTranscribe(wav);
  GBOT_ASK.busy = false;
  if (!GBOT.open || !GBOT_ASK.on) return;
  if (res.text) gbotAskSend(res.text);
  else gbotAskSay(u[res.error] || u.mic_fail, false);
}

document.addEventListener("click", (e) => {
  const b = e.target.closest("[data-gbask]");
  if (!b || !GBOT.open) return;
  const act = b.dataset.gbask;
  if (act === "open") gbotAskOpen();
  else if (act === "back") { gbotMicCancel(); gbotAskReset(); gbotRender(); }
  else if (act === "q") gbotAskSend(b.dataset.q);
  else if (act === "send") gbotAskSend(document.getElementById("gbot-ask-in")?.value);
  else if (act === "mic") gbotAskMic();
});

document.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && e.target && e.target.id === "gbot-ask-in") {
    e.preventDefault();
    gbotAskSend(e.target.value);
  }
});
