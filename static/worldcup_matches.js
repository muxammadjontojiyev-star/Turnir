// ============================================================
//  worldcup_matches.js — World Cup profil bo'limi:
//  o'yinlar ro'yxati + natija kiritish + tasdiqlash/rad etish.
//
//  worldcup.js dagi WC state va renderWorldCup'ga ulanadi (WC.section==="profile").
//  Liga (api.js) natija mantig'i naqshiga izchil, lekin /wc/* endpointlari bilan.
// ============================================================

// WC profil bo'limidagi o'yinlar (yuklangach saqlanadi — modal uchun)
WC.myMatches = [];

// ---- PROFIL bo'limi (liga profili kabi: avatar+bayroq+statistika+o'yinlar) ----
function wcRenderProfile() {
  const t = APP.t;
  const reg = WC.profile;

  // Ro'yxatdan o'tmagan bo'lsa — eslatma (lekin admin panel baribir ko'rinishi mumkin)
  if (!reg || !reg.registered) {
    return `
      <div class="wc-placeholder">
        <span class="wc-placeholder-icon" data-icon="user"></span>
        <div class="wc-placeholder-text">${escHtml(t.wc_not_registered || "Siz hali World Cup'ga ro'yxatdan o'tmagansiz")}</div>
      </div>
      <div id="wc-admin-panel" class="admin-panel hidden"></div>`;
  }

  const flag = wcTeamFlag(reg.team_name);
  const groupLabel = (t.wc_group || "{g} guruh").replace("{g}", reg.group_letter);

  // Avatar: Telegram profil rasmi (bo'lmasa — bayroq). Liga kabi.
  const photoUrl = APP.currentUser?.photo_url || null;
  const nick = APP.currentUser?.first_name || reg.team_name || "?";
  const avatarInner = photoUrl
    ? `<img src="${escHtml(photoUrl)}" alt="" style="width:56px;height:56px;object-fit:cover;border-radius:50%;" onerror="this.style.display='none';this.parentElement.querySelector('.wc-profile-flag').style.display='block'" /><span class="wc-profile-flag" style="display:none">${flag}</span>`
    : `<span class="wc-profile-flag">${flag}</span>`;

  // Username linki (liga kabi)
  const username = APP.currentUser?.username || null;
  const subline = username
    ? `${escHtml(nick)}<br><a class="profile-username" href="https://t.me/${escHtml(username)}" target="_blank">@${escHtml(username)}</a>`
    : escHtml(groupLabel);

  // Statistika (backend /wc/profile rating)
  const r = reg.rating;
  const pos = r ? `#${r.position}` : "—";
  const wins = r ? r.wins : "—";
  const draws = r ? r.draws : "—";
  const losses = r ? r.losses : "—";

  // O'ng tomondagi belgi: tanlangan davlat bayrog'i
  const clubBadge = `<span class="wc-profile-badge-flag">${flag}</span>`;

  return `
    <div class="card card--profile">
      <div class="profile-avatar">${avatarInner}</div>
      <div class="profile-info">
        <h2 class="profile-nickname">${escHtml(reg.team_name || "")}</h2>
        <span class="profile-league">${subline}</span>
      </div>
      <div class="profile-club-badge">${clubBadge}</div>
    </div>

    <!-- Sovrinlarim (async — rasm bilan statistika orasida) -->
    <div id="wc-my-prizes-section"></div>

    <div class="section-label">${escHtml(t.my_stats || "STATISTIKA")}</div>
    <div class="stats-grid">
      <div class="stat-card stat-card--primary">
        <span class="stat-card-value neon-cyan">${pos}</span>
        <span class="stat-card-label">${escHtml(t.stat_pos || "O'rin")}</span>
      </div>
      <div class="stat-card">
        <span class="stat-card-value neon-cyan">${wins}</span>
        <span class="stat-card-label">${escHtml(t.stat_w || "G'alaba")}</span>
      </div>
      <div class="stat-card">
        <span class="stat-card-value">${draws}</span>
        <span class="stat-card-label">${escHtml(t.stat_d || "Durang")}</span>
      </div>
      <div class="stat-card">
        <span class="stat-card-value neon-red">${losses}</span>
        <span class="stat-card-label">${escHtml(t.stat_l || "Mag'lubiyat")}</span>
      </div>
    </div>

    <div class="section-label">${escHtml(t.my_matches || "MENING O'YINLARIM")}</div>
    <div id="wc-matches-list" class="matches-list">
      <div class="wc-loading-row">${escHtml(t.loading || "Yuklanmoqda...")}</div>
    </div>

    <!-- Play-off o'yinlarim (async to'ldiriladi) -->
    <div id="wc-playoff-mymatches"></div>

    <!-- Play-off natija/tasdiqlash modali -->
    <div id="wc-po-modal" class="modal hidden">
      <div class="modal-box">
        <div class="modal-title" id="wc-po-modal-title">${escHtml(t.enter_result || "Natija kiritish")}</div>
        <input type="hidden" id="wc-po-modal-mode" value="submit" />
        <div class="score-input-row">
          <div class="score-input-group">
            <div class="score-logo-input">
              <span class="wc-result-flag" id="wc-po-flag1"></span>
              <input id="wc-po-score1" class="score-input" type="number" min="0" max="99" />
            </div>
          </div>
          <span class="score-separator">:</span>
          <div class="score-input-group">
            <div class="score-logo-input">
              <input id="wc-po-score2" class="score-input" type="number" min="0" max="99" />
              <span class="wc-result-flag" id="wc-po-flag2"></span>
            </div>
          </div>
        </div>
        <p class="confirm-warning">${escHtml(t.wc_playoff_draw_hint || "Durang bo'lmaydi — g'olib aniq bo'lsin (penalti/qo'shimcha vaqt).")}</p>
        <div class="modal-actions modal-actions--stacked">
          <button class="btn btn--primary btn--glow" id="wc-po-modal-submit">${escHtml(t.submit || "Yuborish")}</button>
          <button class="btn btn--danger hidden" id="wc-po-modal-reject">${escHtml(t.confirm_no || "Rad etish")}</button>
          <button class="btn btn--ghost" id="wc-po-modal-cancel">${escHtml(t.cancel || "Bekor")}</button>
        </div>
      </div>
    </div>

    <!-- WC admin paneli (rolga qarab JS ko'rsatadi) -->
    <div id="wc-admin-panel" class="admin-panel hidden"></div>

    <!-- Natija kiritish modali -->
    <div id="wc-modal-result" class="modal hidden">
      <div class="modal-box">
        <div class="modal-title">${escHtml(t.submit_result || "Natija kiritish")}</div>
        <div class="score-input-row">
          <div class="score-input-group">
            <div class="score-logo-input">
              <span class="wc-result-flag" id="wc-result-flag1"></span>
              <input id="wc-input-score1" class="score-input" type="number" min="0" max="99" value="0" />
            </div>
          </div>
          <span class="score-separator">:</span>
          <div class="score-input-group">
            <div class="score-logo-input">
              <input id="wc-input-score2" class="score-input" type="number" min="0" max="99" value="0" />
              <span class="wc-result-flag" id="wc-result-flag2"></span>
            </div>
          </div>
        </div>
        <div class="modal-actions">
          <button class="btn btn--ghost" id="wc-btn-result-cancel">${escHtml(t.cancel || "Bekor")}</button>
          <button class="btn btn--primary btn--glow" id="wc-btn-result-submit">${escHtml(t.submit || "Yuborish")}</button>
        </div>
      </div>
    </div>

    <!-- Tasdiqlash modali -->
    <div id="wc-modal-confirm" class="modal hidden">
      <div class="modal-box">
        <div class="modal-title">${escHtml(t.confirm_result_title || "Natijani tasdiqlaysizmi?")}</div>
        <div id="wc-confirm-score" class="confirm-score"></div>
        <p class="confirm-warning">${escHtml(t.confirm_warning || "Faqat haqiqatan o'ynagan va natija to'g'ri bo'lsa tasdiqlang.")}</p>
        <div class="modal-actions modal-actions--stacked">
          <button class="btn btn--primary" id="wc-btn-confirm-yes">${escHtml(t.confirm_yes || "Ha, o'ynadik va to'g'ri")}</button>
          <button class="btn btn--danger" id="wc-btn-confirm-no">${escHtml(t.confirm_no || "Yo'q, bunday o'yin bo'lmagan")}</button>
          <button class="btn btn--ghost" id="wc-btn-confirm-cancel">${escHtml(t.cancel || "Bekor")}</button>
        </div>
      </div>
    </div>
  `;
}

