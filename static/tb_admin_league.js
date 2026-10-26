// =============================================================
//  tb_admin_league.js — "TEAMLAR JANGI": ligalar boshqaruvi (Admin tabi tepasi, 2026-10-16)
//  Bosh admin: liga ochish (nom, admin @username/ID), admin tayinlash, bo'sh ligani o'chirish.
//  Liga admini (va bosh admin): liga tanlash, sozlamalar (nom, logo — galereyadan (tb_logo.js), tarkib min/max,
//  divizion hajmi), liga taklif havolasi (nusxalash/ulashish/yangilash).
//  2026-10-26: bosh admin — «🌐 Barcha ligalarga qo'llash» (tarkib min/max, divizion hajmi bir bosishda,
//  POST /tb/admin/leagues/bulk-settings; bo'sh maydon — o'zgarmaydi).
//  Backend: tb_api_league.py. tb_admin.js tbAdminLoad/tbAdminRender chaqiradi.
//  Global: TB, apiFetch, escHtml, tbToast, tbConfirm, tbErr, tbWho, tbCopy, tbAdminLoad.
// =============================================================

async function tbAdminLeaguesLoad() {
  TB.adminLeagues = (await apiFetch("/tb/admin/leagues")).leagues || [];
  const ids = TB.adminLeagues.map(l => l.id);
  if (!ids.includes(TB.adminLeagueId)) {
    const mine = TB.me && TB.me.team && TB.me.team.league_id;
    TB.adminLeagueId = ids.includes(mine) ? mine : (ids[0] || null);
    TB.adminLeagueLink = null;
  }
}

function tbAdminCurLeague() { return (TB.adminLeagues || []).find(l => l.id === TB.adminLeagueId) || null; }

function tbAdminLeaguesHtml() {
  const list = TB.adminLeagues || [];
  const chips = list.map(l => `<button class="tb-chip${l.id === TB.adminLeagueId ? " active" : ""}" data-tbl-pick="${l.id}">
      ${tbLogo("league", l.id, l.logo_ver, l.emoji, "tb-logo--xs")} ${escHtml(l.name)}${l.pending ? ` <b class="tb-chip-badge">${l.pending}</b>` : ""}</button>`).join("");
  const add = TB.me.is_super ? `<button class="tb-chip tb-chip--add" data-tbl="new">➕ Liga</button>` : "";
  let html = `<div class="section-label">LIGALAR</div><div class="tb-chips">${chips}${add}</div>`;
  if (TB.me.is_super && TB.adminLeagueForm) {
    html += `<div class="card tb-form">
        <input id="tbl-new-name" class="modal-input" maxlength="${TB.me.name_max}" placeholder="Liga nomi">
        <input id="tbl-new-admin" class="modal-input" placeholder="Liga admini: @username yoki Telegram ID">
        <button class="btn btn--primary" data-tbl="create">🏆 Liga ochish</button>
        <div class="tb-hint">Admin keyin ham tayinlanishi mumkin. U botga /start bosgan bo'lishi kerak. Logo — ochilgandan keyin Sozlamalarda (galereyadan).</div>
      </div>`;
  }
  if (!list.length) return html + `<div class="empty-state">Hali liga yo'q${TB.me.is_super ? " — «➕ Liga» bilan oching" : ""}</div>`;
  if (TB.me.is_super) html += tbAdminBulkHtml(list.length);
  const l = tbAdminCurLeague();
  if (!l) return html;
  const admin = l.admin_username || l.admin_nickname ? tbWho({ username: l.admin_username, nickname: l.admin_nickname }) : "— (faqat bosh admin)";
  html += `<div class="card tb-adm-league">
      <div class="tb-adm-league-head">${tbLogo("league", l.id, l.logo_ver, l.emoji, "tb-logo--lg")}<div><b>${escHtml(l.name)}</b>
        <small>Admin: ${escHtml(admin)} · ${l.teams} team${l.pending ? ` · ${l.pending} ariza` : ""}</small></div></div>
      <div class="tb-adm-acts">
        <button class="btn btn--primary" data-tbl="link">🔗 Liga havolasi</button>
      </div>
      <div id="tbl-link-box">${TB.adminLeagueLink ? tbAdminLinkHtml() : ""}</div>
      <details class="tb-adm-settings"><summary>⚙️ Sozlamalar</summary>
        <input id="tbl-name" class="modal-input" maxlength="${TB.me.name_max}" value="${escHtml(l.name)}" placeholder="Liga nomi">
        <div class="tb-form-label">Liga logosi</div>${tbLogoPickerHtml("league", l.id, l.logo_ver, l.emoji)}
        <div class="tb-adm-line"><span>Asosiy tarkib: kamida</span><input id="tbl-lmin" class="modal-input" type="number" min="3" max="30" value="${l.lineup_min}"></div>
        <div class="tb-adm-line"><span>Asosiy tarkib: ko'pi bilan</span><input id="tbl-lmax" class="modal-input" type="number" min="3" max="30" value="${l.lineup_max}"></div>
        <div class="tb-adm-line"><span>Divizion hajmi</span><input id="tbl-div" class="modal-input" type="number" min="4" max="20" value="${l.division_size}"></div>
        <button class="btn btn--primary" data-tbl="save">💾 Saqlash</button>
        <div class="tb-hint">Tarkib minimumidan kam o'yinchisi bor team bahsda texnik mag'lubiyat oladi.</div>
      </details>
      ${TB.me.is_super ? `<details class="tb-adm-settings"><summary>🛡 Liga admini (bosh admin)</summary>
        <input id="tbl-admin" class="modal-input" placeholder="@username yoki Telegram ID (bo'sh — olib tashlash)">
        <button class="btn btn--ghost" data-tbl="set-admin">Tayinlash</button>
        <button class="btn btn--ghost tb-danger-btn" data-tbl="delete">🗑 Ligani o'chirish</button>
        <div class="tb-hint">Faqat teamsiz va mavsumsiz liga o'chiriladi.</div>
      </details>` : ""}
    </div>`;
  return html;
}

