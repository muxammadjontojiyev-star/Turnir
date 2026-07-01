/**
 * World Cup PLAY-OFF frontend.
 * - Profil "Play-off o'yinlarim" (kunlik matchlar, natija kiritish)
 * - Bracket setka (rasmona, barcha bosqichlar)
 *
 * Bosqich nomlari: r32(1/16) r16(1/8) r8(1/4) r4(1/2) final bronze.
 */

const WC_PLAYOFF_ROUND_NAMES = {
  r32: "1/16",
  r16: "1/8",
  r8: "1/4",
  r4: "1/2",
  final: "Final",
  bronze: "Bronza",
};

// O'yinchining play-off matchlari (profil bo'limi uchun)
async function wcRenderPlayoffMyMatches() {
  const t = APP.t;
  try {
    const data = await apiFetch("/wc/playoff/my-matches");
    const matches = data.matches || [];
    if (matches.length === 0) return "";  // play-off boshlanmagan yoki o'yinchi yo'q

    const items = matches.map(m => wcPlayoffMatchItem(m)).join("");
    return `
      <div class="section-label">${escHtml(t.wc_playoff_my_title || "PLAY-OFF O'YINLARIM")}</div>
      <div class="wc-matches-list">${items}</div>
    `;
  } catch (_) {
    return "";
  }
}

function wcPlayoffMatchItem(m) {
  const t = APP.t;
  const me = WC.profile ? WC.profile.user_id : null;
  const roundName = WC_PLAYOFF_ROUND_NAMES[m.round] || m.round;

  // O'yinchi tomonlari (men / raqib)
  const iAmP1 = m.player1_id === me;
  const myScore = iAmP1 ? m.score1 : m.score2;
  const oppScore = iAmP1 ? m.score2 : m.score1;
  const oppName = iAmP1 ? (m.player2_id ? "?" : "—") : (m.player1_id ? "?" : "—");

  // Skor ko'rinishi — ikki jamoa bayrog'i bilan (guruh o'yinlari kabi)
  const flag1 = m.p1_team ? wcTeamFlag(m.p1_team) : "";
  const flag2 = m.p2_team ? wcTeamFlag(m.p2_team) : "";
  const scoreNum = (m.score1 != null && m.score2 != null)
    ? `${m.score1} : ${m.score2}`
    : "— : —";
  const scoreText = `<span class="wc-mc-flag">${flag1}</span>`
    + `<span class="wc-po-score-num">${escHtml(scoreNum)}</span>`
    + `<span class="wc-mc-flag">${flag2}</span>`;

  // Holat / amal
  let statusBadge = "";
  let action = "";
  if (!m.is_open) {
    statusBadge = `<span class="match-status locked">${escHtml(t.wc_playoff_locked || "Yopiq")}</span>`;
    action = `<span class="match-locked" data-icon="lock"></span>`;
  } else if (m.status === "confirmed") {
    statusBadge = `<span class="match-status confirmed">${escHtml(t.confirmed_short || "Tasdiqlandi")}</span>`;
  } else if (m.status === "awaiting_confirmation") {
    const iSubmitted = m.submitted_by === me;
    if (iSubmitted) {
      statusBadge = `<span class="match-status awaiting">${escHtml(t.awaiting_short || "Kutilmoqda")}</span>`;
    } else {
      statusBadge = `<span class="match-status awaiting">${escHtml(t.awaiting_short || "Kutilmoqda")}</span>`;
      action = `<button class="match-action-btn wc-po-confirm-btn" data-mid="${m.id}">✔</button>`;
    }
  } else {
    // pending — natija kiritish yoki chat. Markaz (bayroqlar) bosilsa VS modal,
    // o'ngdagi 💬 to'g'ridan-to'g'ri Telegram. Natija chat ochilgach ochiladi.
    if (m.player1_id && m.player2_id) {
      statusBadge = `<span class="match-status pending">${escHtml(t.pending_short || "Kutilmoqda")}</span>`;
      const chatDone = WC.chatOpened && WC.chatOpened.has(m.id);
      if (chatDone) {
        action = `<button class="match-action-btn wc-po-result-btn" data-mid="${m.id}">${escHtml(t.enter_result || "Natija")}</button>`;
      } else {
        // O'ngdagi belgi — to'g'ridan-to'g'ri Telegram chatiga o'tadi
        action = `<button class="match-action-btn match-chat-btn wc-po-tgchat-btn" data-mid="${m.id}" title="${escHtml(t.opp_write_button || "Raqib chatiga yozish")}">${ICON.get("chat", 18)}</button>`;
      }
    } else {
      statusBadge = `<span class="match-status pending">${escHtml(t.wc_playoff_waiting_opp || "Raqib kutilmoqda")}</span>`;
    }
  }

  // Markaz (bayroqlar) bosiluvchi — VS modalni ochadi (guruh o'yinlari kabi).
  // Faqat ikkala o'yinchi aniq va match ochiq bo'lsa.
  const centerClickable = m.is_open && m.player1_id && m.player2_id;
  const centerCls = centerClickable ? "wc-po-score wc-po-score--clickable" : "wc-po-score";
  const centerAttr = centerClickable ? `data-wc-po-open="${m.id}"` : "";

  return `
    <div class="wc-match-card wc-po-card">
      <div class="wc-po-round">${escHtml(roundName)}</div>
      <div class="${centerCls}" ${centerAttr}>${scoreText}</div>
      ${statusBadge}
      ${action}
    </div>`;
}

