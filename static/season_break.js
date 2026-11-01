// =============================================================
//  season_break.js — LIGA MAVSUMLARI ORASIDAGI TANAFFUS (2026-11-01)
//  Backend: season_break.py; /season/current -> league_break (api.js loadSeasons -> APP.seasonBreak);
//  /register tanaffusda "season_break"; POST /season/start (bosh admin) — yangi mavsumni ochadi.
//  Bosh sahifa: banner (auksionga taklif), ro'yxat tugmasi o'chiq, klub navbati banneri yashirin.
//  Admin «LIGA MAVSUMI»: holat va «▶️ Yangi mavsumni boshlash» tugmasi.
//  api.js renderHeroCard / loadSeasonInfo, club_priority.js clubPriorityRender qayta tayinlash orqali
//  o'raladi. index.html da promotion.js dan KEYIN ulanadi. Global: APP, apiFetch, escHtml, showToast.
// =============================================================

const SB_TXT = {
  uz: { note: "⏸ Mavsumlar orasidagi tanaffus. Yangi liga mavsumi tez orada boshlanadi.",
        sub: "Hozir Do'kon → Auksion'da mukofot tokenlaringiz bilan klub uchun kurashing — g'oliblarning klubi yangi mavsumda band bo'ladi.",
        toast: "Tanaffus: yangi mavsum hali boshlanmadi. Ro'yxat mavsum ochilganda boshlanadi.",
        adm_state: "⏸ Tanaffus — ro'yxat yopiq, auksion ishlamoqda", adm_btn: "▶️ Yangi mavsumni boshlash",
        adm_hint: "Auksion g'oliblari klubiga yoziladi, ro'yxatdan o'tish ochiladi.",
        confirm: "Yangi liga mavsumini boshlaysizmi? Auksion g'oliblari klubiga yoziladi va ro'yxatdan o'tish ochiladi.",
        done: "✅ Yangi mavsum boshlandi. Auksion: {a} ta klub band qilindi, {f} ta yozilmadi (pul qaytdi).",
        auction_active: "Faol auksion bor ({n} ta). Avval tugashini kuting yoki bekor qiling.",
        not_in_break: "Mavsum allaqachon ochiq." },
  ru: { note: "⏸ Перерыв между сезонами. Новый сезон лиг скоро начнётся.",
        sub: "Сейчас в Магазин → Аукцион боритесь за клуб наградными токенами — клубы победителей будут закреплены в новом сезоне.",
        toast: "Перерыв: новый сезон ещё не начался. Регистрация откроется со стартом сезона.",
        adm_state: "⏸ Перерыв — регистрация закрыта, аукцион работает", adm_btn: "▶️ Начать новый сезон",
        adm_hint: "Победители аукциона будут записаны в свои клубы, регистрация откроется.",
        confirm: "Начать новый сезон лиг? Победители аукциона будут записаны в клубы, регистрация откроется.",
        done: "✅ Новый сезон начался. Аукцион: закреплено клубов — {a}, не записано — {f} (деньги возвращены).",
        auction_active: "Есть активные аукционы ({n}). Дождитесь окончания или отмените.",
        not_in_break: "Сезон уже открыт." },
  en: { note: "⏸ Break between seasons. The new league season starts soon.",
        sub: "Now use your reward tokens in Shop → Auction to fight for a club — winners' clubs will be reserved for the new season.",
        toast: "Break: the new season hasn't started yet. Registration opens when it starts.",
        adm_state: "⏸ Break — registration closed, auction running", adm_btn: "▶️ Start new season",
        adm_hint: "Auction winners get their clubs, registration opens.",
        confirm: "Start the new league season? Auction winners get their clubs and registration opens.",
        done: "✅ New season started. Auction: {a} clubs reserved, {f} not placed (refunded).",
        auction_active: "There are active auctions ({n}). Wait for them to end or cancel them.",
        not_in_break: "The season is already open." },
};

function sbT(key, vars) {
  const d = SB_TXT[APP.lang] || SB_TXT.uz;
  return Object.entries(vars || {}).reduce((s, [k, v]) => s.split(`{${k}}`).join(String(v)), d[key] || SB_TXT.uz[key] || "");
}

function seasonBreakText() { return sbT("toast"); }

function sbRenderNote() {
  const box = document.getElementById("season-break-note");
  if (!box) return;
  if (!APP.seasonBreak) { box.classList.add("hidden"); return; }
  box.className = "club-priority-note is-wait";
  box.innerHTML = `<div>${escHtml(sbT("note"))}</div><small>${escHtml(sbT("sub"))}</small>`;
  const prio = document.getElementById("club-priority-note");
  if (prio) prio.classList.add("hidden");           // tanaffusda navbat vaqtlari ma'nosiz
}

if (typeof renderHeroCard === "function") {
  const _sbOrigHero = renderHeroCard;
  renderHeroCard = function (league) {
    _sbOrigHero(league);
    sbRenderNote();
    const btn = document.getElementById("btn-register");
    if (APP.seasonBreak && btn) { btn.disabled = true; btn.style.opacity = "0.45"; }
  };
}

if (typeof clubPriorityRender === "function") {
  const _sbOrigPrio = clubPriorityRender;
  clubPriorityRender = function () {
    _sbOrigPrio();
    if (APP.seasonBreak) sbRenderNote();
  };
}

function sbRenderAdmin() {
  const btn = document.getElementById("btn-start-season");
  const hint = document.getElementById("season-start-hint");
  const cur = document.getElementById("season-current-hint");
  if (!btn || !hint) return;
  btn.classList.toggle("hidden", !APP.seasonBreak);
  hint.classList.toggle("hidden", !APP.seasonBreak);
  btn.textContent = sbT("adm_btn");
  hint.textContent = sbT("adm_hint");
  if (APP.seasonBreak && cur && !cur.textContent.includes("⏸")) cur.textContent += " · " + sbT("adm_state");
  if (!btn._sbBound) { btn._sbBound = true; btn.addEventListener("click", sbStartSeason); }
}

async function sbStartSeason() {
  if (!window.confirm(sbT("confirm"))) return;
  const btn = document.getElementById("btn-start-season");
  btn.disabled = true;                                  // ikki marta bosish (qoida #38)
  try {
    const r = await apiFetch("/season/start", { method: "POST" });
    const a = r.auction || {};
    window.alert(sbT("done", { a: a.applied || 0, f: a.failed || 0 }));
    if (typeof loadSeasons === "function") await loadSeasons();
    if (typeof loadSeasonInfo === "function") await loadSeasonInfo();
    if (typeof loadHome === "function") { try { await loadHome(); } catch (_) {} }
  } catch (e) {
    const [code, n] = String(e.message || "").split(":");
    showToast("❌ " + (code === "auction_active" ? sbT("auction_active", { n: n || "?" })
      : code === "not_in_break" ? sbT("not_in_break") : e.message));
  } finally {
    btn.disabled = false;
  }
}

if (typeof loadSeasonInfo === "function") {
  const _sbOrigSeasonInfo = loadSeasonInfo;
  loadSeasonInfo = async function () {
    if (typeof loadSeasons === "function") { try { await loadSeasons(); } catch (_) {} }
    await _sbOrigSeasonInfo();
    sbRenderAdmin();
  };
}
