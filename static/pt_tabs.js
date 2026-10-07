// =============================================================
//  pt_tabs.js — SHAXSIY turnir sahifasi: pastki menyuli sahifalar (2026-10-03)
//  2026-10-07: Asosiy — pt_home.js (hero + keyingi qadam + qoidalar), Admin — bo'limlar sarlavhali.
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

// Asosiy sahifa (hero, keyingi qadam, qoidalar, ishtirokchilar) — pt_home.js (2026-10-07)

// ---------------- Reyting: Guruhlar | Setka | Joriy tur ----------------

function ptTabRating(t, p) {
  if (!p) return ptWaitHtml();
  if (PT.playerView && typeof ptPlayerPageHtml === "function") return ptPlayerPageHtml(p);   // ishtirokchi profili
  const hasKo = (p.knockout || []).length > 0;
  const subs = [["groups", p.single_table ? "pt_seg_table" : "pt_seg_groups"], ...(hasKo ? [["bracket", "pt_seg_bracket"]] : []), ["round", "pt_seg_round"]];
  if (!PT.ratingTab || !subs.some(([id]) => id === PT.ratingTab)) PT.ratingTab = hasKo ? "bracket" : "groups";
  const bar = `<div class="pt-rtabs pt-seg">${subs.map(([id, l]) =>
    `<button class="tab-btn${PT.ratingTab === id ? " active" : ""}" data-pt-rtab="${id}">${escHtml(PTT(l))}</button>`).join("")}</div>`;
  let body;
  if (PT.ratingTab === "bracket") body = ptKnockoutStagesHtml(p);
  else if (PT.ratingTab === "round") {
    const all = (p.round_matches || []).map(m => ptMatchCardHtml(m, p, m.player1_id === p.me_id || m.player2_id === p.me_id)).join("");
    body = p.phase ? ptKnockoutStagesHtml(p) : (all || `<div class="empty-state">${escHtml(PTT("pt_tab_wait"))}</div>`);
  } else body = ptStandingsHtml(p.standings, p.me_id);
  return bar + body;
}

// ---------------- Profil: rasmiy turnirlar kabi (pt_profile.js) ----------------

function ptTabProfile(t, p) {
  if (!p) return ptWaitHtml();
  const view = ptMyProfileView(t, p);
  return view ? ptProfileHtml(view, p, true) : `<div class="empty-state">${escHtml(PTT("pt_prof_none"))}</div>`;
}

// ---------------- Sovrinlar: turnir kubogi va chempion ----------------

function ptTabPrizes(t, p) {
  if (p && (p.champions || []).length > 1) return ptLeagueChampionsHtml(t, p);   // ko'p ligali turnir
  const c = p && p.champion;
  const final = p && (p.knockout || []).find(m => m.stage === "final");
  const holder = c
    ? `<div class="pt-champion-label">${escHtml(PTT("pt_champion_title"))}</div><div class="pt-champion-name">${escHtml(ptUserLabel(c))}</div>
       ${c.team_name ? `<div class="pt-champion-team">${ptTeamBadge(c.team_name)}${escHtml(c.team_name)}</div>` : ""}`
    : `<div class="pt-hint">${escHtml(PTT(t.format === "league" ? "pt_prize_hint_league" : "pt_prize_hint"))}</div>`;
  const cup = typeof ptTrophySrc === "function" && ptTrophySrc(t);      // 2026-10-07: format kubogi
  return `<div class="card pt-champion">
      ${cup ? `<img class="pt-champion-img${(t.format || "classic") === "classic" ? " pt-champion-img--glass" : ""}" src="${escHtml(cup)}" alt="" onerror="this.outerHTML='<div class=\'pt-champion-cup\'>🏆</div>'">`
        : `<div class="pt-champion-cup">🏆</div>`}
      <div class="pt-prize-title">${escHtml(PTT("pt_prize_title"))}</div>${holder}</div>
    ${final ? `<div class="section-label pt-label">${escHtml(PTT("pt_stage_final_h"))}</div>${ptMatchCardHtml(final, p, final.player1_id === p.me_id || final.player2_id === p.me_id)}` : ""}`;
}

// Ko'p ligali turnir: har liga kubogi va chempioni (2026-10-07)
function ptLeagueChampionsHtml(t, p) {
  return p.champions.map(c => {
    const cup = typeof LEAGUE_TROPHIES !== "undefined" && LEAGUE_TROPHIES[c.league];
    return `<div class="card pt-champion">
        ${cup ? `<img class="pt-champion-img" src="${escHtml(cup)}" alt="">` : `<div class="pt-champion-cup">🏆</div>`}
        <div class="pt-prize-title">${escHtml(c.league)}</div>
        <div class="pt-champion-label">${escHtml(PTT("pt_champion_title"))}</div>
        <div class="pt-champion-name">${escHtml(ptUserLabel(c))}</div>
        ${c.team_name ? `<div class="pt-champion-team">${ptTeamBadge(c.team_name)}${escHtml(c.team_name)}</div>` : ""}</div>`;
  }).join("");
}