function wcBindPlayoffMyMatches() {
  const root = document.getElementById("worldcup-root");
  if (!root) return;
  if (typeof applyIcons === "function") applyIcons(root);
  root.querySelectorAll(".wc-po-result-btn").forEach(btn => {
    btn.addEventListener("click", () => wcPlayoffOpenResultModal(parseInt(btn.dataset.mid)));
  });
  root.querySelectorAll(".wc-po-confirm-btn").forEach(btn => {
    btn.addEventListener("click", () => wcPlayoffOpenConfirmModal(parseInt(btn.dataset.mid)));
  });
  // Markaz (bayroqlar) bosilsa — VS modal (Chatni ochish / Raqib chatiga yozish)
  root.querySelectorAll("[data-wc-po-open]").forEach(el => {
    el.addEventListener("click", () => wcOpenPlayoffChat(parseInt(el.dataset.wcPoOpen)));
  });
  // O'ngdagi 💬 — to'g'ridan-to'g'ri Telegram chatiga o'tadi
  root.querySelectorAll(".wc-po-tgchat-btn").forEach(btn => {
    btn.addEventListener("click", () => wcOpenPlayoffTelegram(parseInt(btn.dataset.mid)));
  });
}

// O'ngdagi 💬 — raqib Telegram chatini to'g'ridan-to'g'ri ochadi, "Natija" tugmasini ochadi.
async function wcOpenPlayoffTelegram(matchId) {
  const t = APP.t;
  const me = WC.profile ? WC.profile.user_id : null;
  let m = null;
  try {
    const data = await apiFetch("/wc/playoff/my-matches");
    m = (data.matches || []).find(x => x.id === matchId);
  } catch (_) { /* pastda tekshiramiz */ }
  if (!m) {
    if (typeof showToast === "function") showToast(t.opp_no_contact || "Raqib bilan bog'lanib bo'lmaydi");
    return;
  }
  const iAmP1 = m.player1_id === me;
  const oppUser = iAmP1 ? m.p2_user : m.p1_user;

  if (!WC.chatOpened) WC.chatOpened = new Set();
  WC.chatOpened.add(matchId);

  if (oppUser && typeof wcOpenTelegramChat === "function") {
    wcOpenTelegramChat({ username: oppUser, tg: null });
  } else if (typeof showToast === "function") {
    showToast(t.opp_no_contact || "Raqib bilan bog'lanib bo'lmaydi");
  }
  if (typeof wcLoadPlayoffMyMatches === "function") await wcLoadPlayoffMyMatches();
}

