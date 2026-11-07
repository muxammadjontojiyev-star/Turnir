// =============================================================
//  crule.js — NATIJA BOT CHATIGA QARAB (2026-11-07, server: chat_rules.py / chat_agree.py / chat_rules_api.py)
//  1) «⚠️ Raqib yozmadi / o'ynamadi» (mshot.js slot tugmasi) → bot chatni tekshiradi → shart bajarilsa darhol 3:0.
//  2) Bot chati (liga va boshqa rejimlar — api.js #modal-webchat; JCh — #wc-modal-webchat) ichida
//     «📅 Boshqa vaqtga kelishish»: taklif → raqib «Qabul»/«Rad». Rejim fayllariga tegilmaydi — DOM kuzatiladi.
//  Global: APP, apiFetch, escHtml, showToast, msModal, msCloseModal, msRefresh, chatImgContext, CHAT_IMG_MODES, WC_CHAT.
// =============================================================

const CR_MODES = new Set(["league", "wc", "wc_po", "cl", "cl_po", "div", "el", "el_po", "ac", "ac_po", "co", "co_po", "pt"]);
const CR_POLL_MS = 8000;             // chat ochiq turganda kelishuv holatini yangilash
const CR_TZ_OFFSET_MIN = 5 * 60;     // Toshkent (server ham shu vaqtda tushunadi)
const CR_DEFAULT_AHEAD_MIN = 60;     // vaqt maydoni standart qiymati: hozir + 1 soat
const CR = { tech: null, busy: false, bar: null, timer: 0 };

// ---------------- 1) TEX WIN ----------------
function crTechHtml(st) {
  const t = (st && st.tech) || {};
  const lines = [t.deadline && crT("cr_tech_deadline", { d: t.deadline }), t.opens_at && crT("cr_tech_opens", { t: t.opens_at }),
    t.attempts != null && crT("cr_tech_attempts", { n: t.attempts }),
    t.wait_until && crT("cr_tech_wait", { t: t.wait_until })].filter(Boolean);
  const why = st ? (t.ok ? "" : crErr(t.reason)) : crT("cr_wait");
  return `<div class="modal-title">${escHtml(crT("cr_tech_title"))}</div>
    <div class="ms-hint">${escHtml(crT("cr_tech_rule"))}</div>
    ${lines.length ? `<div class="cr-facts">${lines.map(x => `<div>${escHtml(x)}</div>`).join("")}</div>` : ""}
    ${why ? `<div class="cr-why${t.ok ? "" : " cr-why--no"}">${escHtml(why)}</div>` : ""}
    <div class="modal-actions">
      <button class="btn btn--ghost" data-cr="close">${escHtml(crT("cr_close"))}</button>
      <button class="btn btn--primary" data-cr="take" ${t.ok && !CR.busy ? "" : "disabled"}>${escHtml(crT(CR.busy ? "cr_wait" : "cr_tech_take"))}</button>
    </div>`;
}

async function crTechOpen(c) {
  CR.tech = { ctx: c, st: null }; CR.busy = false;
  msModal("cr-tech", crTechHtml(null));
  try { CR.tech.st = await apiFetch(`/crule/${encodeURIComponent(c.mode)}/${Number(c.id)}`); }
  catch (e) { CR.tech.st = { tech: { ok: false, reason: e.message } }; }
  if (document.getElementById("cr-tech")) msModal("cr-tech", crTechHtml(CR.tech.st));
}

async function crTechTake() {
  if (CR.busy || !CR.tech) return;
  CR.busy = true; msModal("cr-tech", crTechHtml(CR.tech.st));
  const c = CR.tech.ctx;
  try {
    await apiFetch("/crule/techwin", { method: "POST", body: JSON.stringify({ mode: c.mode, match_id: c.id }) });
    CR.busy = false;
    msCloseModal("cr-tech");
    showToast(crT("cr_tech_done"));
    if (typeof msRefresh === "function") await msRefresh(c.mode);
  } catch (e) {
    showToast(crErr(e));
    CR.busy = false;
    void crTechOpen(c);
  }
}

