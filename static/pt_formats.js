// =============================================================
//  pt_formats.js — SHAXSIY turnir formatlari va klub/terma jamoa tanlash (2026-10-07)
//  Formatlar: league (liga — 20/18 klub, 1 yoki 2 doira) | cl | el (8..36, yagona jadval +
//  pley-off) | wc (8..48, 4 kishilik guruhlar, terma jamoalar) | classic (erkin, 128 gacha).
//  Klub logolari/nomlari — rasmiy ligalar ma'lumotidan (api.js LEAGUE_CLUBS, LEAGUE_LOGOS,
//  LEAGUE_TROPHIES), terma jamoalar — worldcup.js WC_GROUPS (bayroqlar).
//  Global: PT, PTT, escHtml, LEAGUE_CLUBS, LEAGUE_LOGOS, LEAGUE_TROPHIES, WC_GROUPS.
// =============================================================

const PT_FORMAT_META = {
  league:  { icon: "🏟", bg: "leagues-banner.jpg", trophy: null },
  cl:      { icon: "⭐", bg: "cl-hero.jpg", trophy: "cl-trophy.png" },
  el:      { icon: "🟠", bg: "el-banner.jpg", trophy: "el-trophy.png" },
  wc:      { icon: "🌍", bg: "worldcup-banner.jpg", trophy: "wc-trophy.png" },
  classic: { icon: "⚔️", bg: "pt-hero.jpg", trophy: null },
};
const PT_FORMAT_ORDER = ["league", "cl", "el", "wc", "classic"];

function ptFmt(x) { return (x && x.format) || "classic"; }
// 2026-10-07: ko'p liga — league_name = "Premier Liga|LaLiga"
function ptLeagues(v) { return Array.isArray(v) ? v.filter(Boolean) : String(v || "").split("|").filter(Boolean); }
function ptLeaguesText(v) { return ptLeagues(v).join(" · "); }
function ptLeagueSize(lg) { return ((PT.config && PT.config.leagues) || {})[lg] || (LEAGUE_CLUBS[lg] || []).length || 0; }
function ptLegsFormat(fmt) { return ((PT.config && PT.config.legs_formats) || ["league", "classic"]).includes(fmt); }
function ptUsesTeams(fmt) { return fmt !== "classic"; }
function ptSingleTable(fmt) { return ["league", "cl", "el"].includes(fmt); }
function ptFormatName(fmt) { return PTT("pt_fmt_" + fmt); }

// Sig'im qoidasi {min, max, step}: server /pt/config'dan (liga — ligadagi klublar soni, qat'iy)
function ptFmtRule(fmt, league) {
  const c = PT.config || {};
  if (fmt === "league") {
    const n = ptLeagues(league).reduce((s, lg) => s + ptLeagueSize(lg), 0) || 20;     // klublar yig'indisi
    return { min: n, max: n, step: 1 };
  }
  const r = (c.formats || {})[fmt];
  if (r) return r;
  return { min: c.min_players || 8, max: c.max_players || 128, step: c.group_size || 4 };
}

// ChL/YeL: to'g'ridan setkaga chiqadiganlar (server pt_formats.cl_direct_count bilan bir xil)
function ptDirectCount(n) { for (const q of [8, 4, 2]) if (3 * q <= n) return q; return 2; }

function ptStageOfSize(size) { return { 64: "r64", 32: "r32", 16: "r16", 8: "qf", 4: "semi" }[size] || "semi"; }

// Yaratish formasi xulosasi: format bo'yicha tur soni va pley-off tuzilishi
function ptFormatSummary(fmt, n, legs) {
  const stage = s => PTT(`pt_stage_${s}`).toLowerCase();
  if (fmt === "league") {
    const lgs = ptLeagues(PT.createLeagues || []);
    const big = Math.max(...lgs.map(ptLeagueSize), 2);
    return lgs.length > 1 ? PTT("pt_sum_leagues", { k: lgs.length, n, rounds: (big - 1) * (legs || 1) })
      : PTT("pt_sum_league", { n, rounds: (n - 1) * (legs || 1) });
  }
  if (fmt === "cl" || fmt === "el") {
    const q = ptDirectCount(n);
    return PTT("pt_sum_cl", { rounds: Math.min(8, n - 1), q, from: q + 1, to: 3 * q, stage: stage(ptStageOfSize(2 * q)) });
  }
  const g = Math.floor(n / 4);
  let size = 4;
  while (size * 2 <= Math.min(2 * g, 64)) size *= 2;
  return PTT("pt_size_summary", { g, stage: stage(ptStageOfSize(size)) })
    + (fmt === "classic" && legs === 2 ? " · " + PTT("pt_sum_classic2") : "");
}