// Play-off raqibi bilan Telegram chatini ochadi (guruh oqimi kabi).
// Play-off raqib modali (VS — "Chatni ochish" ichki / "Raqib chatiga yozish" Telegram).
// Liga wcOpenOpponentModal naqshi, lekin play-off match strukturasi (p1_team/p2_team/p1_user/p2_user).
async function wcOpenPlayoffChat(matchId) {
  const t = APP.t;
  const me = WC.profile ? WC.profile.user_id : null;
  let m = null;
  try {
    const data = await apiFetch("/wc/playoff/my-matches");
    m = (data.matches || []).find(x => x.id === matchId);
  } catch (_) { /* pastda tekshiramiz */ }
  if (!m) {
    if (typeof showToast === "function") showToast(t.opp_no_contact || "Raqib bilan bog'lanib bo'lmaydi");
    return;
  }

  // Raqib tomonini aniqlaymiz (men p1 bo'lsam — raqib p2, aks holda p1)
  const iAmP1 = m.player1_id === me;
  const opp = iAmP1
    ? { username: m.p2_user, nickname: m.p2_nick, club: m.p2_team }
    : { username: m.p1_user, nickname: m.p1_nick, club: m.p1_team };

  // Telegram chatiga yozish tugmasi (username bo'lsa)
  const chatBtn = opp.username
    ? `<button class="opp-chat-btn" id="wc-po-opp-tg-btn">${ICON.get("chat", 18)} ${escHtml(t.opp_write_button || "Raqib chatiga yozish")}</button>`
    : `<div class="opp-no-contact">${escHtml(t.opp_no_contact || "Raqib bilan bog'lanib bo'lmaydi")}</div>`;

  // Ichki webchat — faqat aktiv match (pending / awaiting_confirmation)
  const chatActive = (m.status === "pending" || m.status === "awaiting_confirmation");
  const webChatBtn = chatActive
    ? `<button class="opp-chat-btn opp-webchat-btn" id="wc-po-opp-web-btn">${ICON.get("chat", 18)} ${escHtml(t.webchat_open || "Chatni ochish")}</button>`
    : "";

  let modal = document.getElementById("wc-modal-po-opponent");
  if (!modal) {
    modal = document.createElement("div");
    modal.id = "wc-modal-po-opponent";
    modal.className = "modal hidden";
    document.body.appendChild(modal);
  }
  modal.innerHTML = `
    <div class="modal-box opp-modal-box">
      <button class="modal-close" id="wc-po-opp-close">${ICON.get("close", 18)}</button>
      <div class="opp-vs">
        ${wcRenderOpponentSide(m.p1_team, m.p1_user, m.p1_nick)}
        <div class="opp-vs-sep">VS</div>
        ${wcRenderOpponentSide(m.p2_team, m.p2_user, m.p2_nick)}
      </div>
      ${webChatBtn}
      ${chatBtn}
    </div>
  `;
  modal.classList.remove("hidden");
  if (typeof applyIcons === "function") applyIcons(modal);

  const closeModal = () => modal.classList.add("hidden");
  document.getElementById("wc-po-opp-close").addEventListener("click", closeModal);
  modal.addEventListener("click", (e) => { if (e.target === modal) closeModal(); });

  // Chat ochilgan deb belgilaymiz — "Natija" tugmasi ochiladi
  const markChatOpened = () => {
    if (!WC.chatOpened) WC.chatOpened = new Set();
    WC.chatOpened.add(matchId);
    if (typeof wcLoadPlayoffMyMatches === "function") void wcLoadPlayoffMyMatches();
  };

  // "Raqib chatiga yozish" → Telegram
  const tgBtn = document.getElementById("wc-po-opp-tg-btn");
  if (tgBtn && opp.username && typeof wcOpenTelegramChat === "function") {
    tgBtn.addEventListener("click", () => {
      markChatOpened();
      wcOpenTelegramChat({ username: opp.username, tg: null });
    });
  }

  // "Chatni ochish" → WebApp ichki chat (play-off rejimida)
  const webBtn = document.getElementById("wc-po-opp-web-btn");
  if (webBtn && typeof wcOpenWebChat === "function") {
    const oppLabel = opp.nickname || (opp.username ? "@" + String(opp.username).replace(/^@/, "") : (t.webchat_opponent || "Raqib"));
    webBtn.addEventListener("click", () => {
      closeModal();
      markChatOpened();
      wcOpenWebChat(matchId, oppLabel, 1);  // 3-arg: is_playoff=1
    });
  }
}

