// ============================================================
//  worldcup_admin.js — World Cup admin paneli (WC Profil ichida)
//
//  Rolga qarab ko'rsatadi:
//   - Bosh admin (config): natija tuzatish + o'yinchi chiqarish + admin tayinlash
//   - Oddiy WC admin: faqat natija tuzatish
//   - Admin emas: panel yashirin
//
//  liga admin paneliga TEGMAYDI. /admin/whoami, /wc/admin/* endpointlaridan
//  foydalanadi.
// ============================================================

// WC admin holati (whoami natijasi)
const WC_ADMIN = {
  isSuper: false,
  isWcAdmin: false,
};

async function wcLoadAdminPanel() {
  const panel = document.getElementById("wc-admin-panel");
  if (!panel) return;

  // Rolni aniqlaymiz
  try {
    const who = await apiFetch("/admin/whoami");
    WC_ADMIN.isSuper = !!who.is_super;
    WC_ADMIN.isWcAdmin = !!who.is_wc_admin;
  } catch (_) {
    WC_ADMIN.isSuper = false;
    WC_ADMIN.isWcAdmin = false;
  }

  // WC admin emas (na bosh, na wc) — panel yashirin
  if (!WC_ADMIN.isSuper && !WC_ADMIN.isWcAdmin) {
    panel.classList.add("hidden");
    panel.innerHTML = "";
    return;
  }

  panel.classList.remove("hidden");
  panel.innerHTML = wcRenderAdminPanel();
  wcBindAdminPanel();

  // Bosh admin uchun qo'shimcha ma'lumotlar
  if (WC_ADMIN.isSuper) {
    void wcLoadAdminPlayers();
    void wcLoadAdminRoles();
  }
}