function wcBindProfile() {
  // Modal yopish tugmalari
  document.getElementById("wc-btn-result-cancel")?.addEventListener("click", wcCloseResultModal);
  document.getElementById("wc-btn-result-submit")?.addEventListener("click", wcSubmitResult);
  document.getElementById("wc-btn-confirm-cancel")?.addEventListener("click", wcCloseConfirmModal);
  document.getElementById("wc-btn-confirm-yes")?.addEventListener("click", () => wcConfirmAction("confirm"));
  document.getElementById("wc-btn-confirm-no")?.addEventListener("click", () => wcConfirmAction("reject"));

  void wcLoadMatches();
  if (typeof wcLoadAdminPanel === "function") void wcLoadAdminPanel();

  // Sovrinlarim (liga renderMyPrizes'ni qayta ishlatamiz)
  void wcLoadMyPrizes();

  // Play-off o'yinlarim (async to'ldiriladi) + modal listenerlar
  if (typeof wcLoadPlayoffMyMatches === "function") void wcLoadPlayoffMyMatches();
  document.getElementById("wc-po-modal-cancel")?.addEventListener("click", () => {
    document.getElementById("wc-po-modal")?.classList.add("hidden");
  });
  document.getElementById("wc-po-modal-submit")?.addEventListener("click", () => {
    if (typeof wcPlayoffSubmitFromModal === "function") wcPlayoffSubmitFromModal();
  });
  document.getElementById("wc-po-modal-reject")?.addEventListener("click", () => {
    if (typeof wcPlayoffRejectFromModal === "function") wcPlayoffRejectFromModal();
  });
}

