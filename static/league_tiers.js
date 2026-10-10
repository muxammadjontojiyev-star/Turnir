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
};
const LEAGUE_ZONE_SIZE = 3;   // tushish / ko'tarilish zonasidagi o'rinlar soni

const TIER_TEXTS = {
  uz: { tier1_tab: "1-ligalar", tier2_tab: "2-ligalar",
        zone_releg: "Quyi ligaga tushish zonasi", zone_promo: "Yuqori ligaga ko'tarilish zonasi" },
  ru: { tier1_tab: "Высшие лиги", tier2_tab: "Вторые лиги",
        zone_releg: "Зона вылета", zone_promo: "Зона повышения" },
  en: { tier1_tab: "Top divisions", tier2_tab: "Second divisions",
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
  const hasLower = Object.values(LEAGUE_SECOND_TIERS).includes(league.name);
  if (hasLower && league.max_players > LEAGUE_ZONE_SIZE) {
    return { releg: league.max_players - LEAGUE_ZONE_SIZE + 1 };
  }
  return {};
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