// ---------------- Jamoa ma'lumoti: logo / bayroq ----------------

let PT_TEAM_INDEX = null;   // nom -> {logo} | {flag}
function ptTeamIndex() {
  if (PT_TEAM_INDEX) return PT_TEAM_INDEX;
  PT_TEAM_INDEX = {};
  Object.entries(typeof LEAGUE_CLUBS !== "undefined" ? LEAGUE_CLUBS : {}).forEach(([lg, clubs]) =>
    clubs.forEach(c => { PT_TEAM_INDEX[c.name] = { logo: c.logo, league: lg }; }));
  Object.values(typeof WC_GROUPS !== "undefined" ? WC_GROUPS : {}).forEach(teams =>
    teams.forEach(([name, flag]) => { if (!PT_TEAM_INDEX[name]) PT_TEAM_INDEX[name] = { flag }; }));
  return PT_TEAM_INDEX;
}

function ptTeamBadge(team, cls = "") {
  if (!team) return "";
  const info = ptTeamIndex()[team] || {};
  if (info.logo) return `<img class="pt-tlogo ${cls}" src="${escHtml(info.logo)}" alt="" loading="lazy" onerror="this.style.visibility='hidden'">`;
  if (info.flag) return `<span class="pt-tflag ${cls}">${info.flag}</span>`;
  return "";
}

// Jamoalar ro'yxati (bo'limlarga ajratilgan): [{title, logo, teams:[{name, logo|flag}]}]
function ptTeamSections(fmt, league) {
  const clubs = lg => (LEAGUE_CLUBS[lg] || []).map(c => ({ name: c.name, logo: c.logo }));
  if (fmt === "league") return ptLeagues(league).map(lg => ({ title: lg, logo: (LEAGUE_LOGOS || {})[lg], teams: clubs(lg) }));
  if (fmt === "cl" || fmt === "el") {
    return Object.keys(LEAGUE_CLUBS).map(lg => ({ title: lg, logo: (LEAGUE_LOGOS || {})[lg], teams: clubs(lg) }));
  }
  if (fmt === "wc") {
    const all = Object.values(typeof WC_GROUPS !== "undefined" ? WC_GROUPS : {}).flat()
      .map(([name, flag]) => ({ name, flag })).sort((a, b) => a.name.localeCompare(b.name));
    return [{ title: PTT("pt_fmt_wc"), logo: null, teams: all }];
  }
  return [];
}

// ---------------- Jamoa tanlash oynasi ----------------
// opts: {fmt, league, taken[], mine, id} — tanlangan jamoa PT.teamPick[id] da saqlanadi
function ptTeamPickerHtml(opts) {
  const taken = new Set((opts.taken || []).filter(x => x !== opts.mine));
  const sel = (PT.teamPick || {})[opts.id] || opts.mine || "";
  const q = ((PT.teamSearch || {})[opts.id] || "").toLowerCase();
  const sections = ptTeamSections(opts.fmt, opts.league).map(sec => {
    const items = sec.teams.filter(tm => !q || tm.name.toLowerCase().includes(q))
      .sort((a, b) => taken.has(a.name) - taken.has(b.name)).map(tm => {     // bo'shlari birinchi
      const busy = taken.has(tm.name);
      const icon = tm.logo ? `<img class="pt-tlogo" src="${escHtml(tm.logo)}" alt="" loading="lazy" onerror="this.style.visibility='hidden'">`
        : `<span class="pt-tflag">${tm.flag || ""}</span>`;
      return `<button class="pt-team${busy ? " pt-team--busy" : ""}${tm.name === sel ? " pt-team--sel" : ""}"
          data-pt-team="${escHtml(tm.name)}" data-pt-picker="${opts.id}" ${busy ? "disabled" : ""}>
          ${icon}<span class="pt-team-name">${escHtml(tm.name)}</span>${busy ? `<span class="pt-team-busy">${escHtml(PTT("pt_team_busy"))}</span>` : ""}</button>`;
    }).join("");
    if (!items) return "";
    const head = sec.title && ptTeamSections(opts.fmt, opts.league).length > 1
      ? `<div class="pt-team-sec">${sec.logo ? `<img src="${escHtml(sec.logo)}?v=3" alt="">` : ""}${escHtml(sec.title)}</div>` : "";
    return `${head}<div class="pt-team-grid">${items}</div>`;
  }).join("");
  const search = opts.fmt === "league" && ptLeagues(opts.league).length < 2 ? "" : `<input class="modal-input pt-team-search" data-pt-search="${opts.id}"
      placeholder="${escHtml(PTT("pt_team_search"))}" value="${escHtml((PT.teamSearch || {})[opts.id] || "")}" autocomplete="off">`;
  return `<div class="pt-picker" id="pt-picker-${opts.id}">${search}
      <div class="pt-team-list">${sections || `<div class="empty-state">${escHtml(PTT("pt_team_none"))}</div>`}</div></div>`;
}

