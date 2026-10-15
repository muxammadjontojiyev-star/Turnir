// =============================================================
//  tb.js — "TEAMLAR JANGI" bo'limi (2026-10-15, 1-bosqich: teamlar)
//  Bo'lim tanlashdagi 3-karta -> showTeamBattle(). #tb-root.
//  Tablar: Mening teamim | Teamlar | (bosh admin) Admin.
//  Teamni sardor ochadi, a'zolarni taklif havolasi bilan yig'adi, asosiy
//  tarkibni (TB.me.lineup_min..max) tuzadi; bosh admin tasdiqlaydi.
//  Backend: tb_api.py. Global: APP, apiFetch, escHtml, showToast, ICON, showHubSelect.
//  Sardor amallari — tb_team.js; admin — tb_admin.js.
// =============================================================

const TB = { me: null, teams: null, tab: "my", view: null, joinCode: null, invite: null,
             createEmoji: null, lineupSel: null, adminTeams: null, adminFilter: "pending" };

const TB_ERR = {
  bad_name_len: "Nom 3–24 belgidan iborat bo'lsin",
  bad_name_chars: "Nomda faqat harf, raqam, probel va - . ' bo'lishi mumkin",
  bad_name_profanity: "Nomda nomaqbul so'z bor",
  bad_emoji: "Belgini ro'yxatdan tanlang",
  already_in_team: "Siz allaqachon boshqa teamdasiz",
  already_member: "Siz allaqachon shu teamdasiz",
  name_taken: "Bu nom band — boshqasini tanlang",
  not_found: "Team topilmadi yoki havola eskirgan",
  rejected: "Bu team admin tomonidan rad etilgan",
  not_in_team: "Siz teamda emassiz",
  captain_cannot_leave: "Sardor chiqa olmaydi — avval sardorlikni topshiring yoki teamni tarqating",
  not_captain: "Bu amal faqat sardorga ruxsat etilgan",
  member_not_found: "A'zo topilmadi",
  cannot_remove_self: "O'zingizni chiqara olmaysiz",
  lineup_size: "Asosiy tarkib soni chegaradan tashqarida",
  lineup_duplicate: "Tarkibda takror o'yinchi bor",
  lineup_not_member: "Tarkibda teamga a'zo bo'lmagan o'yinchi bor",
  bot_username_missing: "Bot nomi sozlanmagan (BOT_USERNAME)",
  too_many_requests: "Juda tez — biroz kuting",
};
function tbErr(e) { return TB_ERR[e && e.message] || ("Xato: " + (e && e.message || "")); }

function tbWho(o) { return o.username ? "@" + o.username : (o.nickname || "—"); }

// Taklif kodi: URL ?tb_join=<kod> yoki Telegram startapp (tb_<kod>). Bir marta o'qiladi.
function tbConsumeInviteParam() {
  let code = null;
  try {
    const params = new URLSearchParams(window.location.search);
    code = params.get("tb_join");
    if (code) {
      params.delete("tb_join");
      const q = params.toString();
      window.history.replaceState(null, "", window.location.pathname + (q ? "?" + q : "") + window.location.hash);
    }
  } catch (_) { code = null; }
  if (!code) {
    const sp = window.Telegram?.WebApp?.initDataUnsafe?.start_param || "";
    if (sp.startsWith("tb_") && !TB._startParamUsed) { code = sp.slice(3); TB._startParamUsed = true; }
  }
  return code && /^[A-Za-z0-9_-]{4,40}$/.test(code) ? code : null;
}

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
  TB.joinCode = joinCode || null;
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
  tbRenderTab();
}

