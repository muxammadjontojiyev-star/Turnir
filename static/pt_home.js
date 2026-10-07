// =============================================================
//  pt_home.js — SHAXSIY turnir: Asosiy sahifa va ro'yxat sarlavhasi (2026-10-07)
//  Admin so'rovi: "pulga arziydigan" darajada sodda va chiroyli — ligalardagi kabi
//  stadion rasmi (pt-hero.jpg) fonida hero, bitta aniq "Keyingi qadam" kartasi
//  (natija kiritish / taklif / boshlash), qoidalar (pt_rules.js) va ishtirokchilar.
//  Global: PT, PTT, escHtml, ptStatusLabel, ptPayBlockHtml, ptMatchCardHtml,
//  ptChampionHtml, ptStart, ptCopy, apiFetch, showToast, ptRulesHtml.
// =============================================================

function ptProgressHtml(n, max) {
  const pct = Math.max(0, Math.min(100, Math.round((n / Math.max(1, max)) * 100)));
  return `<div class="pt-progress"><div class="pt-progress-bar" style="width:${pct}%"></div></div>`;
}

// Joriy bosqich (hero va admin uchun): guruh turi "1/3" yoki pley-off bosqichi nomi
function ptCurrentStageText(p) {
  if (!p) return "—";
  if (p.phase === "finished") return "🏆";
  if (p.phase === "ko_ready") return PTT("pt_ko_short");
  if (p.phase) return p.phase === "final" ? PTT("pt_stage_final") : PTT(`pt_stage_${p.phase}`);
  return `${Math.min(p.current_round, p.total_rounds)}/${p.total_rounds}`;
}

// ---------------- Hero (stadion fonida) ----------------

function ptHeroHtml(t, p) {
  const fmt = typeof ptFmt === "function" ? ptFmt(t) : "classic";
  const single = typeof ptSingleTable === "function" && ptSingleTable(fmt);
  const groups = p ? Object.keys(p.standings || {}).length : Math.floor((t.max_players || 0) / (t.group_size || 4));
  const stat = (v, l) => `<div class="pt-hero-stat"><span class="pt-hero-stat-value">${escHtml(String(v))}</span>
      <span class="pt-hero-stat-label">${escHtml(PTT(l))}</span></div>`;
  const role = t.is_owner ? `<span class="pt-tag">${escHtml(PTT("pt_owner_tag"))}</span>`
    : t.is_admin ? `<span class="pt-tag pt-tag--admin">${escHtml(PTT("pt_admin_tag"))}</span>` : "";
  const live = p && t.status === "running" && (p.phase ? !["ko_ready", "finished"].includes(p.phase) : !p.groups_finished);
  const deadline = live
    ? `<div class="pt-hero-deadline">⏱ ${escHtml(PTT("pt_hero_deadline"))}: <b>${escHtml(p.deadline_local || PTT("pt_no_deadline"))}</b></div>` : "";
  const progress = t.status === "recruiting" ? ptProgressHtml(t.approved_count, t.max_players) : "";
  // 2026-10-07: format nomi va foni (liga — liga logosi)
  const lgLogo = fmt === "league" && typeof LEAGUE_LOGOS !== "undefined" && LEAGUE_LOGOS[t.league_name]
    ? `<img class="pt-hero-lglogo" src="${escHtml(LEAGUE_LOGOS[t.league_name])}?v=3" alt="">` : "";
  const kicker = fmt === "classic" ? PTT("pt_hero_kicker")
    : `${ptFormatName(fmt)}${t.league_name ? " · " + t.league_name : ""}`.toUpperCase();
  const rounds = p ? p.total_rounds : (fmt === "league" ? (t.max_players - 1) * (t.legs || 1) : Math.min(8, (t.max_players || 8) - 1));
  const second = single ? stat(rounds || "—", "pt_hero_rounds") : stat(groups || "—", "pt_hero_groups");
  const bg = typeof PT_FORMAT_META !== "undefined" && PT_FORMAT_META[fmt] ? ` style="background-image:url('${PT_FORMAT_META[fmt].bg}')"` : "";
  return `<div class="pt-hero pt-hero--${escHtml(fmt)}"${bg}>
      <div class="pt-hero-overlay">
        <div class="pt-hero-top">
          <span class="pt-hero-kicker">${lgLogo}${escHtml(kicker)}</span>${role}
        </div>
        <div class="pt-hero-title">${escHtml(t.name)}</div>
        <div class="pt-hero-status"><span class="pt-status pt-status--${escHtml(t.status)}">${escHtml(ptStatusLabel(t.status))}</span></div>
        <div class="pt-hero-stats">
          ${stat(`${t.approved_count}/${t.max_players}`, "pt_hero_players")}
          ${second}
          ${stat(ptCurrentStageText(p), p && p.phase ? "pt_hero_stage" : "pt_hero_round")}
        </div>
        ${progress}${deadline}
      </div></div>`;
}

