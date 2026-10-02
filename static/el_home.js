// ============================================================
//  el_home.js — YeL "Asosiy" sahifasi (World Cup bosh sahifasi naqshi)
//  el.js dan ajratildi (qoida 21). Global: EL, EL_ROUNDS, EL_TOTAL,
//  escHtml, elClubBadge (el.js), renderEuropaLeague.
// ============================================================

// ---- HOME: WC naqshi (hero + liga bosqichi ishtirokchilari) ----
// Yangi format: guruh yo'q — barcha 36 ishtirokchi yagona ro'yxatda.
function elRenderHome() {
  const g = EL.groups;
  if (!g) return `<div class="card">${ET("el_load_failed")}</div>`;

  if (!g.drawn) return elRenderHomeBeforeDraw();

  const members = g.participants.filter(p => p.group_number);

  const hero = elRenderHero(ET("el_league_phase"), [
    { v: members.length, l: ET("el_stat_clubs") },
    { v: EL_ROUNDS, l: ET("el_stat_rounds") },
    { v: g.el_season ?? 1, l: ET("el_stat_season") },
  ], EL.meParticipant ? ET("el_you_in") : ET("el_you_out"));

  const list = members.length
    ? members.map(p => `
        <div class="match-item el-group-row">
          ${elClubBadge(p.club_name, 26)}
          <b>${escHtml(p.nickname || "")}</b>
        </div>`).join("")
    : `<div class="wc-loading-row">${ET("el_group_empty")}</div>`;

  return `${hero}
    <div class="section-label">${ET("el_participants_label")}</div>
    <div class="matches-list">${list}</div>
    ${elRenderRules()}`;
}

// Hero karta (WC bosh kartasi naqshi: sarlavha + 3 ta stat + holat tugmasi)
function elRenderHero(title, stats, statusText) {
  const cells = stats.map(s => `
    <div class="el-hero-stat">
      <span class="el-hero-stat-value">${escHtml(String(s.v))}</span>
      <span class="el-hero-stat-label">${escHtml(s.l)}</span>
    </div>`).join("");
  return `
    <div class="el-hero">
      <div class="el-hero-overlay">
        <div class="el-hero-kicker">${ICON.get("trophy", 15)} YEVROPA LIGASI</div>
        <div class="el-hero-title">${escHtml(title)}</div>
        <div class="el-hero-stats">${cells}</div>
        <div class="el-hero-status">${escHtml(statusText)}</div>
      </div>
    </div>`;
}

// Qur'agacha: hero + kvalifikantlar ro'yxati
function elRenderHomeBeforeDraw() {
  const qs = (EL.qualifiers && EL.qualifiers.qualifiers) || [];
  const hero = elRenderHero(ET("el_draw_pending"), [
    { v: qs.length, l: ET("el_stat_qualifiers") },
    { v: EL_TOTAL, l: ET("el_stat_clubs") },
    { v: EL_ROUNDS, l: ET("el_stat_rounds") },
  ], EL.meParticipant ? ET("el_you_in") : ET("el_you_out"));

  if (!qs.length) {
    return `${hero}<div class="card">${ET("el_qual_pending")}</div>${elRenderRules()}`;
  }
  const rows = qs.map(q => `
    <div class="match-item el-group-row">
      <b>${escHtml(q.nickname || ET("el_participant"))}</b>
      <span class="el-qual-meta">${escHtml(q.league_name || "")} · ${q.position}-o'rin · ${q.points} ochko</span>
    </div>`).join("");
  return `${hero}
    <div class="section-label">${ET("el_qualifiers_label")} (${qs.length}/${EL_TOTAL})</div>
    <div class="matches-list">${rows}</div>
    ${elRenderRules()}`;
}

// ---- QOIDALAR ----
// Muhim qiymatlar <mark> (el-key) bilan ajratiladi; eng kritik 3 band alohida
// "el-rule--important" kartada (qoida #52: foydalanuvchi jarima olmasligi uchun
// deadline, 0:0 va yopiq tur qoidalari ko'zga tashlanib turishi shart).
function elRenderRules() {
  const key = (v) => `<strong class="rule-hl">${v}</strong>`;

  const important = [
    `Deadline — ${key("23:30")} (Toshkent). Shu vaqtda joriy tur yopiladi va keyingisi ochiladi.`,
    `Deadlinegacha natija kiritilmagan o'yin ${key("0:0 durang")} bilan yopiladi.`,
    `Natijani faqat ${key("ochiq turda")} kiritish mumkin — yopiq turlar qulf belgisi bilan turadi.`,
  ].map(x => `<li>${x}</li>`).join("");

  const general = [
    `Ligalarda ${key("8–14-o'rin")} egallaganlar (ChL'ga o'tgan eng yaxshi 8-o'rindan tashqari) va eng yaxshi ${key("ikkita 15-o'rin")} — jami ${key(EL_TOTAL + " ta")} ishtirokchi qatnashadi.`,
    `Qatnashish huquqi ${key("Telegram akkauntingizga")} beriladi — yangi mavsumda boshqa klub tanlasangiz ham saqlanadi.`,
    `Guruhlar ${key("yo'q")}: barcha ishtirokchi yagona liga bosqichida.`,
    `Har ishtirokchi ${key(EL_ROUNDS + " ta turli raqib")} bilan ${key("1 martadan")} (mehmon o'yinisiz) o'ynaydi.`,
    `Kuniga ${key("bitta tur")} o'ynaladi. Turlar admin ruxsatidan keyin ochiladi.`,
    `Bir tomon kiritgan, ikkinchisi tasdiqlamagan natija deadline'da ${key("avtomatik tasdiqlanadi")}.`,
    `Ochko: g'alaba ${key("3")} · durang ${key("1")} · mag'lubiyat ${key("0")}.`,
    `Saralash: ochko → gol farqi → urilgan gollar.`,
    `${EL_ROUNDS} tur tugagach: ${key("top-8")} to'g'ridan setkaga, ${key("9-24 o'rin")} pley-in (uy+mehmon) o'ynab 8 tasi setkaga qo'shiladi.`,
  ].map(x => `<li>${x}</li>`).join("");

  return `
    <div class="section-label">QOIDALAR</div>
    <div class="card el-rules rules-block el-rules--important">
      <div class="el-rules-head">${ICON.get("megaphone", 15)} <span>MUHIM — ESDA TUTING</span></div>
      <ul>${important}</ul>
    </div>
    <div class="card el-rules rules-block">
      <div class="el-rules-head">${ICON.get("clipboard", 15)} <span>UMUMIY QOIDALAR</span></div>
      <ul>${general}</ul>
    </div>`;
}
