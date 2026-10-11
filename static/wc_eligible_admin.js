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
    ? `✅ <b>${d.total}</b> yo'llanma — Divizion <b>${escHtml(d.season_number)}</b>-mavsumi · davlat tanlagan: <b>${d.registered ?? 0}</b> / ${d.slots}`
    : `⚠️ <b>Ro'yxat bo'sh</b> — hozir hech kim JCh'ga ro'yxatdan o'ta olmaydi`;
  // 2026-10-11: ✅ davlat tanlagan, ⏳ hali tanlamagan; "admin" — o'rniga qo'shilgan
  const rows = (d.list || []).map(r => `
      <div class="wc-elig-row">
        <span class="wc-elig-place">${r.place}</span>
        <span class="wc-elig-name">${r.registered ? "✅" : "⏳"} ${escHtml(r.username ? "@" + r.username : (r.nickname || "#" + r.user_id))}${r.via === "admin" ? ' <span class="wc-elig-tag">admin</span>' : ""}</span>
        <span class="wc-elig-pts">${r.points ?? "—"}</span>
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
    </div>

    <div class="admin-player-league" style="margin:14px 2px 6px"><b>O'rniga qo'shish</b> — bo'sh o'rin: <b>${d.free ?? 0}</b> ta.
      Telegram ID'larni yozing (vergul, bo'sh joy yoki yangi qator bilan). Divizion orqali yo'llanma olib,
      hali davlat tanlamaganlarning huquqi bekor bo'ladi; qo'shilganlarga botdan xabar boradi va ular davlatni o'zlari tanlaydi.</div>
    <textarea class="modal-input" id="wc-elig-add-ids" rows="4" placeholder="123456789, 987654321"></textarea>
    <button class="btn btn--primary" id="wc-btn-elig-add" style="width:100%;margin-top:8px">➕ Yo'llanma berish</button>`;
  document.getElementById("wc-btn-elig-rebuild")
    ?.addEventListener("click", e => void wcEligibleRebuild(e.currentTarget, d.prev_season_number));
  document.getElementById("wc-btn-elig-add")
    ?.addEventListener("click", e => void wcEligibleAdd(e.currentTarget, d.free ?? 0));
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

// 2026-10-11: bo'sh o'rinlarga Telegram ID'lar bilan bir yo'la yo'llanma (POST /wc/admin/eligible/add)
async function wcEligibleAdd(btn, free) {
  const raw = document.getElementById("wc-elig-add-ids")?.value || "";
  const ids = [...new Set(raw.split(/[\s,;]+/).filter(x => /^\d+$/.test(x)))];
  if (!ids.length) { showToast("Telegram ID kiriting"); return; }
  if (!confirm(`${ids.length} ta Telegram ID ga JCh yo'llanmasi berilsinmi?\n\nDivizion orqali olib, hali davlat tanlamaganlarning huquqi bekor bo'ladi.`)) return;
  btn.disabled = true;
  try {
    const r = await apiFetch("/wc/admin/eligible/add", { method: "POST", body: JSON.stringify({ ids: ids.join(",") }) });
    const extra = [];
    if (r.not_found.length) extra.push(`topilmadi (botga /start bosmagan): ${r.not_found.join(", ")}`);
    if (r.already.length) extra.push(`avvaldan bor: ${r.already.join(", ")}`);
    showToast(`✅ ${r.added} kishiga yo'llanma berildi` + (extra.length ? ` · ${extra.join(" · ")}` : ""));
    await wcEligibleLoad();
  } catch (e) {
    const msg = {
      empty: "Telegram ID kiriting",
      too_many: `Bo'sh o'rindan ko'p (bo'sh: ${free}). Ro'yxatni qisqartiring`,
      none_added: "Hech kim qo'shilmadi: ID'lar topilmadi yoki ular allaqachon ro'yxatda",
    }[e.message] || e.message;
    showToast("❌ " + msg);
    btn.disabled = false;
  }
}
