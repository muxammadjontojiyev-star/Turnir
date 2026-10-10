/**
 * wc_eligible_admin.js — JCh yo'llanmalari (Divizion top-48) — bosh admin kartasi (2026-10-10).
 * Ko'rsatadi: ro'yxatda nechta odam, qaysi Divizion mavsumidan, o'rinlar ro'yxati.
 * Tugma: "Qayta hisoblash" — tugagan Divizion mavsumi reytingidan yo'llanmalarni qayta yozadi
 * (POST /wc/admin/eligible/rebuild; sovrinlarga tegmaydi).
 * Konteyner: #wc-eligible-box (worldcup_admin.js wcRenderAdminPanel, faqat bosh admin).
 * Global: apiFetch, escHtml, showToast.
 */

async function wcEligibleLoad() {
  const box = document.getElementById("wc-eligible-box");
  if (!box) return;
  box.innerHTML = `<div class="wc-loading-row">Yuklanmoqda...</div>`;
  let d;
  try {
    d = await apiFetch("/wc/admin/eligible");
  } catch (e) {
    box.innerHTML = `<div class="admin-player-league">Ro'yxat yuklanmadi: ${escHtml(e.message)}</div>`;
    return;
  }
  const head = d.total > 0
    ? `✅ <b>${d.total}</b> / ${d.slots} kishi — Divizion <b>${escHtml(d.season_number)}</b>-mavsumi`
    : `⚠️ <b>Ro'yxat bo'sh</b> — hozir hech kim JCh'ga ro'yxatdan o'ta olmaydi`;
  const rows = (d.list || []).map(r => `
      <div class="wc-elig-row">
        <span class="wc-elig-place">${r.place}</span>
        <span class="wc-elig-name">${escHtml(r.username ? "@" + r.username : (r.nickname || "#" + r.user_id))}</span>
        <span class="wc-elig-pts">${r.points ?? 0}</span>
      </div>`).join("");
  box.innerHTML = `
    <div class="admin-player-league" style="margin:0 2px 8px">${head}</div>
    ${rows ? `<div class="wc-elig-list">${rows}</div>` : ""}
    <button class="btn btn--primary" id="wc-btn-elig-rebuild" style="width:100%;margin-top:8px">
      🔄 Divizion ${escHtml(d.prev_season_number)}-mavsumidan qayta hisoblash
    </button>
    <div class="admin-player-league" style="margin:6px 2px 0">
      Tugagan Divizion mavsumi reytingidagi top-${d.slots} JCh'ga yo'llanma oladi. Sovrinlarga tegmaydi;
      allaqachon JCh'da ro'yxatdan o'tganlar joyida qoladi.
    </div>`;
  document.getElementById("wc-btn-elig-rebuild")
    ?.addEventListener("click", e => void wcEligibleRebuild(e.currentTarget, d.prev_season_number));
}

async function wcEligibleRebuild(btn, seasonNumber) {
  if (!confirm(`JCh yo'llanmalari Divizion ${seasonNumber}-mavsumi reytingidan qayta yozilsinmi?\n\nEski ro'yxat almashtiriladi.`)) return;
  btn.disabled = true;
  try {
    const r = await apiFetch("/wc/admin/eligible/rebuild", {
      method: "POST",
      body: JSON.stringify({ season: "prev" }),
    });
    showToast(`✅ ${r.count} kishi JCh'ga yo'llanma oldi (Divizion ${r.season_number}-mavsum)`);
    await wcEligibleLoad();
  } catch (e) {
    const msg = {
      no_participants: "Bu mavsumda o'yin o'ynaganlar yo'q",
      rebuild_failed: "Qayta hisoblashda xatolik",
    }[e.message] || e.message;
    showToast("❌ " + msg);
    btn.disabled = false;
  }
}