// 2026-10-26: bosh admin — sozlamalarni barcha ligalarga birdan qo'llash
function tbAdminBulkHtml(n) {
  return `<details class="card tb-adm-settings tb-adm-bulk"><summary>🌐 Barcha ligalarga qo'llash (${n} ta liga)</summary>
      <div class="tb-adm-line"><span>Asosiy tarkib: kamida</span><input id="tbl-b-lmin" class="modal-input" type="number" min="3" max="30" placeholder="—"></div>
      <div class="tb-adm-line"><span>Asosiy tarkib: ko'pi bilan</span><input id="tbl-b-lmax" class="modal-input" type="number" min="3" max="30" placeholder="—"></div>
      <div class="tb-adm-line"><span>Divizion hajmi</span><input id="tbl-b-div" class="modal-input" type="number" min="4" max="20" placeholder="—"></div>
      <button class="btn btn--primary" data-tbl="bulk">🌐 Hammasiga qo'llash</button>
      <div class="tb-hint">Bo'sh qoldirilgan maydon hech bir ligada o'zgarmaydi. Divizion hajmi keyingi qur'adan ta'sir qiladi. Tarkib minimumi «N vs N»siz ochilgan joriy mavsumda keyingi turlardan qo'llanadi — tarkibi yetmagan team texnik mag'lubiyat oladi.</div>
    </details>`;
}

async function tbAdminBulkApply(btn) {
  const num = (id) => { const v = (document.getElementById(id)?.value || "").trim(); return v === "" ? null : +v; };
  const body = { lineup_min: num("tbl-b-lmin"), lineup_max: num("tbl-b-lmax"), division_size: num("tbl-b-div") };
  if (Object.values(body).every(v => v === null)) { tbToast("Kamida bitta qiymat kiriting"); return; }
  const n = (TB.adminLeagues || []).length;
  if (!tbConfirm(`Sozlamalar ${n} ta liganing hammasiga qo'llansinmi?`)) return;
  const r = await tbAdminLeaguePost("/tb/admin/leagues/bulk-settings", body, null, btn);
  if (!r) return;
  const bad = (r.failed || []).map(f => `${f.name}: ${tbErr({ message: f.reason })}`);
  tbToast(`✅ ${r.updated} ta ligaga qo'llandi` + (bad.length ? ` · ${bad.length} tasida xato — ${bad.join("; ")}` : ""));
  await tbAdminReloadAll();
}

function tbAdminLinkHtml() {
  return `<div class="tb-invite-link">${escHtml(TB.adminLeagueLink)}</div>
    <div class="tb-invite-acts">
      <button class="btn btn--primary" data-tbl="share">📤 Ulashish</button>
      <button class="btn btn--ghost" data-tbl="copy">📋 Nusxalash</button>
    </div>
    <button class="tb-mini" data-tbl="regen">↻ Yangi havola (eskisi ishlamay qoladi)</button>
    <div class="tb-hint">Havolani bosgan kishi shu ligada team ochadi; team sizning tasdig'ingizdan keyin qatnashadi.</div>`;
}