// Natija kiritish modali
function wcPlayoffOpenResultModal(matchId) {
  const t = APP.t;
  WC.poActiveMatch = matchId;
  const modal = document.getElementById("wc-po-modal");
  if (!modal) return;
  document.getElementById("wc-po-score1").value = "";
  document.getElementById("wc-po-score2").value = "";
  document.getElementById("wc-po-score1").readOnly = false;
  document.getElementById("wc-po-score2").readOnly = false;
  document.getElementById("wc-po-modal-title").textContent = t.enter_result || "Natija kiritish";
  document.getElementById("wc-po-modal-mode").value = "submit";
  document.getElementById("wc-po-modal-reject")?.classList.add("hidden");
  document.getElementById("wc-po-modal-submit").textContent = t.submit || "Yuborish";
  // Bayroqlar (tanlangan jamoalar)
  wcPlayoffSetModalFlags(matchId);
  modal.classList.remove("hidden");
}

// Play-off natija modalidagi bayroqlarni match jamoalaridan to'ldiradi.
async function wcPlayoffSetModalFlags(matchId) {
  const f1 = document.getElementById("wc-po-flag1");
  const f2 = document.getElementById("wc-po-flag2");
  if (!f1 || !f2) return;
  try {
    const data = await apiFetch("/wc/playoff/my-matches");
    const m = (data.matches || []).find(x => x.id === matchId);
    if (m) {
      f1.textContent = m.p1_team ? wcTeamFlag(m.p1_team) : "";
      f2.textContent = m.p2_team ? wcTeamFlag(m.p2_team) : "";
    }
  } catch (_) { /* jim — bayroqsiz ham modal ishlaydi */ }
}

// Tasdiqlash modali (raqib kiritgan natijani ko'rib tasdiqlash/rad etish)
async function wcPlayoffOpenConfirmModal(matchId) {
  const t = APP.t;
  WC.poActiveMatch = matchId;
  // Match ma'lumotini olamiz (skorni ko'rsatish uchun)
  try {
    const data = await apiFetch("/wc/playoff/my-matches");
    const m = (data.matches || []).find(x => x.id === matchId);
    if (!m) return;
    const modal = document.getElementById("wc-po-modal");
    document.getElementById("wc-po-modal-title").textContent =
      `${t.confirm_short || "Tasdiqlash"}: ${m.score1} : ${m.score2}`;
    document.getElementById("wc-po-score1").value = m.score1;
    document.getElementById("wc-po-score2").value = m.score2;
    document.getElementById("wc-po-modal-mode").value = "confirm";
    document.getElementById("wc-po-modal-reject")?.classList.remove("hidden");
    document.getElementById("wc-po-modal-submit").textContent = t.confirm_yes || "Tasdiqlash";
    document.getElementById("wc-po-score1").readOnly = true;
    document.getElementById("wc-po-score2").readOnly = true;
    // Bayroqlar (m allaqachon olingan)
    const f1 = document.getElementById("wc-po-flag1");
    const f2 = document.getElementById("wc-po-flag2");
    if (f1) f1.textContent = m.p1_team ? wcTeamFlag(m.p1_team) : "";
    if (f2) f2.textContent = m.p2_team ? wcTeamFlag(m.p2_team) : "";
    modal.classList.remove("hidden");
  } catch (_) {}
}

