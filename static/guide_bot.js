// =============================================================
//  guide_bot.js — YO'L KO'RSATUVCHI ROBOT «Robi» (2026-11-03, egasi so'rovi)
//  Bo'limlar sahifasida (hub) — bo'limlar turi, farqi va vazifasi; rejimlar sahifasida — rejimlar
//  qanday bog'langani; har rejim ichida (bosh sahifasida) — o'sha rejim haqida. Do'stona gapiradi,
//  o'z ovozi (guide_bot_voice.js) va harakatlari (guide_bot.css) bor.
//  Kontekst DOM'dan aniqlanadi (qm.js FAB naqshi) — boshqa fayllarga tegilmaydi.
//  Birinchi kirishda har sahifada bir marta qisqa «hint» chiqadi; bosilsa — gaplashish oynasi.
//  Sozlamalar (ovoz, yashirish, ko'rilgan sahifalar) — localStorage (try/catch; ishlamasa ham ishlaydi).
//  Matnlar: guide_bot_uz/ru/en.js (GBOT_I18N). Global: APP, escHtml, openGuide (guide.js), GUIDE, QM.
// =============================================================

const GBOT = { ctx: null, open: false, i: 0, n: 0, typeT: null, hintT: null, idleT: null, mini: false, seen: {} };
const GBOT_KEY = "gbot_v1";
const GBOT_TICK_MS = 700;       // kontekstni tekshirish oralig'i
const GBOT_TYPE_MS = 24;        // bitta harf yozilish vaqti
const GBOT_TYPE_MAX_MS = 110;   // ovozga moslanganda eng sekin
const GBOT_TYPE_SYNC = 0.92;    // yozuv ovozdan biroz oldin tugaydi
const GBOT_CHIRP_EVERY = 2;     // har nechta harfga bitta «bip»
const GBOT_HINT_DELAY_MS = 900;
const GBOT_HINT_MS = 7000;      // hint qancha turadi
const GBOT_IDLE_MS = 9000;      // bekor turganda harakat oralig'i
const GBOT_ACT_MS = 1700;       // bitta harakat davomiyligi
const GBOT_BYE_MS = 1600;
const GBOT_IDLE_ACTS = ["is-look", "is-wave", "is-hop"];
// Kontekst -> qo'llanma bo'limi («📖 Batafsil», guide.js)
const GBOT_GUIDE_SEC = { hub: null, modes: null, league: "leagues", cl: "cups", el: "cups", ac: "cups",
                         co: "cups", division: "division", wc: "wc", pt: "pt", tb: "tb" };
// [root id, kontekst, «bosh sahifa»mi] — rejim ichida faqat bosh sahifada ko'rinadi
const GBOT_ROOTS = [
  ["worldcup-root", "wc", () => typeof WC === "undefined" || WC.section === "home"],
  ["cl-root", "cl", () => typeof CL === "undefined" || CL.section === "home"],
  ["el-root", "el", () => typeof EL === "undefined" || EL.section === "home"],
  ["ac-root", "ac", () => typeof AC === "undefined" || AC.section === "home"],
  ["co-root", "co", () => typeof CO === "undefined" || CO.section === "home"],
  ["div-root", "division", () => typeof DIV === "undefined" || DIV.section === "home"],
  ["pt-root", "pt", () => typeof PT === "undefined" || PT.view === "list"],
  ["tb-root", "tb", () => typeof TB === "undefined" || !TB.view],
];

function gbotLoadPrefs() {
  try {
    const p = JSON.parse(localStorage.getItem(GBOT_KEY) || "{}");
    GBOT_VOICE.muted = !!p.muted; GBOT_VOICE.speak = p.voice !== false; GBOT.mini = !!p.mini;   // ovoz — standart yoqilgan
    GBOT.seen = p.seen && typeof p.seen === "object" ? p.seen : {};
  } catch (_) { /* xotira yopiq — standart sozlamalar */ }
}
function gbotSavePrefs() {
  try {
    localStorage.setItem(GBOT_KEY, JSON.stringify({ muted: GBOT_VOICE.muted, voice: GBOT_VOICE.speak,
      mini: GBOT.mini, seen: GBOT.seen }));
  } catch (_) { /* xotira yopiq */ }
}

