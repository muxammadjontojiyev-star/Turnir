// ============================================================
//  ac_home.js — OChL "Asosiy" sahifasi (World Cup bosh sahifasi naqshi)
//  ac.js dan ajratildi (qoida 21). Global: AC, AC_ROUNDS, AC_TOTAL,
//  escHtml, acClubBadge (ac.js), renderAsianChampionsLeague.
// ============================================================

// ---- HOME: WC naqshi (hero + liga bosqichi ishtirokchilari) ----
// Yangi format: guruh yo'q — barcha 32 ishtirokchi yagona ro'yxatda.
function acRenderHome() {
  const g = AC.groups;
  if (!g) return `<div class="card">${ACT("ac_load_failed")}</div>`;

  if (!g.drawn) return acRenderHomeBeforeDraw();

  const members = g.participants.filter(p => p.group_number);

  const hero = acRenderHero(ACT("ac_league_phase"), [
    { v: members.length, l: ACT("ac_stat_clubs") },
    { v: AC_ROUNDS, l: ACT("ac_stat_rounds") },
    { v: g.ac_season ?? 1, l: ACT("ac_stat_season") },
  ], AC.meParticipant ? ACT("ac_you_in") : ACT("ac_you_out"));

  const list = members.length
    ? members.map(p => `
        <div class="match-item ac-group-row">
          ${acClubBadge(p.club_name, 26)}
          <b>${escHtml(p.nickname || "")}</b>
        </div>`).join("")
    : `<div class="wc-loading-row">${ACT("ac_group_empty")}</div>`;

  return `${hero}
    <div class="section-label">${ACT("ac_participants_label")}</div>
    <div class="matches-list">${list}</div>
    ${acRenderRules()}`;
}

// Hero karta (WC bosh kartasi naqshi: sarlavha + 3 ta stat + holat tugmasi)
function acRenderHero(title, stats, statusText) {
  const cells = stats.map(s => `
    <div class="ac-hero-stat">
      <span class="ac-hero-stat-value">${escHtml(String(s.v))}</span>
      <span class="ac-hero-stat-label">${escHtml(s.l)}</span>
    </div>`).join("");
  return `
    <div class="ac-hero">
      <div class="ac-hero-overlay">
        <div class="ac-hero-kicker">${ICON.get("trophy", 15)} OSIYO CHEMPIONLAR LIGASI</div>
        <div class="ac-hero-title">${escHtml(title)}</div>
        <div class="ac-hero-stats">${cells}</div>
        <div class="ac-hero-status">${escHtml(statusText)}</div>
      </div>
    </div>`;
}

// Qur'agacha: hero + kvalifikantlar ro'yxati
function acRenderHomeBeforeDraw() {
  const qs = (AC.qualifiers && AC.qualifiers.qualifiers) || [];
  const hero = acRenderHero(ACT("ac_draw_pending"), [
    { v: qs.length, l: ACT("ac_stat_qualifiers") },
    { v: AC_TOTAL, l: ACT("ac_stat_clubs") },
    { v: AC_ROUNDS, l: ACT("ac_stat_rounds") },
  ], AC.meParticipant ? ACT("ac_you_in") : ACT("ac_you_out"));

  if (!qs.length) {
    return `${hero}<div class="card">${ACT("ac_qual_pending")}</div>${acRenderRules()}`;
  }
  const rows = qs.map(q => `
    <div class="match-item ac-group-row">
      <b>${escHtml(q.nickname || ACT("ac_participant"))}</b>
      <span class="ac-qual-meta">${escHtml(q.league_name || "")} · ${q.position}-o'rin · ${q.points} ochko</span>
    </div>`).join("");
  return `${hero}
    <div class="section-label">${ACT("ac_qualifiers_label")} (${qs.length}/${AC_TOTAL})</div>
    <div class="matches-list">${rows}</div>
    ${acRenderRules()}`;
}

// ---- QOIDALAR ----
// Muhim qiymatlar <mark> (ac-key) bilan ajratiladi; eng kritik 3 band alohida
// "ac-rule--important" kartada (qoida #52: foydalanuvchi jarima olmasligi uchun
// deadline, 0:0 va yopiq tur qoidalari ko'zga tashlanib turishi shart).
function acRenderRules() {
  const key = (v) => `<strong class="rule-hl">${v}</strong>`;

  const important = [
    `Deadline — ${key("23:30")} (Toshkent). Shu vaqtda joriy tur yopiladi va keyingisi ochiladi.`,
    `Deadlinegacha natija kiritilmagan o'yin ${key("0:0 durang")} bilan yopiladi.`,
    `Natijani faqat ${key("ochiq turda")} kiritish mumkin — yopiq turlar qulf belgisi bilan turadi.`,
  ].map(x => `<li>${x}</li>`).join("");

  const general = [
    // 2026-10-15: 4 ta Osiyo ligasidan top-8 (ac_qualification.AC_LEAGUES / AC_TOP_N)
    `${key("4 ta Osiyo ligasi")} (Superliga, Saudi Pro Liga, UAE Pro Liga, J1 Liga) har biridan ${key("top-8")} — jami ${key(AC_TOTAL + " ta")} ishtirokchi qatnashadi. Yevropa ligalari va 2-ligalar kirmaydi.`,
    `Qatnashish huquqi ${key("Telegram akkauntingizga")} beriladi — yangi mavsumda boshqa klub tanlasangiz ham saqlanadi.`,
    `Guruhlar ${key("yo'q")}: barcha ishtirokchi yagona liga bosqichida.`,
    `Har ishtirokchi ${key(AC_ROUNDS + " ta turli raqib")} bilan ${key("1 martadan")} (mehmon o'yinisiz) o'ynaydi.`,
    `Kuniga ${key("bitta tur")} o'ynaladi. Turlar admin ruxsatidan keyin ochiladi.`,
    `Bir tomon kiritgan, ikkinchisi tasdiqlamagan natija deadline'da ${key("avtomatik tasdiqlanadi")}.`,
    `Ochko: g'alaba ${key("3")} · durang ${key("1")} · mag'lubiyat ${key("0")}.`,
    `Saralash: ochko → gol farqi → urilgan gollar.`,
    `${AC_ROUNDS} tur tugagach: ${key("top-8")} to'g'ridan setkaga, ${key("9-24 o'rin")} pley-in (uy+mehmon) o'ynab 8 tasi setkaga qo'shiladi.`,
  ].map(x => `<li>${x}</li>`).join("");

  return `
    <div class="section-label">QOIDALAR</div>
    <div class="card ac-rules rules-block ac-rules--important">
      <div class="ac-rules-head">${ICON.get("megaphone", 15)} <span>MUHIM — ESDA TUTING</span></div>
      <ul>${important}</ul>
    </div>
    <div class="card ac-rules rules-block">
      <div class="ac-rules-head">${ICON.get("clipboard", 15)} <span>UMUMIY QOIDALAR</span></div>
      <ul>${general}</ul>
    </div>`;
}