// ---------------- 2) KELISHUV (chat ichida) ----------------
function crChatCtx(modal) {
  if (typeof chatImgContext !== "function") return null;
  if (modal.id === "wc-modal-webchat") return chatImgContext("wc");
  const pre = APP.chatUrlPrefix || "/matches";
  if (typeof CHAT_IMG_MODES === "undefined" || !CHAT_IMG_MODES[pre]) return null;   // /pt/support va h.k. — o'yin emas
  return chatImgContext("app");
}

function crLocalIso(addMin) {                        // Toshkent vaqti «YYYY-MM-DDTHH:MM» (qurilma mintaqasidan qat'i nazar)
  const d = new Date(Date.now() + (CR_TZ_OFFSET_MIN + addMin) * 60000);
  return d.toISOString().slice(0, 16);
}

function crBarHtml(st) {
  const a = (st && st.agree) || {};
  const p = a.proposal, g = a.agreed;
  if (!st || st.status !== "pending") return "";
  const cd = st.concede;                             // «win sizga» (chat_concede.py) — kelishuvdan ustun
  if (cd && cd.mine) {
    return `<div class="cr-ag-row cr-cd"><span>${escHtml(crT("cr_cd_ask"))}</span>
      <button class="cr-ag-b cr-ag-b--ok" data-cr-cd="1" data-id="${Number(cd.msg_id)}">${escHtml(crT("cr_cd_yes"))}</button>
      <button class="cr-ag-b" data-cr-cd="0" data-id="${Number(cd.msg_id)}">${escHtml(crT("cr_cd_no"))}</button></div>`;
  }
  if (cd && !cd.mine) return `<div class="cr-ag-row cr-cd"><span>${escHtml(crT("cr_cd_theirs"))}</span></div>`;
  if (p && !p.mine) {
    return `<div class="cr-ag-row"><span>${escHtml(crT("cr_ag_theirs", { at: p.at }))}</span>
      <button class="cr-ag-b cr-ag-b--ok" data-cr-ag="accept" data-id="${Number(p.id)}">${escHtml(crT("cr_ag_accept"))}</button>
      <button class="cr-ag-b" data-cr-ag="decline" data-id="${Number(p.id)}">${escHtml(crT("cr_ag_decline"))}</button></div>`;
  }
  if (p && p.mine) {
    return `<div class="cr-ag-row"><span>${escHtml(crT("cr_ag_mine", { at: p.at }))}</span>
      <button class="cr-ag-b" data-cr-ag="cancel" data-id="${Number(p.id)}">${escHtml(crT("cr_ag_cancel"))}</button></div>`;
  }
  const locked = g && g.active ? `<span class="cr-ag-lock">${escHtml(crT("cr_ag_locked", { at: g.at }))}</span>` : "";
  if (CR.bar && CR.bar.form) {
    return `<div class="cr-ag-form">
      <input type="datetime-local" class="cr-ag-at" value="${crLocalIso(CR_DEFAULT_AHEAD_MIN)}" min="${crLocalIso(0)}">
      <button class="cr-ag-b cr-ag-b--ok" data-cr-ag="send">${escHtml(crT("cr_ag_send"))}</button>
      <button class="cr-ag-b" data-cr-ag="now">${escHtml(crT("cr_ag_now"))}</button>
      <div class="cr-ag-hint">${escHtml(crT("cr_ag_hint"))}</div></div>`;
  }
  return `<div class="cr-ag-row">${locked}<button class="cr-ag-b" data-cr-ag="form">${escHtml(crT(locked ? "cr_ag_other" : "cr_ag_btn"))}</button></div>`;
}

function crPaintBar() {
  const b = CR.bar;
  if (!b || !b.modal.isConnected) return;
  const row = b.modal.querySelector(".webchat-input-row");
  if (!row) return;
  let el = b.modal.querySelector(".cr-ag");
  if (!el) { el = document.createElement("div"); el.className = "cr-ag"; row.parentNode.insertBefore(el, row); }
  const typing = document.activeElement && el.contains(document.activeElement) && document.activeElement.tagName === "INPUT";
  const html = crBarHtml(b.st);
  if (el._html !== html && !typing) { el.innerHTML = html; el._html = html; }
}

