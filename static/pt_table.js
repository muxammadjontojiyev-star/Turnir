// =============================================================
//  pt_table.js — SHAXSIY turnir: yagona jadval (liga / ChL / YeL formatlari, 2026-10-07)
//  Rasmiy turnirlar jadvali kabi: klub logosi + nomi, o'yinchi, O' G D M ± Ochko.
//  Zonalar: ChL/YeL — top-Q to'g'ridan setkaga (yashil), Q+1..3Q pley-off raundi (sariq),
//  qolganlari chiqib ketadi; liga — 1-o'rin chempion (oltin). Qatorni bosish — profil.
//  Global: PT, PTT, escHtml, ptTeamBadge, ptDirectCount.
// =============================================================

function ptZoneOf(p, i) {
  if (p.format === "league") return i === 0 ? "champ" : "";
  const q = p.direct_count || ptDirectCount((Object.values(p.standings || {})[0] || []).length);
  return i < q ? "direct" : i < 3 * q ? "po" : "out";
}

function ptTableHtml(p, meId) {
  const rows = Object.values(p.standings || {})[0] || [];
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
  return `<div class="card pt-table-card pt-table-card--full">
      <div class="pt-table-title">${escHtml(p.league_name || PTT("pt_fmt_" + (p.format || "classic")))}${p.legs === 2 ? ` · ${escHtml(PTT("pt_legs_2"))}` : ""}</div>
      <div class="pt-table-scroll"><table class="pt-table pt-table--full"><thead><tr><th>#</th><th></th>
        ${th("pt_col_p")}${th("pt_col_w")}${th("pt_col_d")}${th("pt_col_l")}${th("pt_col_gd")}${th("pt_col_pts")}</tr></thead>
        <tbody>${body}</tbody></table></div>${legend}</div>`;
}
