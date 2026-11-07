// =============================================================
//  tb_my.js — "TEAMLAR JANGI": «Teamim» sahifasi (2026-11-07, egasi: «juda chiroyli, hammaga tushunarli va qulay»).
//  Team kartasi → plitkalar (sardor: Taklif · Tarkib · A'zolar · Forma · Logo; a'zo: Tarkib · A'zolar · Forma) →
//  bitta ochiq panel → pastda «Xavfli amallar».
//  * A'zolar: har bir a'zo O'NG tomonida «＋» — asosiy tarkibga qo'shadi (liga maksimumidan ko'p — yo'q); tarkibdagida «✓».
//    Sardor a'zo qatorini bosadi → oyna: «👑 Sardor qilib tayinlash» / «🚪 Teamdan chiqarish».
//  * Asosiy tarkib: faqat «＋» bilan qo'shilganlar (bo'sh — izoh); sardorda o'ngda «−» (olib tashlash).
//  * Forma: tb_form.js (10 ballik baho, MVP).
//  tb.js (tbTeamHeadHtml, tbMemberRowHtml), tb_team.js (tbCap*Html), tb_form.js dan KEYIN ulanadi.
//  Global: TB, escHtml, tbI18nApply, tbRerenderMyTeam, tbAction, tbToast, tbConfirm, tbAvatarHtml, tbNameHtml, tbWho.
// =============================================================

const TB_MY_SECS = {
  invite: { ic: "🔗", t: "Taklif qilish", cap: true },
  lineup: { ic: "📋", t: "Asosiy tarkib" },
  members: { ic: "👥", t: "A'zolar" },
  form: { ic: "📈", t: "Forma" },
  logo: { ic: "🖼", t: "Team logosi", cap: true },
};

function tbLineupIds(t) {
  return t.members.filter(m => m.in_lineup).sort((a, b) => a.lineup_pos - b.lineup_pos).map(m => m.user_id);
}

function tbMySecDefault(t) {
  const lineup = tbLineupIds(t).length;
  if (t.is_captain && t.members.length < TB.me.lineup_min) return "invite";      // a'zo yetmaydi — avval taklif
  if (t.is_captain && lineup < TB.me.lineup_min) return "members";             // «＋» bilan tarkib yig'ish
  return "lineup";
}

function tbMyTileHtml(key, t) {
  const s = TB_MY_SECS[key];
  const lineup = tbLineupIds(t).length;
  const lmin = TB.me.lineup_min;
  const sub = {
    invite: "Do'stlarni chaqiring", lineup: `${lineup} / ${TB.me.lineup_max}`, members: `${t.members.length} kishi`,
    form: "Kim qanday o'ynayapti", logo: "Galereyadan",
  }[key];
  const warn = key === "lineup" && lineup < lmin;
  return `<button class="tb-tile${TB.mySec === key ? " active" : ""}${warn ? " warn" : ""}" data-tb-sec="${key}">
      <span class="tb-tile-ic">${s.ic}</span>
      <span class="tb-tile-t">${escHtml(s.t)}</span>
      <span class="tb-tile-s">${escHtml(sub)}</span>
    </button>`;
}

