// =============================================================
//  pt_profile.js — SHAXSIY turnir: ishtirokchi profili (2026-10-04)
//  Rasmiy turnirlar profili bilan bir xil ko'rinish (card--profile, profile-avatar,
//  stats-grid, stat-card): Telegram rasmi (/players/{id}/photo; bo'lmasa bosh harf),
//  guruh va o'rin, statistika (2 qator), so'nggi o'yinlar shakli, keyingi o'yin, o'yinlar.
//  Mening profilim — PT.play'dan; boshqa ishtirokchi — GET /pt/{id}/player/{uid}
//  (Reyting jadvalidagi qatorni bosganda). Global: PT, PTT, apiFetch, escHtml, API_BASE,
//  ptMatchCardHtml, ptRenderDetailTabs, showToast.
// =============================================================

function ptWinnerOf(m, uid) {
  if (m.status !== "confirmed" || m.score1 == null) return null;
  const mine = m.player1_id === uid ? m.score1 : m.score2, opp = m.player1_id === uid ? m.score2 : m.score1;
  return mine > opp ? "w" : mine < opp ? "l" : "d";
}

// view: {user:{id,nickname,username}, group, position, row, matches}
function ptProfileHtml(view, p, isMe) {
  const u = view.user || {};
  const name = u.username ? "@" + u.username : (u.nickname || "");
  const letter = ((u.nickname || u.username || "?")[0] || "?").toUpperCase();
  const r = view.row || { played: 0, wins: 0, draws: 0, losses: 0, goals_for: 0, goals_against: 0, goal_diff: 0, points: 0 };
  const single = p && p.single_table;                       // 2026-10-07: liga/ChL/YeL — guruhsiz jadval
  const groupLabel = view.group ? PTT(single ? "pt_prof_table" : "pt_prof_group", { g: view.group, pos: view.position || "—" }) : "";
  const team = u.team_name ? `<span class="pt-prof-team">${typeof ptTeamBadge === "function" ? ptTeamBadge(u.team_name) : ""}${escHtml(u.team_name)}</span>` : "";
  const stat = (v, l, cls = "", primary = false) => `<div class="stat-card${primary ? " stat-card--primary" : ""}">
      <span class="stat-card-value ${cls}">${escHtml(String(v))}</span><span class="stat-card-label">${escHtml(PTT(l))}</span></div>`;
  const form = (view.matches || []).map(m => ptWinnerOf(m, u.id)).filter(Boolean).slice(-5);
  const formHtml = form.length
    ? `<div class="pt-formline">${form.map(f => `<span class="pt-form-dot pt-form-dot--${f}">${escHtml(PTT("pt_form_" + f))}</span>`).join("")}</div>`
    : `<div class="pt-muted">${escHtml(PTT("pt_form_none"))}</div>`;
  const next = (view.matches || []).find(m => m.status !== "confirmed" && m.player1_id && m.player2_id);
  return `
    <div class="card card--profile pt-profile-card">
      <div class="profile-avatar" data-pt-avatar="${u.id}">${escHtml(letter)}</div>
      <div class="profile-info">
        <h2 class="profile-nickname">${escHtml(name)}</h2>
        ${team}<span class="profile-league">${escHtml(groupLabel)}</span>
      </div>
      ${view.position === 1 ? `<div class="pt-prof-badge">🥇</div>` : ""}
    </div>
    <div class="section-label pt-label">${escHtml(PTT("pt_section_stats"))}</div>
    <div class="stats-grid">
      ${stat(view.position ? "#" + view.position : "—", "pt_stat_pos", "neon-cyan", true)}
      ${stat(r.wins, "pt_stat_w", "neon-cyan")}${stat(r.draws, "pt_stat_d")}${stat(r.losses, "pt_stat_l", "neon-red")}
    </div>
    <div class="stats-grid pt-stats-2">
      ${stat(r.points, "pt_stat_pts", "neon-cyan", true)}${stat(r.played, "pt_stat_played")}
      ${stat(`${r.goals_for}:${r.goals_against}`, "pt_stat_goals")}${stat((r.goal_diff > 0 ? "+" : "") + r.goal_diff, "pt_stat_gd")}
    </div>
    <div class="section-label pt-label">${escHtml(PTT("pt_form_title"))}</div>${formHtml}
    ${next ? `<div class="section-label pt-label">${escHtml(PTT("pt_next_match"))}</div>${ptMatchCardHtml(next, p, isMe)}` : ""}
    <div class="section-label pt-label">${escHtml(PTT(isMe ? "pt_my_matches" : "pt_player_matches"))}</div>
    ${(view.matches || []).map(m => ptMatchCardHtml(m, p, isMe)).join("") || `<div class="empty-state">${escHtml(PTT("pt_no_my_matches"))}</div>`}`;
}

// Mening profilim (Profil sahifasi) — PT.play'dagi standings va my_matches'dan
function ptMyProfileView(t, p) {
  let group = null, position = null, row = null;
  for (const [g, rows] of Object.entries(p.standings || {})) {
    const i = rows.findIndex(x => x.user_id === p.me_id);
    if (i >= 0) { group = g; position = i + 1; row = rows[i]; break; }
  }
  if (!row) return null;
  const me = (t.members || []).find(m => m.user_id === p.me_id) || {};
  return { user: { id: p.me_id, nickname: me.nickname, username: me.username, team_name: me.team_name || row.team_name },
           group, position, row, matches: p.my_matches || [] };
}

// Rasmlar: [data-pt-avatar] — Telegram profil rasmi (bo'lmasa bosh harf qoladi, qoida #40)
function ptLoadAvatars(root) {
  (root || document).querySelectorAll("[data-pt-avatar]").forEach(box => {
    const uid = box.dataset.ptAvatar;
    if (!uid || box.dataset.loaded) return;
    box.dataset.loaded = "1";
    const img = new Image();
    img.src = `${API_BASE}/players/${encodeURIComponent(uid)}/photo`;
    img.alt = "";
    img.className = "pt-avatar-img";
    img.onload = () => { box.textContent = ""; box.appendChild(img); };
    img.onerror = () => {};
  });
}

// Reyting'dan ishtirokchi profiliga (o'zim bo'lsam — Profil sahifasiga)
async function ptOpenPlayer(uid) {
  const p = PT.play;
  if (p && Number(uid) === Number(p.me_id)) { PT.tab = "profile"; PT.playerView = null; ptRenderDetailTabs(); window.scrollTo(0, 0); return; }
  try {
    const data = await apiFetch(`/pt/${encodeURIComponent(PT.detailId)}/player/${encodeURIComponent(uid)}`);
    PT.playerView = data;
    PT.tab = "rating";
    ptRenderDetailTabs();
    window.scrollTo(0, 0);
  } catch (e) {
    showToast(PTT("pt_load_err"));
  }
}

function ptPlayerPageHtml(p) {
  return `<button class="btn btn--ghost pt-back-rating" id="pt-player-back">${escHtml(PTT("pt_back_rating"))}</button>
    ${ptProfileHtml(PT.playerView, p, false)}`;
}
