// =============================================================
//  pt_match_ui.js — SHAXSIY turnir: o'yin kartasi tugmalari (2026-10-11)
//  Admin so'rovi: rasmiy rejimlar kabi sodda — ochiq o'yinda [Natija] [💬].
//    • Natija → hisob oynasi (#modal-pt-result); yuborish pt_play.js
//      ptSubmitResult orqali (input id'lari bir xil: pt-s1-{id} / pt-s2-{id}).
//    • 💬     → VS-oyna (#modal-pt-opponent): 🎮 Xona ID / bot chati / Telegram.
//  Backend o'zgarmadi. Global: PT, PTT, APP, escHtml, ICON, ptNameOf, ptTeamBadge,
//  ptSubmitResult, roomCodeBtnHtml, openWebChat, showToast.
// =============================================================

const PT_SCORE_MAX = 99;   // hisob kiritish chegarasi (oldingi inline formadagi max bilan bir xil)

function ptFindMatch(mid) {
  const p = PT.play || {};
  return [...(p.my_matches || []), ...(p.round_matches || []), ...(p.knockout || [])]
    .find(x => String(x.id) === String(mid)) || null;
}

// Karta pastidagi tugmalar: ochiq o'yinda [Natija][💬], qolganida faqat [💬]
function ptMatchButtonsHtml(m, canSubmit, unread) {
  const t = APP.t || {};
  const badge = unread ? `<span class="chat-badge">${unread > 9 ? "9+" : unread}</span>` : "";
  const result = canSubmit
    ? `<button class="match-action-btn" data-pt-result="${m.id}">${escHtml(t.enter_result || "Natija")}</button>` : "";
  return `<div class="pt-match-tools pt-match-tools--end">${result}`
    + `<button class="match-action-btn match-chat-btn" data-pt-vs="${m.id}" title="${escHtml(t.chat_first_hint || "Avval raqib bilan kelishing")}">${ICON.get("chat", 18)}${badge}</button></div>`;
}

function ptModalShell(id) {
  let modal = document.getElementById(id);
  if (!modal) {
    modal = document.createElement("div");
    modal.id = id;
    modal.className = "modal hidden";
    document.body.appendChild(modal);
  }
  return modal;
}

function ptOpenResultModal(tid, mid) {
  const m = ptFindMatch(mid);
  if (!m) return;
  const t = APP.t || {};
  const modal = ptModalShell("modal-pt-result");
  const side = k => `<div class="pt-res-side">${ptTeamBadge(m[`p${k}_team`], "pt-tlogo--lg")}<span>${escHtml(ptNameOf(m, k))}</span></div>`;
  const inp = k => `<input id="pt-s${k}-${m.id}" class="score-input" type="number" min="0" max="${PT_SCORE_MAX}" inputmode="numeric" value="0">`;
  modal.innerHTML = `
    <div class="modal-box">
      <div class="modal-title">${escHtml(t.submit_result || "Natija kiritish")}</div>
      <div class="pt-res-sides">${side(1)}${side(2)}</div>
      <div class="score-input-row">
        <div class="score-input-group">${inp(1)}</div>
        <span class="score-separator">:</span>
        <div class="score-input-group">${inp(2)}</div>
      </div>
      <div class="modal-actions">
        <button class="btn btn--ghost" id="pt-res-cancel">${escHtml(t.cancel || "Bekor")}</button>
        <button class="btn btn--primary btn--glow" id="pt-res-send">${escHtml(PTT("pt_submit"))}</button>
      </div>
    </div>`;
  modal.classList.remove("hidden");
  const close = () => { modal.classList.add("hidden"); modal.innerHTML = ""; };
  document.getElementById("pt-res-cancel").addEventListener("click", close);
  modal.onclick = e => { if (e.target === modal) close(); };
  document.getElementById("pt-res-send").addEventListener("click", () => {
    // ptSubmitResult qiymatlarni sinxron o'qiydi; bo'sh yoki bekor qilinsa undefined qaytaradi
    const pending = ptSubmitResult(tid, mid);
    if (pending) close();
  });
}

function ptOpenTelegram(username) {
  const t = APP.t || {};
  if (!username) { showToast(t.opp_no_contact || "Raqib bilan bog'lanib bo'lmaydi"); return; }
  const link = `https://t.me/${String(username).replace(/^@/, "")}`;
  const tg = window.Telegram?.WebApp;
  if (tg?.openTelegramLink) {
    try { tg.openTelegramLink(link); } catch (_) { window.open(link, "_blank"); }
  } else {
    window.open(link, "_blank");
  }
}