function tbLineupBarHtml(t) {
  const n = tbLineupIds(t).length, { lineup_min: lmin, lineup_max: lmax } = TB.me;
  return `<div class="tb-lu-bar">
      <span>Asosiy tarkib: <b class="${n >= lmin && n <= lmax ? "tb-ok" : "tb-bad"}">${n}</b> / ${lmax}</span>
      <small>${n >= lmax ? "Tarkib to'ldi" : `«＋» — tarkibga qo'shish${n < lmin ? ` · kamida ${lmin} kishi kerak` : ""}`}</small>
    </div>`;
}

function tbLineupToggleHtml(m, t) {
  const ids = tbLineupIds(t);
  const pos = ids.indexOf(m.user_id);
  if (pos >= 0) {
    return `<button class="tb-lu-tog on" data-tb-lutog="${m.user_id}" title="Tarkibdan olish" aria-label="Tarkibdan olish">✓<i>${pos + 1}</i></button>`;
  }
  const full = ids.length >= TB.me.lineup_max;
  return `<button class="tb-lu-tog${full ? " full" : ""}" data-tb-lutog="${m.user_id}" ${full ? "disabled" : ""}
      title="${full ? "Tarkib to'ldi" : "Tarkibga qo'shish"}" aria-label="Tarkibga qo'shish">＋</button>`;
}

// Asosiy tarkib — faqat qo'shilganlar, tartib bilan; sardorda o'ngda «−»
function tbLineupPanelHtml(t) {
  const cap = t.is_captain;
  const byId = new Map(t.members.map(m => [m.user_id, m]));
  const list = tbLineupIds(t).map(id => byId.get(id)).filter(Boolean);
  const lmin = TB.me.lineup_min;
  const warn = list.length < lmin
    ? `<div class="tb-warn">Asosiy tarkib to'liq emas: ${list.length}/${lmin}. ${cap ? "A'zolar bo'limidan «＋» bilan qo'shing." : "Sardor tarkibni tuzishi kerak."}</div>` : "";
  if (!list.length) {
    return `${warn}<div class="card tb-empty-lu"><span>📋</span><b>Asosiy tarkib hali bo'sh</b>
      <small>${cap ? "A'zolar bo'limida o'yinchi o'ng tomonidagi «＋» ni bosing — u shu yerda paydo bo'ladi." : "Sardor tarkibni tuzganda shu yerda ko'rinadi."}</small>
      ${cap ? `<button class="btn btn--primary" data-tb-sec="members">👥 A'zolarga o'tish</button>` : ""}</div>`;
  }
  return `${warn}<div class="card tb-list">${list.map((m, i) => `
    <div class="tb-member">
      <span class="tb-lu-num">${i + 1}</span>
      ${tbAvatarHtml(m)}
      <div class="tb-member-info">${tbNameHtml(m)}${m.role === "captain" ? `<span class="tb-badge tb-badge--cap">SARDOR</span>` : ""}</div>
      ${cap ? `<button class="tb-lu-tog tb-lu-tog--rm" data-tb-lutog="${m.user_id}" title="Tarkibdan olish" aria-label="Tarkibdan olish">−</button>` : ""}
    </div>`).join("")}</div>`;
}

function tbMyPanelHtml(key, t) {
  const cap = t.is_captain;
  if (key === "invite" && cap) return tbCapInviteHtml(t);
  if (key === "logo" && cap) return tbCapLogoHtml(t);
  if (key === "lineup") return tbLineupPanelHtml(t);
  if (key === "form") return typeof tbFormBoxHtml === "function" ? tbFormBoxHtml() : "";
  const head = cap ? tbLineupBarHtml(t) + `<div class="tb-hint tb-mem-hint">O'yinchi qatorini bosing — sardor qilish yoki teamdan chiqarish.</div>` : "";
  return `${head}<div class="card tb-list">${t.members.map(m => tbMemberRowHtml(m, t, cap)).join("")}</div>`;
}

function tbMyTeamHtml(t) {
  const cap = t.is_captain;
  const keys = Object.keys(TB_MY_SECS).filter(k => cap || !TB_MY_SECS[k].cap);
  if (!keys.includes(TB.mySec)) TB.mySec = tbMySecDefault(t);
  if (TB.mySec === "form" && typeof tbFormMount === "function") setTimeout(() => void tbFormMount(t.id), 0);
  return `
    ${tbTeamHeadHtml(t)}
    ${t.status === "pending" ? `<div class="tb-note">Team admin tasdig'ini kutmoqda. Shu vaqtda a'zolarni yig'ib, tarkibni tuzib qo'ying.</div>` : ""}
    <div class="tb-tiles tb-tiles--${keys.length}">${keys.map(k => tbMyTileHtml(k, t)).join("")}</div>
    <div class="tb-panel">
      <div class="tb-panel-title">${TB_MY_SECS[TB.mySec].ic} <span>${escHtml(TB_MY_SECS[TB.mySec].t)}</span></div>
      ${tbMyPanelHtml(TB.mySec, t)}
    </div>
    <details class="tb-danger-zone"><summary>⚠️ Xavfli amallar</summary>
      ${cap
        ? `<div class="tb-hint">Team butunlay o'chadi, barcha a'zolar chiqariladi. Mavsum davomida tarqatib bo'lmaydi.</div>
           <button class="btn btn--ghost tb-danger-btn" data-tb="dissolve">Teamni tarqatish</button>`
        : `<button class="btn btn--ghost tb-danger-btn" data-tb="leave">Teamdan chiqish</button>`}
    </details>`;
}