function gbotT() {
  const all = window.GBOT_I18N || {};
  return all[(typeof APP !== "undefined" && APP.lang) || "uz"] || all.uz || null;
}
function gbotFmt(s) { return escHtml(s).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>"); }
function gbotShown(id) {
  const el = document.getElementById(id);
  return !!(el && !el.classList.contains("hidden") && el.getClientRects().length);
}
function gbotHaptic(kind) {
  try { window.Telegram?.WebApp?.HapticFeedback?.impactOccurred(kind || "light"); } catch (_) { /* yo'q */ }
}

// Hozirgi sahifa (kontekst) yoki null — robot ko'rinmaydi
function gbotContext() {
  if ((typeof GUIDE !== "undefined" && GUIDE.open) || (typeof QM !== "undefined" && QM.open)) return null;
  if (document.querySelector(".modal:not(.hidden)")) return null;
  const ae = document.activeElement;
  if (ae && /^(INPUT|TEXTAREA|SELECT)$/.test(ae.tagName)) return null;   // klaviatura ochiq
  if (gbotShown("hub-select")) return "hub";
  if (gbotShown("mode-select")) return "modes";
  for (const [id, ctx, isHome] of GBOT_ROOTS) {
    if (gbotShown(id)) return isHome() ? ctx : null;
  }
  const home = document.getElementById("section-home");
  return home && home.classList.contains("active") && home.getClientRects().length ? "league" : null;
}

function gbotSvg(u) {
  return `<svg class="gbot-svg" viewBox="0 0 100 118" aria-hidden="true">
    <defs><linearGradient id="gbh${u}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#a68bff"/><stop offset="1" stop-color="#4cc3ff"/></linearGradient>
      <radialGradient id="gbf${u}" cx=".5" cy=".15" r=".85"><stop offset="0" stop-color="#fff6b0"/><stop offset=".45" stop-color="#ffb347"/><stop offset="1" stop-color="#ff5e3a" stop-opacity="0"/></radialGradient></defs>
    <ellipse class="gbot-flame" cx="50" cy="103" rx="9" ry="13" fill="url(#gbf${u})"/>
    <g class="gbot-arm gbot-arm-l"><rect x="17" y="70" width="11" height="22" rx="5.5" fill="url(#gbh${u})"/></g>
    <g class="gbot-arm gbot-arm-r"><rect x="72" y="70" width="11" height="22" rx="5.5" fill="url(#gbh${u})"/></g>
    <rect x="30" y="67" width="40" height="29" rx="13" fill="url(#gbh${u})"/>
    <circle class="gbot-core" cx="50" cy="82" r="5" fill="#ffd84d"/>
    <g class="gbot-head">
      <line x1="50" y1="21" x2="50" y2="10" stroke="#c9b8ff" stroke-width="3" stroke-linecap="round"/>
      <circle class="gbot-bulb" cx="50" cy="8" r="5.5" fill="#4cf0ff"/>
      <rect x="11" y="36" width="9" height="18" rx="4.5" fill="#7c5cff"/><rect x="80" y="36" width="9" height="18" rx="4.5" fill="#7c5cff"/>
      <rect x="17" y="19" width="66" height="50" rx="21" fill="url(#gbh${u})"/>
      <rect x="25" y="28" width="50" height="33" rx="14" fill="#11163a"/>
      <g class="gbot-eyes"><rect class="gbot-eye" x="35" y="36" width="9" height="13" rx="4.5" fill="#7ff3ff"/>
        <rect class="gbot-eye" x="56" y="36" width="9" height="13" rx="4.5" fill="#7ff3ff"/></g>
      <circle cx="31.5" cy="53" r="3.2" fill="#ff7eb6" opacity=".55"/><circle cx="68.5" cy="53" r="3.2" fill="#ff7eb6" opacity=".55"/>
      <path class="gbot-mouth" d="M43.5 52 Q50 58 56.5 52" fill="none" stroke="#7ff3ff" stroke-width="3" stroke-linecap="round"/>
    </g></svg>`;
}

function gbotEnsure() {
  let w = document.getElementById("gbot");
  if (w) return w;
  w = document.createElement("div");
  w.id = "gbot";
  w.className = "gbot hidden";
  w.innerHTML = `<div class="gbot-hint hidden" id="gbot-hint"></div>
    <button class="gbot-btn" id="gbot-btn" type="button"><span class="gbot-bot" id="gbot-mini-bot">${gbotSvg("a")}</span>
      <span class="gbot-shadow"></span></button>`;
  document.body.appendChild(w);
  document.getElementById("gbot-btn").addEventListener("click", gbotOpen);
  document.getElementById("gbot-hint").addEventListener("click", gbotOpen);
  return w;
}

// Robot bir lahza harakat qiladi (qo'l silkitish, sakrash, atrofga qarash, xursandlik)
function gbotAct(el, cls) {
  if (!el) return;
  GBOT_IDLE_ACTS.concat("is-happy").forEach(c => el.classList.remove(c));
  void el.offsetWidth;                                // animatsiya qaytadan boshlansin
  el.classList.add(cls);
  setTimeout(() => el.classList.remove(cls), GBOT_ACT_MS);
}

function gbotIdle() {
  clearTimeout(GBOT.idleT);
  GBOT.idleT = setTimeout(() => {
    if (!GBOT.open && GBOT.ctx && !document.hidden) {
      gbotAct(document.getElementById("gbot-mini-bot"), GBOT_IDLE_ACTS[Math.floor(Math.random() * GBOT_IDLE_ACTS.length)]);
    }
    gbotIdle();
  }, GBOT_IDLE_MS);
}

function gbotShowHint(ctx) {
  const d = gbotT();
  const hint = document.getElementById("gbot-hint");
  if (!d || !d[ctx] || !hint || GBOT.mini) return;
  hint.innerHTML = gbotFmt(d[ctx].hint);
  hint.classList.remove("hidden");
  gbotAct(document.getElementById("gbot-mini-bot"), "is-wave");
  clearTimeout(GBOT.hintT);
  GBOT.hintT = setTimeout(() => hint.classList.add("hidden"), GBOT_HINT_MS);
}

function gbotTick() {
  const w = gbotEnsure();
  const ctx = GBOT.open ? GBOT.ctx : gbotContext();
  const d = gbotT();
  const show = !!(ctx && d && d[ctx]);
  w.classList.toggle("hidden", !show || GBOT.open);
  w.classList.toggle("is-mini", GBOT.mini);
  if (!show) { document.getElementById("gbot-hint")?.classList.add("hidden"); GBOT.ctx = null; return; }
  if (ctx !== GBOT.ctx) {
    GBOT.ctx = ctx;
    GBOT.i = 0;
    w.classList.remove("is-enter"); void w.offsetWidth; w.classList.add("is-enter");
    document.getElementById("gbot-hint")?.classList.add("hidden");
    if (!GBOT.seen[ctx]) {
      GBOT.seen[ctx] = 1;
      gbotSavePrefs();
      setTimeout(() => { if (GBOT.ctx === ctx && !GBOT.open) gbotShowHint(ctx); }, GBOT_HINT_DELAY_MS);
    }
  }
}

function gbotInit() {
  if (GBOT._init) return;
  GBOT._init = true;
  gbotLoadPrefs();
  setInterval(gbotTick, GBOT_TICK_MS);
  gbotIdle();
}

if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", gbotInit);
else gbotInit();
