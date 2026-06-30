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

  // --- Natija tuzatish (bosh + oddiy WC admin) ---
  html += `
    <div class="section-label">${escHtml(t.admin_fix_title || "TASDIQLANGAN NATIJANI TUZATISH")}</div>
    <div class="admin-fix-form">
      <input id="wc-admin-fix-match-id" class="modal-input" type="number" min="1"
        placeholder="${escHtml(t.admin_fix_match_id_placeholder || "Match ID")}" />
      <div class="score-input-row">
        <div class="score-input-group">
          <span class="score-input-label">P1</span>
          <input id="wc-admin-fix-score1" class="score-input" type="number" min="0" max="99" value="0" />
        </div>
        <span class="score-separator">:</span>
        <div class="score-input-group">
          <span class="score-input-label">P2</span>
          <input id="wc-admin-fix-score2" class="score-input" type="number" min="0" max="99" value="0" />
        </div>
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
  if (WC_ADMIN.isSuper) {
    document.getElementById("wc-btn-admin-add")?.addEventListener("click", wcAdminAddRole);
    document.getElementById("wc-btn-fix-schedules")?.addEventListener("click", wcAdminFixSchedules);
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
  if (!matchId || isNaN(score1) || isNaN(score2)) {
    showToast("❌ " + (t.admin_fix_invalid || "Match ID va natijani to'g'ri kiriting"));
    return;
  }
  try {
    await apiFetch(`/wc/admin/match/set-score?match_id=${matchId}&score1=${score1}&score2=${score2}`, { method: "POST" });
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
  if (!matchId) {
    showToast("❌ " + (t.admin_fix_invalid || "Match ID ni kiriting"));
    return;
  }
  if (!window.confirm(t.admin_reset_confirm || "Bu o'yin natijasini bekor qilasizmi? O'yin qayta — : — bo'ladi.")) return;
  try {
    await apiFetch(`/wc/admin/match/reset?match_id=${matchId}`, { method: "POST" });
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
