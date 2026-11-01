// =============================================================
//  promotion.js — 2-ligadan KO'TARILISH: 1-ligada band joy (2026-11-01)
//  Backend: promotion.py; /profile -> "promotion" {league_id, league_name, from_league, position, expires_at};
//  /leagues -> har ligada "reserved" (band joylar soni, is_full ga allaqachon qo'shilgan).
//  Ko'tarilgan ishtirokchi uchun: o'z 1-ligasi ochiq va tanlangan, bosh sahifada banner.
//  Boshqalar uchun: liga kartasida "🔒 N band".
//  api.js dagi renderLeagues / renderHeroCard qayta tayinlash orqali o'raladi (classic script).
//  index.html da api.js va club_priority.js dan KEYIN ulanadi. Global: APP, escHtml.
// =============================================================

const PROMO_TXT = {
  uz: { banner: "🎉 Siz {from}da {pos}-o'rinni olib, {league}ga ko'tarildingiz!",
        hold: "🔒 Joyingiz {t} gacha band — klub tanlab ro'yxatdan o'ting.", reserved: "🔒 {n} band",
        hold_pending: "🔒 Joyingiz band. Yangi mavsum boshlangach {h} soat ichida klub tanlab ro'yxatdan o'ting." },
  ru: { banner: "🎉 Вы заняли {pos}-е место в {from} и поднялись в {league}!",
        hold: "🔒 Место забронировано до {t} — выберите клуб и зарегистрируйтесь.", reserved: "🔒 {n} брони",
        hold_pending: "🔒 Место забронировано. После старта сезона зарегистрируйтесь в течение {h} ч." },
  en: { banner: "🎉 You finished {pos} in {from} and are promoted to {league}!",
        hold: "🔒 Your place is reserved until {t} — pick a club and register.", reserved: "🔒 {n} reserved",
        hold_pending: "🔒 Your place is reserved. Register within {h} hours after the new season starts." },
};

function promoT(key, vars) {
  const d = PROMO_TXT[APP.lang] || PROMO_TXT.uz;
  return Object.entries(vars || {}).reduce((s, [k, v]) => s.split(`{${k}}`).join(String(v)),
    d[key] || PROMO_TXT.uz[key] || "");
}

// Faol band joy (ro'yxatdan o'tmagan va muddati o'tmagan bo'lsa)
function promoActive() {
  const p = APP.profileData && APP.profileData.promotion;
  if (!p || (APP.profileData && APP.profileData.league_id)) return null;
  if (p.expires_at && Date.parse(p.expires_at) <= Date.now()) return null;
  return p;
}

function promoTime(iso) {
  return typeof clubPrioTime === "function" ? clubPrioTime(iso) : String(iso || "").slice(0, 16).replace("T", " ");
}

function promoRenderNote() {
  let box = document.getElementById("promotion-note");
  if (!box) return;
  const p = promoActive();
  if (!p) { box.classList.add("hidden"); return; }
  box.className = "club-priority-note is-ok";
  box.innerHTML = `<div>${escHtml(promoT("banner", { from: p.from_league, pos: p.position, league: p.league_name }))}</div>`
    + `<small>${escHtml(p.pending ? promoT("hold_pending", { h: p.hold_hours || "" })
                                  : promoT("hold", { t: promoTime(p.expires_at) }))}</small>`;
}

if (typeof renderLeagues === "function") {
  const _promoOrigRenderLeagues = renderLeagues;
  renderLeagues = function (leagues) {
    const p = promoActive();
    if (p) {
      const mine = (leagues || []).find(l => l.id === p.league_id);
      if (mine) {                       // o'z 1-ligasi: band joy uniki — ochiq va tanlangan
        mine.is_full = false;
        mine.is_locked = false;
        APP.selectedLeagueId = mine.id;
      }
    }
    _promoOrigRenderLeagues(leagues);
    (leagues || []).forEach(l => {     // boshqalar uchun band joylar soni liga kartasida
      if (!l.reserved || (p && l.id === p.league_id)) return;
      const cnt = document.querySelector(`.league-item[data-id="${l.id}"] .league-item-count`);
      if (cnt) cnt.textContent += ` · ${promoT("reserved", { n: l.reserved })}`;
    });
    promoRenderNote();
  };
}

if (typeof renderHeroCard === "function") {
  const _promoOrigRenderHero = renderHeroCard;
  renderHeroCard = function (league) {
    // loadHome birinchi ochiq ligani beradi — band joyi bo'lsa o'z 1-ligasi ko'rsatiladi
    const p = promoActive();
    if (p && league && league.id !== p.league_id && APP.selectedLeagueId === p.league_id) {
      league = (APP.leagues || []).find(l => l.id === p.league_id) || league;
    }
    _promoOrigRenderHero(league);
  };
}