function wcRenderAdminPanel() {
  const t = APP.t;
  let html = `<div class="section-label">${escHtml(t.admin_panel_title || "ADMIN PANEL")}</div>`;

  // Katta hisob (admin_pending) — barcha WC adminlariga
  html += `
    <div class="section-label">${escHtml(t.admin_pending_title || "ADMIN TASDIG'I (KATTA HISOB)")}</div>
    <div id="wc-admin-pending-list" class="admin-players-list"></div>`;

  // --- Natija tuzatish (bosh + oddiy WC admin) ---
  html += `
    <div class="section-label">${escHtml(t.admin_fix_title || "TASDIQLANGAN NATIJANI TUZATISH")}</div>
    <div class="admin-fix-form">
      <input id="wc-admin-fix-match-id" class="modal-input" type="number" min="1"
        placeholder="${escHtml(t.admin_fix_match_id_placeholder || "Match ID")}" />
      <label class="admin-fix-playoff-check">
        <input id="wc-admin-fix-is-playoff" type="checkbox" />
        <span>${escHtml(t.admin_fix_is_playoff || "Play-off o'yini")}</span>
      </label>
      <div class="score-input-row">
        <span class="admin-fix-logo-slot" id="wc-admin-fix-flag1"></span>
        <div class="score-input-group">
          <span class="score-input-label">P1</span>
          <input id="wc-admin-fix-score1" class="score-input" type="number" min="0" max="99" value="0" />
        </div>
        <span class="score-separator">:</span>
        <div class="score-input-group">
          <span class="score-input-label">P2</span>
          <input id="wc-admin-fix-score2" class="score-input" type="number" min="0" max="99" value="0" />
        </div>
        <span class="admin-fix-logo-slot" id="wc-admin-fix-flag2"></span>
      </div>
      <button class="btn btn--primary btn--glow" id="wc-btn-admin-fix-submit">${escHtml(t.admin_fix_submit || "Tuzatish")}</button>
      <button class="btn btn--ghost" id="wc-btn-admin-reset" style="margin-top:8px;color:var(--red-neon);border-color:rgba(255,69,96,.3)">${escHtml(t.admin_reset_btn || "Natijani bekor qilish")}</button>
    </div>`;

  // --- Faqat bosh admin: o'yinchi chiqarish + admin tayinlash ---
  if (WC_ADMIN.isSuper) {
    html += `
      <div class="section-label">${escHtml(t.wc_admin_schedules_title || "O'YIN JADVALLARI")}</div>
      <button class="btn btn--ghost" id="wc-btn-fix-schedules" style="width:100%">${escHtml(t.wc_admin_fix_schedules_btn || "Yo'qolgan jadvallarni yaratish")}</button>
      <div class="admin-player-league" style="margin:6px 2px 0;text-align:center">${escHtml(t.wc_admin_fix_schedules_hint || "To'lgan, lekin o'yinlari yo'q guruhlar uchun")}</div>
      <button class="btn btn--primary btn--glow" id="wc-btn-start-today" style="width:100%;margin-top:10px">${escHtml(t.wc_admin_start_today_btn || "Bugundan start berish")}</button>
      <div class="admin-player-league" style="margin:6px 2px 0;text-align:center">${escHtml(t.wc_admin_start_today_hint || "Bugun 1-2 tur ochiq, ertaga oxirgi tur (23:30)")}</div>

      <div class="section-label">${escHtml(t.wc_admin_playoff_title || "PLAY-OFF")}</div>
      <button class="btn btn--primary btn--glow" id="wc-btn-playoff-start" style="width:100%">${escHtml(t.wc_admin_playoff_start_btn || "Play-off boshlash")}</button>
      <div class="admin-player-league" id="wc-playoff-status-hint" style="margin:6px 2px 0;text-align:center">${escHtml(t.wc_admin_playoff_hint || "32 jamoa: 12 g'olib + 12 ikkinchi + 8 eng yaxshi 3-o'rin")}</div>

      <div class="section-label">${escHtml(t.wc_season_title || "WC MAVSUMI")}</div>
      <div class="admin-player-league" id="wc-season-current-hint" style="margin:0 2px 8px">—</div>
      <button class="btn btn--danger" id="wc-btn-finalize-season" style="width:100%">${escHtml(t.wc_season_finalize_btn || "WC mavsumini yakunlash")}</button>
      <div class="admin-player-league" style="margin:6px 2px 0">${escHtml(t.wc_season_finalize_hint || "WC kubogi (play-off chempioni) saqlanadi, WC mavsumi oshadi")}</div>

      <div class="section-label">${escHtml(t.wc_admin_players_title || "WC ISHTIROKCHILAR")}</div>
      <div id="wc-admin-players-list" class="admin-players-list">
        <div class="wc-loading-row">${escHtml(t.loading || "Yuklanmoqda...")}</div>
      </div>

      <div class="section-label">${escHtml(t.admin_manage_title || "ADMIN TAYINLASH")}</div>
      <div class="admin-fix-form">
        <input id="wc-admin-new-id" class="modal-input" type="number" min="1"
          placeholder="${escHtml(t.admin_new_id_placeholder || "Telegram ID")}" />
        <button class="btn btn--primary btn--glow" id="wc-btn-admin-add">${escHtml(t.admin_add_btn || "Admin qo'shish")}</button>
      </div>
      <div id="wc-admin-roles-list" class="admin-players-list">
        <div class="wc-loading-row">${escHtml(t.loading || "Yuklanmoqda...")}</div>
      </div>`;
  }

  return html;
}

function wcBindAdminPanel() {
  document.getElementById("wc-btn-admin-fix-submit")?.addEventListener("click", wcAdminFixResult);
  document.getElementById("wc-btn-admin-reset")?.addEventListener("click", wcAdminResetMatch);
  // "Play-off o'yini" checkbox holatini tiklash + o'zgarishda saqlash
  // (admin o'zi o'chirmaguncha yoniq qoladi — ilova qayta ochilsa ham).
  const poCheck = document.getElementById("wc-admin-fix-is-playoff");
  // v4.15: Match ID yoki play-off belgisi o'zgarsa — bayroqlarni jonli ko'rsatish
  const wcFixIdInput = document.getElementById("wc-admin-fix-match-id");
  if (wcFixIdInput) wcFixIdInput.addEventListener("input", scheduleWcFixPreview);
  if (poCheck) poCheck.addEventListener("change", () => refreshWcFixPreview());
  if (poCheck) {
    try {
      poCheck.checked = localStorage.getItem("wc_admin_fix_playoff") === "1";
    } catch (_) { /* localStorage yo'q — default o'chiq */ }
    poCheck.addEventListener("change", () => {
      try {
        localStorage.setItem("wc_admin_fix_playoff", poCheck.checked ? "1" : "0");
      } catch (_) { /* jim */ }
    });
  }
  if (WC_ADMIN.isSuper) {
    document.getElementById("wc-btn-admin-add")?.addEventListener("click", wcAdminAddRole);
    document.getElementById("wc-btn-fix-schedules")?.addEventListener("click", wcAdminFixSchedules);
    document.getElementById("wc-btn-start-today")?.addEventListener("click", wcAdminStartToday);
    document.getElementById("wc-btn-playoff-start")?.addEventListener("click", wcAdminPlayoffStart);
    document.getElementById("wc-btn-finalize-season")?.addEventListener("click", wcFinalizeSeason);
    void wcLoadPlayoffStatus();
    void wcLoadSeasonInfo();
  }
  // Katta hisob ro'yxati — barcha WC adminlariga (bosh + oddiy)
  void wcLoadPendingMatches();
}

