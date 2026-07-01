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
    // pending — avval raqib bilan chatlashish (💬), chat ochilgach "Natija" (guruh oqimi kabi)
    if (m.player1_id && m.player2_id) {
      statusBadge = `<span class="match-status pending">${escHtml(t.pending_short || "Kutilmoqda")}</span>`;
      const chatDone = WC.chatOpened && WC.chatOpened.has(m.id);
      if (chatDone) {
        action = `<button class="match-action-btn wc-po-result-btn" data-mid="${m.id}">${escHtml(t.enter_result || "Natija")}</button>`;
      } else {
        action = `<button class="match-action-btn match-chat-btn wc-po-chat-btn" data-mid="${m.id}" title="${escHtml(t.chat_first_hint || "Avval raqib bilan kelishing")}">${ICON.get("chat", 18)}</button>`;
      }
    } else {
      statusBadge = `<span class="match-status pending">${escHtml(t.wc_playoff_waiting_opp || "Raqib kutilmoqda")}</span>`;
    }
  }

  return `
    <div class="wc-match-card wc-po-card">
      <div class="wc-po-round">${escHtml(roundName)}</div>
      <div class="wc-po-score">${scoreText}</div>
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
  // Chat tugmasi (💬) — raqib bilan Telegram chatini ochadi, keyin "Natija" ochiladi
  root.querySelectorAll(".wc-po-chat-btn").forEach(btn => {
    btn.addEventListener("click", () => wcOpenPlayoffChat(parseInt(btn.dataset.mid)));
  });
}

// Play-off raqibi bilan Telegram chatini ochadi (guruh oqimi kabi).
// Chat ochilgach WC.chatOpened ga belgilanadi va ro'yxat yangilanib "Natija" ochiladi.
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
  const oppUser = iAmP1 ? m.p2_user : m.p1_user;

  // Chat ochilgan deb belgilaymiz — "Natija" tugmasi ochiladi
  if (!WC.chatOpened) WC.chatOpened = new Set();
  WC.chatOpened.add(matchId);

  if (typeof wcOpenTelegramChat === "function") {
    wcOpenTelegramChat({ username: oppUser || null, tg: null });
  }
  // Play-off ro'yxatini qayta chizamiz (chat ochilgani uchun "Natija" ko'rinadi)
  if (typeof wcLoadPlayoffMyMatches === "function") {
    await wcLoadPlayoffMyMatches();
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
  modal.classList.remove("hidden");
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