// Play-off matchlarni profil konteyneriga yuklash
async function wcLoadPlayoffMyMatches() {
  const box = document.getElementById("wc-playoff-mymatches");
  if (!box) return;
  const html = await wcRenderPlayoffMyMatches();
  box.innerHTML = html;
  if (typeof wcBindPlayoffMyMatches === "function") wcBindPlayoffMyMatches();
  // Tasdiqlash rejimida reject tugmasini ko'rsatish uchun modal ochilganda hal qilinadi
}

// ---- O'yinlar ro'yxatini yuklash ----
async function wcLoadMatches() {
  const list = document.getElementById("wc-matches-list");
  if (!list) return;
  try {
    const data = await apiFetch("/wc/matches/my");
    WC.myMatches = data.matches || [];
  } catch (_) {
    WC.myMatches = [];
  }
  wcRenderMatchesList();
}

function wcRenderMatchesList() {
  const t = APP.t;
  const list = document.getElementById("wc-matches-list");
  if (!list) return;
  if (WC.myMatches.length === 0) {
    list.innerHTML = `<div class="wc-loading-row">${escHtml(t.wc_no_matches || "Hali o'yinlar yo'q")}</div>`;
    return;
  }
  list.innerHTML = WC.myMatches.map(m => wcRenderMatchItem(m)).join("");
  wcBindMatchActions();
}

