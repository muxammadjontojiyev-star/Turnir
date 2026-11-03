// =============================================================
//  guide_bot_panel.js — «Robi» bilan GAPLASHISH OYNASI (2026-11-03)
//  Robot katta bo'lib chiqadi, gaplar navbat bilan «yozilib» aytiladi (har harfga «bip» —
//  guide_bot_voice.js), gapirayotganda og'zi qimirlaydi, oxirida xursand bo'ladi.
//  Tugmalar: ‹ Ortga / Keyingisi ›, oxirida — Boshidan, Batafsil (guide.js qo'llanmasi), Rahmat.
//  Yuqorida: ovoz 🔊/🔇, haqiqiy nutq 🗣 (server yoki qurilma ovozi bo'lsa), Yashirish, ✕.
//  2026-11-03: har gap ostida «💬 Robiga savol berish» (guide_bot_ask.js). Haqiqiy ovoz ulansa (hozircha
//  yo'q) — yozish tezligi ovozga moslanadi (GBOT._retime), og'iz ovoz tugaguncha qimirlaydi.
//  Matn bosilsa — yozish darhol tugaydi. guide_bot.js dan KEYIN ulanadi.
// =============================================================

function gbotPanelEnsure() {
  let p = document.getElementById("gbot-panel");
  if (p) return p;
  p = document.createElement("div");
  p.id = "gbot-panel";
  p.className = "gbot-panel hidden";
  p.setAttribute("role", "dialog");
  p.innerHTML = `<div class="gbot-sheet">
      <div class="gbot-top">
        <span class="gbot-bot gbot-bot--big" id="gbot-big-bot">${gbotSvg("b")}</span>
        <div class="gbot-name"><b id="gbot-name"></b><small id="gbot-role"></small></div>
        <div class="gbot-tools" id="gbot-tools"></div>
      </div>
      <div class="gbot-bubble" id="gbot-bubble"><div class="gbot-text" id="gbot-text"></div></div>
      <div class="gbot-dots" id="gbot-dots"></div>
      <div class="gbot-actions" id="gbot-actions"></div>
    </div>`;
  document.body.appendChild(p);
  p.addEventListener("click", gbotPanelClick);
  return p;
}

function gbotOpen() {
  const d = gbotT();
  if (!d || !GBOT.ctx || !d[GBOT.ctx]) return;
  gbotAc();                                               // ovoz ruxsati — aynan shu bosishda
  if (typeof gbotAskReset === "function") gbotAskReset();
  clearTimeout(GBOT.hintT);
  document.getElementById("gbot-hint")?.classList.add("hidden");
  if (GBOT.mini) { GBOT.mini = false; gbotSavePrefs(); }
  const p = gbotPanelEnsure();
  GBOT.open = true;
  GBOT.n = d[GBOT.ctx].say.length;
  if (GBOT.i >= GBOT.n) GBOT.i = 0;
  p.classList.remove("hidden");
  document.getElementById("gbot")?.classList.add("hidden");
  gbotHaptic("light");
  gbotSfx("hello");
  gbotAct(document.getElementById("gbot-big-bot"), "is-wave");
  gbotRender();
}

function gbotClose(sfx) {
  clearInterval(GBOT.typeT);
  GBOT.typeT = null;
  gbotSpeakStop();
  if (sfx) gbotSfx("bye");
  GBOT.open = false;
  document.getElementById("gbot-panel")?.classList.add("hidden");
  gbotTick();
}

function gbotToolsHtml(u) {
  const btn = (act, label, title, on) =>
    `<button class="gbot-tool${on ? " is-on" : ""}" data-gbot="${act}" title="${escHtml(title)}" aria-label="${escHtml(title)}">${escHtml(label)}</button>`;
  return btn("mute", GBOT_VOICE.muted ? u.sound_off : u.sound_on, u.sound_on, !GBOT_VOICE.muted)
    + (gbotCanSpeak() ? btn("speak", u.speak, u.speak, GBOT_VOICE.speak) : "")
    + btn("hide", "🙈", u.hide, false)
    + btn("close", "✕", u.close, false);
}

function gbotRender() {
  const d = gbotT();
  const u = d.ui;
  const say = d[GBOT.ctx].say;
  const last = GBOT.i >= say.length - 1;
  document.getElementById("gbot-name").textContent = u.name;
  document.getElementById("gbot-role").textContent = u.role;
  document.getElementById("gbot-tools").innerHTML = gbotToolsHtml(u);
  document.getElementById("gbot-dots").innerHTML = say.map((_, k) =>
    `<i class="${k === GBOT.i ? "is-on" : k < GBOT.i ? "is-done" : ""}"></i>`).join("");
  const a = (act, label, cls) => `<button class="gbot-act ${cls || ""}" data-gbot="${act}">${escHtml(label)}</button>`;
  document.getElementById("gbot-actions").innerHTML = last
    ? a("again", u.again) + (typeof openGuide === "function" ? a("more", u.more) : "") + a("bye", u.bye, "gbot-act--main")
    : (GBOT.i > 0 ? a("prev", u.prev) : "") + a("next", u.next, "gbot-act--main");
  if (typeof gbotAskButtonHtml === "function") {
    document.getElementById("gbot-actions").insertAdjacentHTML("beforeend", gbotAskButtonHtml());
  }
  gbotType(say[GBOT.i], last);
}

