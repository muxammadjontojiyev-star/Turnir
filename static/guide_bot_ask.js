// =============================================================
//  guide_bot_ask.js — «Robi»GA SAVOL BERISH oynasi (2026-11-03)
//  Gaplashish oynasida «💬 Robiga savol berish» -> savol yoziladi (yoki namuna tugma bosiladi) -> javob
//  bilimlar bazasidan (guide_bot_faq.js, BEPUL, faqat bot qoidalari va turnirlar) topiladi va Robi uni
//  yozib aytadi. Javobga kanal qo'llanmasi havolasi bo'lsa — tugma (Telegram ichida ochiladi).
//  2026-11-03: «dyn» savollarda (bo'sh joy, ro'yxatdan o'tish, topshirilayotgan klublar) javob botdagi
//  HOZIRGI holatdan tuziladi (guide_bot_live.js) — joy bo'lmasa klub olish yo'li + Divizion/Tezkor o'yin.
//  Topilmasa yoki savol murakkab bo'lsa — bosh adminga (APP.adminContact, standart @Tojiyev_M)
//  murojaat qilishni aytadi va «✉️ yozish» tugmasini beradi + savol namunalari.
//  Foydalanuvchi matni faqat escHtml bilan chiqariladi (qoida: XSS); havola faqat https://t.me/.
//  Ovoz hozircha qo'shilmagan (egasi qarori). guide_bot_panel.js dan KEYIN ulanadi.
//  Global: APP, GBOT, escHtml, gbotType, gbotFmt, gbotRender, gbotSpeakStop, gbotAct, gbotHaptic, gbotSfx, gbotFaq*.
// =============================================================

const GBOT_ASK = { on: false, busy: false, seq: 0 };
const GBOT_ASK_MAX = 200;              // savol uzunligi
const GBOT_ASK_CHIPS = 3;              // namuna savollar soni
const GBOT_ASK_CHIPS_AFTER = 2;        // javobdan keyingi namunalar
const GBOT_ASK_ADMIN_DEFAULT = "@Tojiyev_M";
const GBOT_LINK_RE = /^https:\/\/t\.me\/[A-Za-z0-9_/]+$/;

function gbotAskLang() { return (typeof APP !== "undefined" && APP.lang) || "uz"; }
function gbotAskUi() { return gbotFaqData(gbotAskLang()).ui; }

// Bosh admin kontakti (/membership javobidan — app.js APP.adminContact)
function gbotAskAdmin() {
  const c = (typeof APP !== "undefined" && APP.adminContact) || {};
  const username = /^@[A-Za-z0-9_]{3,32}$/.test(c.username || "") ? c.username : GBOT_ASK_ADMIN_DEFAULT;
  return { username, url: "https://t.me/" + username.slice(1) };
}

function gbotAskButtonHtml() {
  if (typeof GBOT_FAQ === "undefined" || !GBOT_FAQ.uz) return "";
  return `<button class="gbot-ask-open" data-gbask="open">${escHtml(gbotAskUi().ask_btn)}</button>`;
}