// Bitta o'yin kartasi (liga renderMatchItem naqshi: status label + chat oqimi)
function wcRenderMatchItem(m) {
  const t = APP.t;
  const flag1 = wcTeamFlag(m.player1_club);
  const flag2 = wcTeamFlag(m.player2_club);
  const hasScore = (m.score1 !== null && m.score1 !== undefined);
  const center = hasScore
    ? `<span class="wc-mc-flag">${flag1}</span><span class="match-score">${m.score1} : ${m.score2}</span><span class="wc-mc-flag">${flag2}</span>`
    : `<span class="wc-mc-flag">${flag1}</span><span class="match-score">— : —</span><span class="wc-mc-flag">${flag2}</span>`;

  // Status label (liga kabi)
  let statusCls  = "status--pending";
  let statusText = t.status_pending || "KUTILMOQDA";
  if (m.status === "awaiting_confirmation") { statusCls = "status--awaiting";  statusText = t.status_awaiting  || "TASDIQ"; }
  if (m.status === "admin_pending")         { statusCls = "status--awaiting";  statusText = t.status_admin_pending || "ADMIN TASDIG'I"; }
  if (m.status === "confirmed")             { statusCls = "status--confirmed"; statusText = t.status_confirmed || "TASDIQLANDI"; }

  // Amal tugmasi: status va lock holatiga qarab (liga oqimi)
  const myTgId = (window.Telegram?.WebApp?.initDataUnsafe?.user?.id) || null;
  const iSubmitted = m.submitted_by && (
    (m.player1_id === m.submitted_by && m.player1_telegram_id === myTgId) ||
    (m.player2_id === m.submitted_by && m.player2_telegram_id === myTgId)
  );

  let action = "";
  if (m.status === "pending") {
    if (m.is_locked) {
      action = `<span class="match-locked" data-icon="lock"></span>`;
    } else {
      // Avval raqib bilan chatlashish kerak: 💬 tugmasi. Chat ochilgach "Natija" ochiladi.
      const chatDone = WC.chatOpened && WC.chatOpened.has(m.id);
      if (chatDone) {
        action = `<button class="match-action-btn wc-match-result-btn" data-mid="${m.id}">${escHtml(t.enter_result || "Natija")}</button>`;
      } else {
        action = `<button class="match-action-btn match-chat-btn wc-match-chat-btn" data-mid="${m.id}" title="${escHtml(t.chat_first_hint || "Avval raqib bilan kelishing")}">${ICON.get("chat", 18)}</button>`;
      }
    }
  } else if (m.status === "awaiting_confirmation") {
    if (iSubmitted) {
      // Men yubordim — raqib tasdiqlashini kutyapman
      action = `<span class="match-waiting" title="${escHtml(t.awaiting_hint || "Raqib tasdiqlashini kuting")}">${escHtml(t.awaiting_short || "Kutilmoqda")}</span>`;
    } else {
      // Raqib yubordi — men ko'rib tasdiqlayman/rad etaman (modal skorni ko'rsatadi)
      action = `<button class="match-action-btn wc-match-confirm-btn" data-mid="${m.id}">✔</button>`;
    }
  }

  // Markaz bosiluvchi (qulfsiz) — raqib modalini ochadi (liga kabi)
  const isOpen = !m.is_locked;
  const centerCls = isOpen ? "match-center match-center--clickable" : "match-center";
  const centerAttr = isOpen ? `data-wc-open-match="${m.id}"` : "";

  return `
    <div class="match-item">
      <span class="match-names">#${m.id}</span>
      <div class="${centerCls}" ${centerAttr}>${center}</div>
      <span class="match-status ${statusCls}">${statusText}</span>
      ${action}
    </div>`;
}

