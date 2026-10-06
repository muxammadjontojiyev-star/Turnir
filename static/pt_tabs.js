// =============================================================
//  pt_tabs.js — SHAXSIY turnir sahifasi: pastki menyuli sahifalar (2026-10-03)
//  🏠 Asosiy | 🏆 Jadval | ⚽ O'yinlarim | 👥 Ishtirokchilar | 🛡 Admin (faqat tashkilotchi/admin)
//  Mavjud bo'laklar qayta ishlatiladi (pt.js, pt_play.js, pt_knockout.js, pt_members.js,
//  pt_admins.js, pt_size.js, pt_payment.js). O'yin ma'lumoti (PT.play) bir marta yuklanadi —
//  sahifalar orasida o'tish so'rovsiz. Rozetkalar: O'yinlarim — o'qilmagan xabarlar,
//  Admin — kutilayotgan so'rovlar. Global: PT, PTT, escHtml, ptRender, ptHeadHtml, ...
// =============================================================

const PT_TABS = [
  { id: "home", icon: "home", label: "pt_tab_home" },
  { id: "table", icon: "trophy", label: "pt_tab_table" },
  { id: "matches", icon: "play", label: "pt_tab_matches" },
  { id: "members", icon: "user", label: "pt_tab_members" },
  { id: "admin", icon: "shield", label: "pt_tab_admin", managerOnly: true },
];

function ptIsManager(t) { return !!(t && (t.is_manager || t.is_owner)); }

function ptVisibleTabs(t) { return PT_TABS.filter(x => !x.managerOnly || ptIsManager(t)); }

function ptWaitHtml() { return `<div class="empty-state">${escHtml(PTT("pt_tab_wait"))}</div>`; }

// ---------------- Sahifalar mazmuni ----------------

function ptTabHome(t, p) {
  const parts = [ptPayBlockHtml(t)];
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
  return parts.filter(Boolean).join("");
}

function ptTabTable(t, p) {
  if (!p) return ptWaitHtml();
  const ko = (p.knockout || []).length && typeof ptKnockoutStagesHtml === "function" ? ptKnockoutStagesHtml(p) : "";
  return `${ko}
    <div class="section-label pt-label">${escHtml(PTT("pt_groups_title"))}</div>${ptStandingsHtml(p.standings, p.me_id)}
    ${ptRoundOthersHtml(p)}`;
}

function ptTabMatches(t, p) {
  return p ? ptMyMatchesHtml(p) : ptWaitHtml();
}

// Ishtirokchilar: faqat ko'rish (boshqaruv — Admin sahifasida)
function ptTabMembers(t) {
  const ro = { ...t, is_manager: false, is_owner: false };      // amal tugmalarisiz
  const approved = (t.members || []).filter(m => m.status === "approved");
  const admins = (t.admins || []).length
    ? `<div class="section-label pt-label">🛡 ${escHtml(PTT("pt_admins_title"))} (${t.admins.length})</div>` +
      t.admins.map(a => `<div class="match-item pt-member"><span>${escHtml(a.nickname || "")}${a.username ? ` <span class="pt-muted">@${escHtml(a.username)}</span>` : ""}</span>
        <span class="pt-tag pt-tag--admin">${escHtml(PTT("pt_admin_tag"))}</span></div>`).join("")
    : "";
  return `${admins}
    <div class="section-label pt-label">${escHtml(PTT("pt_members_title"))} (${approved.length}/${t.max_players})</div>
    ${approved.map(m => ptMemberRowHtml(ro, m)).join("")}`;
}

// Admin: boshlash, tur/pley-off boshqaruvi, havola, so'rovlar va a'zolar, adminlar, sig'im
function ptTabAdmin(t, p) {
  if (!ptIsManager(t)) return "";
  const parts = [ptPlayHtml(t)];                      // recruiting: boshlash tugmasi
  if (p) parts.push(ptAdminPlayHtml(p));              // tur / pley-off boshqaruvi + tuzatish
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
  const builders = { home: ptTabHome, table: ptTabTable, matches: ptTabMatches, members: ptTabMembers, admin: ptTabAdmin };
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
  setNavBadge(document.querySelector('#pt-root [data-pt-tab="matches"]'), unread);
  const pending = t.status === "recruiting" ? (t.members || []).filter(m => m.status === "pending").length : 0;
  setNavBadge(document.querySelector('#pt-root [data-pt-tab="admin"]'), pending);
}