// ---- Katta hisob (admin_pending) — WC admin tasdig'ini kutayotgan o'yinlar ----
async function wcLoadPendingMatches() {
  const list = document.getElementById("wc-admin-pending-list");
  if (!list) return;
  try {
    const res = await apiFetch("/wc/admin/match/pending");
    wcRenderPendingMatches(res.matches || []);
  } catch (e) {
    list.innerHTML = `<div class="empty-state">${escHtml(e.message)}</div>`;
  }
}

function wcRenderPendingMatches(matches) {
  const t = APP.t;
  const list = document.getElementById("wc-admin-pending-list");
  if (!list) return;
  if (matches.length === 0) {
    list.innerHTML = `<div class="empty-state">${escHtml(t.admin_pending_empty || "Kutayotgan katta hisob yo'q")}</div>`;
    return;
  }
  list.innerHTML = matches.map(m => {
    const flag1 = (typeof wcTeamFlag === "function" ? wcTeamFlag(m.p1_team) : "") || "";
    const flag2 = (typeof wcTeamFlag === "function" ? wcTeamFlag(m.p2_team) : "") || "";
    const name1 = escHtml(m.p1_team || "?");
    const name2 = escHtml(m.p2_team || "?");
    return `
    <div class="admin-player-item admin-pending-item">
      <div class="admin-player-info">
        <div class="admin-pending-match">
          <span class="match-id">#${m.id}</span>
          <span>${flag1} ${name1}</span> <b class="admin-pending-score">${m.score1}:${m.score2}</b> <span>${flag2} ${name2}</span>
        </div>
        <div class="admin-player-league">${escHtml(t.wc_group || "Guruh")} ${escHtml(m.group_letter || "")} · ${escHtml(t.matchday || "Tur")} ${m.matchday}</div>
      </div>
      <button class="admin-remove-btn wc-pending-confirm-btn" data-match-id="${m.id}">
        ${escHtml(t.admin_pending_confirm || "Tasdiqlash")}
      </button>
      <button class="admin-remove-btn wc-pending-reject-btn" data-match-id="${m.id}">
        ${escHtml(t.admin_pending_reject || "Rad etish")}
      </button>
    </div>`;
  }).join("");

  list.querySelectorAll(".wc-pending-confirm-btn").forEach(btn => {
    btn.addEventListener("click", () => wcResolvePendingMatch(parseInt(btn.dataset.matchId), "confirm"));
  });
  list.querySelectorAll(".wc-pending-reject-btn").forEach(btn => {
    btn.addEventListener("click", () => wcResolvePendingMatch(parseInt(btn.dataset.matchId), "reject"));
  });
}

async function wcResolvePendingMatch(matchId, action) {
  const t = APP.t;
  try {
    await apiFetch(`/wc/admin/match/pending/resolve?match_id=${matchId}&action=${action}`, { method: "POST" });
    showToast(t.admin_match_resolved || "✅ Bajarildi");
    await wcLoadPendingMatches();
    if (typeof wcLoadMatches === "function") { try { await wcLoadMatches(); } catch (_) {} }
  } catch (e) {
    showToast("❌ " + escHtml(e.message));
  }
}

