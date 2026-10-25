// =============================================================
//  tb.js — "TEAMLAR JANGI" bo'limi (2026-10-15, 1-bosqich: teamlar)
//  Bo'lim tanlashdagi 3-karta -> showTeamBattle(). #tb-root.
//  Tablar: Mening teamim | Teamlar | (bosh admin) Admin.
//  Teamni sardor ochadi, a'zolarni taklif havolasi bilan yig'adi, asosiy
//  tarkibni (TB.me.lineup_min..max) tuzadi; bosh admin tasdiqlaydi.
//  Backend: tb_api.py. Global: APP, apiFetch, escHtml, showToast, ICON, showHubSelect.
//  Sardor amallari — tb_team.js; admin — tb_admin.js, tb_admin_league.js.
//  2026-10-16: LIGALAR — team faqat liga havolasi (?tbl_join=<kod>) orqali ochiladi;
//  Teamlar/Jang/Jadval — o'z teamim ligasi (teami yo'q liga admini uchun — tanlangan liga).
// =============================================================

const TB = { me: null, teams: null, tab: "my", view: null, joinCode: null, invite: null,
             createEmoji: null, lineupSel: null, adminTeams: null, adminFilter: "pending",
             leagueCode: null, joinLeague: null, adminLeagueId: null };

// TB_ERR, tbErr — tb_i18n.js (2026-10-16: matnlar bir joyda)

function tbWho(o) { return o.username ? "@" + o.username : (o.nickname || "—"); }

// tbAvatarHtml, tbNameHtml — tb_logo.js (2026-10-16)

// Taklif kodi: URL ?tb_join=<kod> (team) / ?tbl_join=<kod> (liga, 2026-10-16) yoki Telegram startapp.
// Bir marta o'qiladi. Liga kodi "L:" bilan qaytadi (team kodida ":" bo'lmaydi).
function tbConsumeInviteParam() {
  let code = null, league = false;
  try {
    const params = new URLSearchParams(window.location.search);
    for (const key of ["tb_join", "tbl_join"]) {
      const v = params.get(key);
      if (v && !code) { code = v; league = key === "tbl_join"; }
      params.delete(key);
    }
    if (code) {
      const q = params.toString();
      window.history.replaceState(null, "", window.location.pathname + (q ? "?" + q : "") + window.location.hash);
    }
  } catch (_) { code = null; }
  if (!code && !TB._startParamUsed) {
    const sp = window.Telegram?.WebApp?.initDataUnsafe?.start_param || "";
    if (sp.startsWith("tbl_")) { code = sp.slice(4); league = true; TB._startParamUsed = true; }
    else if (sp.startsWith("tb_")) { code = sp.slice(3); TB._startParamUsed = true; }
  }
  if (!code || !/^[A-Za-z0-9_-]{4,40}$/.test(code)) return null;
  return league ? "L:" + code : code;
}

// Ko'rsatiladigan liga: o'z teamim ligasi, bo'lmasa admin tanlagan liga
function tbCurLeague() {
  return (TB.me && TB.me.team && TB.me.team.league_id) || TB.adminLeagueId
    || (TB.me && TB.me.managed_leagues && TB.me.managed_leagues[0] && TB.me.managed_leagues[0].id) || null;
}
function tbCanManageCur() {
  const l = tbCurLeague();
  return !!(TB.me && (TB.me.is_super || (TB.me.managed_leagues || []).some(x => x.id === l)));
}
function tbLeagueQ(sep) { const l = tbCurLeague(); return l ? `${sep || "?"}league_id=${l}` : ""; }

function showTeamBattle(joinCode) {
  ["hub-select", "mode-select", "pt-root"].forEach(id => document.getElementById(id)?.classList.add("hidden"));
  document.querySelectorAll(".section").forEach(s => s.classList.remove("active"));
  document.querySelector(".bottom-nav")?.classList.add("hidden");
  let root = document.getElementById("tb-root");
  if (!root) {
    root = document.createElement("div");
    root.id = "tb-root";
    (document.querySelector("main") || document.body).appendChild(root);
    root.addEventListener("click", tbHandleClick);
  }
  root.classList.remove("hidden");
  TB.view = null;
  const isLeague = typeof joinCode === "string" && joinCode.startsWith("L:");
  TB.joinCode = isLeague ? null : (joinCode || null);
  if (isLeague) { TB.leagueCode = joinCode.slice(2); TB.tab = "my"; }
  void tbLoad();
}

function exitTeamBattle() {
  document.getElementById("tb-root")?.classList.add("hidden");
  if (typeof showHubSelect === "function") showHubSelect();
}

