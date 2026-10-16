// =============================================================
//  tb_admin_season.js — "TEAMLAR JANGI": bosh admin — mavsum boshqaruvi (2026-10-16, 2-bosqich)
//  Admin tabining tepasida: qatnasha oladigan teamlar soni, qur'a (divizion hajmi),
//  turlarni boshlash, turni hozir yopish, mavsumni yakunlash, o'yin natijasini qo'yish (ID bo'yicha).
//  tb_admin.js tbAdminRender() shu blokni qo'yadi: tbAdminSeasonHtml(). Global: TB, apiFetch, escHtml, showToast, tbErr.
//  2026-10-16: barcha amallar tanlangan liga uchun (TB.adminLeagueId).
// =============================================================

function tbAdminSeasonHtml() {
  const p = TB.seasonPreview;
  if (!p) return `<div class="card tb-hint">Mavsum ma'lumoti yuklanmoqda…</div>`;
  const s = p.active;
  let state, acts;
  if (!s) {
    state = `Faol mavsum yo'q. Qatnasha oladi: <b>${p.eligible}</b> ta team (tasdiqlangan ${p.approved}, tarkibi ≥ ${p.lineup_min}).`;
    acts = `<div class="tb-adm-line"><span>Divizion hajmi</span>
        <input id="tbs-divsize" class="modal-input" type="number" min="4" max="20" value="${p.division_size}"></div>
      <button class="btn btn--primary" data-tbsa="create">🎲 Qur'a o'tkazish (yangi mavsum)</button>`;
  } else if (s.status === "drawn") {
    state = `<b>${s.number}-mavsum</b>: qur'a o'tkazilgan (${s.total_rounds} tur). Turlar hali boshlanmagan.`;
    acts = `<button class="btn btn--primary" data-tbsa="start">▶️ Turlarni boshlash (1-tur bugun ochiladi)</button>`;
  } else {
    state = `<b>${s.number}-mavsum</b>: ${Math.min(s.current_round, s.total_rounds)}/${s.total_rounds}-tur. Tur har kuni 23:30 da almashadi.`;
    acts = `<button class="btn btn--ghost" data-tbsa="advance">⏭ Joriy turni hozir yopish</button>
      <button class="btn btn--ghost tb-danger-btn" data-tbsa="finish">🏁 Mavsumni yakunlash</button>`;
  }
  return `<div class="section-label">MAVSUM</div>
    <div class="card tb-adm-season">
      <div class="tb-hint">${state}</div>
      ${acts}
      ${s ? `<div class="tb-adm-line tb-adm-fix">
          <input id="tbs-gid" class="modal-input" type="number" placeholder="O'yin ID">
          <input id="tbs-s1" class="modal-input" type="number" placeholder="Uy">
          <input id="tbs-s2" class="modal-input" type="number" placeholder="Meh.">
          <button class="tb-mini tb-mini--ok" data-tbsa="setgame">Qo'yish</button>
        </div>
        <div class="tb-hint">O'yin ID — Jadval → tur bahsidagi juftlik raqami (#).</div>` : ""}
    </div>
    <div class="section-label">TEAMLAR</div>`;
}

async function tbAdminSeasonLoad() {
  try { TB.seasonPreview = await apiFetch(`/tb/admin/season/preview?league_id=${TB.adminLeagueId}`); }
  catch (_) { TB.seasonPreview = null; }
}

async function tbAdminSeasonAct(a, btn) {
  const ask = { create: "Qur'a o'tkazilsinmi? Tasdiqlangan, tarkibi to'liq teamlar divizionlarga bo'linadi.",
                start: "Turlar boshlansinmi? 1-tur hozir ochiladi va o'yinchilar juftlanadi.",
                advance: "Joriy tur hozir yopilsinmi? Kiritilmagan o'yinlar 0:0 bo'ladi, keyingi tur ochiladi.",
                finish: "Mavsum yakunlansinmi? Ochiq o'yinlar yopiladi, har divizion g'olibi 🏆 oladi. Keyingi qur'ada har divizionning top-2 tasi ko'tariladi, oxirgi 2 tasi tushadi. Qaytarib bo'lmaydi!" }[a];
  let path, body = {};
  if (a === "setgame") {
    const g = +document.getElementById("tbs-gid").value, s1 = document.getElementById("tbs-s1").value,
          s2 = document.getElementById("tbs-s2").value;
    if (!g || s1 === "" || s2 === "") { showToast("O'yin ID va hisobni kiriting"); return; }
    path = "/tb/admin/game/set"; body = { game_id: g, score1: +s1, score2: +s2 };
  } else {
    if (!confirm(ask)) return;
    path = `/tb/admin/season/${a}`;
    body = { league_id: TB.adminLeagueId };                              // 2026-10-16: liga
    if (a === "create") body.division_size = +(document.getElementById("tbs-divsize")?.value || 0) || null;
  }
  btn.disabled = true;
  try {
    const r = await apiFetch(path, { method: "POST", body: JSON.stringify(body) });
    const msg = a === "create" ? `✅ ${r.number}-mavsum: ${r.teams} team, ${r.divisions} divizion, ${r.total_rounds} tur`
      : a === "start" ? `✅ 1-tur ochildi: ${r.games} ta 1v1 o'yin`
      : a === "advance" ? `✅ ${r.closed_round}-tur yopildi`
      : a === "finish" ? `🏁 Mavsum yakunlandi. Chempionlar: ${(r.champions || []).map(c => c.division + "-div: " + c.name).join(", ") || "—"}`
      : "✅ Natija qo'yildi";
    showToast(msg);
    if (typeof tbAdminLoad === "function") await tbAdminLoad();
  } catch (e) {
    showToast("❌ " + tbErr(e));
    btn.disabled = false;
  }
}

document.addEventListener("click", (e) => {
  const b = e.target.closest ? e.target.closest("#tb-root [data-tbsa]") : null;
  if (b) void tbAdminSeasonAct(b.dataset.tbsa, b);
});
