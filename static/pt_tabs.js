// =============================================================
//  pt_tabs.js — SHAXSIY turnir sahifasi: pastki menyuli sahifalar (2026-10-03)
//  🏠 Asosiy | 🏆 Reyting | 👤 Profil | 🎁 Sovrinlar | 🛡 Admin (faqat tashkilotchi/admin) —
//  rasmiy turnirlar (EL/ChL) bilan bir xil tuzilma
//  Mavjud bo'laklar qayta ishlatiladi (pt.js, pt_play.js, pt_knockout.js, pt_members.js,
//  pt_admins.js, pt_size.js, pt_payment.js). O'yin ma'lumoti (PT.play) bir marta yuklanadi —
//  sahifalar orasida o'tish so'rovsiz. Rozetkalar: Profil — o'qilmagan xabarlar,
//  Admin — kutilayotgan so'rovlar. Global: PT, PTT, escHtml, ptRender, ptHeadHtml, ...
// =============================================================

// 2026-10-03 (admin so'rovi): rasmiy turnir sahifalari bilan BIR XIL tuzilma —
// Asosiy | Reyting | Profil | Sovrinlar | Admin (EL/ChL kabi)
const PT_TABS = [
  { id: "home", icon: "home", label: "pt_tab_home" },
  { id: "rating", icon: "trophy", label: "pt_tab_rating" },
  { id: "profile", icon: "user", label: "pt_tab_profile" },
  { id: "prizes", icon: "gift", label: "pt_tab_prizes" },
  { id: "admin", icon: "shield", label: "pt_tab_admin", managerOnly: true },
];

function ptIsManager(t) { return !!(t && (t.is_manager || t.is_owner)); }

function ptVisibleTabs(t) { return PT_TABS.filter(x => !x.managerOnly || ptIsManager(t)); }

function ptWaitHtml() { return `<div class="empty-state">${escHtml(PTT("pt_tab_wait"))}</div>`; }

function ptUserLabel(u) { return u.username ? "@" + u.username : (u.nickname || ""); }

// ---------------- Asosiy: statistika kartasi, holat, ishtirokchilar ----------------

function ptStatsHtml(t, p) {
  const groups = p ? Object.keys(p.standings || {}).length : 0;      // qur'agacha guruhlar yo'q — "—"
  const round = p ? (p.phase ? "PO" : `${Math.min(p.current_round, p.total_rounds)}/${p.total_rounds}`) : "—";
  const cell = (v, l) => `<div class="pt-stat"><span class="pt-stat-value">${escHtml(String(v))}</span><span class="pt-stat-label">${escHtml(PTT(l))}</span></div>`;
  return `<div class="pt-stats">${cell(`${t.approved_count}/${t.max_players}`, "pt_stat_players")}${cell(groups || "—", "pt_stat_groups")}${cell(round, "pt_stat_round")}</div>`;
}

function ptTabHome(t, p) {
  const parts = [`<div class="card pt-pay">${ptStatsHtml(t, p)}</div>`, ptPayBlockHtml(t)];
  if (t.status === "recruiting") {
    parts.push(`<div class="card pt-pay"><div class="pt-hint">${escHtml(PTT("pt_home_recruiting", { n: t.approved_count, max: t.max_players }))}</div></div>`);
  }
  if (p) {
    parts.push(p.phase && typeof ptKnockoutHomeHtml === "function" ? ptKnockoutHomeHtml(p)
      : p.groups_finished ? `<div class="pt-note pt-note--ok">${escHtml(PTT("pt_groups_done"))}</div>`
      : ptRoundInfoHtml(p));
  }
  if (ptIsManager(t) && !["finished", "cancelled"].includes(t.status)) {
    parts.push(`<button class="btn btn--ghost" data-pt-goto="admin">🛡 ${escHtml(PTT("pt_home_admin_hint"))}</button>`);
  }
  parts.push(ptParticipantsHtml(t));
  return parts.filter(Boolean).join("");
}

// Ishtirokchilar (faqat ko'rish; boshqaruv — Admin sahifasida)
function ptParticipantsHtml(t) {
  const ro = { ...t, is_manager: false, is_owner: false };      // amal tugmalarisiz
  const approved = (t.members || []).filter(m => m.status === "approved");
  const admins = (t.admins || []).length
    ? `<div class="section-label pt-label">🛡 ${escHtml(PTT("pt_admins_title"))} (${t.admins.length})</div>` +
      t.admins.map(a => `<div class="match-item pt-member"><span>${escHtml(a.nickname || "")}${a.username ? ` <span class="pt-muted">@${escHtml(a.username)}</span>` : ""}</span>
        <span class="pt-tag pt-tag--admin">${escHtml(PTT("pt_admin_tag"))}</span></div>`).join("")
    : "";
  return `<div class="section-label pt-label">${escHtml(PTT("pt_members_title"))} (${approved.length}/${t.max_players})</div>
    ${approved.map(m => ptMemberRowHtml(ro, m)).join("")}${admins}`;
}