// ---------------- Mening klubim / terma jamoam (qur'agacha tanlanadi) ----------------

function ptMyTeamHtml(t) {
  const fmt = typeof ptFmt === "function" ? ptFmt(t) : "classic";
  if (!ptUsesTeams(fmt) || !t.my_status) return "";
  const title = PTT(fmt === "wc" ? "pt_team_my_wc" : "pt_team_my_club");
  if (t.status !== "recruiting") return "";
  if (t.my_team && !PT.teamEdit) {
    return `<div class="card pt-myteam">
        <div class="pt-myteam-row">${ptTeamBadge(t.my_team, "pt-tlogo--lg")}
          <div><div class="pt-next-kicker">${escHtml(title)}</div><div class="pt-myteam-name">${escHtml(t.my_team)}</div></div>
          <button class="pt-mini pt-mini--edit" id="pt-team-change">${escHtml(PTT("pt_team_change"))}</button></div></div>`;
  }
  return `<div class="card pt-next pt-myteam">
      <div class="pt-next-kicker">${escHtml(PTT(t.my_team ? "pt_team_change" : "pt_next_title"))}</div>
      <div class="pt-next-title">${escHtml(PTT(fmt === "wc" ? "pt_team_pick_wc" : "pt_team_pick_club"))}</div>
      ${ptTeamPickerHtml({ id: "home", fmt, league: t.league_name, taken: t.taken_teams || [], mine: t.my_team })}
      <div class="pt-pay-actions${t.my_team ? "" : " pt-pay-actions--one"}">
        ${t.my_team ? `<button class="btn btn--ghost" id="pt-team-cancel">${escHtml(PTT("pt_rules_cancel"))}</button>` : ""}
        <button class="btn btn--primary" id="pt-team-save" disabled>${escHtml(PTT("pt_team_save"))}</button></div></div>`;
}

function ptBindMyTeam(t) {
  const opts = { id: "home", fmt: ptFmt(t), league: t.league_name, taken: t.taken_teams || [], mine: t.my_team };
  document.getElementById("pt-team-change")?.addEventListener("click", () => { PT.teamEdit = true; ptRenderDetailTabs(); });
  document.getElementById("pt-team-cancel")?.addEventListener("click", () => { PT.teamEdit = false; ptRenderDetailTabs(); });
  if (typeof ptBindTeamPicker === "function") {
    ptBindTeamPicker(opts, team => {
      const b = document.getElementById("pt-team-save");
      if (b) b.disabled = !team || team === t.my_team;
    });
  }
  document.getElementById("pt-team-save")?.addEventListener("click", () => void ptSaveTeam(t, (PT.teamPick || {}).home));
}

async function ptSaveTeam(t, team) {
  if (PT.busy || !team) return;
  PT.busy = true;
  try {
    await apiFetch(`/pt/${encodeURIComponent(t.id)}/team`, { method: "POST", body: JSON.stringify({ team }) });
    PT.teamEdit = false;
    PT.teamPick = { ...(PT.teamPick || {}), home: null };
    showToast(PTT("pt_team_saved"));
  } catch (e) {
    const map = { team_taken: "pt_err_team_taken", not_recruiting: "pt_join_closed" };
    showToast(PTT(map[e && e.message] || "pt_err_generic"));
  } finally {
    PT.busy = false;
  }
  await ptOpenDetail(t.id);
}

// ---------------- Keyingi qadam: foydalanuvchi hozir nima qilishi kerak ----------------

function ptNextCard(title, body, extra = "") {
  return `<div class="card pt-next">
      <div class="pt-next-kicker">${escHtml(PTT("pt_next_title"))}</div>
      <div class="pt-next-title">${escHtml(title)}</div>${body ? `<div class="pt-hint">${escHtml(body)}</div>` : ""}${extra}</div>`;
}

function ptMyActionMatch(p) {
  const mine = p.my_matches || [];
  const open = m => (m.stage === "group" ? m.round === p.current_round : true);
  // avval men tasdiqlashim kerak bo'lganlar, keyin natija kiritilmaganlar
  return mine.find(m => m.status === "awaiting_confirmation" && m.submitted_by !== p.me_id)
    || mine.find(m => m.status === "pending" && open(m) && m.player1_id && m.player2_id)
    || mine.find(m => m.status === "awaiting_confirmation");
}