function ptOpenVsModal(mid) {
  const m = ptFindMatch(mid);
  if (!m) return;
  const t = APP.t || {};
  const oppK = m.player1_id === (PT.play || {}).me_id ? 2 : 1;
  const oppUser = m[`p${oppK}_username`];
  const modal = ptModalShell("modal-pt-opponent");
  const side = k => `
    <div class="opp-side">
      <div class="pt-vs-logo">${ptTeamBadge(m[`p${k}_team`], "pt-tlogo--xl")}</div>
      <div class="opp-club">${escHtml(m[`p${k}_team`] || m[`p${k}_name`] || "—")}</div>
      <div class="opp-user">${m[`p${k}_username`] ? "@" + escHtml(m[`p${k}_username`]) : escHtml(m[`p${k}_name`] || "—")}</div>
    </div>`;
  const tgBtn = oppUser
    ? `<button class="opp-chat-btn" id="pt-opp-tg">${ICON.get("chat", 18)} ${escHtml(t.opp_write_button || "Raqib chatiga yozish")}</button>`
    : `<div class="opp-no-contact">${escHtml(t.opp_no_contact || "Raqib bilan bog'lanib bo'lmaydi")}</div>`;
  modal.innerHTML = `
    <div class="modal-box opp-modal-box">
      <button class="modal-close" id="pt-opp-close">${ICON.get("close", 18)}</button>
      <div class="opp-vs">${side(1)}<div class="opp-vs-sep">VS</div>${side(2)}</div>
      ${typeof roomCodeBtnHtml === "function" ? roomCodeBtnHtml(m.id, "pt") : ""}
      <button class="opp-chat-btn opp-webchat-btn" id="pt-opp-webchat">${ICON.get("chat", 18)} ${escHtml(t.webchat_open || "Chatni ochish")}</button>
      ${tgBtn}
    </div>`;
  modal.classList.remove("hidden");
  const close = () => modal.classList.add("hidden");
  document.getElementById("pt-opp-close").addEventListener("click", close);
  modal.onclick = e => { if (e.target === modal) close(); };
  document.getElementById("pt-opp-webchat").addEventListener("click", () => {
    close();
    if (PT.unread) delete PT.unread[m.id];                 // ochilgach o'qildi deb hisoblanadi
    document.querySelector(`#pt-root [data-pt-vs="${m.id}"] .chat-badge`)?.remove();
    openWebChat(m.id, ptNameOf(m, oppK), "/pt/matches");
  });
  document.getElementById("pt-opp-tg")?.addEventListener("click", () => { ptOpenTelegram(oppUser); close(); });
}

// -------------------------------------------------------------
//  2026-10-11: PROFIL — o'yinlar rasmiy "Mening o'yinlarim" qatori kabi
//  (api.js renderMatchItem naqshi): tur | #id | logo hisob logo | holat yoki tugmalar.
//  Tugmalar ptBindPlayBody'da bog'langan: data-pt-result, data-pt-vs,
//  data-pt-confirm, data-pt-rejectres (qo'shimcha bog'lash shart emas).
// -------------------------------------------------------------
const PT_ROW_STAGE_SHORT = { final: "F", semi: "1/2", qf: "1/4", r16: "1/8", r32: "1/16", r64: "1/32", po: "PO" };

function ptRowBadge(team) {
  const b = team && typeof ptTeamBadge === "function" ? ptTeamBadge(team, "match-club-logo") : "";
  return b || `<span class="match-club-logo match-club-logo--empty" title="${escHtml(team || "")}"></span>`;
}

function ptMatchRowHtml(m, p, mine) {
  const t = APP.t || {};
  const me = p.me_id;
  const day = m.stage === "group" ? m.round : (PT_ROW_STAGE_SHORT[m.stage] || m.round);
  const open = m.stage === "group" ? ptRoundOpen(m, p) : true;
  const canSubmit = mine && m.status === "pending" && open && p.status === "running";
  const reachable = mine && m.player1_id && m.player2_id
    && (m.stage !== "group" || m.round <= (p.open_upto || p.current_round));

  // O'qilmagan xabar rozetkasi — RAQIB logosi ustida (rasmiy naqsh)
  const n = mine ? ((PT.unread || {})[m.id] || 0) : 0;
  const badge = n ? `<span class="chat-badge">${n > 9 ? "9+" : n}</span>` : "";
  const iAmP1 = m.player1_id === me;
  const score = m.score1 != null ? `${m.score1} : ${m.score2}` : "— : —";
  const center = `<span class="match-badge-wrap">${ptRowBadge(m.p1_team)}${iAmP1 ? "" : badge}</span>`
    + `<span class="match-score">${score}</span>`
    + `<span class="match-badge-wrap">${ptRowBadge(m.p2_team)}${iAmP1 ? badge : ""}</span>`;

  const ST = {
    pending:               ["status--pending",   t.status_pending || "KUTILMOQDA"],
    awaiting_confirmation: ["status--awaiting",  t.status_awaiting || "TASDIQ"],
    admin_pending:         ["status--awaiting",  t.status_admin_pending || "ADMIN TASDIG'I"],
    confirmed:             ["status--confirmed", t.status_confirmed || "TASDIQLANDI"],
  }[m.status] || ["status--pending", t.status_pending || "KUTILMOQDA"];
  let status = `<span class="match-status ${ST[0]}">${escHtml(ST[1])}</span>`;

  let action = "";
  if (canSubmit) {
    status = "";
    action = `<button class="match-action-btn" data-pt-result="${m.id}">${escHtml(t.enter_result || "Natija")}</button>`
      + `<button class="match-action-btn match-chat-btn" data-pt-vs="${m.id}" title="${escHtml(t.chat_first_hint || "Avval raqib bilan kelishing")}">${ICON.get("chat", 18)}</button>`;
  } else if (mine && m.status === "pending" && !open) {
    action = `<span class="match-locked" title="${escHtml(t.matchday_locked_short || "Tur hali ochilmagan")}">${ICON.get("lock", 16)}</span>`;
  } else if (mine && m.status === "awaiting_confirmation" && m.submitted_by !== me) {
    action = `<button class="match-action-btn" data-pt-confirm="${m.id}">✔</button>`
      + `<button class="match-action-btn pt-row-reject" data-pt-rejectres="${m.id}">✖</button>`;
  }

  const cls = reachable ? "match-center match-center--clickable" : "match-center";
  const attr = reachable ? `data-pt-vs="${m.id}"` : "";
  return `
    <div class="match-item pt-mrow">
      <span class="match-day" title="${escHtml(ptStageLabel(m))}">${escHtml(String(day))}</span>
      <span class="match-names"><span class="match-id">#${m.id}</span></span>
      <span class="${cls}" ${attr}>${center}</span>
      ${status}${action}
    </div>`;
}