// ---- WC mavsum ma'lumoti + yakunlash (bosh admin) ----
async function wcLoadSeasonInfo() {
  const hint = document.getElementById("wc-season-current-hint");
  if (!hint) return;
  try {
    const d = await apiFetch("/season/current");
    hint.textContent = (APP.t.wc_season_current || "Joriy WC mavsumi") + ": " + (d.wc_season ?? "—");
  } catch (_) {}
}

async function wcFinalizeSeason() {
  const t = APP.t;
  if (!window.confirm(t.wc_season_finalize_confirm || "WC mavsumini yakunlaysizmi? Play-off chempioni saqlanadi va WC mavsumi oshadi. Bu amalni ortga qaytarib bo'lmaydi.")) return;
  try {
    const r = await apiFetch("/season/wc/finalize", { method: "POST" });
    const c = r.counts || {};
    window.alert(`✅ ${t.wc_season_finalized || "WC mavsumi yakunlandi"} (#${r.season})\n🌍 ${c.wc_cup || 0} JCH kubogi, 👟 ${c.wc_golden_boot || 0} JCH to'purari`);
    // Mavsum raqami + tozalangan holat darhol ko'rinsin: WC ekranini qayta yuklaymiz
    if (typeof loadSeasons === "function") { try { await loadSeasons(); } catch (_) {} }
    if (typeof wcLoadProfileThenRender === "function") { void wcLoadProfileThenRender(); }
    else { void wcLoadSeasonInfo(); }
  } catch (e) {
    const errMap = {
      already_finalized: t.season_already_finalized || "Bu mavsum allaqachon yakunlangan",
    };
    showToast("❌ " + (errMap[e.message] || e.message));
  }
}

// ---- Play-off holatini yuklash (tugma matnini moslash) ----
async function wcLoadPlayoffStatus() {
  const hint = document.getElementById("wc-playoff-status-hint");
  const btn = document.getElementById("wc-btn-playoff-start");
  if (!hint || !btn) return;
  const t = APP.t;
  try {
    const s = await apiFetch("/wc/playoff/status");
    if (s.started) {
      btn.disabled = true;
      btn.style.opacity = "0.5";
      hint.textContent = t.wc_admin_playoff_already || "✅ Play-off allaqachon boshlangan";
    } else if (s.ready) {
      hint.textContent = t.wc_admin_playoff_ready || "✅ 32 jamoa tayyor — boshlash mumkin";
    } else {
      hint.textContent = t.wc_admin_playoff_notready || "⏳ Barcha guruhlar hali tugamagan";
    }
  } catch (_) {}
}

// ---- Play-off boshlash ----
async function wcAdminPlayoffStart() {
  const t = APP.t;
  if (!window.confirm(t.wc_admin_playoff_confirm || "Play-off boshlansinmi? 32 jamoa saralanadi va setka tuziladi. Bu amalni ortga qaytarib bo'lmaydi.")) return;
  try {
    const r = await apiFetch("/wc/admin/playoff/start", { method: "POST" });
    window.alert(`✅ Play-off boshlandi! ${r.created} ta o'yin yaratildi.`);
    void wcLoadPlayoffStatus();
  } catch (e) {
    const msg = {
      already_started: t.wc_admin_playoff_already || "Play-off allaqachon boshlangan",
      not_ready:       t.wc_admin_playoff_notready || "Barcha guruhlar hali tugamagan",
    }[e.message] || (e.message && e.message.indexOf("incomplete") >= 0
      ? (t.wc_admin_playoff_notready || "Barcha guruhlar hali tugamagan")
      : e.message);
    showToast("❌ " + msg);
  }
}

// ---- Bugundan start berish (barcha o'yinli guruhlar draw_date = bugun) ----
async function wcAdminStartToday() {
  const t = APP.t;
  if (!window.confirm(t.wc_admin_start_today_confirm || "Barcha guruhlarga bugundan start berilsinmi? Bugun 1-2 tur ochiq, ertaga oxirgi tur ochiladi.")) return;
  try {
    const r = await apiFetch("/wc/admin/start-today", { method: "POST" });
    const started = r.started || [];
    if (started.length === 0) {
      showToast(t.wc_admin_start_today_none || "O'yinli guruh topilmadi");
    } else {
      showToast(`✅ ${started.length} ta guruh: ${started.join(", ")}`);
    }
  } catch (e) {
    showToast("❌ " + e.message);
  }
}