function tbRender(bodyHtml) {
  const root = document.getElementById("tb-root");
  if (!root) return;
  const admin = TB.me && TB.me.is_admin;
  const tabs = [["my", "Mening teamim"], ["teams", "Teamlar"]].concat(admin ? [["admin", "Admin"]] : []);
  root.innerHTML = `
    <div class="wc-header">
      <button class="wc-back" data-tb="exit" aria-label="Ortga">←</button>
      <div class="wc-header-title tb-title">${ICON.get("shield", 20)} <span>TEAMLAR JANGI</span></div>
    </div>
    <div class="wc-body tb-body-wrap">
      ${TB.view ? "" : `<div class="tb-tabs">${tabs.map(([k, l]) =>
        `<button class="tb-tab${TB.tab === k ? " active" : ""}" data-tb-tab="${k}">${escHtml(l)}</button>`).join("")}</div>`}
      <div class="tb-body">${bodyHtml}</div>
    </div>`;
}

function tbRenderTab() {
  TB.view = null;
  if (TB.tab === "teams") { void tbLoadTeams(); return; }
  if (TB.tab === "admin" && typeof tbAdminLoad === "function") { void tbAdminLoad(); return; }
  tbRender(TB.me.team ? tbMyTeamHtml(TB.me.team) : tbNoTeamHtml());
  if (TB.me.team && TB.me.team.is_captain && typeof tbBindCaptain === "function") tbBindCaptain();
}

// ---------------- Teami yo'q: tushuntirish + team ochish ----------------
function tbNoTeamHtml() {
  const em = TB.me.emojis || [];
  if (!TB.createEmoji) TB.createEmoji = em[0];
  return `
    <div class="card tb-hero">
      <div class="tb-hero-kicker">${ICON.get("swords", 16)} TEAMLAR JANGI</div>
      <div class="tb-hero-title">Jamoangizni yig'ing va jangga kiring</div>
      <ul class="tb-hero-list">
        <li>Team ochasiz yoki do'stingiz teamiga <b>taklif havolasi</b> orqali qo'shilasiz.</li>
        <li>Sardor <b>asosiy tarkib</b>ni tuzadi (${TB.me.lineup_min}–${TB.me.lineup_max} kishi).</li>
        <li>Ikki team bahsida o'yinchilar <b>1v1</b> o'ynaydi — ko'p g'alaba olgan team yutadi.</li>
        <li>Teamlar divizionlarda liga formatida bellashadi.</li>
      </ul>
    </div>
    <div class="section-label">TEAM OCHISH</div>
    <div class="card tb-form">
      <input id="tb-name" class="modal-input" maxlength="${TB.me.name_max}" placeholder="Team nomi (${TB.me.name_min}–${TB.me.name_max} belgi)" autocomplete="off">
      <div class="tb-form-label">Belgi</div>
      <div class="tb-emoji-grid">${em.map(e =>
        `<button class="tb-emoji${e === TB.createEmoji ? " active" : ""}" data-tb-emoji="${escHtml(e)}">${escHtml(e)}</button>`).join("")}</div>
      <button class="btn btn--primary btn--glow" data-tb="create">⚔️ Team ochish</button>
      <div class="tb-hint">Team admin tasdig'idan keyin turnirda qatnashadi. A'zolarni hozirdan yig'ishingiz mumkin.</div>
    </div>
    <div class="tb-hint tb-hint--center">Do'stingiz teamiga qo'shilish uchun undan taklif havolasini so'rang.</div>`;
}

const TB_STATUS = { pending: ["⏳ Tasdiq kutilmoqda", "pending"], approved: ["✅ Tasdiqlangan", "approved"],
                    rejected: ["❌ Rad etilgan", "rejected"] };

