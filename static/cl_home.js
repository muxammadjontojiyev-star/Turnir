// ============================================================
//  cl_home.js — ChL "Asosiy" sahifasi (World Cup bosh sahifasi naqshi)
//  cl.js dan ajratildi (qoida 21). Global: CL, CL_ROUNDS, CL_TOTAL,
//  escHtml, clClubBadge (cl.js), renderChampionsLeague.
// ============================================================

// ---- HOME: WC naqshi (hero + liga bosqichi ishtirokchilari) ----
// Yangi format: guruh yo'q — barcha 36 ishtirokchi yagona ro'yxatda.
function clRenderHome() {
  const g = CL.groups;
  if (!g) return `<div class="card">${CT("cl_load_failed")}</div>`;

  if (!g.drawn) return clRenderHomeBeforeDraw();

  const members = g.participants.filter(p => p.group_number);

  const hero = clRenderHero(CT("cl_league_phase"), [
    { v: members.length, l: CT("cl_stat_clubs") },
    { v: CL_ROUNDS, l: CT("cl_stat_rounds") },
    { v: g.cl_season ?? 1, l: CT("cl_stat_season") },
  ], CL.meParticipant ? CT("cl_you_in") : CT("cl_you_out"));

  const list = members.length
    ? members.map(p => `
        <div class="match-item cl-group-row">
          ${clClubBadge(p.club_name, 26)}
          <b>${escHtml(p.nickname || "")}</b>
        </div>`).join("")
    : `<div class="wc-loading-row">${CT("cl_group_empty")}</div>`;

  return `${hero}
    <div class="section-label">${CT("cl_participants_label")}</div>
    <div class="matches-list">${list}</div>
    ${clRenderRules()}`;
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
        <div class="cl-hero-kicker">${ICON.get("ucl", 15)} CHEMPIONLAR LIGASI</div>
        <div class="cl-hero-title">${escHtml(title)}</div>
        <div class="cl-hero-stats">${cells}</div>
        <div class="cl-hero-status">${escHtml(statusText)}</div>
      </div>
    </div>`;
}

// Qur'agacha: hero + kvalifikantlar ro'yxati
function clRenderHomeBeforeDraw() {
  const qs = (CL.qualifiers && CL.qualifiers.qualifiers) || [];
  const hero = clRenderHero(CT("cl_draw_pending"), [
    { v: qs.length, l: CT("cl_stat_qualifiers") },
    { v: CL_TOTAL, l: CT("cl_stat_clubs") },
    { v: CL_ROUNDS, l: CT("cl_stat_rounds") },
  ], CL.meParticipant ? CT("cl_you_in") : CT("cl_you_out"));

  if (!qs.length) {
    return `${hero}<div class="card">${CT("cl_qual_pending")}</div>${clRenderRules()}`;
  }
  const rows = qs.map(q => `
    <div class="match-item cl-group-row">
      <b>${escHtml(q.nickname || CT("cl_participant"))}</b>
      <span class="cl-qual-meta">${escHtml(q.league_name || "")} · ${q.position}-o'rin · ${q.points} ochko</span>
    </div>`).join("");
  return `${hero}
    <div class="section-label">${CT("cl_qualifiers_label")} (${qs.length}/${CL_TOTAL})</div>
    <div class="matches-list">${rows}</div>
    ${clRenderRules()}`;
}

// ---- QOIDALAR ----
// Muhim qiymatlar <mark> (cl-key) bilan ajratiladi; eng kritik 3 band alohida
// "cl-rule--important" kartada (qoida #52: foydalanuvchi jarima olmasligi uchun
// deadline, 0:0 va yopiq tur qoidalari ko'zga tashlanib turishi shart).
function clRenderRules() {
  const key = (v) => `<strong class="rule-hl">${v}</strong>`;

  const important = [
    `Deadline — ${key("23:30")} (Toshkent). Shu vaqtda joriy tur yopiladi va keyingisi ochiladi.`,
    `Deadlinegacha natija kiritilmagan o'yin ${key("0:0 durang")} bilan yopiladi.`,
    `Natijani faqat ${key("ochiq turda")} kiritish mumkin — yopiq turlar qulf belgisi bilan turadi.`,
  ].map(x => `<li>${x}</li>`).join("");

  const general = [
    `Liga mavsumi bo'yicha eng ko'p ochko to'plagan ${key(CL_TOTAL + " ta")} ishtirokchi qatnashadi.`,
    `Guruhlar ${key("yo'q")}: barcha ishtirokchi yagona liga bosqichida.`,
    `Har ishtirokchi ${key(CL_ROUNDS + " ta turli raqib")} bilan ${key("1 martadan")} (mehmon o'yinisiz) o'ynaydi.`,
    `Kuniga ${key("bitta tur")} o'ynaladi. Turlar admin ruxsatidan keyin ochiladi.`,
    `Bir tomon kiritgan, ikkinchisi tasdiqlamagan natija deadline'da ${key("avtomatik tasdiqlanadi")}.`,
    `Ochko: g'alaba ${key("3")} · durang ${key("1")} · mag'lubiyat ${key("0")}.`,
    `Saralash: ochko → gol farqi → urilgan gollar.`,
    `${CL_ROUNDS} tur tugagach: ${key("top-8")} to'g'ridan setkaga, ${key("9-24 o'rin")} pley-in (uy+mehmon) o'ynab 8 tasi setkaga qo'shiladi.`,
  ].map(x => `<li>${x}</li>`).join("");

  return `
    <div class="section-label">QOIDALAR</div>
    <div class="card cl-rules rules-block cl-rules--important">
      <div class="cl-rules-head">${ICON.get("megaphone", 15)} <span>MUHIM — ESDA TUTING</span></div>
      <ul>${important}</ul>
    </div>
    <div class="card cl-rules rules-block">
      <div class="cl-rules-head">${ICON.get("clipboard", 15)} <span>UMUMIY QOIDALAR</span></div>
      <ul>${general}</ul>
    </div>`;
}
