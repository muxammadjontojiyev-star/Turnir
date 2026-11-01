/**
 * league_tiers.js — rasmiy ligalarning darajalari (2026-10-10).
 * 2026-11-01: reyting tablari endi MINTAQA bo'yicha — «🌍 Yevropa | 🌏 Osiyo» (liga.region, /leagues);
 *   2-ligalar nofaol (botda ko'rinmaydi) — ular yoqilsa zonalar avvalgidek ishlaydi.
 *   Yevropa kuboklari zonalari — har ligaga o'z kvotasi (EURO_QUOTAS, backend cl_qualification bilan bir xil).
 *
 * Reyting sahifasida ligalar ikki guruh tabiga ajratiladi: "1-ligalar" va "2-ligalar".
 * 2-darajali liga va uning 1-ligasi LEAGUE_SECOND_TIERS'da (kalit/qiymat = DB liga nomi).
 * Zonalar (faqat KO'RINISH — odamlarni ko'chirish yo'q):
 *   - 2-ligasi bor 1-liga: oxirgi LEAGUE_ZONE_SIZE o'rin (20 kishida 18-20) — qizil chiziq ostida;
 *   - 2-liga: birinchi LEAGUE_ZONE_SIZE o'rin (1-3) — yashil chiziq ustida.
 * Chiziqlar style.css dagi mavjud .cl-cut-red / .cl-cut-green klasslari (ChL reytingi bilan DRY).
 * Global: APP, escHtml, renderLeagueLogo (api.js), TEXTS (app.js).
 * MUHIM: index.html da app.js dan KEYIN ulanadi (TEXTS ga tarjima qo'shadi).
 */

// 2-liga nomi -> uning 1-ligasi (yangi 2-liga qo'shilsa — faqat shu yerga bir qator)
const LEAGUE_SECOND_TIERS = {
  "LaLiga 2": "LaLiga",
  "Championship": "Premier Liga",
  "2. Bundesliga": "Bundesliga",   // 2026-10-13
  "Serie B": "Serie A",            // 2026-10-13
  "Ligue 2": "Ligue 1",            // 2026-10-14
  "Liga Portugal 2": "Liga Portugal",   // 2026-10-15
};
const LEAGUE_ZONE_SIZE = 3;   // tushish / ko'tarilish zonasidagi o'rinlar soni

// 2026-11-01: Yevropa kuboklariga yo'llanma — LIGA KUCHIGA qarab: liga -> [ChL o'rinlari, YeL o'rinlari]
// (1..cl — ChL, cl+1..cl+el — YeL). Backend bilan bir xil: cl_qualification.EURO_QUOTAS.
const EURO_QUOTAS = {
  "LaLiga": [4, 4], "Premier Liga": [4, 4], "Bundesliga": [4, 4], "Serie A": [4, 4], "Ligue 1": [4, 4],
  "Liga Portugal": [3, 3], "Eredivisie": [3, 3],
  "Jupiler Pro League": [2, 2], "Süper Lig": [2, 2], "Chance Liga": [2, 2], "RPL": [2, 2],
  "Eliteserien": [1, 1], "Greek Super League": [1, 1],
};
const EURO_QUAL_LEAGUES = Object.keys(EURO_QUOTAS);
// 2026-11-01: Konferensiya ligasi — YeL o'rinlaridan keyin (backend: co_qualification.CO_QUOTAS)
const CO_QUOTAS = {
  "LaLiga": 4, "Premier Liga": 4, "Bundesliga": 4, "Serie A": 4, "Ligue 1": 4,
  "Liga Portugal": 3, "Eredivisie": 3,
  "Jupiler Pro League": 2, "Süper Lig": 2, "Chance Liga": 2, "RPL": 2,
  "Eliteserien": 1, "Greek Super League": 1,
};
// 2026-10-15: Osiyo Chempionlar ligasi — 4 ta Osiyo ligasidan top-8
// (backend: ac_qualification.AC_LEAGUES / AC_TOP_N)
const ASIA_QUAL_LEAGUES = ["Superliga", "Saudi Pro Liga", "UAE Pro Liga", "J1 Liga"];
const AQ_TOP = 8;