function gbotAskReset() {
  GBOT_ASK.on = false;
  document.getElementById("gbot-you")?.remove();
  document.getElementById("gbot-dots")?.classList.remove("hidden");
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

// links: [[yozuv, url], ...] (javobdagi qo'llanmalar); admin — «✉️ adminga yozish» tugmasi
function gbotAskControls(items, links, admin) {
  const u = gbotAskUi();
  const linkBtns = (links || []).filter(l => GBOT_LINK_RE.test(l[1])).map(l =>
    `<button class="gbot-link" data-gbask="link" data-url="${escHtml(l[1])}">${escHtml(l[0])}</button>`).join("");
  const adminBtn = admin
    ? `<button class="gbot-link gbot-link--admin" data-gbask="admin">${escHtml(u.write_admin.replace("{admin}", gbotAskAdmin().username))}</button>` : "";
  const chips = items.map(it => `<button class="gbot-chip" data-gbask="q" data-q="${escHtml(it.q)}">${escHtml(it.q)}</button>`).join("");
  document.getElementById("gbot-actions").innerHTML = `${linkBtns || adminBtn ? `<div class="gbot-links">${linkBtns}${adminBtn}</div>` : ""}
    <div class="gbot-chips">${chips}</div>
    <div class="gbot-ask-row">
      <input class="gbot-ask-in" id="gbot-ask-in" type="text" maxlength="${GBOT_ASK_MAX}" placeholder="${escHtml(u.ph)}" enterkeyhint="send">
      <button class="gbot-ask-btn gbot-ask-send" data-gbask="send" aria-label="${escHtml(u.send)}">➤</button>
    </div>
    <button class="gbot-act gbot-ask-back" data-gbask="back">${escHtml(u.back)}</button>`;
}

function gbotAskOpen() {
  GBOT_ASK.on = true;
  gbotSpeakStop();
  document.getElementById("gbot-dots")?.classList.add("hidden");
  gbotAct(document.getElementById("gbot-big-bot"), "is-hop");
  gbotSfx("next");
  gbotAskControls(gbotFaqSuggest(gbotAskLang(), GBOT.ctx, GBOT_ASK_CHIPS));
  gbotType(gbotAskUi().hello, false);
}

function gbotAskItems(lang, ids) {
  const items = gbotFaqData(lang).items;
  return ids.map(id => items.find(it => it.id === id)).filter(Boolean);
}

async function gbotAskSend(raw) {
  const text = String(raw || "").replace(/\s+/g, " ").trim().slice(0, GBOT_ASK_MAX);
  if (!text || GBOT_ASK.busy) return;
  gbotHaptic("light");
  gbotAskYou(text);
  const lang = gbotAskLang();
  const hit = gbotFaqFind(text, lang, GBOT.ctx);
  const bot = document.getElementById("gbot-big-bot");
  if (hit && hit.dyn && typeof gbotLiveAnswer === "function") {
    // Botdagi hozirgi holat — serverdan (bir necha soniya)
    const seq = ++GBOT_ASK.seq;
    GBOT_ASK.busy = true;
    gbotAct(bot, "is-look");
    clearInterval(GBOT.typeT);
    GBOT.typeT = null;
    document.getElementById("gbot-text").innerHTML = gbotFmt(gbotFaqData(lang).live.checking);
    let live;
    try { live = await gbotLiveAnswer(hit.dyn, lang); } finally { GBOT_ASK.busy = false; }
    if (seq !== GBOT_ASK.seq || !GBOT.open || !GBOT_ASK.on) return;
    gbotAct(bot, "is-happy");
    gbotType((hit.a ? hit.a + "\n\n" : "") + live.text, false);
    const chips = live.chips.length ? gbotAskItems(lang, live.chips) : gbotFaqSuggest(lang, GBOT.ctx, GBOT_ASK_CHIPS_AFTER, hit.id);
    gbotAskControls(chips, hit.l, !!hit.admin);
  } else if (hit) {
    gbotAct(bot, "is-happy");
    gbotType(hit.a.replace("{admin}", gbotAskAdmin().username), false);
    gbotAskControls(gbotFaqSuggest(lang, GBOT.ctx, GBOT_ASK_CHIPS_AFTER, hit.id), hit.l, !!hit.admin);
  } else {
    gbotAct(bot, "is-look");
    gbotType(gbotAskUi().not_found.replace("{admin}", gbotAskAdmin().username), false);
    gbotAskControls(gbotFaqSuggest(lang, GBOT.ctx, GBOT_ASK_CHIPS), null, true);
  }
  document.getElementById("gbot-ask-in")?.blur();
}

function gbotAskOpenLink(url) {
  if (!GBOT_LINK_RE.test(url || "")) return;
  const tg = window.Telegram?.WebApp;
  if (tg?.openTelegramLink) { try { tg.openTelegramLink(url); return; } catch (_) { /* oddiy oyna */ } }
  window.open(url, "_blank");
}

document.addEventListener("click", (e) => {
  const b = e.target.closest("[data-gbask]");
  if (!b || !GBOT.open) return;
  const act = b.dataset.gbask;
  if (act === "open") gbotAskOpen();
  else if (act === "back") { gbotAskReset(); gbotRender(); }
  else if (act === "q") gbotAskSend(b.dataset.q);
  else if (act === "send") gbotAskSend(document.getElementById("gbot-ask-in")?.value);
  else if (act === "link") gbotAskOpenLink(b.dataset.url);
  else if (act === "admin") gbotAskOpenLink(gbotAskAdmin().url);
});

document.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && e.target && e.target.id === "gbot-ask-in") {
    e.preventDefault();
    gbotAskSend(e.target.value);
  }
});