function tbTeamHeadHtml(t) {
  const [label, cls] = TB_STATUS[t.status] || [t.status, ""];
  return `
    <div class="card tb-team-head">
      <div class="tb-team-emoji">${escHtml(t.emoji || "⚔️")}</div>
      <div class="tb-team-name">${escHtml(t.name)}</div>
      <span class="tb-status tb-status--${cls}">${escHtml(label)}</span>
      <div class="tb-team-meta">Sardor: <b>${escHtml(tbWho({ username: t.captain_username, nickname: t.captain_nickname }))}</b></div>
      <div class="tb-team-stats">
        <div><b>${t.members_count}</b><span>A'ZO</span></div>
        <div><b>${t.lineup_count ?? "—"}</b><span>ASOSIY TARKIB</span></div>
      </div>
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
      <div class="tb-member-info"><b>${escHtml(tbWho(m))}</b>${role}${lu}
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
    TB.teams = (await apiFetch("/tb/teams")).teams || [];
  } catch (e) {
    tbRender(`<div class="empty-state">${escHtml(tbErr(e))}</div>`);
    return;
  }
  const rows = TB.teams.map((t, i) => `
    <button class="tb-team-row" data-tb-team="${t.id}">
      <span class="tb-row-n">${i + 1}</span>
      <span class="tb-row-emoji">${escHtml(t.emoji || "⚔️")}</span>
      <span class="tb-row-info"><b>${escHtml(t.name)}</b><span>Sardor: ${escHtml(tbWho({ username: t.captain_username, nickname: t.captain_nickname }))}</span></span>
      <span class="tb-row-count">${t.members_count}<small>a'zo</small></span>
    </button>`).join("");
  tbRender(`<div class="section-label">TASDIQLANGAN TEAMLAR (${TB.teams.length})</div>
    ${rows || `<div class="empty-state">Hozircha tasdiqlangan team yo'q</div>`}`);
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
    if (okMsg) showToast(okMsg);
    TB.me = await apiFetch("/tb/me");
    TB.lineupSel = null;
    tbRenderTab();
    return true;
  } catch (e) {
    showToast("❌ " + tbErr(e));
    if (btn) btn.disabled = false;
    return false;
  }
}

function tbHandleClick(e) {
  const t = e.target;
  if (!t.closest) return;
  const tab = t.closest("[data-tb-tab]");
  if (tab) { TB.tab = tab.dataset.tbTab; tbRenderTab(); return; }
  const emo = t.closest("[data-tb-emoji]");
  if (emo) {
    TB.createEmoji = emo.dataset.tbEmoji;
    document.querySelectorAll(".tb-emoji").forEach(b => b.classList.toggle("active", b === emo));
    return;
  }
  const team = t.closest("[data-tb-team]");
  if (team) { void tbOpenTeam(team.dataset.tbTeam); return; }
  const kick = t.closest("[data-tb-kick]");
  if (kick && confirm("A'zo teamdan chiqarilsinmi?")) { void tbAction("/tb/members/remove", { user_id: +kick.dataset.tbKick }, "✅ Chiqarildi", kick); return; }
  const cap = t.closest("[data-tb-cap]");
  if (cap && confirm("Sardorlik shu a'zoga topshirilsinmi? Siz oddiy a'zo bo'lib qolasiz.")) {
    void tbAction("/tb/captain/transfer", { user_id: +cap.dataset.tbCap }, "✅ Sardorlik topshirildi", cap); return;
  }
  const act = t.closest("[data-tb]");
  if (!act) return;
  const a = act.dataset.tb;
  if (a === "exit") exitTeamBattle();
  else if (a === "back") { TB.joinCode = null; TB.view = null; tbRenderTab(); }
  else if (a === "create") {
    const name = (document.getElementById("tb-name")?.value || "").trim();
    void tbAction("/tb/teams", { name, emoji: TB.createEmoji }, "✅ Team ochildi! Endi a'zolarni taklif qiling", act);
  } else if (a === "join") {
    const code = TB.joinCode;
    TB.joinCode = null;
    void tbAction("/tb/join", { code }, "✅ Teamga qo'shildingiz", act);
  } else if (a === "leave" && confirm("Teamdan chiqasizmi?")) void tbAction("/tb/leave", {}, "Teamdan chiqdingiz", act);
  else if (a === "dissolve" && confirm("Team butunlay tarqatilsinmi? Barcha a'zolar chiqariladi. Qaytarib bo'lmaydi!")) {
    void tbAction("/tb/dissolve", {}, "Team tarqatildi", act);
  } else if (typeof tbCaptainClick === "function") tbCaptainClick(a, act);
}