const TIER_TEXTS = {
  uz: { zone_cl: "Chempionlar ligasi", zone_clx: "6-o'rin: eng yaxshisi ChL, qolganlari YeL", zone_el: "Yevropa ligasi", zone_co: "Konferensiya ligasi", zone_elx: "11-o'rin: eng yaxshi 2 tasi YeL", zone_acl: "Osiyo Chempionlar ligasi",
        tier1_tab: "🌍 Yevropa", tier2_tab: "🌏 Osiyo",
        zone_releg: "Quyi ligaga tushish zonasi", zone_promo: "Yuqori ligaga ko'tarilish zonasi" },
  ru: { zone_cl: "Лига чемпионов", zone_clx: "6-е место: лучшее — ЛЧ, остальные — ЛЕ", zone_el: "Лига Европы", zone_co: "Лига конференций", zone_elx: "11-е место: 2 лучших — ЛЕ", zone_acl: "Азиатская лига чемпионов",
        tier1_tab: "🌍 Европа", tier2_tab: "🌏 Азия",
        zone_releg: "Зона вылета", zone_promo: "Зона повышения" },
  en: { zone_cl: "Champions League", zone_clx: "6th: best one UCL, others UEL", zone_el: "Europa League", zone_co: "Conference League", zone_elx: "11th: best two UEL", zone_acl: "Asian Champions League",
        tier1_tab: "🌍 Europe", tier2_tab: "🌏 Asia",
        zone_releg: "Relegation zone", zone_promo: "Promotion zone" },
};
if (typeof TEXTS !== "undefined") {
  for (const lang of ["uz", "ru", "en"]) {
    if (TEXTS[lang]) Object.assign(TEXTS[lang], TIER_TEXTS[lang]);
  }
}

// 2-darajali liga (nofaol bo'lsa APP.leagues da yo'q — zonalar chizilmaydi)
function isSecondTier(name) {
  return !!LEAGUE_SECOND_TIERS[name];
}

// 2026-11-01: reyting tab guruhi — 1 = Yevropa, 2 = Osiyo (liga.region; zaxira — Osiyo ro'yxati).
// (Nomi tarixiy: api.js renderRatingFilter shu funksiyani chaqiradi.)
function leagueTier(name) {
  const lg = (APP.leagues || []).find(l => l.name === name);
  const region = (lg && lg.region) || (ASIA_QUAL_LEAGUES.includes(name) ? "asia" : "eu");
  return region === "asia" ? 2 : 1;
}

function hasSecondTierLeagues() {   // ikkala mintaqa ham bor bo'lsa — tablar chiziladi
  const g = new Set((APP.leagues || []).map(l => leagueTier(l.name)));
  return g.size > 1;
}

// Liga uchun zona: {releg: 18 (shu o'rindan pastga — tushish)} yoki {promo: 3} yoki {}
function leagueZones(league) {
  if (!league) return {};
  if (isSecondTier(league.name)) return { promo: LEAGUE_ZONE_SIZE };
  const zones = {};
  if (EURO_QUOTAS[league.name]) zones.euro = [...EURO_QUOTAS[league.name], CO_QUOTAS[league.name] || 0];   // 2026-11-01: [cl, el, co]
  if (ASIA_QUAL_LEAGUES.includes(league.name)) zones.asia = true;   // 2026-10-15
  // 2026-11-01: tushish zonasi — faqat 2-ligasi FAOL bo'lsa (APP.leagues da bor)
  const hasLower = Object.entries(LEAGUE_SECOND_TIERS)
    .some(([low, up]) => up === league.name && (APP.leagues || []).some(l => l.name === low));
  if (hasLower && league.max_players > LEAGUE_ZONE_SIZE) {
    zones.releg = league.max_players - LEAGUE_ZONE_SIZE + 1;
  }
  return zones;
}

