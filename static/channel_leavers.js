// =============================================================
//  channel_leavers.js — Admin panel: "KANALNI TARK ETGANLAR" (2026-10-14)
//  Tekshirish tugmasi → GET /admin/channel-leavers (barcha liga ishtirokchilari
//  kanalda bormi — bot tekshiradi). Bosh admin: barcha ligalar; liga admini: o'z ligalari.
//  Har qatorda: liga, klub, @username, ID. Bosh adminda "Hal qilish" — ishtirokchi
//  "ISHTIROKCHILAR" vositasida (admin_participants.js) tanlanadi: yangi akkountga
//  o'tkazish / almashtirish / chiqarish. Klub avtomatik bo'shatilmaydi.
//  Global: apiFetch, escHtml, showToast, findClubLogo, ADM_PP, admPpRenderPanel.
// =============================================================

function chlRowHtml(o, canManage) {
  const logo = o.club_name && typeof findClubLogo === "function" ? findClubLogo(o.club_name) : null;
  const logoHtml = logo
    ? `<img class="admin-player-logo" src="${escHtml(logo)}" alt="">`
    : `<span class="admin-player-logo admin-player-logo--empty"></span>`;
  const name = o.username ? `@${escHtml(o.username)}` : escHtml(o.nickname || "—");
  const st = o.status === "kicked" ? "chetlatilgan" : "chiqib ketgan";
  return `<div class="chl-row">
      ${logoHtml}
      <span class="adm-pp-info">
        <b>${escHtml(o.club_name || "—")} <span class="chl-league">· ${escHtml(o.league_name || "?")}</span></b>
        <span>${name} · ID ${escHtml(String(o.telegram_id))} · ${st}</span>
      </span>
      ${canManage ? `<button class="btn chl-fix" data-chl-fix="${o.user_id}">Hal qilish</button>` : ""}
    </div>`;
}

async function chlScan(btn) {
  const box = document.getElementById("chl-list");
  if (!box) return;
  btn.disabled = true;
  const old = btn.textContent;
  btn.textContent = "⏳ Tekshirilmoqda…";
  try {
    const d = await apiFetch("/admin/channel-leavers");
    const list = d.leavers || [];
    const cnt = document.getElementById("chl-count");
    if (cnt) cnt.textContent = list.length ? `${list.length} ta` : "";
    const note = `<div class="adm-pp-hint">${d.checked || 0} ishtirokchi tekshirildi${d.unknown ? ` · ${d.unknown} tasini tekshirib bo'lmadi` : ""}</div>`;
    box.innerHTML = list.length
      ? note + list.map(o => chlRowHtml(o, !!d.can_manage)).join("")
        + (d.can_manage ? "" : `<div class="adm-pp-hint">Klubni o'tkazish uchun bosh adminga murojaat qiling.</div>`)
      : note + `<div class="adm-pp-empty">✅ Hamma ishtirokchi kanalda</div>`;
  } catch (e) {
    showToast(e.message === "too_many_requests" ? "Biroz kuting va qayta urinib ko'ring" : "Xato: " + e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = old;
  }
}

// "Hal qilish" — ISHTIROKCHILAR vositasida shu ishtirokchini tanlash
function chlFix(userId) {
  if (typeof ADM_PP === "undefined" || typeof admPpRenderPanel !== "function") return;
  const o = ADM_PP.list.find(x => String(x.user_id) === String(userId));
  if (!o) { showToast("Ishtirokchi ro'yxatda topilmadi — sahifani yangilang"); return; }
  ADM_PP.sel = o;
  ADM_PP.swapB = null;
  admPpRenderPanel();
  const grp = document.getElementById("adm-pp")?.closest("details");
  if (grp) grp.open = true;
  document.getElementById("adm-pp-panel")?.scrollIntoView({ behavior: "smooth", block: "start" });
}

if (!window._chlBound) {
  window._chlBound = true;
  document.addEventListener("click", (e) => {
    if (!e.target.closest) return;
    const scan = e.target.closest("#chl-scan");
    if (scan) { void chlScan(scan); return; }
    const fix = e.target.closest("[data-chl-fix]");
    if (fix) chlFix(fix.dataset.chlFix);
  });
}
