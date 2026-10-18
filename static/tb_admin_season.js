// =============================================================
//  tb_admin_season.js — "TEAMLAR JANGI": bosh admin — mavsum boshqaruvi (2026-10-16, 2-bosqich)
//  Admin tabining tepasida: qatnasha oladigan teamlar soni, qur'a (divizion hajmi),
//  turlarni boshlash, turni hozir yopish, mavsumni yakunlash, o'yin natijasini qo'yish (ID bo'yicha).
//  tb_admin.js tbAdminRender() shu blokni qo'yadi: tbAdminSeasonHtml(). Global: TB, apiFetch, escHtml, showToast, tbErr.
//  2026-10-16: barcha amallar tanlangan liga uchun (TB.adminLeagueId).
//  2026-10-18: qur'a formasi — tb_admin_draw.js (Liga / UCL, N vs N).
// =============================================================

function tbAdminSeasonHtml() {
  const p = TB.seasonPreview;
  if (!p) return `<div class="card tb-hint">Mavsum ma'lumoti yuklanmoqda…</div>`;
  const s = p.active;
  let state, acts;
  if (!s) {
    state = `Faol mavsum yo'q. Tasdiqlangan teamlar: ${p.approved}.`;
    acts = tbAdminDrawFormHtml(p);                // 2026-10-18: Liga / UCL, N vs N (tb_admin_draw.js)
  } else if (s.status === "drawn") {
    state = `<b>${s.number}-mavsum</b>${tbsFmtTag(s)}: qur'a o'tkazilgan (${s.total_rounds} tur). Turlar hali boshlanmagan.`;
    acts = `<button class="btn btn--primary" data-tbsa="start">▶️ Turlarni boshlash (1-tur bugun ochiladi)</button>`;
  } else {
    state = `<b>${s.number}-mavsum</b>${tbsFmtTag(s)}: ${Math.min(s.current_round, s.total_rounds)}/${s.total_rounds}-tur. Tur har kuni 23:30 da almashadi.`
      + (s.waiting_admin ? `<div class="tb-warn">⚖️ Pley-offda teng juftlik bor — g'olibni belgilang (Jadval → Pley-off). Shundan keyin keyingi bosqich ochiladi.</div>` : "");
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
  const ask = { create: "Qur'a o'tkazilsinmi? Tasdiqlangan va asosiy tarkibi yetarli teamlar qatnashadi.",
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
    if (a === "create") Object.assign(body, tbAdminDrawBody());      // 2026-10-18
  }
  btn.disabled = true;
  try {
    const r = await apiFetch(path, { method: "POST", body: JSON.stringify(body) });
    const msg = a === "create" ? (r.format === "ucl" ? `✅ ${r.number}-mavsum (UCL): ${r.teams} team, ${r.total_rounds} tur`
                                                     : `✅ ${r.number}-mavsum: ${r.teams} team, ${r.divisions} divizion, ${r.total_rounds} tur`)
      : a === "start" ? `✅ 1-tur ochildi: ${r.games} ta 1v1 o'yin`
      : a === "advance" ? (r.waiting_admin ? `✅ ${r.closed_round}-tur yopildi. ⚖️ Pley-offda teng juftlik — g'olibni belgilang`
                                           : `✅ ${r.closed_round}-tur yopildi`)
      : a === "finish" ? `🏁 Mavsum yakunlandi. Chempion: ${(r.champions || []).map(c => c.name).join(", ") || "—"}`
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
