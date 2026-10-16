// =============================================================
//  tb_league_ui.js — "TEAMLAR JANGI": liga sarlavhasi va teami yo'q ekran (2026-10-16)
//  tb.js dan ajratildi (qoida #21). Liga havolasi bilan kelgan foydalanuvchi (TB.joinLeague)
//  shu ligada team ochadi; havolasiz — liga adminidan havola olish haqida izoh.
//  Global: TB, escHtml, ICON, tbWho.
// =============================================================

function tbLeagueBarHtml() {
  const lg = TB.me && TB.me.league;
  return lg ? `<div class="tb-league-bar">${escHtml(lg.emoji || "🏆")} <b>${escHtml(lg.name)}</b></div>` : "";
}

// ---------------- Teami yo'q: tushuntirish + (liga havolasi bo'lsa) team ochish ----------------
function tbNoTeamHtml() {
  const em = TB.me.emojis || [];
  if (!TB.createEmoji) TB.createEmoji = em[0];
  const L = TB.joinLeague;
  const lmin = L ? L.lineup_min : TB.me.lineup_min, lmax = L ? L.lineup_max : TB.me.lineup_max;
  const hero = `
    <div class="card tb-hero">
      <div class="tb-hero-kicker">${ICON.get("swords", 16)} TEAMLAR JANGI</div>
      <div class="tb-hero-title">Jamoangizni yig'ing va jangga kiring</div>
      <ul class="tb-hero-list">
        <li>Team ochasiz yoki do'stingiz teamiga taklif havolasi orqali qo'shilasiz.</li>
        <li>Sardor asosiy tarkibni tuzadi (${lmin}–${lmax} kishi).</li>
        <li>Ikki team bahsida o'yinchilar 1v1 o'ynaydi — ko'p g'alaba olgan team yutadi.</li>
        <li>Teamlar divizionlarda liga formatida bellashadi.</li>
      </ul>
    </div>`;
  if (!L) {
    return hero + `<div class="card tb-note">Team ochish uchun liga adminidan liga havolasini oling.</div>
      <div class="tb-hint tb-hint--center">Do'stingiz teamiga qo'shilish uchun undan taklif havolasini so'rang.</div>`;
  }
  return hero + `
    <div class="section-label">LIGA</div>
    <div class="card tb-league-card"><span>${escHtml(L.emoji || "🏆")}</span><div><b>${escHtml(L.name)}</b>
      ${L.admin_username || L.admin_nickname ? `<small>Liga admini: ${escHtml(tbWho({ username: L.admin_username, nickname: L.admin_nickname }))}</small>` : ""}</div></div>
    <div class="section-label">TEAM OCHISH</div>
    <div class="card tb-form">
      <input id="tb-name" class="modal-input" maxlength="${TB.me.name_max}" placeholder="Team nomi (${TB.me.name_min}–${TB.me.name_max} belgi)" autocomplete="off">
      <div class="tb-form-label">Belgi</div>
      <div class="tb-emoji-grid">${em.map(e =>
        `<button class="tb-emoji${e === TB.createEmoji ? " active" : ""}" data-tb-emoji="${escHtml(e)}">${escHtml(e)}</button>`).join("")}</div>
      <button class="btn btn--primary btn--glow" data-tb="create">⚔️ Team ochish</button>
      <div class="tb-hint">Team admin tasdig'idan keyin turnirda qatnashadi. A'zolarni hozirdan yig'ishingiz mumkin.</div>
    </div>
    <div class="tb-hint tb-hint--center">Do'stingiz teamiga qo'shilish uchun undan taklif havolasini so'rang.</div>`;
}
