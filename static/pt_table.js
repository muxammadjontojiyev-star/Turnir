// =============================================================
//  pt_table.js — SHAXSIY turnir: yagona jadval (liga / ChL / YeL formatlari, 2026-10-07)
//  Rasmiy turnirlar jadvali kabi: klub logosi + nomi, o'yinchi, O' G D M ± Ochko.
//  Zonalar: ChL/YeL — top-Q to'g'ridan setkaga (yashil), Q+1..3Q pley-off raundi (sariq),
//  qolganlari chiqib ketadi; liga — 1-o'rin chempion (oltin). Qatorni bosish — profil.
//  Global: PT, PTT, escHtml, ptTeamBadge, ptDirectCount.
// =============================================================

// i — jadvaldagi o'rin (0 dan); har liga jadvalida 1-o'rin chempion
function ptZoneOf(p, i) {
  if (p.format === "league") return i === 0 ? "champ" : "";
  const q = p.direct_count || ptDirectCount((Object.values(p.standings || {})[0] || []).length);
  return i < q ? "direct" : i < 3 * q ? "po" : "out";
}

function ptTableHtml(p, meId) {
  if (p.format === "league") return ptLeagueRatingHtml(p, meId);     // rasmiy ligalar Reyting sahifasi kabi
  // 2026-10-07: ko'p ligali turnir — har liga alohida jadval (tanlash tartibida)
  const st = p.standings || {};
  const keys = Object.keys(st).sort((a, b) => {
    const o = p.leagues || [];
    return (o.includes(a) ? o.indexOf(a) : 99) - (o.includes(b) ? o.indexOf(b) : 99);
  });
  return keys.map(k => ptOneTableHtml(p, k, st[k], meId)).join("");
}

function ptOneTableHtml(p, key, rows, meId) {
  const th = k => `<th>${escHtml(PTT(k))}</th>`;
  const body = rows.map((r, i) => {
    const zone = ptZoneOf(p, i);
    const user = r.username ? "@" + r.username : (r.nickname || "");
    return `<tr class="pt-row-link${zone ? " pt-zone-" + zone : ""}${r.user_id === meId ? " pt-row-me" : ""}" data-pt-player="${r.user_id}">
        <td><span class="pt-pos">${i + 1}</span></td>
        <td class="pt-table-name pt-table-club">${r.team_name ? ptTeamBadge(r.team_name) : ""}
          <span class="pt-club-text"><span class="pt-club-name">${escHtml(r.team_name || user)}</span>
          ${r.team_name ? `<span class="pt-club-user">${escHtml(user)}</span>` : ""}</span></td>
        <td>${r.played}</td><td>${r.wins}</td><td>${r.draws}</td><td>${r.losses}</td>
        <td>${r.goal_diff > 0 ? "+" : ""}${r.goal_diff}</td><td><b>${r.points}</b></td></tr>`;
  }).join("");
  const legend = p.format === "league"
    ? `<div class="pt-legend"><span class="pt-lg pt-lg--champ"></span>${escHtml(PTT("pt_zone_champ"))}</div>`
    : `<div class="pt-legend"><span class="pt-lg pt-lg--direct"></span>${escHtml(PTT("pt_zone_direct", { q: p.direct_count || "" }))}
        <span class="pt-lg pt-lg--po"></span>${escHtml(PTT("pt_zone_po", { from: (p.direct_count || 0) + 1, to: 3 * (p.direct_count || 0) }))}</div>`;
  const title = p.format === "league" && key !== "L" ? key : PTT("pt_fmt_" + (p.format || "classic"));
  const logo = p.format === "league" && typeof LEAGUE_LOGOS !== "undefined" && LEAGUE_LOGOS[key]
    ? `<img class="pt-table-lglogo" src="${escHtml(LEAGUE_LOGOS[key])}?v=3" alt="">` : "";
  return `<div class="card pt-table-card pt-table-card--full">
      <div class="pt-table-title">${logo}${escHtml(title)}${p.legs === 2 ? ` · ${escHtml(PTT("pt_legs_2"))}` : ""}</div>
      <div class="pt-table-scroll"><table class="pt-table pt-table--full"><thead><tr><th>#</th><th></th>
        ${th("pt_col_p")}${th("pt_col_w")}${th("pt_col_d")}${th("pt_col_l")}${th("pt_col_gd")}${th("pt_col_pts")}</tr></thead>
        <tbody>${body}</tbody></table></div>${legend}</div>`;
}

// =============================================================
//  2026-10-07: LIGA formati — Reyting rasmiy ligalar sahifasi kabi (api.js renderRatingFilter /
//  renderRatingTable naqshi, o'sha klasslar): liga tablari (logo bilan) + "⚽ To'p urarlar",
//  .rating-table (# · O'yinchi · B G D M GF GA GD), top-3 rang/fon, o'z qatorim (is-me).
//  Bitta liga bo'lsa tablarda faqat o'sha liga va To'p urarlar.
// =============================================================

function ptLgT(key, def) { return (typeof APP !== "undefined" && APP.t && APP.t[key]) || def; }

function ptLeagueKeys(p) {
  const st = p.standings || {}, o = p.leagues || [];
  return Object.keys(st).sort((a, b) => (o.includes(a) ? o.indexOf(a) : 99) - (o.includes(b) ? o.indexOf(b) : 99));
}