async function tbAdminLeaguePost(path, body, okMsg, btn) {
  if (btn) btn.disabled = true;
  try {
    const r = await apiFetch(path, { method: "POST", body: JSON.stringify(body) });
    if (okMsg) tbToast(okMsg);
    return r;
  } catch (e) {
    tbToast("❌ " + tbErr(e));
    if (btn) btn.disabled = false;
    return null;
  }
}

async function tbAdminLeagueAct(a, btn) {
  const lid = TB.adminLeagueId;
  const val = (id) => (document.getElementById(id)?.value || "").trim();
  if (a === "new") { TB.adminLeagueForm = !TB.adminLeagueForm; tbAdminRender(); return; }
  if (a === "bulk") { await tbAdminBulkApply(btn); return; }
  if (a === "create") {
    const r = await tbAdminLeaguePost("/tb/admin/leagues",
      { name: val("tbl-new-name"), admin_who: val("tbl-new-admin") || null }, "✅ Liga ochildi", btn);
    if (r) { TB.adminLeagueForm = false; TB.adminLeagueId = r.league_id; TB.adminLeagueLink = null; await tbAdminReloadAll(); }
  } else if (a === "save") {
    const r = await tbAdminLeaguePost("/tb/admin/league/settings", { league_id: lid, name: val("tbl-name"),
      lineup_min: +val("tbl-lmin"), lineup_max: +val("tbl-lmax"),
      division_size: +val("tbl-div") }, "✅ Sozlamalar saqlandi", btn);
    if (r) await tbAdminReloadAll();
  } else if (a === "set-admin") {
    const r = await tbAdminLeaguePost("/tb/admin/leagues/admin", { league_id: lid, admin_who: val("tbl-admin") || null },
      "✅ Liga admini yangilandi", btn);
    if (r) await tbAdminLoad();
  } else if (a === "delete") {
    if (!tbConfirm("Liga o'chirilsinmi?")) return;
    const r = await tbAdminLeaguePost("/tb/admin/leagues/delete", { league_id: lid }, "Liga o'chirildi", btn);
    if (r) { TB.adminLeagueId = null; await tbAdminLoad(); }
  } else if (a === "link" || a === "regen") {
    if (a === "regen" && !tbConfirm("Yangi havola yaratilsinmi? Eski havola ishlamay qoladi.")) return;
    btn.disabled = true;
    try {
      const d = a === "link" ? await apiFetch(`/tb/admin/league/link?league_id=${lid}`)
        : await apiFetch("/tb/admin/league/link/regen", { method: "POST", body: JSON.stringify({ league_id: lid }) });
      TB.adminLeagueLink = d.link;
      const box = document.getElementById("tbl-link-box");
      if (box) { box.innerHTML = tbAdminLinkHtml(); tbI18nApply(box); }
      if (a === "regen") tbToast("✅ Yangi havola tayyor");
    } catch (e) { tbToast("❌ " + tbErr(e)); }
    btn.disabled = false;
  } else if (a === "copy" && TB.adminLeagueLink) {
    void tbCopy(TB.adminLeagueLink);
  } else if (a === "share" && TB.adminLeagueLink) {
    const l = tbAdminCurLeague();
    const text = `🏆 «${l ? l.name : ""}» ligasi — team ochib qo'shiling! (Teamlar jangi)`;
    const url = `https://t.me/share/url?url=${encodeURIComponent(TB.adminLeagueLink)}&text=${encodeURIComponent(text)}`;
    const tg = window.Telegram?.WebApp;
    if (tg?.openTelegramLink) tg.openTelegramLink(url); else window.open(url, "_blank");
  }
}

// /tb/me ham yangilanadi (tarkib chegaralari, liga nomi o'zgargan bo'lishi mumkin)
async function tbAdminReloadAll() {
  try { TB.me = await apiFetch("/tb/me"); } catch (_) { /* admin ro'yxati baribir yangilanadi */ }
  await tbAdminLoad();
}

document.addEventListener("click", (e) => {
  if (!e.target.closest) return;
  const pick = e.target.closest("#tb-root [data-tbl-pick]");
  if (pick) {
    TB.adminLeagueId = +pick.dataset.tblPick;
    TB.adminLeagueLink = null;
    if (typeof TBS !== "undefined") { TBS.division = null; TBS.round = null; }
    void tbAdminLoad();
    return;
  }
  const b = e.target.closest("#tb-root [data-tbl]");
  if (b) void tbAdminLeagueAct(b.dataset.tbl, b);
});

Object.assign(TB_ERR, { nothing_to_update: "Kamida bitta qiymat kiriting" });   // 2026-10-26
