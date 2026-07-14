// ============================================================
//  cl_home.js — ChL "Asosiy" sahifasi (World Cup bosh sahifasi naqshi)
//  cl.js dan ajratildi (qoida 21). Global: CL, CL_GROUP_COUNT, CL_GROUP_SIZE,
//  escHtml, clClubBadge (cl.js), renderChampionsLeague.
// ============================================================

// ---- HOME: WC naqshi (hero + guruh tanlash + guruh a'zolari) ----
function clRenderHome() {
  const g = CL.groups;
  if (!g) return `<div class="card">Ma'lumot yuklanmadi. Qayta urinib ko'ring.</div>`;

  if (!g.drawn) return clRenderHomeBeforeDraw();

  const byGroup = {};
  for (const p of g.participants) {
    if (!p.group_number) continue;
    (byGroup[p.group_number] ||= []).push(p);
  }
  const sel = CL.homeGroup;
  const members = byGroup[sel] || [];

  const hero = clRenderHero(`GURUH ${sel}`, [
    { v: members.length, l: "ISHTIROKCHI" },
    { v: CL_GROUP_COUNT, l: "GURUHLAR" },
    { v: g.season ?? "—", l: "MAVSUM" },
  ], CL.meParticipant ? "🎟 Siz ishtirokchisiz" : "Siz ishtirokchi emassiz");

  let chips = `<div class="section-label">GURUH TANLASH</div><div class="cl-group-grid">`;
  for (let n = 1; n <= CL_GROUP_COUNT; n++) {
    chips += `<button class="cl-group-chip${sel === n ? " active" : ""}" data-cl-home-group="${n}">G${n}</button>`;
  }
  chips += `</div>`;

  const list = members.length
    ? members.map(p => `
        <div class="match-item cl-group-row">
          ${clClubBadge(p.club_name, 26)}
          <b>${escHtml(p.nickname || "")}</b>
        </div>`).join("")
    : `<div class="wc-loading-row">Bu guruhda ishtirokchi yo'q.</div>`;

  return `${hero}${chips}
    <div class="section-label">GURUHDAGI ISHTIROKCHILAR</div>
    <div class="matches-list">${list}</div>`;
}

// Hero karta (WC bosh kartasi naqshi: sarlavha + 3 ta stat + holat tugmasi)
function clRenderHero(title, stats, statusText) {
  const cells = stats.map(s => `
    <div class="cl-hero-stat">
      <span class="cl-hero-stat-value">${escHtml(String(s.v))}</span>
      <span class="cl-hero-stat-label">${escHtml(s.l)}</span>
    </div>`).join("");
  return `
    <div class="cl-hero">
      <div class="cl-hero-overlay">
        <div class="cl-hero-kicker">CHEMPIONLAR LIGASI</div>
        <div class="cl-hero-title">${escHtml(title)}</div>
        <div class="cl-hero-stats">${cells}</div>
        <div class="cl-hero-status">${escHtml(statusText)}</div>
      </div>
    </div>`;
}

// Qur'agacha: hero + kvalifikantlar ro'yxati
function clRenderHomeBeforeDraw() {
  const qs = (CL.qualifiers && CL.qualifiers.qualifiers) || [];
  const hero = clRenderHero("QUR'A KUTILMOQDA", [
    { v: qs.length, l: "KVALIFIKANT" },
    { v: CL_GROUP_COUNT, l: "GURUHLAR" },
    { v: CL_GROUP_SIZE, l: "HAR GURUHDA" },
  ], CL.meParticipant ? "🎟 Siz ishtirokchisiz" : "Siz ishtirokchi emassiz");

  if (!qs.length) {
    return `${hero}<div class="card">Kvalifikatsiya hali aniqlanmagan. Liga mavsumi yakunlangach, 5 liga bo'yicha top-6 va eng yaxshi 2 ta 7-o'rin (jami 32) shu yerda ko'rinadi.</div>`;
  }
  const rows = qs.map(q => `
    <div class="match-item cl-group-row">
      <b>${escHtml(q.nickname || "Ishtirokchi")}</b>
      <span class="cl-qual-meta">${escHtml(q.league_name || "")} · ${q.position}-o'rin · ${q.points} ochko</span>
    </div>`).join("");
  return `${hero}
    <div class="section-label">KVALIFIKANTLAR (${qs.length}/32)</div>
    <div class="matches-list">${rows}</div>`;
}