// 2026-10-14: o'rin raqami belgisi klassi (Yevropa ligalarida) — yo'q bo'lsa ""
function ratingRankBadgeClass(rank, zones) {
  if (zones && zones.asia) return rank <= AQ_TOP ? "rk rk--acl" : "";   // 2026-10-15
  if (!zones || !zones.euro) return "";
  const [cl, el, co] = zones.euro;
  if (rank <= cl) return "rk rk--cl";
  if (rank <= cl + el) return "rk rk--el";
  if (rank <= cl + el + (co || 0)) return "rk rk--co";   // 2026-11-01: Konferensiya ligasi
  return "";
}

// Qator uchun chegara klassi: chiziq qatorning PASTKI chetida chiziladi —
// tushish: zonadan oldingi qator (17-o'rin), ko'tarilish: zonaning oxirgi qatori (3-o'rin).
function ratingZoneRowClass(rank, total, zones) {
  if (zones.promo && rank === zones.promo && total > rank) return "cl-cut-green";
  if (zones.releg && rank === zones.releg - 1 && total >= zones.releg) return "cl-cut-red";
  return "";
}

// Jadval ostidagi izoh (zona bo'lsa ko'rsatiladi, aks holda yashiriladi)
function renderRatingZoneLegend(zones) {
  const card = document.getElementById("rating-card");
  if (!card) return;
  let el = document.getElementById("rating-zone-legend");
  if (!el) {
    el = document.createElement("div");
    el.id = "rating-zone-legend";
    el.className = "rating-zone-legend";
    card.insertAdjacentElement("afterend", el);
  }
  const t = APP.t || {};
  const items = [];
  if (zones.asia) {   // 2026-10-15
    items.push(`<span class="zl-item"><i class="rk rk--acl zl-rk">1</i>${escHtml(t.zone_acl || "")} (1–${AQ_TOP})</span>`);
  }
  if (zones.euro) {   // 2026-11-01: ligaga o'z kvotasi
    const [cl, el, co] = zones.euro;
    const range = (a, b) => (a === b ? `${a}` : `${a}–${b}`);
    items.push(`<span class="zl-item"><i class="rk rk--cl zl-rk">1</i>${escHtml(t.zone_cl || "")} (${range(1, cl)})</span>`);
    items.push(`<span class="zl-item"><i class="rk rk--el zl-rk">${cl + 1}</i>${escHtml(t.zone_el || "")} (${range(cl + 1, cl + el)})</span>`);
    if (co) items.push(`<span class="zl-item"><i class="rk rk--co zl-rk">${cl + el + 1}</i>${escHtml(t.zone_co || "Konferensiya ligasi")} (${range(cl + el + 1, cl + el + co)})</span>`);
  }
  if (zones.promo) items.push(`<span class="zl-item"><i class="zl-sw zl-sw--promo"></i>${escHtml(t.zone_promo || "")} (1–${zones.promo})</span>`);
  if (zones.releg) items.push(`<span class="zl-item"><i class="zl-sw zl-sw--releg"></i>${escHtml(t.zone_releg || "")}</span>`);
  el.innerHTML = items.join("");
  el.classList.toggle("hidden", items.length === 0 || APP.ratingTab !== "league");
}

// "1-ligalar | 2-ligalar" guruh tablari (2-liga bo'lmasa — chizilmaydi).
// onSelect(tier) — tanlangan guruhning birinchi ligasini ochish (api.js).
function renderRatingTierTabs(container, onSelect) {
  if (!hasSecondTierLeagues()) return;
  const t = APP.t || {};
  const row = document.createElement("div");
  row.className = "tier-tabs";
  [[1, t.tier1_tab || "1"], [2, t.tier2_tab || "2"]].forEach(([tier, label]) => {
    const b = document.createElement("button");
    b.className = "tier-tab" + (APP.ratingTier === tier ? " active" : "");
    b.textContent = label;
    b.addEventListener("click", () => { if (APP.ratingTier !== tier) onSelect(tier); });
    row.appendChild(b);
  });
  container.appendChild(row);
}