// Matnni harfma-harf «yozadi» (emoji bo'linmaydi — Array.from), **qalin** saqlanadi
function gbotType(text, last) {
  clearInterval(GBOT.typeT);
  const bot = document.getElementById("gbot-big-bot");
  const box = document.getElementById("gbot-text");
  const parts = String(text).split(/(\*\*.+?\*\*)/).filter(Boolean)
    .map(s => s.startsWith("**") ? { b: true, c: Array.from(s.slice(2, -2)) } : { b: false, c: Array.from(s) });
  const flat = parts.flatMap(p => p.c);
  const total = flat.length;
  const html = (n) => parts.map(p => {
    const take = Math.max(0, Math.min(p.c.length, n));
    n -= p.c.length;
    const s = escHtml(p.c.slice(0, take).join(""));
    return p.b && s ? `<b>${s}</b>` : s;
  }).join("");
  let n = 0;
  const done = () => {
    clearInterval(GBOT.typeT);
    GBOT.typeT = null;
    GBOT._retime = null;
    box.innerHTML = html(total);
    if (!gbotIsSpeaking()) bot.classList.remove("is-talk");   // ovoz davom etsa — og'iz ham
    if (last) { gbotAct(bot, "is-happy"); gbotSfx("happy"); }
  };
  const step = () => {
    n += 1;
    const ch = flat[n - 1];
    if (ch && /\p{L}/u.test(ch) && n % GBOT_CHIRP_EVERY === 0) gbotChirp(ch);
    box.innerHTML = html(n);
    if (n >= total) done();
  };
  // Ovoz davomiyligi ma'lum bo'lsa — qolgan harflar ovoz bilan birga tugaydi
  GBOT._retime = (ms) => {
    if (!GBOT.typeT || n >= total) return;
    const per = Math.max(GBOT_TYPE_MS, Math.min(GBOT_TYPE_MAX_MS, (ms * GBOT_TYPE_SYNC) / (total - n)));
    clearInterval(GBOT.typeT);
    GBOT.typeT = setInterval(step, per);
  };
  GBOT._finish = done;
  bot.classList.add("is-talk");
  GBOT.typeT = setInterval(step, Math.min(GBOT_TYPE_MS, GBOT_TYPE_MAX_TOTAL_MS / Math.max(1, total)));
  gbotSpeak(text);
}

function gbotGo(i) {
  GBOT.i = Math.max(0, Math.min(GBOT.n - 1, i));
  gbotHaptic("light");
  gbotSfx("next");
  gbotRender();
}

function gbotPanelClick(e) {
  const p = document.getElementById("gbot-panel");
  if (e.target === p) { gbotClose(true); return; }                 // fon bosildi
  const b = e.target.closest("[data-gbot]");
  if (!b) {
    if (e.target.closest("#gbot-bubble") && GBOT.typeT && GBOT._finish) GBOT._finish();   // tezlashtirish
    return;
  }
  const act = b.dataset.gbot;
  if (act === "next") gbotGo(GBOT.i + 1);
  else if (act === "prev") gbotGo(GBOT.i - 1);
  else if (act === "again") gbotGo(0);
  else if (act === "close") gbotClose(true);
  else if (act === "more") {
    const sec = GBOT_GUIDE_SEC[GBOT.ctx];
    gbotClose(false);
    openGuide(sec);
  } else if (act === "bye") {
    const bot = document.getElementById("gbot-big-bot");
    clearInterval(GBOT.typeT);
    document.getElementById("gbot-text").innerHTML = gbotFmt(gbotT().ui.bye_reply);
    document.getElementById("gbot-actions").innerHTML = "";
    gbotAct(bot, "is-wave");
    gbotSfx("happy");
    gbotHaptic("medium");
    GBOT.i = 0;
    setTimeout(() => { if (GBOT.open) gbotClose(false); }, GBOT_BYE_MS);
  } else if (act === "hide") {
    GBOT.mini = true;
    gbotSavePrefs();
    gbotClose(true);
  } else if (act === "mute") {
    GBOT_VOICE.muted = !GBOT_VOICE.muted;
    if (GBOT_VOICE.muted) gbotSpeakStop(); else gbotSfx("next");
    gbotSavePrefs();
    document.getElementById("gbot-tools").innerHTML = gbotToolsHtml(gbotT().ui);
  } else if (act === "speak") {
    GBOT_VOICE.speak = !GBOT_VOICE.speak;
    if (!GBOT_VOICE.speak) gbotSpeakStop();
    gbotSavePrefs();
    document.getElementById("gbot-tools").innerHTML = gbotToolsHtml(gbotT().ui);
  }
}