async function crLoadBar() {
  const b = CR.bar;
  if (!b) return;
  try { b.st = await apiFetch(`/crule/${encodeURIComponent(b.mode)}/${Number(b.id)}`); } catch (_) { b.st = null; }
  if (CR.bar === b) crPaintBar();
}

function crSyncChat() {
  const modal = ["modal-webchat", "wc-modal-webchat"].map(id => document.getElementById(id))
    .find(m => m && !m.classList.contains("hidden"));
  const c = modal ? crChatCtx(modal) : null;
  if (!c || !c.matchId || !CR_MODES.has(c.mode)) {
    if (CR.bar) { clearInterval(CR.timer); CR.bar = null; }
    return;
  }
  if (CR.bar && CR.bar.modal === modal && CR.bar.mode === c.mode && CR.bar.id === Number(c.matchId)) {
    if (!modal.querySelector(".cr-ag")) crPaintBar();          // chat qayta chizilgan bo'lsa
    return;
  }
  clearInterval(CR.timer);
  CR.bar = { modal, mode: c.mode, id: Number(c.matchId), st: null, form: false };
  void crLoadBar();
  CR.timer = setInterval(() => { if (CR.bar && !CR.bar.form) void crLoadBar(); }, CR_POLL_MS);
}

async function crConcede(btn) {                      // «win sizga»: Ha — raqibga darhol 3:0, Yo'q — taslim emas
  const b = CR.bar;
  if (!b || CR.busy) return;
  const accept = btn.dataset.crCd === "1";
  if (accept && !window.confirm(crT("cr_cd_q"))) return;
  CR.busy = true; btn.disabled = true;
  try {
    await apiFetch("/crule/concede", { method: "POST",
      body: JSON.stringify({ mode: b.mode, match_id: b.id, msg_id: Number(btn.dataset.id), accept }) });
    showToast(crT(accept ? "cr_cd_done" : "cr_cd_declined"));
    if (accept && typeof msRefresh === "function") void msRefresh(b.mode);
  } catch (e) { showToast(crErr(e)); }
  finally { CR.busy = false; await crLoadBar(); }
}

async function crAgreeAct(btn) {
  const b = CR.bar;
  if (!b || CR.busy) return;
  const act = btn.dataset.crAg;
  if (act === "form") { b.form = true; crPaintBar(); return; }
  CR.busy = true; btn.disabled = true;
  try {
    if (act === "send" || act === "now") {
      const at = act === "now" ? crLocalIso(0) : (b.modal.querySelector(".cr-ag-at")?.value || "");
      const r = await apiFetch("/crule/agree", { method: "POST", body: JSON.stringify({ mode: b.mode, match_id: b.id, at }) });
      b.form = false;
      showToast(r && r.after_deadline ? crT("cr_ag_late") : crT("cr_ag_sent"));
    } else {
      const r = await apiFetch(`/crule/agree/${Number(btn.dataset.id)}/decide`,
        { method: "POST", body: JSON.stringify({ accept: act === "accept" }) });
      if (act === "accept") showToast(r && r.after_deadline ? crT("cr_ag_late") : crT("cr_ag_ok"));
    }
  } catch (e) {
    showToast(crErr(e));
  } finally {
    CR.busy = false;
    await crLoadBar();
    if (typeof loadWebChatMessages === "function" && b.modal.id === "modal-webchat") void loadWebChatMessages();
    if (typeof wcLoadWebChatMessages === "function" && b.modal.id === "wc-modal-webchat") void wcLoadWebChatMessages();
  }
}

document.addEventListener("click", (e) => {
  const cr = e.target.closest ? e.target.closest("[data-cr]") : null;
  if (cr && cr.closest("#cr-tech")) {
    e.preventDefault();
    if (cr.dataset.cr === "close") msCloseModal("cr-tech");
    if (cr.dataset.cr === "take") void crTechTake();
    return;
  }
  const cd = e.target.closest ? e.target.closest("[data-cr-cd]") : null;
  if (cd) { e.preventDefault(); e.stopPropagation(); void crConcede(cd); return; }
  const ag = e.target.closest ? e.target.closest("[data-cr-ag]") : null;
  if (ag) { e.preventDefault(); e.stopPropagation(); void crAgreeAct(ag); }
}, true);

