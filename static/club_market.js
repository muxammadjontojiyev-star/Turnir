// =============================================================
//  club_market.js — ligada KLUBNI TOPSHIRISH (2026-10-18)
//  1) Profil (#club-offer-box): "Klubimni topshiraman" tugmachasi (switch). Yoqishdan oldin
//     klub tanlash navbati haqida ogohlantirish (club_priority.js qoidasi).
//  2) Bosh sahifa (#club-market): topshirilayotgan klublar ro'yxati — klubsiz o'yinchi
//     "Olish" bilan klubni (jadval va natijalari bilan) o'ziga rasmiylashtiradi.
//     Shu mavsumda klubini topshirganlar ololmaydi.
//  Backend: club_market.py — GET /club-offers, POST /club-offers/me, POST /club-offers/take.
//  api.js: loadHome -> clubMarketLoad(); loadProfile -> clubOfferBoxLoad().
//  Global: APP, apiFetch, escHtml, showToast, renderLeagueLogo, clubPriorityWaitText, loadHome, loadProfile.
// =============================================================

const CLUB_MKT_TXT = {
  uz: {
    title: "KLUBINI TOPSHIRAYOTGANLAR",
    hint: "Klub yetmay qoldimi? Quyidagi klublardan birini o'zingizga rasmiylashtiring — jadval va natijalari bilan birga.",
    played: "o'yin o'ynalgan", take: "Olish",
    reason_registered: "Siz allaqachon ligada qatnashyapsiz.",
    reason_gave_up: "Shu mavsumda klubingizni topshirgansiz — boshqa klub ola olmaysiz.",
    take_ask: "«{club}» ({league}) klubini o'zingizga rasmiylashtirasizmi?\n\nSiz uning o'rnida jadvaldagi o'rin va natijalar bilan davom etasiz.",
    taken: "✅ «{club}» endi sizniki! Omad!",
    sw_title: "Klubimni topshiraman",
    sw_hint: "Yoqsangiz, klubingiz bosh sahifadagi ro'yxatga chiqadi. Kimdir olsa — siz ligadan chiqasiz.",
    sw_on: "⏳ Klubingiz ro'yxatda. Kimdir olsa, sizga xabar keladi. Fikringiz o'zgarsa — o'chiring.",
    warn: "⚠️ Diqqat!\n\nKlubingizni kimdir olsa, siz mavsumni tashlab ketgan hisoblanasiz va keyingi mavsumda klub tanlash navbatida OXIRGI bo'lasiz (oxirigacha o'ynaganlar va yangilardan keyin).\n\nShu mavsumda boshqa klub ham ololmaysiz.\n\nKlubni topshirishga qo'yasizmi?",
    on_ok: "Klubingiz ro'yxatga qo'yildi", off_ok: "Klubingiz ro'yxatdan olindi",
    errors: { offer_not_found: "Bu klubni kimdir allaqachon oldi", nothing_to_reassign: "Bu klubni kimdir allaqachon oldi",
      already_registered: "Siz allaqachon ligada qatnashyapsiz", gave_up_club: "Shu mavsumda klubingizni topshirgansiz",
      new_already_participant: "Siz allaqachon ligada qatnashyapsiz", not_registered: "Siz ligada ro'yxatda emassiz",
      own_offer: "Bu sizning klubingiz" },
  },
  ru: {
    title: "КЛУБЫ, КОТОРЫЕ ОТДАЮТ",
    hint: "Не хватило клуба? Оформите один из этих клубов на себя — вместе с местом в таблице и результатами.",
    played: "игр сыграно", take: "Взять",
    reason_registered: "Вы уже участвуете в лиге.",
    reason_gave_up: "В этом сезоне вы уже отдали свой клуб — взять другой нельзя.",
    take_ask: "Оформить клуб «{club}» ({league}) на себя?\n\nВы продолжите с его местом и результатами в таблице.",
    taken: "✅ «{club}» теперь ваш! Удачи!",
    sw_title: "Отдаю свой клуб",
    sw_hint: "Если включить, ваш клуб появится в списке на главной. Если его кто-то возьмёт — вы выбываете из лиги.",
    sw_on: "⏳ Ваш клуб в списке. Если его возьмут, придёт сообщение. Передумали — выключите.",
    warn: "⚠️ Внимание!\n\nЕсли ваш клуб кто-то возьмёт, вы будете считаться бросившим сезон и в следующем сезоне выберете клуб ПОСЛЕДНИМ (после доигравших и новых).\n\nВ этом сезоне взять другой клуб тоже нельзя.\n\nВыставить клуб?",
    on_ok: "Клуб выставлен", off_ok: "Клуб снят из списка",
    errors: { offer_not_found: "Этот клуб уже кто-то взял", nothing_to_reassign: "Этот клуб уже кто-то взял",
      already_registered: "Вы уже участвуете в лиге", gave_up_club: "В этом сезоне вы уже отдали клуб",
      new_already_participant: "Вы уже участвуете в лиге", not_registered: "Вы не зарегистрированы в лиге",
      own_offer: "Это ваш клуб" },
  },
  en: {
    title: "CLUBS BEING GIVEN UP",
    hint: "No club left for you? Take one of these clubs — together with its table position and results.",
    played: "games played", take: "Take",
    reason_registered: "You are already in a league.",
    reason_gave_up: "You gave up your club this season — you can't take another.",
    take_ask: "Take over «{club}» ({league})?\n\nYou'll continue with its table position and results.",
    taken: "✅ «{club}» is yours now! Good luck!",
    sw_title: "Give up my club",
    sw_hint: "If on, your club appears in the list on the home page. If someone takes it, you leave the league.",
    sw_on: "⏳ Your club is listed. You'll get a message if someone takes it. Changed your mind — switch off.",
    warn: "⚠️ Attention!\n\nIf someone takes your club, you'll count as having left the season and next season you'll pick a club LAST (after finishers and new players).\n\nYou also can't take another club this season.\n\nList your club?",
    on_ok: "Your club is listed", off_ok: "Your club was removed from the list",
    errors: { offer_not_found: "Someone has already taken this club", nothing_to_reassign: "Someone has already taken this club",
      already_registered: "You are already in a league", gave_up_club: "You gave up your club this season",
      new_already_participant: "You are already in a league", not_registered: "You are not registered in a league",
      own_offer: "This is your club" },
  },
};