// ---- Yo'qolgan WC jadvallarni yaratish (to'lgan-o'yinsiz guruhlar) ----
async function wcAdminFixSchedules() {
  const t = APP.t;
  if (!window.confirm(t.wc_admin_fix_schedules_confirm || "To'lgan, lekin o'yinsiz guruhlar uchun jadval yaratilsinmi?")) return;
  try {
    const r = await apiFetch("/wc/admin/fix-schedules", { method: "POST" });
    const fixed = r.fixed || [];
    const notFull = r.skipped_not_full || [];
    const okAlready = r.already_ok || [];

    // Batafsil diagnostika: qaysi guruh qaysi holatda
    let lines = [];
    if (fixed.length) lines.push(`✅ Yaratildi: ${fixed.join(", ")}`);
    if (okAlready.length) lines.push(`☑️ Allaqachon bor: ${okAlready.join(", ")}`);
    if (notFull.length) lines.push(`⏳ To'lmagan: ${notFull.join(", ")}`);

    const msg = lines.length ? lines.join("\n") : (t.wc_admin_fix_schedules_none || "✅ Hamma jadval joyida");
    window.alert(msg);
  } catch (e) {
    showToast("❌ " + e.message);
  }
}

// ---- Natija o'zgartirish (har qanday holat — o'ynamasdan kiritilgan natijani tuzatish) ----
async function wcAdminFixResult() {
  const t = APP.t;
  const matchId = parseInt(document.getElementById("wc-admin-fix-match-id").value);
  const score1 = parseInt(document.getElementById("wc-admin-fix-score1").value);
  const score2 = parseInt(document.getElementById("wc-admin-fix-score2").value);
  const isPlayoff = document.getElementById("wc-admin-fix-is-playoff")?.checked ? 1 : 0;
  if (!matchId || isNaN(score1) || isNaN(score2)) {
    showToast("❌ " + (t.admin_fix_invalid || "Match ID va natijani to'g'ri kiriting"));
    return;
  }
  try {
    await apiFetch(`/wc/admin/match/set-score?match_id=${matchId}&score1=${score1}&score2=${score2}&is_playoff=${isPlayoff}`, { method: "POST" });
    showToast(t.admin_fix_done || "✅ Natija tuzatildi");
    document.getElementById("wc-admin-fix-match-id").value = "";
  } catch (e) {
    const msg = {
      match_not_found: t.admin_match_not_found || "Match topilmadi",
    }[e.message] || e.message;
    showToast("❌ " + msg);
  }
}

// ---- Natijani bekor qilish (— : — pending holatiga qaytarish) ----
async function wcAdminResetMatch() {
  const t = APP.t;
  const matchId = parseInt(document.getElementById("wc-admin-fix-match-id").value);
  const isPlayoff = document.getElementById("wc-admin-fix-is-playoff")?.checked ? 1 : 0;
  if (!matchId) {
    showToast("❌ " + (t.admin_fix_invalid || "Match ID ni kiriting"));
    return;
  }
  if (!window.confirm(t.admin_reset_confirm || "Bu o'yin natijasini bekor qilasizmi? O'yin qayta — : — bo'ladi.")) return;
  try {
    await apiFetch(`/wc/admin/match/reset?match_id=${matchId}&is_playoff=${isPlayoff}`, { method: "POST" });
    showToast(t.admin_reset_done || "✅ Natija bekor qilindi");
    document.getElementById("wc-admin-fix-match-id").value = "";
  } catch (e) {
    const msg = {
      match_not_found: t.admin_match_not_found || "Match topilmadi",
      already_pending: t.admin_already_pending || "Bu o'yinda natija yo'q",
    }[e.message] || e.message;
    showToast("❌ " + msg);
  }
}