function ptNextStepHtml(t, p) {
  if (["awaiting_payment", "rejected", "payment_review"].includes(t.status)) return ptPayBlockHtml(t);
  if (t.status === "recruiting") {
    const mgr = t.is_manager || t.is_owner;
    if (!mgr) return ptNextCard(PTT("pt_next_wait_start"), PTT("pt_next_wait_sub"));
    const ready = !t.start_block;
    // 2026-10-07: formatga xos to'siqlar (liga to'lmagan, juft emas, jamoa tanlamaganlar bor)
    const approved = (t.members || []).filter(m => m.status === "approved");
    const blockText = {
      teams_missing: PTT("pt_block_teams", { n: approved.filter(m => !m.team_name).length }),
      league_not_full: PTT("pt_block_league", { n: approved.length, max: t.max_players }),
      not_even: PTT("pt_block_even", { n: approved.length }),
    }[t.start_block];
    const btns = `<div class="pt-next-actions">
        ${ready ? `<button class="btn btn--primary btn--glow" id="pt-start-btn">${escHtml(PTT("pt_start_btn"))}</button>` : ""}
        <button class="btn ${ready ? "btn--ghost" : "btn--primary btn--glow"}" id="pt-home-share">${escHtml(PTT("pt_share_link"))}</button></div>`;
    return ptNextCard(ready ? PTT("pt_next_ready") : t.start_block === "teams_missing" ? PTT("pt_next_teams") : PTT("pt_next_invite"),
      ready ? "" : blockText || PTT("pt_next_invite_sub", { min: t.min_players || 8 }), btns);
  }
  if (!p) return "";
  if (p.phase === "finished") return typeof ptChampionHtml === "function" ? ptChampionHtml(p) : "";
  const m = ptMyActionMatch(p);
  if (m && p.status === "running") {
    const needConfirm = m.status === "awaiting_confirmation" && m.submitted_by !== p.me_id;
    return `<div class="card pt-next pt-next--match">
        <div class="pt-next-kicker">${escHtml(PTT("pt_next_your_match"))}</div>
        ${needConfirm ? `<div class="pt-next-title">${escHtml(PTT("pt_next_confirm"))}</div>` : ""}
        ${ptMatchCardHtml(m, p, true)}
        <button class="pt-linkbtn" data-pt-goto="profile">${escHtml(PTT("pt_next_all_matches"))}</button></div>`;
  }
  const rating = `<div class="pt-next-actions"><button class="btn btn--ghost" data-pt-goto="rating">${escHtml(PTT("pt_next_open_rating"))}</button></div>`;
  if (p.phase === "ko_ready") {
    return ptNextCard(PTT(p.single_table ? "pt_table_done" : "pt_groups_done"), (p.is_manager || t.is_manager) ? ptKoReadyHint(p)
      : PTT("pt_semis_wait"), (p.is_manager || t.is_manager) ? `<div class="pt-next-actions">
        <button class="btn btn--primary btn--glow" data-pt-goto="admin">${escHtml(PTT("pt_semis_btn"))}</button></div>` : rating);
  }
  if (p.phase) return ptNextCard(PTT("pt_ko_title"), PTT("pt_next_ko_wait"), rating);
  return ptNextCard(PTT("pt_next_done"), PTT("pt_next_done_sub"), rating);
}

// ---------------- Ishtirokchilar: rasmli kartochkalar ----------------

function ptMembersGridHtml(t, p) {
  const approved = (t.members || []).filter(m => m.status === "approved");
  const adminIds = new Set((t.admins || []).map(a => a.user_id));
  const meId = p && p.me_id;
  const chip = m => {
    const name = m.username ? "@" + m.username : (m.nickname || "");
    const letter = ((m.nickname || m.username || "?")[0] || "?").toUpperCase();
    const badge = m.user_id === t.owner_user_id ? "👑" : adminIds.has(m.user_id) ? "🛡" : "";
    const link = p ? ` pt-row-link" data-pt-player="${m.user_id}` : "";
    const team = m.team_name && typeof ptTeamBadge === "function"
      ? `<span class="pt-mchip-team">${ptTeamBadge(m.team_name)}</span>` : "";
    return `<div class="pt-mchip${m.user_id === meId ? " pt-mchip--me" : ""}${link}">
        <div class="pt-mchip-ava-wrap"><div class="pt-mchip-ava" data-pt-avatar="${m.user_id}">${escHtml(letter)}</div>${team}</div>
        <div class="pt-mchip-name">${escHtml(name)}</div>
        ${m.team_name ? `<div class="pt-mchip-club">${escHtml(m.team_name)}</div>` : ""}
        ${badge ? `<span class="pt-mchip-badge">${badge}</span>` : ""}</div>`;
  };
  return `<div class="section-label pt-label">${escHtml(PTT("pt_members_title"))} (${approved.length}/${t.max_players})</div>
    ${approved.length ? `<div class="pt-mgrid">${approved.map(chip).join("")}</div>`
      : `<div class="empty-state">${escHtml(PTT("pt_members_none"))}</div>`}`;
}

