/**
 * league_tiers.js — rasmiy ligalarning darajalari (2026-10-10).
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

// 2026-10-14: Yevropa kuboklariga yo'llanma zonalari (o'rin raqami rangli belgi bilan).
// Backend bilan bir xil: cl_qualification.CL_LEAGUES / CL_TOP_N, el_qualification.EL_*_POS.
const EURO_QUAL_LEAGUES = ["LaLiga", "Premier Liga", "Bundesliga", "Serie A", "Ligue 1", "Liga Portugal", "Süper Lig"];
const EQ_CL_TOP  = 5;    // 1–5: Chempionlar ligasi
const EQ_CL_BEST = 6;    // 6-o'rin: 7 liga ichida eng yaxshisi — ChL, qolganlari — YeL
const EQ_EL_LAST = 10;   // 6–10: Yevropa ligasi
const EQ_EL_BEST = 11;   // 11-o'rin: 7 liga ichida eng yaxshi 2 tasi — YeL
// 2026-10-15: Osiyo Chempionlar ligasi — 4 ta Osiyo ligasidan top-8
// (backend: ac_qualification.AC_LEAGUES / AC_TOP_N)
const ASIA_QUAL_LEAGUES = ["Superliga", "Saudi Pro Liga", "UAE Pro Liga", "J1 Liga"];
const AQ_TOP = 8;

const TIER_TEXTS = {
  uz: { zone_cl: "Chempionlar ligasi", zone_clx: "6-o'rin: eng yaxshisi ChL, qolganlari YeL", zone_el: "Yevropa ligasi", zone_elx: "11-o'rin: eng yaxshi 2 tasi YeL", zone_acl: "Osiyo Chempionlar ligasi",
        tier1_tab: "1-ligalar", tier2_tab: "2-ligalar",
        zone_releg: "Quyi ligaga tushish zonasi", zone_promo: "Yuqori ligaga ko'tarilish zonasi" },
  ru: { zone_cl: "Лига чемпионов", zone_clx: "6-е место: лучшее — ЛЧ, остальные — ЛЕ", zone_el: "Лига Европы", zone_elx: "11-е место: 2 лучших — ЛЕ", zone_acl: "Азиатская лига чемпионов",
        tier1_tab: "Высшие лиги", tier2_tab: "Вторые лиги",
        zone_releg: "Зона вылета", zone_promo: "Зона повышения" },
  en: { zone_cl: "Champions League", zone_clx: "6th: best one UCL, others UEL", zone_el: "Europa League", zone_elx: "11th: best two UEL", zone_acl: "Asian Champions League",
        tier1_tab: "Top divisions", tier2_tab: "Second divisions",
        zone_releg: "Relegation zone", zone_promo: "Promotion zone" },
};
if (typeof TEXTS !== "undefined") {
  for (const lang of ["uz", "ru", "en"]) {
    if (TEXTS[lang]) Object.assign(TEXTS[lang], TIER_TEXTS[lang]);
  }
}

function leagueTier(name) {
  return LEAGUE_SECOND_TIERS[name] ? 2 : 1;
}

function hasSecondTierLeagues() {
  return (APP.leagues || []).some(l => leagueTier(l.name) === 2);
}

// Liga uchun zona: {releg: 18 (shu o'rindan pastga — tushish)} yoki {promo: 3} yoki {}
function leagueZones(league) {
  if (!league) return {};
  if (leagueTier(league.name) === 2) return { promo: LEAGUE_ZONE_SIZE };
  const zones = {};
  if (EURO_QUAL_LEAGUES.includes(league.name)) zones.euro = true;   // 2026-10-14
  if (ASIA_QUAL_LEAGUES.includes(league.name)) zones.asia = true;   // 2026-10-15
  const hasLower = Object.values(LEAGUE_SECOND_TIERS).includes(league.name);
  if (hasLower && league.max_players > LEAGUE_ZONE_SIZE) {
    zones.releg = league.max_players - LEAGUE_ZONE_SIZE + 1;
  }
  return zones;
}

// 2026-10-14: o'rin raqami belgisi klassi (Yevropa ligalarida) — yo'q bo'lsa ""
function ratingRankBadgeClass(rank, zones) {
  if (zones && zones.asia) return rank <= AQ_TOP ? "rk rk--acl" : "";   // 2026-10-15
  if (!zones || !zones.euro) return "";
  if (rank <= EQ_CL_TOP) return "rk rk--cl";
  if (rank === EQ_CL_BEST) return "rk rk--clx";
  if (rank <= EQ_EL_LAST) return "rk rk--el";
  if (rank === EQ_EL_BEST) return "rk rk--elx";
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
  if (zones.euro) {
    items.push(`<span class="zl-item"><i class="rk rk--cl zl-rk">1</i>${escHtml(t.zone_cl || "")} (1–${EQ_CL_TOP})</span>`);
    items.push(`<span class="zl-item"><i class="rk rk--el zl-rk">${EQ_CL_BEST + 1}</i>${escHtml(t.zone_el || "")} (${EQ_CL_BEST}–${EQ_EL_LAST})</span>`);
    items.push(`<span class="zl-item"><i class="rk rk--clx zl-rk">${EQ_CL_BEST}</i>${escHtml(t.zone_clx || "")}</span>`);
    items.push(`<span class="zl-item"><i class="rk rk--elx zl-rk">${EQ_EL_BEST}</i>${escHtml(t.zone_elx || "")}</span>`);
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
