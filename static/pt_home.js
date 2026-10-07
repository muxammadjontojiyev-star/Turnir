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
  const groups = p ? Object.keys(p.standings || {}).length : Math.floor((t.max_players || 0) / (t.group_size || 4));
  const stat = (v, l) => `<div class="pt-hero-stat"><span class="pt-hero-stat-value">${escHtml(String(v))}</span>
      <span class="pt-hero-stat-label">${escHtml(PTT(l))}</span></div>`;
  const role = t.is_owner ? `<span class="pt-tag">${escHtml(PTT("pt_owner_tag"))}</span>`
    : t.is_admin ? `<span class="pt-tag pt-tag--admin">${escHtml(PTT("pt_admin_tag"))}</span>` : "";
  const live = p && t.status === "running" && (p.phase ? !["ko_ready", "finished"].includes(p.phase) : !p.groups_finished);
  const deadline = live
    ? `<div class="pt-hero-deadline">⏱ ${escHtml(PTT("pt_hero_deadline"))}: <b>${escHtml(p.deadline_local || PTT("pt_no_deadline"))}</b></div>` : "";
  const progress = t.status === "recruiting" ? ptProgressHtml(t.approved_count, t.max_players) : "";
  return `<div class="pt-hero">
      <div class="pt-hero-overlay">
        <div class="pt-hero-top">
          <span class="pt-hero-kicker">${escHtml(PTT("pt_hero_kicker"))}</span>${role}
        </div>
        <div class="pt-hero-title">${escHtml(t.name)}</div>
        <div class="pt-hero-status"><span class="pt-status pt-status--${escHtml(t.status)}">${escHtml(ptStatusLabel(t.status))}</span></div>
        <div class="pt-hero-stats">
          ${stat(`${t.approved_count}/${t.max_players}`, "pt_hero_players")}
          ${stat(groups || "—", "pt_hero_groups")}
          ${stat(ptCurrentStageText(p), p && p.phase ? "pt_hero_stage" : "pt_hero_round")}
        </div>
        ${progress}${deadline}
      </div></div>`;
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
    const btns = `<div class="pt-next-actions">
        ${ready ? `<button class="btn btn--primary btn--glow" id="pt-start-btn">${escHtml(PTT("pt_start_btn"))}</button>` : ""}
        <button class="btn ${ready ? "btn--ghost" : "btn--primary btn--glow"}" id="pt-home-share">${escHtml(PTT("pt_share_link"))}</button></div>`;
    return ptNextCard(ready ? PTT("pt_next_ready") : PTT("pt_next_invite"),
      ready ? "" : PTT("pt_next_invite_sub", { min: t.min_players || 8 }), btns);
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
    return ptNextCard(PTT("pt_groups_done"), (p.is_manager || t.is_manager) ? PTT("pt_semis_hint", { size: p.bracket_size })
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
    return `<div class="pt-mchip${m.user_id === meId ? " pt-mchip--me" : ""}${link}">
        <div class="pt-mchip-ava" data-pt-avatar="${m.user_id}">${escHtml(letter)}</div>
        <div class="pt-mchip-name">${escHtml(name)}</div>${badge ? `<span class="pt-mchip-badge">${badge}</span>` : ""}</div>`;
  };
  return `<div class="section-label pt-label">${escHtml(PTT("pt_members_title"))} (${approved.length}/${t.max_players})</div>
    ${approved.length ? `<div class="pt-mgrid">${approved.map(chip).join("")}</div>`
      : `<div class="empty-state">${escHtml(PTT("pt_members_none"))}</div>`}`;
}

// ---------------- Asosiy sahifa ----------------

function ptTabHome(t, p) {
  return [
    ptHeroHtml(t, p),
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
      <div class="pt-card-meta">
        <span class="pt-status pt-status--${escHtml(t.status)}">${escHtml(ptStatusLabel(t.status))}</span>
        <span>${t.members_count}${max ? "/" + max : ""} ${escHtml(PTT("pt_members"))}</span>
      </div>
      ${max && t.status === "recruiting" ? ptProgressHtml(t.members_count, max) : ""}
      <span class="pt-card-arrow">›</span>
    </button>`;
}

// Yaratish formasi: sig'im bo'yicha guruhlar soni va pley-off boshlanadigan bosqich
function ptSizeSummary(n) {
  const g = Math.floor(n / ((PT.config && PT.config.group_size) || 4));
  let size = 4;
  while (size * 2 <= Math.min(2 * g, 64)) size *= 2;
  const stage = { 64: "r64", 32: "r32", 16: "r16", 8: "qf", 4: "semi" }[size];
  return PTT("pt_size_summary", { g, stage: PTT(`pt_stage_${stage}`).toLowerCase() });
}