function ptPlayerCellHtml(r) {
  const logo = r.team_name ? ptTeamBadge(r.team_name, "pt-rt-logo") : "";
  return `<div class="player-cell">${logo}<div class="player-cell-text">
      <span class="player-clubname">${escHtml(r.team_name || r.nickname || "")}</span>
      ${r.username ? `<span class="player-username">@${escHtml(r.username)}</span>` : ""}</div></div>`;
}

function ptLeagueRatingHtml(p, meId) {
  const keys = ptLeagueKeys(p);
  if (!keys.includes(PT.lgTab) && PT.lgTab !== "scorers") PT.lgTab = keys[0];
  const tab = (id, label, logo) => `<button class="tab-btn${PT.lgTab === id ? " active" : ""}" data-pt-lgtab="${escHtml(id)}">${logo}<span>${escHtml(label)}</span></button>`;
  const tabs = `<div class="tab-filter pt-lg-filter">${keys.map(k => tab(k, k,
      typeof renderLeagueLogo === "function" ? renderLeagueLogo(k, "tab-league-logo") : "")).join("")}
    ${tab("scorers", ptLgT("tab_top_scorers", "⚽ To'p urarlar"), "")}</div>`;
  if (PT.lgTab === "scorers") return tabs + ptScorersHtml(p);
  const rows = (p.standings || {})[PT.lgTab] || [];
  const body = rows.map((r, i) => {
    const rank = i + 1, gd = (r.goal_diff >= 0 ? "+" : "") + r.goal_diff;
    return `<tr class="rating-row${r.user_id === meId ? " is-me" : ""}" data-pt-player="${r.user_id}">
        <td${rank <= 3 ? ` class="rank-${rank}"` : ""}>${rank}</td><td>${ptPlayerCellHtml(r)}</td>
        <td class="pts">${r.points}</td><td>${r.wins}</td><td>${r.draws}</td><td>${r.losses}</td>
        <td>${r.goals_for}</td><td>${r.goals_against}</td><td>${gd}</td></tr>`;
  }).join("");
  return `${tabs}<div class="card card--flat card--table pt-rt-card"><table class="rating-table pt-rating-table">
      <thead><tr><th>#</th><th>${escHtml(ptLgT("th_player", "O'yinchi"))}</th><th>${escHtml(ptLgT("th_pts", "B"))}</th>
        <th>${escHtml(ptLgT("th_w", "G"))}</th><th>${escHtml(ptLgT("th_d", "D"))}</th><th>${escHtml(ptLgT("th_l", "M"))}</th>
        <th>${escHtml(ptLgT("th_gf", "GF"))}</th><th>${escHtml(ptLgT("th_ga", "GA"))}</th><th>${escHtml(ptLgT("th_gd", "GD"))}</th></tr></thead>
      <tbody>${body || `<tr><td colspan="9" class="empty-state">${escHtml(ptLgT("no_data", "Ma'lumot yo'q"))}</td></tr>`}</tbody></table></div>`;
}

// To'p urarlar (rasmiy kabi). 2026-10-08: BARCHA formatlar — jadval/guruh gollari (standings, tasdiqlangan)
// + pley-off gollari (tasdiqlangan o'yinlar). Liga formatida "Liga" ustuni, boshqalarida o'yinlar soni.
function ptScorerRows(p) {
  const by = {};
  Object.entries(p.standings || {}).forEach(([k, rows]) => rows.forEach(r => {
    by[r.user_id] = { ...r, league: k, goals: r.goals_for, games: r.played };
  }));
  (p.knockout || []).filter(m => m.status === "confirmed" && m.score1 != null).forEach(m => {
    [[m.player1_id, m.score1], [m.player2_id, m.score2]].forEach(([uid, g]) => {
      if (!by[uid]) return;
      by[uid].goals += g; by[uid].games += 1;
    });
  });
  return Object.values(by).filter(r => r.goals > 0)
    .sort((a, b) => b.goals - a.goals || a.games - b.games || String(a.team_name || a.nickname).localeCompare(String(b.team_name || b.nickname)));
}

function ptScorersHtml(p) {
  const lg = p.format === "league";
  const all = ptScorerRows(p);
  const body = all.map((r, i) => `<tr class="rating-row${r.user_id === p.me_id ? " is-me" : ""}" data-pt-player="${r.user_id}">
      <td${i < 3 ? ` class="rank-${i + 1}"` : ""}>${i + 1}</td><td>${ptPlayerCellHtml(r)}</td>
      ${lg ? `<td class="pt-rt-league">${typeof renderLeagueLogo === "function" ? renderLeagueLogo(r.league, "tab-league-logo") : ""}${escHtml(r.league)}</td>`
        : `<td>${r.games}</td>`}
      <td class="pts">${r.goals}</td></tr>`).join("");
  const col3 = lg ? ptLgT("th_league", "Liga") : PTT("pt_col_p");
  return `<div class="card card--flat card--table pt-rt-card"><table class="rating-table pt-scorers-table">
      <thead><tr><th>#</th><th>${escHtml(ptLgT("th_player", "O'yinchi"))}</th><th>${escHtml(col3)}</th>
        <th>${escHtml(ptLgT("th_goals_col", "Gol"))}</th></tr></thead>
      <tbody>${body || `<tr><td colspan="4" class="empty-state">${escHtml(PTT("pt_sc_none"))}</td></tr>`}</tbody></table></div>`;
}