async function wcPlayoffSubmitFromModal() {
  const t = APP.t;
  const mode = document.getElementById("wc-po-modal-mode").value;
  const matchId = WC.poActiveMatch;
  const s1 = parseInt(document.getElementById("wc-po-score1").value);
  const s2 = parseInt(document.getElementById("wc-po-score2").value);

  try {
    if (mode === "confirm") {
      await apiFetch(`/wc/playoff/confirm-result?match_id=${matchId}&accept=true`, { method: "POST" });
      showToast(t.confirmed_done || "✅ Tasdiqlandi");
    } else {
      if (isNaN(s1) || isNaN(s2)) { showToast("❌ " + (t.fill_scores || "Hisobni kiriting")); return; }
      if (s1 === s2) { showToast("❌ " + (t.wc_playoff_draw_err || "Durang bo'lmaydi — g'olib aniq bo'lsin")); return; }
      await apiFetch(`/wc/playoff/submit-result?match_id=${matchId}&score1=${s1}&score2=${s2}`, { method: "POST" });
      showToast(t.result_sent || "✅ Natija yuborildi");
    }
    document.getElementById("wc-po-modal").classList.add("hidden");
    renderWorldCup();
  } catch (e) {
    const msg = {
      draw_not_allowed: t.wc_playoff_draw_err || "Durang bo'lmaydi",
      not_open:         t.wc_playoff_locked || "Bu bosqich hali ochilmagan",
      already_done:     t.already_confirmed || "Allaqachon tasdiqlangan",
    }[e.message] || e.message;
    showToast("❌ " + msg);
  }
}

async function wcPlayoffRejectFromModal() {
  const t = APP.t;
  const matchId = WC.poActiveMatch;
  try {
    await apiFetch(`/wc/playoff/confirm-result?match_id=${matchId}&accept=false`, { method: "POST" });
    showToast(t.rejected_done || "Rad etildi");
    document.getElementById("wc-po-modal").classList.add("hidden");
    renderWorldCup();
  } catch (e) {
    showToast("❌ " + e.message);
  }
}

// ===== BRACKET SETKA (rasmona) =====
const WC_BRACKET_ORDER = ["r32", "r16", "r8", "r4", "final", "bronze"];

async function wcRenderBracket() {
  const t = APP.t;
  try {
    const data = await apiFetch("/wc/playoff/bracket");
    if (!data.started) {
      return `<div class="empty-state">${escHtml(t.wc_playoff_not_started || "Play-off hali boshlanmagan")}</div>`;
    }
    const rounds = data.rounds || {};
    const cols = WC_BRACKET_ORDER.filter(r => rounds[r] && rounds[r].length).map(r => {
      const matches = rounds[r].sort((a, b) => a.position - b.position);
      const cards = matches.map(m => wcBracketCard(m)).join("");
      return `
        <div class="wc-bracket-col">
          <div class="wc-bracket-round-label">${escHtml(WC_PLAYOFF_ROUND_NAMES[r] || r)}</div>
          ${cards}
        </div>`;
    }).join("");
    return `
      <div class="section-label">${escHtml(t.wc_bracket_title || "PLAY-OFF SETKASI")}</div>
      <div class="wc-bracket-scroll"><div class="wc-bracket">${cols}</div></div>
    `;
  } catch (_) {
    return `<div class="empty-state">${escHtml(t.no_data || "Ma'lumot yo'q")}</div>`;
  }
}

function wcBracketCard(m) {
  const p1 = wcBracketSide(m.p1_team, m.p1_user, m.p1_nick, m.score1, m.status);
  const p2 = wcBracketSide(m.p2_team, m.p2_user, m.p2_nick, m.score2, m.status);
  const win1 = m.status === "confirmed" && m.score1 > m.score2;
  const win2 = m.status === "confirmed" && m.score2 > m.score1;
  return `
    <div class="wc-bracket-card">
      <div class="wc-bracket-side ${win1 ? "winner" : ""}">${p1}</div>
      <div class="wc-bracket-side ${win2 ? "winner" : ""}">${p2}</div>
    </div>`;
}