// ---- WC ishtirokchilar ro'yxati (bosh admin) ----
async function wcLoadAdminPlayers() {
  const list = document.getElementById("wc-admin-players-list");
  if (!list) return;
  try {
    const data = await apiFetch("/wc/admin/players");
    const players = data.players || [];
    if (players.length === 0) {
      list.innerHTML = `<div class="wc-loading-row">${escHtml(APP.t.no_data || "Ma'lumot yo'q")}</div>`;
      return;
    }
    list.innerHTML = players.map(p => {
      const flag = wcTeamFlag(p.team_name);
      const name = p.username ? `@${escHtml(p.username)}` : escHtml(p.nickname || "?");
      return `
        <div class="admin-player-item">
          <div class="admin-player-info">
            ${flag} ${escHtml(p.team_name)}
            <div class="admin-player-league">${p.group_letter} — ${name}</div>
          </div>
          <button class="admin-remove-btn" data-uid="${p.user_id}">${escHtml(APP.t.admin_remove_player || "Chiqarish")}</button>
        </div>`;
    }).join("");
    list.querySelectorAll(".admin-remove-btn").forEach(btn => {
      btn.addEventListener("click", () => wcAdminRemovePlayer(parseInt(btn.dataset.uid)));
    });
  } catch (_) {
    list.innerHTML = `<div class="wc-loading-row">${escHtml(APP.t.no_data || "Ma'lumot yo'q")}</div>`;
  }
}

async function wcAdminRemovePlayer(userId) {
  const t = APP.t;
  if (!window.confirm(t.wc_admin_remove_confirm || "Bu o'yinchini WC ro'yxatidan chiqarasizmi?")) return;
  try {
    await apiFetch(`/wc/admin/players/${userId}`, { method: "DELETE" });
    showToast(t.wc_admin_removed || "✅ O'yinchi chiqarildi");
    void wcLoadAdminPlayers();
  } catch (e) {
    const msg = {
      not_registered: t.wc_admin_not_registered || "O'yinchi ro'yxatda yo'q",
      group_started:  t.wc_admin_group_started  || "Guruh boshlangan — chiqarib bo'lmaydi",
    }[e.message] || e.message;
    showToast("❌ " + msg);
  }
}

// ---- Admin tayinlash (bosh admin) ----
async function wcLoadAdminRoles() {
  const list = document.getElementById("wc-admin-roles-list");
  if (!list) return;
  try {
    const data = await apiFetch("/admin/roles/wc");
    const admins = data.admins || [];
    if (admins.length === 0) {
      list.innerHTML = `<div class="wc-loading-row">${escHtml(APP.t.admin_no_admins || "Tayinlangan admin yo'q")}</div>`;
      return;
    }
    list.innerHTML = admins.map(a => {
      const name = a.username ? `@${escHtml(a.username)}` : (a.nickname ? escHtml(a.nickname) : `ID ${a.telegram_id}`);
      return `
        <div class="admin-player-item">
          <div class="admin-player-info">
            ${name}
            <div class="admin-player-league">ID ${a.telegram_id}</div>
          </div>
          <button class="admin-remove-btn" data-tid="${a.telegram_id}">${escHtml(APP.t.admin_remove_role || "O'chirish")}</button>
        </div>`;
    }).join("");
    list.querySelectorAll(".admin-remove-btn").forEach(btn => {
      btn.addEventListener("click", () => wcAdminRemoveRole(parseInt(btn.dataset.tid)));
    });
  } catch (_) {
    list.innerHTML = `<div class="wc-loading-row">${escHtml(APP.t.no_data || "Ma'lumot yo'q")}</div>`;
  }
}

async function wcAdminAddRole() {
  const t = APP.t;
  const tid = parseInt(document.getElementById("wc-admin-new-id").value);
  if (!tid) {
    showToast("❌ " + (t.admin_id_invalid || "Telegram ID ni kiriting"));
    return;
  }
  try {
    await apiFetch(`/admin/roles/wc?telegram_id=${tid}`, { method: "POST" });
    showToast(t.admin_added || "✅ Admin qo'shildi");
    document.getElementById("wc-admin-new-id").value = "";
    void wcLoadAdminRoles();
  } catch (e) {
    const msg = {
      already_admin:    t.admin_already   || "Bu odam allaqachon admin",
      cannot_add_super: t.admin_is_super  || "Bu odam allaqachon bosh admin",
    }[e.message] || e.message;
    showToast("❌ " + msg);
  }
}