async function tbLoad() {
  tbRender(`<div class="empty-state">Yuklanmoqda…</div>`);
  try {
    TB.me = await apiFetch("/tb/me");
  } catch (e) {
    tbRender(`<div class="empty-state">${escHtml(tbErr(e))}</div>`);
    return;
  }
  if (TB.joinCode) { await tbOpenJoin(TB.joinCode); return; }
  if (TB.leagueCode && !TB.joinLeague) {
    try { TB.joinLeague = await apiFetch(`/tb/league/by-code/${encodeURIComponent(TB.leagueCode)}`); }
    catch (e) { TB.leagueCode = null; tbToast("❌ " + tbErr(e)); }
    if (TB.me.team && TB.leagueCode) {                  // bir kishi — faqat bitta team
      tbToast("Siz allaqachon teamdasiz — yangi team ochish uchun avval undan chiqing");
      TB.leagueCode = null; TB.joinLeague = null;
    }
  }
  tbRenderTab();
}

function tbRender(bodyHtml) {
  const root = document.getElementById("tb-root");
  if (!root) return;
  const admin = TB.me && TB.me.is_admin;
  // 2026-10-16 (2-bosqich): + "Jang" (mening 1v1 o'yinim) va "Jadval" (divizionlar, turlar)
  // 2026-10-16: tablar PASTKI panelda (ilovaning asosiy pastki menyusi kabi), ikonka bilan
  const tabs = [["my", "Teamim", "user"], ["battle", "Jang", "swords"], ["table", "Jadval", "trophy"],
                ["teams", "Teamlar", "shield"]].concat(admin ? [["admin", "Admin", "lock"]] : []);
  root.innerHTML = `
    <div class="wc-header">
      <button class="wc-back" data-tb="exit" aria-label="Ortga">←</button>
      <div class="wc-header-title tb-title">${ICON.get("shield", 20)} <span>TEAMLAR JANGI</span></div><button class="wc-back tb-help" data-guide-open="tb" aria-label="?">?</button>
    </div>
    <div class="wc-body tb-body-wrap">
      ${tbLeagueBarHtml()}
      <div class="tb-body">${bodyHtml}</div>
    </div>
    ${TB.view ? "" : `<nav class="tb-nav">${tabs.map(([k, l, ic]) =>
      `<button class="tb-nav-item${TB.tab === k ? " active" : ""}" data-tb-tab="${k}">
        <span class="tb-nav-icon">${ICON.get(ic, 22)}</span><span class="tb-nav-label">${escHtml(l)}</span></button>`).join("")}</nav>`}`;
  root.classList.toggle("tb-has-nav", !TB.view);
  tbI18nApply(root);                    // 2026-10-16 (3-bosqich): ru/en
}

function tbRenderTab() {
  TB.view = null;
  if (TB.tab === "teams") { void tbLoadTeams(); return; }
  if (TB.tab === "battle" && typeof tbBattleLoad === "function") { void tbBattleLoad(); return; }
  if (TB.tab === "table" && typeof tbTableLoad === "function") { void tbTableLoad(); return; }
  if (TB.tab === "admin" && typeof tbAdminLoad === "function") { void tbAdminLoad(); return; }
  tbRender(TB.me.team ? tbMyTeamHtml(TB.me.team) : tbNoTeamHtml());
  if (TB.me.team && TB.me.team.is_captain && typeof tbBindCaptain === "function") tbBindCaptain();
}

// tbLeagueBarHtml, tbNoTeamHtml — tb_league_ui.js (2026-10-16)

const TB_STATUS = { pending: ["⏳ Tasdiq kutilmoqda", "pending"], approved: ["✅ Tasdiqlangan", "approved"],
                    rejected: ["❌ Rad etilgan", "rejected"] };

function tbTeamHeadHtml(t) {
  const [label, cls] = TB_STATUS[t.status] || [t.status, ""];
  return `
    <div class="card tb-team-head">
      <div class="tb-team-emoji">${tbLogo("team", t.id, t.logo_ver, t.emoji, "tb-logo--xl")}</div>
      <div class="tb-team-name">${escHtml(t.name)}</div>
      <span class="tb-status tb-status--${cls}">${escHtml(label)}</span>
      <div class="tb-team-meta">Sardor: <b>${escHtml(tbWho({ username: t.captain_username, nickname: t.captain_nickname }))}</b></div>
      ${t.league_name ? `<div class="tb-team-meta">Liga: ${tbLogo("league", t.league_id, t.league_logo_ver, t.league_emoji, "tb-logo--xs")} <b>${escHtml(t.league_name)}</b></div>` : ""}
      <div class="tb-team-stats">
        <div><b>${t.members_count}</b><span>A'ZO</span></div>
        <div><b>${t.lineup_count ?? "—"}</b><span>ASOSIY TARKIB</span></div>
      </div>
      ${(t.titles || []).length ? `<div class="tb-titles">${t.titles.map(x =>
        `<span>🏆 ${x.season_number}-mavsum · ${x.division}-divizion chempioni</span>`).join("")}</div>` : ""}
      ${t.status === "rejected" && t.reject_reason ? `<div class="tb-warn">Sabab: ${escHtml(t.reject_reason)}</div>` : ""}
    </div>`;
}