let _crT = 0;
new MutationObserver(() => {                         // throttle — chat har 2 s yangilanganda ham ishlaydi
  if (_crT) return;
  _crT = requestAnimationFrame(() => { _crT = 0; crSyncChat(); });
}).observe(document.body, { subtree: true, childList: true, attributes: true, attributeFilter: ["class"] });

// ---------------- 3) XONA ID — chatdan nusxalash yoziladi (qo'lda natija sharti, server: chat_room.py) ----------------
// «🎮 Xona ID: <kod>» (har qanday 4–16 belgili kod) ham bosiluvchan bo'ladi; 8 xonali sonlarni api.js o'zi o'raydi.
const CR_ROOM_RE = /^(🎮 Xona ID:\s*)([A-Za-z0-9]{4,16})$/;
const CR_SPLIT_RE = /(?<!\d)(?<!\d[ -])(\d{4})([ -])(\d{4})(?![ -]?\d)/g;           // «4432 1462» — server: chat_room.ROOM_SPLIT_RE
if (typeof chatTextWithCopyableIds === "function") {
  const _crCopyable = chatTextWithCopyableIds;
  chatTextWithCopyableIds = function (escapedText) {                       // eslint-disable-line no-global-assign
    return _crCopyable(escapedText).replace(CR_ROOM_RE,
      (_a, pre, id) => `${pre}<span class="chat-copy-id" data-copy-id="${id}">${id}</span>`)
      .replace(CR_SPLIT_RE, (_a, a, sep, b) => `<span class="chat-copy-id" data-copy-id="${a}${b}">${a}${sep}${b}</span>`);
  };
}
if (typeof copyChatId === "function") {
  const _crCopy = copyChatId;
  copyChatId = function (id) {                                              // eslint-disable-line no-global-assign
    _crCopy(id);
    if (!CR.bar) crSyncChat();
    const b = CR.bar;
    if (!b || !id) return;
    apiFetch("/crule/room-copy", { method: "POST", body: JSON.stringify({ mode: b.mode, match_id: b.id, code: String(id) }) })
      .catch(() => {});
  };
}

// ---------------- 4) YIRIK HISOB — skrinshot so'raladi (server: chat_gate.py «big_needs_shot|mode|id|s1|s2») ----------------
// Qo'lda kiritilgan yirik hisob rad etiladi → skrinshot oynasi ochiladi; skrinshotdagi hisob bir xil bo'lsa — darhol tasdiq.
const CR_BIG_CODE = "big_needs_shot|";
if (typeof apiFetch === "function") {
  const _crFetch = apiFetch;
  apiFetch = async function (path, opts) {                                  // eslint-disable-line no-global-assign
    try {
      return await _crFetch(path, opts);
    } catch (e) {
      const msg = String((e && e.message) || "");
      if (!msg.startsWith(CR_BIG_CODE) || typeof msShotOpen !== "function") throw e;
      const [, mode, id, s1, s2] = msg.split("|");
      const m = { mode, id: Number(id), s1: Number(s1), s2: Number(s2) };
      void crBigShot(m);
      throw new Error(crT("cr_big_toast"));
    }
  };
}

async function crBigShot(m) {
  let me1 = true;                                    // «siz : raqib» ko'rinishi uchun — men player1 manmi
  try {
    const st = await _crMatchSide(m);
    if (st != null) me1 = st;
  } catch (_) { /* ko'rinish uchun, majburiy emas */ }
  const label = me1 ? `${m.s1}:${m.s2}` : `${m.s2}:${m.s1}`;
  if (typeof closeResultModal === "function") { try { closeResultModal(); } catch (_) { /* boshqa rejim oynasi */ } }
  await msShotOpen({ mode: m.mode, id: m.id, expect: { s1: m.s1, s2: m.s2, label } });
}

async function _crMatchSide(m) {
  const st = await apiFetch(`/crule/${encodeURIComponent(m.mode)}/${m.id}`);
  return st && typeof st.me_p1 === "boolean" ? st.me_p1 : null;
}