function wcBindMatchActions() {
  const root = document.getElementById("worldcup-root");
  if (typeof applyIcons === "function") applyIcons(root);
  root.querySelectorAll(".wc-match-result-btn").forEach(btn => {
    btn.addEventListener("click", () => wcOpenResultModal(parseInt(btn.dataset.mid, 10)));
  });
  root.querySelectorAll(".wc-match-confirm-btn").forEach(btn => {
    btn.addEventListener("click", () => wcOpenConfirmModal(parseInt(btn.dataset.mid, 10)));
  });
  // Chat tugmasi (💬) — chat oynasini ochadi
  root.querySelectorAll(".wc-match-chat-btn").forEach(btn => {
    btn.addEventListener("click", () => wcOpenMatchChat(parseInt(btn.dataset.mid, 10)));
  });
  // Markaz bosish (qulfsiz o'yin) — raqib modalini ochadi
  root.querySelectorAll("[data-wc-open-match]").forEach(el => {
    el.addEventListener("click", () => wcOpenOpponentModal(parseInt(el.dataset.wcOpenMatch, 10)));
  });
}

// ---- Natija kiritish modali ----
function wcOpenResultModal(matchId) {
  WC.activeMatchId = matchId;
  const m = WC.myMatches.find(x => x.id === matchId);
  const f1 = document.getElementById("wc-result-flag1");
  const f2 = document.getElementById("wc-result-flag2");
  if (m && f1) f1.textContent = wcTeamFlag(m.player1_club);
  if (m && f2) f2.textContent = wcTeamFlag(m.player2_club);
  document.getElementById("wc-input-score1").value = "0";
  document.getElementById("wc-input-score2").value = "0";
  document.getElementById("wc-modal-result")?.classList.remove("hidden");
}

function wcCloseResultModal() {
  document.getElementById("wc-modal-result")?.classList.add("hidden");
  WC.activeMatchId = null;
}

async function wcSubmitResult() {
  const t = APP.t;
  const matchId = WC.activeMatchId;
  if (!matchId) return;
  const s1 = parseInt(document.getElementById("wc-input-score1").value, 10) || 0;
  const s2 = parseInt(document.getElementById("wc-input-score2").value, 10) || 0;
  try {
    const res = await apiFetch(`/wc/match/submit-result?match_id=${matchId}&score1=${s1}&score2=${s2}`, { method: "POST" });
    if (res && res.reason === "ok_admin_pending") {
      showToast(t.result_admin_pending || "✅ Natija yuborildi. Katta hisob — adminga skrinshot yuboring.");
    } else {
      showToast(t.result_submitted || "✅ Natija yuborildi");
    }
    wcCloseResultModal();
    await wcLoadMatches();
  } catch (e) {
    const msg = {
      matchday_locked:    t.matchday_locked || "Bu tur hali ochilmagan",
      already_submitted:  t.already_submitted || "Natija allaqachon kiritilgan",
      not_participant:    t.not_participant || "Siz bu o'yin ishtirokchisi emassiz",
    }[e.message] || e.message;
    showToast("❌ " + msg);
  }
}

// ---- Tasdiqlash modali ----
function wcOpenConfirmModal(matchId) {
  WC.activeMatchId = matchId;
  const m = WC.myMatches.find(x => x.id === matchId);
  const scoreEl = document.getElementById("wc-confirm-score");
  if (m && scoreEl) {
    const f1 = wcTeamFlag(m.player1_club), f2 = wcTeamFlag(m.player2_club);
    scoreEl.innerHTML = `${f1} <b>${m.score1} : ${m.score2}</b> ${f2}`;
  }
  document.getElementById("wc-modal-confirm")?.classList.remove("hidden");
}

function wcCloseConfirmModal() {
  document.getElementById("wc-modal-confirm")?.classList.add("hidden");
  WC.activeMatchId = null;
}