function tbMemberRowHtml(m, t, captainView) {
  const role = m.role === "captain" ? `<span class="tb-badge tb-badge--cap">SARDOR</span>` : "";
  const lu = m.in_lineup ? `<span class="tb-badge tb-badge--lu">#${m.lineup_pos}</span>` : "";
  const acts = captainView && m.role !== "captain"
    ? `<div class="tb-member-acts">
         <button class="tb-mini" data-tb-cap="${m.user_id}">Sardor qilish</button>
         <button class="tb-mini tb-mini--danger" data-tb-kick="${m.user_id}">Chiqarish</button>
       </div>` : "";
  return `<div class="tb-member">
      ${tbAvatarHtml(m)}
      <div class="tb-member-info">${tbNameHtml(m)}${role}${lu}
        ${captainView && m.telegram_id ? `<span class="tb-member-id">ID ${escHtml(String(m.telegram_id))}</span>` : ""}</div>
      ${acts}
    </div>`;
}

function tbMyTeamHtml(t) {
  const cap = t.is_captain;
  const lmin = TB.me.lineup_min;
  const lineup = t.members.filter(m => m.in_lineup).sort((a, b) => a.lineup_pos - b.lineup_pos);
  const short = lineup.length < lmin
    ? `<div class="tb-warn">Asosiy tarkib to'liq emas: ${lineup.length}/${lmin}. ${cap ? "Tarkibni tuzing." : "Sardor tarkibni tuzishi kerak."}</div>` : "";
  return `
    ${tbTeamHeadHtml(t)}
    ${t.status === "pending" ? `<div class="tb-note">Team admin tasdig'ini kutmoqda. Shu vaqtda a'zolarni yig'ib, tarkibni tuzib qo'ying.</div>` : ""}
    ${cap && typeof tbCaptainBlocksHtml === "function" ? tbCaptainBlocksHtml(t) : `
      <div class="section-label">ASOSIY TARKIB (${lineup.length})</div>
      ${short}
      <div class="card tb-list">${lineup.length ? lineup.map(m => tbMemberRowHtml(m, t, false)).join("") : `<div class="tb-hint">Tarkib hali tuzilmagan</div>`}</div>`}
    <div class="section-label">A'ZOLAR (${t.members.length})</div>
    <div class="card tb-list">${t.members.map(m => tbMemberRowHtml(m, t, cap)).join("")}</div>
    ${cap
      ? `<button class="btn btn--ghost tb-danger-btn" data-tb="dissolve">Teamni tarqatish</button>`
      : `<button class="btn btn--ghost tb-danger-btn" data-tb="leave">Teamdan chiqish</button>`}`;
}

// ---------------- Teamlar ro'yxati ----------------
async function tbLoadTeams() {
  tbRender(`<div class="empty-state">Yuklanmoqda…</div>`);
  try {
    TB.teams = (await apiFetch("/tb/teams" + tbLeagueQ())).teams || [];
  } catch (e) {
    tbRender(`<div class="empty-state">${escHtml(tbErr(e))}</div>`);
    return;
  }
  const rows = TB.teams.map((t, i) => `
    <button class="tb-team-row" data-tb-team="${t.id}">
      <span class="tb-row-n">${i + 1}</span>
      <span class="tb-row-emoji">${tbLogo("team", t.id, t.logo_ver, t.emoji)}</span>
      <span class="tb-row-info"><b>${escHtml(t.name)}${t.titles_count ? ` <i class="tb-title-cnt">🏆${t.titles_count > 1 ? "×" + t.titles_count : ""}</i>` : ""}</b><span>Sardor: ${escHtml(tbWho({ username: t.captain_username, nickname: t.captain_nickname }))}</span></span>
      <span class="tb-row-count">${t.members_count}<small>a'zo</small></span>
    </button>`).join("");
  tbRender(`<div class="section-label">TASDIQLANGAN TEAMLAR (${TB.teams.length})</div>
    ${rows || `<div class="empty-state">${tbCurLeague() ? "Hozircha tasdiqlangan team yo'q" : "Siz hali hech qaysi ligada emassiz"}</div>`}`);
}