async function wcAdminRemoveRole(telegramId) {
  const t = APP.t;
  if (!window.confirm(t.admin_remove_confirm || "Bu adminni o'chirasizmi?")) return;
  try {
    await apiFetch(`/admin/roles/wc/${telegramId}`, { method: "DELETE" });
    showToast(t.admin_removed || "✅ Admin o'chirildi");
    void wcLoadAdminRoles();
  } catch (e) {
    showToast("❌ " + e.message);
  }
}

/* ============================================================
   v4.15 — JCH admin fix: Match ID yozilganda jamoa bayroqlari
   /wc/admin/match/{id}/info (is_playoff bilan) so'raladi va ikkala
   bayroq score kataklari yonida "tomchi" animatsiyasi bilan chiqadi.
   Tartib: [bayroq] [P1] : [P2] [bayroq].
   ============================================================ */
let _wcFixDebounce = null;
let _wcFixLastKey = "";

// Jamoa nomi -> bayroq emoji. LAZY: WC_GROUPS (worldcup.js) yuklangach birinchi
// chaqiruvda yig'iladi. Ilgari `const ... = (() => ...)()` edi — agar bu fayl
// worldcup.js dan OLDIN baholansa xarita bo'sh qolib, bayroqlar chiqmasdi.
let _wcTeamFlags = null;
function wcTeamFlags() {
  if (_wcTeamFlags) return _wcTeamFlags;
  const map = {};
  if (typeof WC_GROUPS !== "undefined") {
    for (const letter of Object.keys(WC_GROUPS)) {
      for (const [name, flag] of WC_GROUPS[letter]) map[name] = flag;
    }
    _wcTeamFlags = map;   // faqat to'lgach keshlaymiz
  }
  return map;
}

function renderWcFlagBadge(teamName) {
  const safe = escHtml(teamName || "");
  if (!teamName) {
    return `<span class="match-club-logo match-club-logo--empty"></span>`;
  }
  const flag = wcTeamFlags()[teamName];
  // Bayroq topilmasa ham jamoa nomi ko'rinsin (bo'sh katak qolmasin)
  return flag
    ? `<span class="wc-fix-flag" title="${safe}">${flag}</span>`
    : `<span class="wc-fix-flag wc-fix-flag--text" title="${safe}">${safe.slice(0, 3).toUpperCase()}</span>`;
}

function scheduleWcFixPreview() {
  clearTimeout(_wcFixDebounce);
  _wcFixDebounce = setTimeout(refreshWcFixPreview, 350);
}

async function refreshWcFixPreview() {
  const slot1 = document.getElementById("wc-admin-fix-flag1");
  const slot2 = document.getElementById("wc-admin-fix-flag2");
  const idEl = document.getElementById("wc-admin-fix-match-id");
  if (!slot1 || !slot2 || !idEl) return;
  const id = parseInt(idEl.value, 10);
  const isPlayoff = document.getElementById("wc-admin-fix-is-playoff")?.checked ? 1 : 0;
  if (!id || id <= 0) { slot1.innerHTML = ""; slot2.innerHTML = ""; return; }
  const key = `${id}:${isPlayoff}`;
  _wcFixLastKey = key;
  try {
    const info = await apiFetch(`/wc/admin/match/${id}/info?is_playoff=${isPlayoff}`);
    if (_wcFixLastKey !== key) return; // eskirgan javob
    slot1.innerHTML = renderWcFlagBadge(info.team1);
    slot2.innerHTML = renderWcFlagBadge(info.team2);
    if (slot1.firstElementChild) slot1.firstElementChild.classList.add("logo-drop-in");
    if (slot2.firstElementChild) slot2.firstElementChild.classList.add("logo-drop-in");
  } catch (err) {
    if (_wcFixLastKey !== key) return;
    // O'yin topilmadi (404) yoki xato — adminga bilinsin (qoida #40).
    // Play-off o'yinini guruhdan qidirsa ham shu holat: checkbox eslatmasi.
    const mark = `<span class="match-club-logo match-club-logo--empty" title="O'yin topilmadi">?</span>`;
    slot1.innerHTML = mark; slot2.innerHTML = mark;
  }
}