// Admin: boshlash, tur/pley-off boshqaruvi, havola, so'rovlar va a'zolar, adminlar, sig'im
// Admin paneli sarlavhasi: rol, kutilayotgan so'rovlar, joriy tur/bosqich, muddat (rasmiy turnirlar kabi)
function ptAdminHeaderHtml(t, p) {
  const pending = (t.members || []).filter(m => m.status === "pending").length;
  const stage = !p ? "—" : p.phase === "finished" ? PTT("pt_status_finished")
    : p.phase ? PTT("pt_ko_short") : `${Math.min(p.current_round, p.total_rounds)}/${p.total_rounds}`;
  const stat = (v, l, cls = "") => `<div class="stat-card"><span class="stat-card-value ${cls}">${escHtml(String(v))}</span>
      <span class="stat-card-label">${escHtml(PTT(l))}</span></div>`;
  return `<div class="card pt-admin-head">
      <div class="pt-admin-title">🛡 ${escHtml(PTT("pt_admin_panel"))}
        <span class="pt-tag ${t.is_owner ? "" : "pt-tag--admin"}">${escHtml(PTT(t.is_owner ? "pt_owner_tag" : "pt_admin_tag"))}</span></div>
      <div class="stats-grid pt-admin-stats">
        ${stat(pending, "pt_adm_requests", pending ? "neon-red" : "")}
        ${stat(stage, "pt_adm_stage", "neon-cyan")}
        ${stat((p && p.deadline_local) || "—", "pt_adm_deadline")}
      </div></div>`;
}

// Admin sahifasi: bo'limlar sarlavhali (boshlash → tur → tuzatish → taklif → a'zolar → adminlar → sozlamalar)
function ptSectionHtml(key, body) {
  return body ? `<div class="section-label pt-label pt-sec">${escHtml(PTT(key))}</div>${body}` : "";
}

function ptTabAdmin(t, p) {
  if (!ptIsManager(t)) return "";
  const pm = p ? { ...p, is_manager: p.is_manager || ptIsManager(t) } : null;  // eski server: play'da is_manager yo'q
  const ko = pm && pm.phase;
  const parts = [
    ptAdminHeaderHtml(t, p),
    ptSectionHtml("pt_adm_sec_start", ptPlayHtml(t)),
    pm ? ptSectionHtml(ko ? "pt_adm_sec_ko" : "pt_adm_sec_round", ptAdminPlayHtml(pm)) : "",
    pm && pm.phase !== "finished" && typeof ptFixCardHtml === "function" ? ptSectionHtml("pt_adm_sec_fix", ptFixCardHtml()) : "",
    typeof ptManageHtml === "function" ? ptSectionHtml("pt_adm_sec_invite", ptManageHtml(t)) : "",
    t.status === "recruiting" && typeof ptMembersHtml === "function" ? ptMembersHtml(t) : "",
    typeof ptAdminsHtml === "function" ? ptAdminsHtml(t) : "",
    typeof ptSizeEditHtml === "function" ? ptSectionHtml("pt_adm_sec_settings", ptSizeEditHtml(t)) : "",
    typeof ptDeleteHtml === "function" ? ptSectionHtml("pt_adm_sec_delete", ptDeleteHtml(t)) : "",
  ];
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
  if (PT.playerView && String(PT.playerView._tid || PT.detailId) !== String(PT.detailId)) PT.playerView = null;
  const builders = { home: ptTabHome, rating: ptTabRating, profile: ptTabProfile, prizes: ptTabPrizes, admin: ptTabAdmin };
  // Asosiy sahifada sarlavha o'rniga stadion fonidagi hero (pt_home.js)
  ptRender(`${PT.tab === "home" ? "" : ptHeadHtml(t)}${builders[PT.tab](t, p)}`, ptNavHtml(t));
  ptBindDetail(t);
  ptUpdateTabBadges(t, p);
}

function ptBindDetail(t) {
  document.querySelectorAll("#pt-root [data-pt-tab]").forEach(b => b.addEventListener("click", () => {
    if (PT.tab === b.dataset.ptTab && !PT.playerView) return;
    PT.tab = b.dataset.ptTab;
    PT.playerView = null;                                  // boshqa sahifa — ishtirokchi profili yopiladi
    PT.rulesEdit = false;                                  // saqlanmagan qoidalar tahriri yopiladi
    ptRenderDetailTabs();
    document.querySelector("#pt-root .pt-body")?.scrollTo?.(0, 0);
    window.scrollTo(0, 0);
  }));
  document.querySelectorAll("#pt-root [data-pt-rtab]").forEach(b => b.addEventListener("click", () => {
    PT.ratingTab = b.dataset.ptRtab; ptRenderDetailTabs();
  }));
  // Reyting: ishtirokchi qatoriga bosilsa — uning profili (pt_profile.js)
  document.querySelectorAll("#pt-root [data-pt-player]").forEach(el => el.addEventListener("click", () => {
    if (typeof ptOpenPlayer === "function") void ptOpenPlayer(el.dataset.ptPlayer);
  }));
  document.getElementById("pt-player-back")?.addEventListener("click", () => { PT.playerView = null; ptRenderDetailTabs(); });
  if (typeof ptLoadAvatars === "function") ptLoadAvatars(document.getElementById("pt-root"));
  document.querySelectorAll("#pt-root [data-pt-goto]").forEach(b => b.addEventListener("click", () => {
    PT.tab = b.dataset.ptGoto; ptRenderDetailTabs(); window.scrollTo(0, 0);
  }));
  document.querySelectorAll("#pt-root [data-pt-copy]").forEach(el =>
    el.addEventListener("click", () => ptCopy(el.dataset.ptCopy)));
  if (typeof ptBindPaymentActions === "function") ptBindPaymentActions(t);
  document.getElementById("pt-size-save")?.addEventListener("click", () => void ptSaveSize(t.id));
  if (PT.tab === "home" && typeof ptBindHome === "function") ptBindHome(t);
  if (typeof ptBindManage === "function") ptBindManage(t);
  if (typeof ptBindPlay === "function") ptBindPlay(t);
  if (typeof ptBindAdmins === "function") ptBindAdmins(t);
  if (typeof ptBindDelete === "function") ptBindDelete();
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