async function wcConfirmAction(action) {
  const t = APP.t;
  const matchId = WC.activeMatchId;
  if (!matchId) return;
  try {
    await apiFetch(`/wc/match/confirm?match_id=${matchId}&action=${action}`, { method: "POST" });
    showToast(action === "confirm"
      ? (t.confirmed_ok || "✅ Natija tasdiqlandi")
      : (t.rejected_ok || "❌ Natija rad etildi"));
    wcCloseConfirmModal();
    await wcLoadMatches();
  } catch (e) {
    const msg = {
      wrong_status:   t.wrong_status || "Bu o'yin holati o'zgargan",
      not_opponent:   t.not_opponent || "Siz bu natijani tasdiqlay olmaysiz",
    }[e.message] || e.message;
    showToast("❌ " + msg);
  }
}

// ============================================================
//  BOSHQA O'YINCHI WC PROFILI (reytingdan bosilganda, faqat ko'rish)
// ============================================================

function wcRenderViewProfile() {
  const t = APP.t;
  const data = WC.viewedProfile;

  if (!data) {
    return `
      <div class="wc-placeholder">
        <span class="wc-placeholder-icon" data-icon="user"></span>
        <div class="wc-placeholder-text">${escHtml(t.no_data || "Ma'lumot yo'q")}</div>
      </div>`;
  }

  const flag = wcTeamFlag(data.team_name);
  const nick = data.nickname || data.team_name || "?";

  // Avatar: boshqa o'yinchining Telegram rasmi (proxy orqali), bo'lmasa bayroq
  const avatarInner = data.user_id
    ? `<img src="${API_BASE}/players/${data.user_id}/photo" alt="" style="width:56px;height:56px;object-fit:cover;border-radius:50%;" onerror="this.style.display='none';this.parentElement.querySelector('.wc-profile-flag').style.display='block'" /><span class="wc-profile-flag" style="display:none">${flag}</span>`
    : `<span class="wc-profile-flag">${flag}</span>`;

  // Username linki yoki "Username yo'q"
  const subline = data.username
    ? `<a class="profile-username" href="https://t.me/${escHtml(data.username)}" target="_blank">@${escHtml(data.username)}</a>`
    : `<span class="profile-no-username">${escHtml(t.no_username || "Username yo'q")}</span>`;

  // Statistika
  const r = data.rating;
  const pos = r ? `#${r.position}` : "—";
  const wins = r ? r.wins : "—";
  const draws = r ? r.draws : "—";
  const losses = r ? r.losses : "—";

  // O'yinlar (faqat ko'rish — tugmasiz)
  const matches = data.matches || [];
  const matchesHtml = matches.length === 0
    ? `<div class="wc-loading-row">${escHtml(t.no_matches || "Hali o'yinlar yo'q")}</div>`
    : matches.map(m => wcRenderViewMatchItem(m)).join("");

  // Play-off o'yinlari (match ID bilan — admin xato hisobni topishi uchun)
  const poMatches = data.playoff_matches || [];
  const poHtml = poMatches.length
    ? `<div class="section-label">${escHtml(t.wc_playoff_my_title || "PLAY-OFF O'YINLARI")}</div>
       <div class="matches-list">${poMatches.map(m => wcRenderViewPlayoffItem(m)).join("")}</div>`
    : "";

  return `
    <button class="back-btn" id="wc-viewplayer-back">
      <span class="back-btn-arrow" data-icon="back"></span>
      <span>${escHtml(t.nav_rating || "Reyting")}</span>
    </button>

    <div class="card card--profile">
      <div class="profile-avatar">${avatarInner}</div>
      <div class="profile-info">
        <h2 class="profile-nickname">${escHtml(data.team_name || nick)}</h2>
        <span class="profile-league">${subline}</span>
      </div>
      <div class="profile-club-badge"><span class="wc-profile-badge-flag">${flag}</span></div>
    </div>

    <div class="section-label">${escHtml(t.my_stats || "STATISTIKA")}</div>
    <div class="stats-grid">
      <div class="stat-card stat-card--primary">
        <span class="stat-card-value neon-cyan">${pos}</span>
        <span class="stat-card-label">${escHtml(t.stat_pos || "O'rin")}</span>
      </div>
      <div class="stat-card">
        <span class="stat-card-value neon-cyan">${wins}</span>
        <span class="stat-card-label">${escHtml(t.stat_w || "G'alaba")}</span>
      </div>
      <div class="stat-card">
        <span class="stat-card-value">${draws}</span>
        <span class="stat-card-label">${escHtml(t.stat_d || "Durang")}</span>
      </div>
      <div class="stat-card">
        <span class="stat-card-value neon-red">${losses}</span>
        <span class="stat-card-label">${escHtml(t.stat_l || "Mag'lubiyat")}</span>
      </div>
    </div>

    <div id="wc-view-prizes-section"></div>

    <div class="section-label">${escHtml(t.player_matches || t.my_matches || "O'YINLAR")}</div>
    <div class="matches-list">${matchesHtml}</div>
    ${poHtml}
  `;
}