// onPick(team) — tanlov o'zgarganda; qidiruv faqat ro'yxatni qayta chizadi (fokus saqlanadi)
function ptBindTeamItems(opts, onPick) {
  const root = document.getElementById(`pt-picker-${opts.id}`);
  root?.querySelectorAll(`[data-pt-picker="${opts.id}"]`).forEach(b => b.addEventListener("click", () => {
    PT.teamPick = { ...(PT.teamPick || {}), [opts.id]: b.dataset.ptTeam };
    root.querySelectorAll(".pt-team--sel").forEach(x => x.classList.remove("pt-team--sel"));
    b.classList.add("pt-team--sel");
    if (onPick) onPick(b.dataset.ptTeam);
  }));
}

function ptBindTeamPicker(opts, onPick) {
  const root = document.getElementById(`pt-picker-${opts.id}`);
  if (!root) return;
  ptBindTeamItems(opts, onPick);
  const input = root.querySelector("[data-pt-search]");
  input?.addEventListener("input", () => {
    PT.teamSearch = { ...(PT.teamSearch || {}), [opts.id]: input.value };
    const tmp = document.createElement("div");
    tmp.innerHTML = ptTeamPickerHtml(opts);
    root.querySelector(".pt-team-list").replaceWith(tmp.querySelector(".pt-team-list"));
    ptBindTeamItems(opts, onPick);
  });
}

// ---------------- Yaratish formasi: format va liga tanlash ----------------

function ptFormatCardsHtml(sel) {
  return `<div class="pt-fmt-grid">${PT_FORMAT_ORDER.map(f => `
      <button class="pt-fmt${f === sel ? " pt-fmt--sel" : ""} pt-fmt--${f}" data-pt-fmt="${f}" style="--pt-fmt-bg:url('${PT_FORMAT_META[f].bg}')">
        <span class="pt-fmt-icon">${PT_FORMAT_META[f].icon}</span>
        <span class="pt-fmt-name">${escHtml(ptFormatName(f))}</span>
        <span class="pt-fmt-sub">${escHtml(PTT("pt_fmt_" + f + "_sub"))}</span>
      </button>`).join("")}</div>`;
}

function ptLeagueCardsHtml(sel) {
  const leagues = Object.keys((PT.config && PT.config.leagues) || LEAGUE_CLUBS);
  const chosen = ptLeagues(sel);                          // ko'p tanlov (2026-10-07)
  return `<div class="pt-league-grid">${leagues.map(lg => `
      <button class="pt-league${chosen.includes(lg) ? " pt-league--sel" : ""}" data-pt-league="${escHtml(lg)}">
        ${(LEAGUE_LOGOS || {})[lg] ? `<img src="${escHtml(LEAGUE_LOGOS[lg])}?v=3" alt="">` : ""}
        <span class="pt-league-name">${escHtml(lg)}</span>
        <span class="pt-league-n">${escHtml(PTT("pt_league_clubs", { n: ((PT.config && PT.config.leagues) || {})[lg] || (LEAGUE_CLUBS[lg] || []).length }))}</span>
      </button>`).join("")}</div>`;
}

function ptLegsHtml(legs) {
  return `<div class="pt-seg pt-legs">${[1, 2].map(n => `
      <button class="tab-btn${n === legs ? " active" : ""}" data-pt-legs="${n}">${escHtml(PTT("pt_legs_" + n))}</button>`).join("")}</div>`;
}

// Sovrin kubogi rasmi (format bo'yicha; liga — o'sha liga kubogi)
function ptTrophySrc(t) {
  const f = ptFmt(t);
  if (f === "league") return (typeof LEAGUE_TROPHIES !== "undefined" && LEAGUE_TROPHIES[ptLeagues(t.league_name)[0]]) || null;
  return PT_FORMAT_META[f] && PT_FORMAT_META[f].trophy;
}

// Jamoa nomi + logo (kartochka, jadval, o'yin kartasi uchun)
function ptTeamLine(team, user) {
  return `${ptTeamBadge(team)}<span class="pt-tname">${escHtml(team || user || "")}</span>`;
}