async function tbOpenTeam(id) {
  TB.view = "team";
  tbRender(`<div class="empty-state">Yuklanmoqda…</div>`);
  try {
    const t = await apiFetch(`/tb/teams/${id}`);
    tbRender(`<button class="tb-link-back" data-tb="back">← Ro'yxatga qaytish</button>
      ${tbTeamHeadHtml(t)}
      <div class="section-label">A'ZOLAR (${t.members.length})</div>
      <div class="card tb-list">${t.members.map(m => tbMemberRowHtml(m, t, false)).join("")}</div>`);
  } catch (e) {
    tbRender(`<div class="empty-state">${escHtml(tbErr(e))}</div>`);
  }
}

// ---------------- Taklif bilan qo'shilish ----------------
async function tbOpenJoin(code) {
  TB.view = "join";
  tbRender(`<div class="empty-state">Yuklanmoqda…</div>`);
  try {
    TB.invite = await apiFetch(`/tb/invite/${encodeURIComponent(code)}`);
  } catch (e) {
    TB.joinCode = null;
    tbRender(`<div class="empty-state">${escHtml(tbErr(e))}</div><button class="btn btn--ghost" data-tb="back">Davom etish</button>`);
    return;
  }
  const p = TB.invite;
  let action;
  if (p.my_team_id === p.id) action = `<div class="tb-note">Siz shu teamning a'zosisiz.</div>`;
  else if (p.my_team_id) action = `<div class="tb-warn">Siz boshqa teamdasiz. Qo'shilish uchun avval undan chiqing.</div>`;
  else if (p.status === "rejected") action = `<div class="tb-warn">Bu team admin tomonidan rad etilgan.</div>`;
  else action = `<button class="btn btn--primary btn--glow" data-tb="join">⚔️ Teamga qo'shilish</button>`;
  tbRender(`<div class="section-label">TEAMGA TAKLIF</div>${tbTeamHeadHtml(p)}${action}
    <button class="btn btn--ghost" data-tb="back">Bo'limga o'tish</button>`);
}

// ---------------- Amallar ----------------
async function tbAction(path, body, okMsg, btn) {
  if (btn) btn.disabled = true;
  try {
    await apiFetch(path, { method: "POST", body: JSON.stringify(body || {}) });
    if (okMsg) tbToast(okMsg);
    TB.me = await apiFetch("/tb/me");
    TB.lineupSel = null;
    tbRenderTab();
    return true;
  } catch (e) {
    tbToast("❌ " + tbErr(e));
    if (btn) btn.disabled = false;
    return false;
  }
}

function tbHandleClick(e) {
  const t = e.target;
  if (!t.closest) return;
  const tab = t.closest("[data-tb-tab]");
  if (tab) { TB.tab = tab.dataset.tbTab; tbRenderTab(); return; }
  const team = t.closest("[data-tb-team]");
  if (team) { void tbOpenTeam(team.dataset.tbTeam); return; }
  const kick = t.closest("[data-tb-kick]");
  if (kick && tbConfirm("A'zo teamdan chiqarilsinmi?")) { void tbAction("/tb/members/remove", { user_id: +kick.dataset.tbKick }, "✅ Chiqarildi", kick); return; }
  const cap = t.closest("[data-tb-cap]");
  if (cap && tbConfirm("Sardorlik shu a'zoga topshirilsinmi? Siz oddiy a'zo bo'lib qolasiz.")) {
    void tbAction("/tb/captain/transfer", { user_id: +cap.dataset.tbCap }, "✅ Sardorlik topshirildi", cap); return;
  }
  const act = t.closest("[data-tb]");
  if (!act) return;
  const a = act.dataset.tb;
  if (a === "exit") exitTeamBattle();
  else if (a === "back") { TB.joinCode = null; TB.view = null; tbRenderTab(); }
  else if (a === "create") {
    const name = (document.getElementById("tb-name")?.value || "").trim();
    void tbAction("/tb/teams", { name, emoji: TB.createEmoji, league_code: TB.leagueCode },
      "✅ Team ochildi! Endi a'zolarni taklif qiling", act).then(ok => { if (ok) { TB.leagueCode = null; TB.joinLeague = null; } });
  } else if (a === "join") {
    const code = TB.joinCode;
    TB.joinCode = null;
    void tbAction("/tb/join", { code }, "✅ Teamga qo'shildingiz", act);
  } else if (a === "leave" && tbConfirm("Teamdan chiqasizmi?")) void tbAction("/tb/leave", {}, "Teamdan chiqdingiz", act);
  else if (a === "dissolve" && tbConfirm("Team butunlay tarqatilsinmi? Barcha a'zolar chiqariladi. Qaytarib bo'lmaydi!")) {
    void tbAction("/tb/dissolve", {}, "Team tarqatildi", act);
  } else if (typeof tbCaptainClick === "function") tbCaptainClick(a, act);
}