// ---------------- Asosiy sahifa ----------------

function ptTabHome(t, p) {
  return [
    ptHeroHtml(t, p),
    ptMyTeamHtml(t),
    ptNextStepHtml(t, p),
    typeof ptRulesHtml === "function" ? ptRulesHtml(t) : "",
    ptMembersGridHtml(t, p),
  ].filter(Boolean).join("");
}

// Asosiy sahifadan to'g'ridan-to'g'ri taklif havolasini ulashish (Admin sahifasiga o'tmasdan)
async function ptShareInvite(t) {
  try {
    const { link } = await apiFetch(`/pt/${encodeURIComponent(t.id)}/invite-link`);
    const url = "https://t.me/share/url?url=" + encodeURIComponent(link)
      + "&text=" + encodeURIComponent(PTT("pt_share_text", { name: t.name }));
    const tg = window.Telegram?.WebApp;
    if (tg && typeof tg.openTelegramLink === "function") tg.openTelegramLink(url);
    else if (typeof ptCopy === "function") ptCopy(link);
  } catch (e) {
    showToast(PTT("pt_load_err"));
  }
}

function ptBindHome(t) {
  document.getElementById("pt-home-share")?.addEventListener("click", () => void ptShareInvite(t));
  if (typeof ptBindRules === "function") ptBindRules(t);
  ptBindMyTeam(t);
}

// ---------------- Ro'yxat sahifasi sarlavhasi ----------------

function ptListHeroHtml() {
  return `<div class="pt-hero pt-hero--list">
      <div class="pt-hero-overlay">
        <span class="pt-hero-kicker">${escHtml(PTT("pt_list_kicker"))}</span>
        <div class="pt-hero-title">${escHtml(PTT("pt_list_title"))}</div>
        <div class="pt-hero-sub">${escHtml(PTT("pt_list_sub"))}</div>
        <button class="btn btn--primary btn--glow pt-hero-cta" id="pt-new-btn">${escHtml(PTT("pt_new"))}</button>
      </div></div>`;
}

function ptHowHtml() {
  return `<div class="card pt-how">
      <div class="pt-next-kicker">${escHtml(PTT("pt_how_title"))}</div>
      ${[1, 2, 3].map(i => `<div class="pt-how-step"><span class="pt-how-num">${i}</span><span>${escHtml(PTT("pt_how_" + i))}</span></div>`).join("")}
    </div>`;
}

function ptListCardHtml(t) {
  const role = t.is_owner ? `<span class="pt-tag">${escHtml(PTT("pt_owner_tag"))}</span>`
    : t.is_admin ? `<span class="pt-tag pt-tag--admin">${escHtml(PTT("pt_admin_tag"))}</span>` : "";
  const max = t.max_players || 0;
  return `<button class="pt-card pt-card--rich" data-pt-open="${t.id}">
      <div class="pt-card-top"><span class="pt-card-name">${escHtml(t.name)}</span>${role}</div>
      ${typeof ptFormatName === "function" ? `<div class="pt-card-fmt">${PT_FORMAT_META[ptFmt(t)].icon} ${escHtml(ptFormatName(ptFmt(t)))}${t.league_name ? " · " + escHtml(t.league_name) : ""}</div>` : ""}
      <div class="pt-card-meta">
        <span class="pt-status pt-status--${escHtml(t.status)}">${escHtml(ptStatusLabel(t.status))}</span>
        <span>${t.members_count}${max ? "/" + max : ""} ${escHtml(PTT("pt_members"))}</span>
      </div>
      ${max && t.status === "recruiting" ? ptProgressHtml(t.members_count, max) : ""}
      <span class="pt-card-arrow">›</span>
    </button>`;
}
