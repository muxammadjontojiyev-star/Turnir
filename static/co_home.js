// ============================================================
//  co_home.js — KL "Asosiy" sahifasi (World Cup bosh sahifasi naqshi)
//  co.js dan ajratildi (qoida 21). Global: CO, CO_ROUNDS, CO_TOTAL,
//  escHtml, coClubBadge (co.js), renderConferenceLeague.
// ============================================================

// ---- HOME: WC naqshi (hero + liga bosqichi ishtirokchilari) ----
// Yangi format: guruh yo'q — barcha 36 ishtirokchi yagona ro'yxatda.
function coRenderHome() {
  const g = CO.groups;
  if (!g) return `<div class="card">${COT("co_load_failed")}</div>`;

  if (!g.drawn) return coRenderHomeBeforeDraw();

  const members = g.participants.filter(p => p.group_number);

  const hero = coRenderHero(COT("co_league_phase"), [
    { v: members.length, l: COT("co_stat_clubs") },
    { v: CO_ROUNDS, l: COT("co_stat_rounds") },
    { v: g.co_season ?? 1, l: COT("co_stat_season") },
  ], CO.meParticipant ? COT("co_you_in") : COT("co_you_out"));

  const list = members.length
    ? members.map(p => `
        <div class="match-item co-group-row">
          ${coClubBadge(p.club_name, 26)}
          <b>${escHtml(p.nickname || "")}</b>
        </div>`).join("")
    : `<div class="wc-loading-row">${COT("co_group_empty")}</div>`;

  return `${hero}
    <div class="section-label">${COT("co_participants_label")}</div>
    <div class="matches-list">${list}</div>
    ${coRenderRules()}`;
}

// Hero karta (WC bosh kartasi naqshi: sarlavha + 3 ta stat + holat tugmasi)
function coRenderHero(title, stats, statusText) {
  const cells = stats.map(s => `
    <div class="co-hero-stat">
      <span class="co-hero-stat-value">${escHtml(String(s.v))}</span>
      <span class="co-hero-stat-label">${escHtml(s.l)}</span>
    </div>`).join("");
  return `
    <div class="co-hero">
      <div class="co-hero-overlay">
        <div class="co-hero-kicker">${ICON.get("trophy", 15)} KONFERENSIYA LIGASI</div>
        <div class="co-hero-title">${escHtml(title)}</div>
        <div class="co-hero-stats">${cells}</div>
        <div class="co-hero-status">${escHtml(statusText)}</div>
      </div>
    </div>`;
}

// Qur'agacha: hero + kvalifikantlar ro'yxati
function coRenderHomeBeforeDraw() {
  const qs = (CO.qualifiers && CO.qualifiers.qualifiers) || [];
  const hero = coRenderHero(COT("co_draw_pending"), [
    { v: qs.length, l: COT("co_stat_qualifiers") },
    { v: CO_TOTAL, l: COT("co_stat_clubs") },
    { v: CO_ROUNDS, l: COT("co_stat_rounds") },
  ], CO.meParticipant ? COT("co_you_in") : COT("co_you_out"));

  if (!qs.length) {
    return `${hero}<div class="card">${COT("co_qual_pending")}</div>${coRenderRules()}`;
  }
  const rows = qs.map(q => `
    <div class="match-item co-group-row">
      <b>${escHtml(q.nickname || COT("co_participant"))}</b>
      <span class="co-qual-meta">${escHtml(q.league_name || "")} · ${q.position}-o'rin · ${q.points} ochko</span>
    </div>`).join("");
  return `${hero}
    <div class="section-label">${COT("co_qualifiers_label")} (${qs.length}/${CO_TOTAL})</div>
    <div class="matches-list">${rows}</div>
    ${coRenderRules()}`;
}

// ---- QOIDALAR ----
// Muhim qiymatlar <mark> (co-key) bilan ajratiladi; eng kritik 3 band alohida
// "co-rule--important" kartada (qoida #52: foydalanuvchi jarima olmasligi uchun
// deadline, 0:0 va yopiq tur qoidalari ko'zga tashlanib turishi shart).
function coRenderRules() {
  const key = (v) => `<strong class="rule-hl">${v}</strong>`;

  const important = [
    `Deadline — ${key("23:30")} (Toshkent). Shu vaqtda joriy tur yopiladi va keyingisi ochiladi.`,
    `Deadlinegacha natija kiritilmagan o'yin ${key("0:0 durang")} bilan yopiladi.`,
    `Natijani faqat ${key("ochiq turda")} kiritish mumkin — yopiq turlar qulf belgisi bilan turadi.`,
  ].map(x => `<li>${x}</li>`).join("");

  const general = [
    // 2026-11-01: 13 ta Yevropa ligasi, YeL o'rinlaridan keyingilar (co_qualification.CO_QUOTAS)
    `${key("13 ta Yevropa ligasi")}da YeL o'rinlaridan keyingilar: katta 5 liga — ${key("9–12-o'rin")}, Portugaliya, Niderlandiya — ${key("7–9")}, Belgiya, Turkiya, Chexiya, Rossiya — ${key("5–6")}, Norvegiya, Gretsiya — ${key("3-o'rin")} — jami ${key(CO_TOTAL + " ta")} ishtirokchi qatnashadi. Osiyo ligalari kirmaydi.`,
    `Qatnashish huquqi ${key("Telegram akkauntingizga")} beriladi — yangi mavsumda boshqa klub tanlasangiz ham saqlanadi.`,
    `Guruhlar ${key("yo'q")}: barcha ishtirokchi yagona liga bosqichida.`,
    `Har ishtirokchi ${key(CO_ROUNDS + " ta turli raqib")} bilan ${key("1 martadan")} (mehmon o'yinisiz) o'ynaydi.`,
    `Kuniga ${key("bitta tur")} o'ynaladi. Turlar admin ruxsatidan keyin ochiladi.`,
    `Bir tomon kiritgan, ikkinchisi tasdiqlamagan natija deadline'da ${key("avtomatik tasdiqlanadi")}.`,
    `Ochko: g'alaba ${key("3")} · durang ${key("1")} · mag'lubiyat ${key("0")}.`,
    `Saralash: ochko → gol farqi → urilgan gollar.`,
    `${CO_ROUNDS} tur tugagach: ${key("top-8")} to'g'ridan setkaga, ${key("9-24 o'rin")} pley-in (uy+mehmon) o'ynab 8 tasi setkaga qo'shiladi.`,
  ].map(x => `<li>${x}</li>`).join("");

  return `
    <div class="section-label">QOIDALAR</div>
    <div class="card co-rules rules-block co-rules--important">
      <div class="co-rules-head">${ICON.get("megaphone", 15)} <span>MUHIM — ESDA TUTING</span></div>
      <ul>${important}</ul>
    </div>
    <div class="card co-rules rules-block">
      <div class="co-rules-head">${ICON.get("clipboard", 15)} <span>UMUMIY QOIDALAR</span></div>
      <ul>${general}</ul>
    </div>`;
}