// ---------------- Reyting: Guruhlar | Setka | Joriy tur ----------------

function ptTabRating(t, p) {
  if (!p) return ptWaitHtml();
  const hasKo = (p.knockout || []).length > 0;
  const subs = [["groups", "pt_seg_groups"], ...(hasKo ? [["bracket", "pt_seg_bracket"]] : []), ["round", "pt_seg_round"]];
  if (!PT.ratingTab || !subs.some(([id]) => id === PT.ratingTab)) PT.ratingTab = hasKo ? "bracket" : "groups";
  const bar = `<div class="pt-rtabs">${subs.map(([id, l]) =>
    `<button class="tab-btn${PT.ratingTab === id ? " active" : ""}" data-pt-rtab="${id}">${escHtml(PTT(l))}</button>`).join("")}</div>`;
  let body;
  if (PT.ratingTab === "bracket") body = ptKnockoutStagesHtml(p);
  else if (PT.ratingTab === "round") {
    const all = (p.round_matches || []).map(m => ptMatchCardHtml(m, p, m.player1_id === p.me_id || m.player2_id === p.me_id)).join("");
    body = p.phase ? ptKnockoutStagesHtml(p) : (all || `<div class="empty-state">${escHtml(PTT("pt_tab_wait"))}</div>`);
  } else body = ptStandingsHtml(p.standings, p.me_id);
  return bar + body;
}

// ---------------- Profil: mening kartam + o'yinlarim ----------------

function ptMyRow(p) {
  for (const [g, rows] of Object.entries((p && p.standings) || {})) {
    const i = rows.findIndex(r => r.user_id === p.me_id);
    if (i >= 0) return { g, pos: i + 1, r: rows[i] };
  }
  return null;
}

function ptTabProfile(t, p) {
  const me = (t.members || []).find(m => m.user_id === (p ? p.me_id : null)) ||
             (t.members || []).find(m => m.status === "approved" && p && m.user_id === p.me_id);
  const mine = p ? ptMyRow(p) : null;
  if (!p) return ptWaitHtml();
  if (!mine) return `<div class="empty-state">${escHtml(PTT("pt_prof_none"))}</div>`;
  const name = me ? ptUserLabel(me) : "";
  const cell = (v, l) => `<div class="pt-stat"><span class="pt-stat-value">${escHtml(String(v))}</span><span class="pt-stat-label">${escHtml(PTT(l))}</span></div>`;
  return `<div class="card pt-pay pt-prof">
      <div class="pt-prof-top"><div class="pt-avatar">${escHtml((name.replace("@", "")[0] || "?").toUpperCase())}</div>
        <div><div class="pt-prof-name">${escHtml(name)}</div>
        <div class="pt-muted">${escHtml(PTT("pt_prof_group", { g: mine.g, pos: mine.pos }))}</div></div></div>
      <div class="pt-stats">${cell("#" + mine.pos, "pt_stat_pos")}${cell(mine.r.wins, "pt_stat_w")}${cell(mine.r.draws, "pt_stat_d")}${cell(mine.r.losses, "pt_stat_l")}${cell(mine.r.points, "pt_stat_pts")}</div>
    </div>
    <div class="section-label pt-label">${escHtml(PTT("pt_my_matches"))}</div>${ptMyMatchesHtml(p)}`;
}

// ---------------- Sovrinlar: turnir kubogi va chempion ----------------

function ptTabPrizes(t, p) {
  const c = p && p.champion;
  const final = p && (p.knockout || []).find(m => m.stage === "final");
  const holder = c
    ? `<div class="pt-champion-label">${escHtml(PTT("pt_champion_title"))}</div><div class="pt-champion-name">${escHtml(ptUserLabel(c))}</div>`
    : `<div class="pt-hint">${escHtml(PTT("pt_prize_hint"))}</div>`;
  return `<div class="card pt-champion">
      <div class="pt-champion-cup">🏆</div>
      <div class="pt-prize-title">${escHtml(PTT("pt_prize_title"))}</div>${holder}</div>
    ${final ? `<div class="section-label pt-label">${escHtml(PTT("pt_stage_final_h"))}</div>${ptMatchCardHtml(final, p, final.player1_id === p.me_id || final.player2_id === p.me_id)}` : ""}`;
}

