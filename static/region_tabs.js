// =============================================================
//  region_tabs.js — BOSH SAHIFA: ligalar «🌍 Yevropa | 🌏 Osiyo | 🌎 J. Amerika» tablarida (2026-11-01; J. Amerika — 2026-11-02)
//  /leagues har ligada "region" ('eu' | 'asia') qaytaradi; navbat bilan ochilish har mintaqada alohida.
//  Tab — faqat ikkala mintaqa bo'lsa. Tanlangan mintaqa: ko'tarilgan bo'lsa — o'z ligasi mintaqasi,
//  aks holda oxirgi tanlangan / tanlangan liganing mintaqasi.
//  Reyting sahifasidagi tablar — league_tiers.js (leagueTier: 1 = Yevropa, 2 = Osiyo).
//  api.js renderLeagues / renderHeroCard qayta tayinlash orqali o'raladi (promotion.js, season_break.js
//  dan KEYIN ulanadi). Tab matnlari — TEXTS.tier1_tab / tier2_tab (league_tiers.js). Global: APP.
// =============================================================

const REGION_ORDER = ["eu", "asia", "sa"];   // 2026-11-02: + Janubiy Amerika

function regionOf(league) {
  return (league && league.region) || "eu";
}

function regionPick(leagues) {
  const promo = typeof promoActive === "function" ? promoActive() : null;
  const byId = id => leagues.find(l => l.id === id);
  if (promo && byId(promo.league_id)) return regionOf(byId(promo.league_id));
  if (APP.homeRegion && leagues.some(l => regionOf(l) === APP.homeRegion)) return APP.homeRegion;
  return regionOf(byId(APP.selectedLeagueId) || leagues[0]);
}

function regionRenderTabs(regions) {
  let row = document.getElementById("home-region-tabs");
  const list = document.getElementById("leagues-list");
  if (!list) return;
  if (!row) {
    row = document.createElement("div");
    row.id = "home-region-tabs";
    row.className = "tier-tabs";
    list.parentNode.insertBefore(row, list);
  }
  row.classList.toggle("hidden", regions.length < 2);
  const t = APP.t || {};
  row.innerHTML = "";
  regions.forEach(r => {
    const b = document.createElement("button");
    b.className = "tier-tab" + (APP.homeRegion === r ? " active" : "");
    b.textContent = r === "asia" ? (t.tier2_tab || "Osiyo") : r === "sa" ? (t.tier3_tab || "J. Amerika") : (t.tier1_tab || "Yevropa");
    b.addEventListener("click", () => {
      if (APP.homeRegion === r) return;
      APP.homeRegion = r;
      APP.selectedLeagueId = null;          // yangi mintaqada birinchi ochiq liga tanlanadi
      APP.selectedClub = null;
      renderLeagues(APP.leagues || []);
      const sel = (APP.leagues || []).find(l => l.id === APP.selectedLeagueId);
      if (sel) renderHeroCard(sel);
    });
    row.appendChild(b);
  });
}

if (typeof renderLeagues === "function") {
  const _regionOrigRender = renderLeagues;
  renderLeagues = function (leagues) {
    const all = leagues || [];
    const regions = REGION_ORDER.filter(r => all.some(l => regionOf(l) === r));
    if (regions.length < 2) { regionRenderTabs(regions); _regionOrigRender(all); return; }
    APP.homeRegion = regionPick(all);
    const shown = all.filter(l => regionOf(l) === APP.homeRegion);
    if (!shown.some(l => l.id === APP.selectedLeagueId)) {
      const open = shown.find(l => !l.is_locked && !l.is_full) || shown[0];
      APP.selectedLeagueId = open ? open.id : null;
    }
    regionRenderTabs(regions);
    _regionOrigRender(shown);
  };
}

if (typeof renderHeroCard === "function") {
  const _regionOrigHero = renderHeroCard;
  renderHeroCard = function (league) {
    // loadHome barcha ligalardan birinchi ochig'ini beradi — karta tanlangan (shu mintaqadagi) ligani ko'rsatsin
    if (league && APP.selectedLeagueId && league.id !== APP.selectedLeagueId) {
      league = (APP.leagues || []).find(l => l.id === APP.selectedLeagueId) || league;
    }
    _regionOrigHero(league);
  };
}