async function tbLineupToggle(btn) {
  const t = TB.me && TB.me.team;
  if (!t || !t.is_captain || btn.disabled) return;
  const id = +btn.dataset.tbLutog;
  const ids = tbLineupIds(t);
  const next = ids.includes(id) ? ids.filter(x => x !== id) : ids.concat(id);
  if (next.length > TB.me.lineup_max) { tbToast(`Ko'pi bilan ${TB.me.lineup_max} kishi`); return; }
  await tbAction("/tb/lineup", { user_ids: next }, ids.includes(id) ? "Tarkibdan olindi" : "✅ Tarkibga qo'shildi", btn);
}

// ---- Sardor: a'zo qatorini bosish → amallar oynasi ----
function tbMemberSheet(userId) {
  const t = TB.me && TB.me.team;
  const m = t && t.members.find(x => x.user_id === userId);
  if (!m || !t.is_captain || m.role === "captain") return;
  tbMemberSheetClose();
  const wrap = document.createElement("div");
  wrap.className = "tb-sheet-wrap";
  wrap.innerHTML = `<div class="tb-sheet" role="dialog">
      <div class="tb-sheet-head">${tbAvatarHtml(m)}<div><b>${escHtml(tbWho(m))}</b><small>${escHtml(m.nickname || "")}</small></div></div>
      <button class="tb-sheet-btn" data-tb-sheet="cap" data-id="${m.user_id}">👑 <span>Sardor qilib tayinlash</span></button>
      <button class="tb-sheet-btn tb-sheet-btn--danger" data-tb-sheet="kick" data-id="${m.user_id}">🚪 <span>Teamdan chiqarish</span></button>
      <button class="tb-sheet-btn tb-sheet-btn--ghost" data-tb-sheet="close">Bekor qilish</button>
    </div>`;
  document.body.appendChild(wrap);
  tbI18nApply(wrap);
  requestAnimationFrame(() => wrap.classList.add("open"));
}
function tbMemberSheetClose() { document.querySelectorAll(".tb-sheet-wrap").forEach(x => x.remove()); }

async function tbMemberSheetAct(btn) {
  const a = btn.dataset.tbSheet, id = +btn.dataset.id;
  if (a === "close") { tbMemberSheetClose(); return; }
  if (a === "cap" && tbConfirm("Sardorlik shu a'zoga topshirilsinmi? Siz oddiy a'zo bo'lib qolasiz.")) {
    tbMemberSheetClose();
    await tbAction("/tb/captain/transfer", { user_id: id }, "✅ Sardorlik topshirildi");
  } else if (a === "kick" && tbConfirm("A'zo teamdan chiqarilsinmi?")) {
    tbMemberSheetClose();
    await tbAction("/tb/members/remove", { user_id: id }, "✅ Chiqarildi");
  }
}

document.addEventListener("click", (e) => {
  if (!e.target.closest) return;
  const sh = e.target.closest("[data-tb-sheet]");
  if (sh) { e.preventDefault(); void tbMemberSheetAct(sh); return; }
  if (e.target.classList && e.target.classList.contains("tb-sheet-wrap")) { tbMemberSheetClose(); return; }
  const tog = e.target.closest("#tb-root [data-tb-lutog]");
  if (tog) { e.preventDefault(); e.stopPropagation(); void tbLineupToggle(tog); return; }
  const mem = e.target.closest("#tb-root [data-tb-mem]");
  if (mem) { e.preventDefault(); tbMemberSheet(+mem.dataset.tbMem); return; }
  const tile = e.target.closest("#tb-root [data-tb-sec]");
  if (!tile || !TB.me || !TB.me.team) return;
  TB.mySec = tile.dataset.tbSec;
  if (typeof tbRerenderMyTeam === "function") tbRerenderMyTeam();
  document.querySelector("#tb-root .tb-panel")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
}, true);