function wcBracketSide(team, user, nick, score, status) {
  const name = team || "—";
  const flag = team ? wcTeamFlag(team) : "";
  const scoreTxt = (score != null) ? score : "";
  return `
    <span class="wc-bracket-flag">${flag}</span>
    <span class="wc-bracket-name">${escHtml(name)}</span>
    <span class="wc-bracket-score">${scoreTxt}</span>`;
}


// Bracketni reyting konteyneriga yuklash
async function wcLoadBracket() {
  const box = document.getElementById("wc-bracket-box");
  if (!box) return;
  box.innerHTML = await wcRenderBracket();
}


// ===== WC SOVRINLAR (kubok + chempion) =====
function wcRenderPrizes() {
  const t = APP.t;
  return `
    <div class="section-label">${escHtml(t.prizes_title || "SOVRINLAR")}</div>
    <div class="card card--prize wc-prize-card">
      <div class="prize-icon wc-trophy-icon">
        <img src="wc-trophy.png?v=20260628a3" alt="World Cup" class="wc-trophy-img" />
      </div>
      <div class="prize-info">
        <div class="prize-name">${escHtml(t.wc_trophy_name || "Jahon Chempionati Kubogi")}</div>
        <div class="prize-desc">${escHtml(t.wc_trophy_desc || "Play-off g'olibi — jahon chempioni")}</div>
        <div class="prize-holder" id="wc-champion-name">—</div>
        <div class="prize-club" id="wc-champion-user"></div>
      </div>
    </div>
    <div class="card card--prize wc-prize-card">
      <div class="prize-icon wc-trophy-icon">
        <img src="wc-goldenball.png?v=20260628b6" alt="Golden Ball" class="wc-trophy-img" />
      </div>
      <div class="prize-info">
        <div class="prize-name">${escHtml(t.wc_scorer_name || "Jahon Chempionati To'purari")}</div>
        <div class="prize-desc">${escHtml(t.wc_scorer_desc || "Eng ko'p gol urgan o'yinchi")}</div>
        <div class="prize-holder" id="wc-scorer-name">—</div>
        <div class="prize-club" id="wc-scorer-user"></div>
      </div>
    </div>
  `;
}

async function wcBindPrizes() {
  const t = APP.t;
  const nameEl = document.getElementById("wc-champion-name");
  const userEl = document.getElementById("wc-champion-user");
  if (!nameEl) return;
  try {
    const data = await apiFetch("/wc/playoff/champion");
    if (data.champion) {
      const c = data.champion;
      const flag = c.team_name ? wcTeamFlag(c.team_name) : "🏆";
      nameEl.innerHTML = `${flag} ${escHtml(c.team_name || "")}`;
      userEl.textContent = c.username ? `@${c.username}` : (c.nickname || "");
    } else {
      nameEl.textContent = t.wc_champion_pending || "Hali aniqlanmagan";
      userEl.textContent = "";
    }
  } catch (_) {
    nameEl.textContent = t.wc_champion_pending || "Hali aniqlanmagan";
  }

  // To'purar (Oltin To'p) — /wc/top-scorers dan eng ko'p gol urgan (birinchi qator)
  const scorerNameEl = document.getElementById("wc-scorer-name");
  const scorerUserEl = document.getElementById("wc-scorer-user");
  if (scorerNameEl) {
    try {
      const sd = await apiFetch("/wc/top-scorers");
      const top = (sd.scorers || [])[0];
      if (top && (top.goals_for || 0) > 0) {
        const flag = top.team_name ? wcTeamFlag(top.team_name) : "⚽";
        const goalsTxt = t.wc_scorer_goals || "gol";
        scorerNameEl.innerHTML = `${flag} ${escHtml(top.team_name || "")} — ${top.goals_for} ${escHtml(goalsTxt)}`;
        scorerUserEl.textContent = top.username ? `@${top.username}` : (top.nickname || "");
      } else {
        scorerNameEl.textContent = t.wc_champion_pending || "Hali aniqlanmagan";
        scorerUserEl.textContent = "";
      }
    } catch (_) {
      scorerNameEl.textContent = t.wc_champion_pending || "Hali aniqlanmagan";
    }
  }
}