// Boshqa o'yinchi profilida play-off o'yin kartasi (faqat ko'rish, match ID bilan).
function wcRenderViewPlayoffItem(m) {
  const roundName = (typeof WC_PLAYOFF_ROUND_NAMES !== "undefined" && WC_PLAYOFF_ROUND_NAMES[m.round]) || m.round || "";
  const flag1 = m.p1_team ? wcTeamFlag(m.p1_team) : "";
  const flag2 = m.p2_team ? wcTeamFlag(m.p2_team) : "";
  const scoreNum = (m.score1 != null && m.score2 != null) ? `${m.score1} : ${m.score2}` : "— : —";
  return `
    <div class="match-item">
      <span class="match-names">${escHtml(roundName)} <span class="wc-po-id">#${m.id}</span></span>
      <div class="match-center">
        <span class="wc-mc-flag">${flag1}</span>
        <span class="match-score">${escHtml(scoreNum)}</span>
        <span class="wc-mc-flag">${flag2}</span>
      </div>
    </div>`;
}

// O'yin kartasi (faqat ko'rish — tugmasiz, liga renderPlayerMatchItem naqshida)
function wcRenderViewMatchItem(m) {
  const flag1 = wcTeamFlag(m.player1_club);
  const flag2 = wcTeamFlag(m.player2_club);
  const hasScore = (m.score1 !== null && m.score1 !== undefined);
  const center = hasScore
    ? `<span class="wc-mc-flag">${flag1}</span><span class="match-score">${m.score1} : ${m.score2}</span><span class="wc-mc-flag">${flag2}</span>`
    : `<span class="wc-mc-flag">${flag1}</span><span class="match-score">— : —</span><span class="wc-mc-flag">${flag2}</span>`;
  return `
    <div class="match-item">
      <span class="match-names">#${m.id}</span>
      <div class="match-center">${center}</div>
    </div>`;
}

function wcBindViewProfile() {
  const root = document.getElementById("worldcup-root");
  if (typeof applyIcons === "function") applyIcons(root);
  document.getElementById("wc-viewplayer-back")?.addEventListener("click", wcBackToRating);
  // Sovrinlar (liga + WC) — boshqa o'yinchi ko'rilганда ham; liga loadPrizesInto qayta ishlatiladi
  const uid = WC.viewedProfile && WC.viewedProfile.user_id;
  if (uid && typeof loadPrizesInto === "function") void loadPrizesInto(uid, "wc-view-prizes-section");
}


// WC profil sovrinlarim (liga renderMyPrizes'ni qayta ishlatadi)
async function wcLoadMyPrizes() {
  const box = document.getElementById("wc-my-prizes-section");
  if (!box) return;
  const uid = WC.profile ? WC.profile.user_id : null;
  if (!uid) { box.innerHTML = ""; return; }
  try {
    const data = await apiFetch(`/users/${uid}/prizes`);
    const prizes = data.prizes || [];
    if (prizes.length === 0 || typeof renderMyPrizes !== "function") { box.innerHTML = ""; return; }
    box.innerHTML = renderMyPrizes(prizes);
  } catch (_) {
    box.innerHTML = "";
  }
}
