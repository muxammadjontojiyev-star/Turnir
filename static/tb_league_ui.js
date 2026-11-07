// =============================================================
//  tb_league_ui.js — "TEAMLAR JANGI": liga sarlavhasi va teami yo'q ekran (2026-10-16)
//  tb.js dan ajratildi (qoida #21). Liga havolasi bilan kelgan foydalanuvchi (TB.joinLeague)
//  shu ligada team ochadi; havolasiz — liga adminidan havola olish haqida izoh.
//  Global: TB, escHtml, ICON, tbWho.
// =============================================================

function tbLeagueBarHtml() {
  const lg = TB.me && TB.me.league;
  return lg ? `<div class="tb-league-bar">${tbLogo("league", lg.id, lg.logo_ver, lg.emoji, "tb-logo--sm")} <b>${escHtml(lg.name)}</b></div>` : "";
}

// ---------------- Teami yo'q: tushuntirish + (liga havolasi bo'lsa) team ochish ----------------
function tbNoTeamHtml() {
  const em = TB.me.emojis || [];
  if (!TB.createEmoji) TB.createEmoji = em[0];
  const L = TB.joinLeague;
  const lmin = L ? L.lineup_min : TB.me.lineup_min, lmax = L ? L.lineup_max : TB.me.lineup_max;
  // 2026-11-07: dizayn — ixcham kirish + 2 ta aniq yo'l + ochiq ligalar teamlari (tb_public.js)
  const hero = `
    <div class="card tb-hero">
      <div class="tb-hero-kicker">${ICON.get("swords", 16)} TEAMLAR JANGI</div>
      <div class="tb-hero-title">Jamoangizni yig'ing va jangga kiring</div>
      <div class="tb-hero-sub">Ikki team bahsida o'yinchilar 1v1 o'ynaydi — ko'p g'alaba olgan team yutadi. Asosiy tarkib: ${lmin}–${lmax} kishi.</div>
    </div>
    <div class="tb-ways">
      <div class="tb-way"><span class="tb-way-ic">🤝</span><b>Teamga qo'shilish</b>
        <span>Do'stingizdan taklif havolasini so'rang yoki pastdagi teamlar sardoriga yozing.</span></div>
      <div class="tb-way"><span class="tb-way-ic">⚔️</span><b>O'z teamingizni ochish</b>
        <span>${L ? "Pastdagi formada team nomini yozing." : "Liga adminidan liga havolasini oling."}</span></div>
    </div>`;
  if (!L) {
    return hero + (typeof tbPublicBoxHtml === "function" ? tbPublicBoxHtml() : "");
  }
  return hero + `
    <div class="section-label">LIGA</div>
    <div class="card tb-league-card">${tbLogo("league", L.id, L.logo_ver, L.emoji, "tb-logo--lg")}<div><b>${escHtml(L.name)}</b>
      ${L.admin_username || L.admin_nickname ? `<small>Liga admini: ${escHtml(tbWho({ username: L.admin_username, nickname: L.admin_nickname }))}</small>` : ""}</div></div>
    <div class="section-label">TEAM OCHISH</div>
    <div class="card tb-form">
      <input id="tb-name" class="modal-input" maxlength="${TB.me.name_max}" placeholder="Team nomi (${TB.me.name_min}–${TB.me.name_max} belgi)" autocomplete="off">
      <button class="btn btn--primary btn--glow" data-tb="create">⚔️ Team ochish</button>
      <div class="tb-hint">Team admin tasdig'idan keyin turnirda qatnashadi. A'zolarni hozirdan yig'ishingiz mumkin.</div>
      <div class="tb-hint">Team logosini ochilgandan keyin galereyadan qo'yasiz.</div>
    </div>
    ${typeof tbPublicBoxHtml === "function" ? tbPublicBoxHtml() : ""}`;
}
