// =============================================================
//  guide_bot_live.js — «Robi» BOTDAGI HOZIRGI HOLATGA qarab javob beradi (2026-11-03)
//  Bilimlar bazasidagi «dyn» belgili savollar (guide_bot_faq_*.js) uchun serverdan jonli holat olinadi:
//    GET /leagues (bo'sh joylar, navbat), /profile (allaqachon ro'yxatdami), /season/current (tanaffus),
//    /club-offers (topshirilayotgan klublar), /club-priority/me (klub tanlash navbati).
//  dyn "spots" — bo'sh joy bor ligalar; joy bo'lmasa — topshirilayotgan klubni olish yo'li + Divizion va
//  Tezkor o'yin tavsiyasi. dyn "market" — topshirilayotgan klublar soni. Matnlar — GBOT_FAQ[lang].live.
//  Qaytaradi: { text, chips: [faq id] }. Xato bo'lsa — live.error. Holat GBOT_LIVE_TTL_MS keshlanadi.
//  Global: APP, apiFetch, gbotFaqData. guide_bot_ask.js chaqiradi.
// =============================================================

const GBOT_LIVE = { at: 0, st: null };
const GBOT_LIVE_TTL_MS = 20000;
const GBOT_LIVE_MAX_LINES = 5;            // bo'sh joyli ligalar ro'yxati — ko'pi bilan
const GBOT_LIVE_REGIONS = ["eu", "asia", "sa", "na"];
const GBOT_LIVE_RECOMMEND = ["div_how", "qm"];   // joy bo'lmasa — tavsiya tugmalari

async function gbotLiveState() {
  if (GBOT_LIVE.st && Date.now() - GBOT_LIVE.at < GBOT_LIVE_TTL_MS) return GBOT_LIVE.st;
  const get = (p) => apiFetch(p).catch(() => null);
  const [leagues, profile, season, offers, prio] = await Promise.all([
    get("/leagues"), get("/profile"), get("/season/current"), get("/club-offers"), get("/club-priority/me")]);
  if (!Array.isArray(leagues)) return null;
  GBOT_LIVE.st = { leagues, profile, season, offers, prio };
  GBOT_LIVE.at = Date.now();
  return GBOT_LIVE.st;
}

function gbotLiveFill(s, vars) {
  return Object.keys(vars || {}).reduce((t, k) => t.split(`{${k}}`).join(String(vars[k])), s);
}

function gbotLiveTime(iso) {
  return typeof clubPrioTime === "function" ? clubPrioTime(iso) : String(iso || "").slice(0, 16).replace("T", " ");
}

// Topshirilayotgan klublar haqida qism (joy yo'q bo'lsa yoki «market» savolida)
function gbotLiveMarket(st, L) {
  const list = (st.offers && st.offers.offers) || [];
  if (!list.length) return L.market_none;
  const me = (st.offers && st.offers.me) || {};
  let t = gbotLiveFill(L.market_yes, { n: list.length });
  if (me.can_take === false && me.reason === "gave_up_club") t += " " + L.market_gave_up;
  return t;
}

function gbotLiveSpots(st, L) {
  const p = st.profile || {};
  if (p.league_id) {
    const lg = st.leagues.find(l => l.id === p.league_id);
    return { text: gbotLiveFill(L.registered, { league: lg ? lg.name : "—", club: p.club_name || "—" }), chips: [] };
  }
  if (st.season && st.season.league_break) {
    return { text: L.season_break + "\n\n" + L.recommend, chips: GBOT_LIVE_RECOMMEND };
  }
  const open = st.leagues
    .filter(l => !l.is_locked && !l.is_full)
    .map(l => ({ ...l, free: Math.max(0, l.max_players - l.current_players - (l.reserved || 0)) }))
    .filter(l => l.free > 0)
    .sort((a, b) => GBOT_LIVE_REGIONS.indexOf(a.region || "eu") - GBOT_LIVE_REGIONS.indexOf(b.region || "eu"));
  if (!open.length) {
    return { text: [L.full, gbotLiveMarket(st, L), L.recommend].join("\n\n"), chips: GBOT_LIVE_RECOMMEND };
  }
  const lines = open.slice(0, GBOT_LIVE_MAX_LINES).map(l =>
    gbotLiveFill(L.spot_line, { region: L.regions[l.region || "eu"] || "", league: l.name, n: l.free }));
  if (open.length > GBOT_LIVE_MAX_LINES) lines.push(gbotLiveFill(L.spot_more, { n: open.length - GBOT_LIVE_MAX_LINES }));
  let text = L.spots_head + "\n" + lines.join("\n") + "\n\n" + L.spots_how;
  const pr = st.prio || {};
  if (pr.active && !pr.open && pr.opens_at) text += "\n" + gbotLiveFill(L.prio_wait, { t: gbotLiveTime(pr.opens_at) });
  return { text, chips: [] };
}

// dyn savol uchun jonli matn: { text, chips }
async function gbotLiveAnswer(kind, lang) {
  const L = gbotFaqData(lang).live;
  const st = await gbotLiveState();
  if (!st) return { text: L.error, chips: [] };
  if (kind === "market") {
    const list = (st.offers && st.offers.offers) || [];
    if (list.length) return { text: gbotLiveFill(L.market_now, { n: list.length }), chips: [] };
    return { text: L.market_empty + "\n\n" + L.recommend, chips: GBOT_LIVE_RECOMMEND };
  }
  return gbotLiveSpots(st, L);
}