const CLUB_MKT = { data: null };

function clubMktT(key, vars) {
  const d = CLUB_MKT_TXT[APP.lang] || CLUB_MKT_TXT.uz;
  let s = d[key] != null ? d[key] : CLUB_MKT_TXT.uz[key];
  if (vars) Object.keys(vars).forEach(k => { s = s.replace(`{${k}}`, vars[k]); });
  return s;
}

function clubMktErr(e) {
  if (e && e.message === "priority_wait" && typeof clubPriorityWaitText === "function") return clubPriorityWaitText();
  const d = (CLUB_MKT_TXT[APP.lang] || CLUB_MKT_TXT.uz).errors;
  return d[e && e.message] || (e && e.message) || "";
}

async function clubMktFetch() {
  try { CLUB_MKT.data = await apiFetch("/club-offers"); }
  catch (_) { CLUB_MKT.data = null; }
  return CLUB_MKT.data;
}

// ---------------------------------------------------------------- bosh sahifa: ro'yxat
async function clubMarketLoad() {
  await clubMktFetch();
  clubMarketRender();
  clubOfferBoxRender();
}

function clubMarketRender() {
  const box = document.getElementById("club-market");
  if (!box) return;
  const d = CLUB_MKT.data;
  const offers = (d && d.offers) || [];
  if (!offers.length) { box.innerHTML = ""; return; }
  const me = d.me || {};
  const note = me.can_take ? "" : `<div class="club-mkt-note">${escHtml(
    me.reason === "gave_up_club" ? clubMktT("reason_gave_up") : clubMktT("reason_registered"))}</div>`;
  const rows = offers.map(o => `<div class="club-mkt-item">
        ${typeof renderLeagueLogo === "function" ? renderLeagueLogo(o.league_name, "club-mkt-logo") : ""}
        <div class="club-mkt-info"><b>${escHtml(o.club_name || "—")}</b>
          <span>${escHtml(o.league_name)} · ${o.played} ${escHtml(clubMktT("played"))}</span></div>
        ${me.can_take ? `<button class="btn btn--primary club-mkt-take" data-club-take="${o.user_id}"
          data-club="${escHtml(o.club_name || "")}" data-league="${escHtml(o.league_name)}">${escHtml(clubMktT("take"))}</button>` : ""}
      </div>`).join("");
  box.innerHTML = `<div class="section-label">${escHtml(clubMktT("title"))} (${offers.length})</div>
    <div class="card club-mkt">
      <div class="club-mkt-hint">${escHtml(clubMktT("hint"))}</div>
      ${note}${rows}
    </div>`;
}

async function clubMarketTake(btn) {
  const vars = { club: btn.dataset.club, league: btn.dataset.league };
  if (!window.confirm(clubMktT("take_ask", vars))) return;
  btn.disabled = true;
  try {
    await apiFetch("/club-offers/take", { method: "POST", body: JSON.stringify({ owner_user_id: +btn.dataset.clubTake }) });
    showToast(clubMktT("taken", vars));
    if (typeof loadHome === "function") await loadHome();
    if (typeof loadProfile === "function") await loadProfile();
  } catch (e) {
    showToast("❌ " + clubMktErr(e));
    btn.disabled = false;
    void clubMarketLoad();
  }
}

// ---------------------------------------------------------------- profil: switch
async function clubOfferBoxLoad() {
  await clubMktFetch();
  clubOfferBoxRender();
}

function clubOfferBoxRender() {
  const box = document.getElementById("club-offer-box");
  if (!box) return;
  const me = CLUB_MKT.data && CLUB_MKT.data.me;
  if (!me || !me.registered) { box.innerHTML = ""; return; }
  box.innerHTML = `<div class="card club-offer${me.offering ? " is-on" : ""}">
      <div class="club-offer-row">
        <div class="club-offer-text"><b>${escHtml(clubMktT("sw_title"))}</b>
          <span>${escHtml(me.club_name || "")} · ${escHtml(me.league_name || "")}</span></div>
        <button class="ui-switch${me.offering ? " is-on" : ""}" role="switch" aria-checked="${me.offering}" data-club-offer-sw><i></i></button>
      </div>
      <div class="club-offer-hint">${escHtml(me.offering ? clubMktT("sw_on") : clubMktT("sw_hint"))}</div>
    </div>`;
}

async function clubOfferToggle(sw) {
  const on = !(CLUB_MKT.data && CLUB_MKT.data.me && CLUB_MKT.data.me.offering);
  if (on && !window.confirm(clubMktT("warn"))) return;
  sw.disabled = true;
  try {
    await apiFetch("/club-offers/me", { method: "POST", body: JSON.stringify({ on }) });
    showToast((on ? "✅ " : "") + clubMktT(on ? "on_ok" : "off_ok"));
  } catch (e) {
    showToast("❌ " + clubMktErr(e));
  }
  await clubMarketLoad();
}

document.addEventListener("click", (e) => {
  if (!e.target.closest) return;
  const t = e.target.closest("[data-club-take]");
  if (t) { void clubMarketTake(t); return; }
  const sw = e.target.closest("[data-club-offer-sw]");
  if (sw) void clubOfferToggle(sw);
});