// Admin: boshlash, tur/pley-off boshqaruvi, havola, so'rovlar va a'zolar, adminlar, sig'im
function ptTabAdmin(t, p) {
  if (!ptIsManager(t)) return "";
  const parts = [ptPlayHtml(t)];                      // recruiting: boshlash tugmasi
  // is_manager turnir ma'lumotidan ham olinadi — serverda pt_results eski bo'lsa ham
  // (play'da is_manager kelmasa) muddat/tuzatish tugmalari yo'qolmasin
  if (p) parts.push(ptAdminPlayHtml({ ...p, is_manager: p.is_manager || ptIsManager(t) }));
  if (typeof ptManageHtml === "function") parts.push(ptManageHtml(t));     // havola + qo'shish
  if (t.status === "recruiting" && typeof ptMembersHtml === "function") parts.push(ptMembersHtml(t));  // so'rovlar
  if (typeof ptAdminsHtml === "function") parts.push(ptAdminsHtml(t));
  if (typeof ptSizeEditHtml === "function") parts.push(ptSizeEditHtml(t));
  const body = parts.filter(Boolean).join("");
  return body || `<div class="empty-state">${escHtml(PTT("pt_admin_nothing"))}</div>`;
}

// ---------------- Chizish va bog'lash ----------------

function ptNavHtml(t) {
  return `<nav class="wc-nav pt-nav">${ptVisibleTabs(t).map(x => `
      <button class="wc-nav-item ${PT.tab === x.id ? "active" : ""}" data-pt-tab="${x.id}">
        <span class="nav-icon" data-icon="${x.icon}"></span>
        <span class="nav-label">${escHtml(PTT(x.label))}</span>
      </button>`).join("")}</nav>`;
}

function ptRenderDetailTabs() {
  const t = PT.detail, p = PT.play;
  if (!t) return;
  if (!ptVisibleTabs(t).some(x => x.id === PT.tab)) PT.tab = "home";   // admin huquqi olib tashlangan bo'lsa
  const builders = { home: ptTabHome, rating: ptTabRating, profile: ptTabProfile, prizes: ptTabPrizes, admin: ptTabAdmin };
  ptRender(`${ptHeadHtml(t)}${builders[PT.tab](t, p)}`, ptNavHtml(t));
  ptBindDetail(t);
  ptUpdateTabBadges(t, p);
}

function ptBindDetail(t) {
  document.querySelectorAll("#pt-root [data-pt-tab]").forEach(b => b.addEventListener("click", () => {
    if (PT.tab === b.dataset.ptTab) return;
    PT.tab = b.dataset.ptTab;
    ptRenderDetailTabs();
    document.querySelector("#pt-root .pt-body")?.scrollTo?.(0, 0);
    window.scrollTo(0, 0);
  }));
  document.querySelectorAll("#pt-root [data-pt-rtab]").forEach(b => b.addEventListener("click", () => {
    PT.ratingTab = b.dataset.ptRtab; ptRenderDetailTabs();
  }));
  document.querySelectorAll("#pt-root [data-pt-goto]").forEach(b => b.addEventListener("click", () => {
    PT.tab = b.dataset.ptGoto; ptRenderDetailTabs(); window.scrollTo(0, 0);
  }));
  document.querySelectorAll("#pt-root [data-pt-copy]").forEach(el =>
    el.addEventListener("click", () => ptCopy(el.dataset.ptCopy)));
  if (typeof ptBindPaymentActions === "function") ptBindPaymentActions(t);
  document.getElementById("pt-size-save")?.addEventListener("click", () => void ptSaveSize(t.id));
  if (typeof ptBindManage === "function") ptBindManage(t);
  if (typeof ptBindPlay === "function") ptBindPlay(t);
  if (typeof ptBindAdmins === "function") ptBindAdmins(t);
  if (PT.play && typeof ptBindPlayBody === "function") ptBindPlayBody(t.id);
}

// Rozetkalar: O'yinlarim — shu turnir o'yinlaridagi o'qilmagan xabarlar; Admin — kutilayotgan so'rovlar
function ptUpdateTabBadges(t, p) {
  if (typeof setNavBadge !== "function") return;
  const myIds = new Set(((p && p.my_matches) || []).map(m => String(m.id)));
  const unread = Object.entries(PT.unread || {}).reduce((s, [id, n]) => s + (myIds.has(String(id)) ? n : 0), 0);
  setNavBadge(document.querySelector('#pt-root [data-pt-tab="profile"]'), unread);
  const pending = t.status === "recruiting" ? (t.members || []).filter(m => m.status === "pending").length : 0;
  setNavBadge(document.querySelector('#pt-root [data-pt-tab="admin"]'), pending);
}
