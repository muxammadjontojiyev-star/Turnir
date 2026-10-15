// =============================================================
//  tb_team.js — "TEAMLAR JANGI": sardor bloklari (2026-10-15, 1-bosqich)
//  1) Taklif havolasi: olish, nusxalash, Telegram'da ulashish, yangilash.
//  2) Asosiy tarkib muharriri: a'zoni bosish — tarkibga qo'shadi/olib tashlaydi
//     (bosilish tartibi = tarkib tartibi), TB.me.lineup_min..max oralig'ida saqlanadi.
//  tb.js dan KEYIN ulanadi. Global: TB, tbAction, tbErr, tbWho, apiFetch, escHtml, showToast.
// =============================================================

function tbCaptainBlocksHtml(t) {
  if (!TB.lineupSel) {
    TB.lineupSel = t.members.filter(m => m.in_lineup)
      .sort((a, b) => a.lineup_pos - b.lineup_pos).map(m => m.user_id);
  }
  const { lineup_min: lmin, lineup_max: lmax } = TB.me;
  const n = TB.lineupSel.length;
  const okN = n >= lmin && n <= lmax;
  const rows = t.members.map(m => {
    const pos = TB.lineupSel.indexOf(m.user_id);
    return `<button class="tb-lu-row${pos >= 0 ? " on" : ""}" data-tb-lu="${m.user_id}">
        <span class="tb-lu-pos">${pos >= 0 ? pos + 1 : ""}</span>
        <span class="tb-lu-name">${escHtml(tbWho(m))}${m.role === "captain" ? ` <span class="tb-badge tb-badge--cap">SARDOR</span>` : ""}</span>
      </button>`;
  }).join("");
  return `
    <div class="section-label">TAKLIF HAVOLASI</div>
    <div class="card tb-invite">
      <div class="tb-hint">Havolani do'stlaringizga yuboring — bosgan kishi teamingizga qo'shiladi.</div>
      <div id="tb-invite-box"><button class="btn btn--primary" data-tb="invite">🔗 Havolani olish</button></div>
    </div>
    <div class="section-label">ASOSIY TARKIB</div>
    <div class="card tb-lineup">
      <div class="tb-lu-head">
        <span>Tanlangan: <b class="${okN ? "tb-ok" : "tb-bad"}">${n}</b> / ${lmin}–${lmax}</span>
        <button class="tb-mini" data-tb="lu-clear">Tozalash</button>
      </div>
      <div class="tb-hint">O'yinchini bosing — tarkibga qo'shiladi (bosish tartibi = tarkib tartibi). Qayta bossangiz olib tashlanadi.</div>
      <div class="tb-lu-list">${rows}</div>
      <button class="btn btn--primary" data-tb="lu-save" ${okN ? "" : "disabled"}>💾 Tarkibni saqlash</button>
      ${t.members.length < lmin ? `<div class="tb-warn">Tarkib uchun kamida ${lmin} a'zo kerak — hozir ${t.members.length} ta. Ko'proq do'st taklif qiling.</div>` : ""}
    </div>`;
}

function tbBindCaptain() { /* bosishlar tbHandleClick -> tbCaptainClick orqali (delegation) */ }

function tbRerenderMyTeam() {
  const body = document.querySelector("#tb-root .tb-body");
  const scroll = window.scrollY;
  if (body && TB.me && TB.me.team) {
    body.innerHTML = tbMyTeamHtml(TB.me.team);
    if (TB._inviteLink) tbShowInvite(TB._inviteLink);
    window.scrollTo(0, scroll);
  }
}

function tbShowInvite(link) {
  TB._inviteLink = link;
  const box = document.getElementById("tb-invite-box");
  if (!box) return;
  box.innerHTML = `
    <div class="tb-invite-link">${escHtml(link)}</div>
    <div class="tb-invite-acts">
      <button class="btn btn--primary" data-tb="invite-share">📤 Ulashish</button>
      <button class="btn btn--ghost" data-tb="invite-copy">📋 Nusxalash</button>
    </div>
    <button class="tb-mini" data-tb="invite-regen">↻ Yangi havola (eskisi ishlamay qoladi)</button>`;
}

async function tbCopy(text) {
  try { await navigator.clipboard.writeText(text); showToast("✅ Nusxalandi"); }
  catch (_) {
    const ta = document.createElement("textarea");
    ta.value = text; document.body.appendChild(ta); ta.select();
    try { document.execCommand("copy"); showToast("✅ Nusxalandi"); } catch (__) { showToast(text); }
    ta.remove();
  }
}

// tb.js tbHandleClick -> sardor amallari
function tbCaptainClick(a, btn) {
  const luBtn = btn.closest("[data-tb-lu]");
  if (a === "invite" || a === "invite-regen") {
    if (a === "invite-regen" && !confirm("Yangi havola yaratilsinmi? Eski havola ishlamay qoladi.")) return;
    btn.disabled = true;
    apiFetch(a === "invite" ? "/tb/invite-link" : "/tb/invite/regen", a === "invite" ? undefined : { method: "POST" })
      .then(d => { tbShowInvite(d.link); if (a === "invite-regen") showToast("✅ Yangi havola tayyor"); })
      .catch(e => { showToast("❌ " + tbErr(e)); btn.disabled = false; });
  } else if (a === "invite-copy" && TB._inviteLink) {
    void tbCopy(TB._inviteLink);
  } else if (a === "invite-share" && TB._inviteLink) {
    const text = `⚔️ «${TB.me.team.name}» teamiga qo'shiling — Teamlar jangi!`;
    const url = `https://t.me/share/url?url=${encodeURIComponent(TB._inviteLink)}&text=${encodeURIComponent(text)}`;
    const tg = window.Telegram?.WebApp;
    if (tg?.openTelegramLink) tg.openTelegramLink(url); else window.open(url, "_blank");
  } else if (a === "lu-clear") {
    TB.lineupSel = [];
    tbRerenderMyTeam();
  } else if (a === "lu-save") {
    void tbAction("/tb/lineup", { user_ids: TB.lineupSel }, "✅ Asosiy tarkib saqlandi", btn);
  }
  void luBtn;
}

// A'zo qatorini bosish (tarkib muharriri) — tb.js'dagi data-tb delegatsiyasidan alohida
document.addEventListener("click", (e) => {
  const row = e.target.closest ? e.target.closest("#tb-root [data-tb-lu]") : null;
  if (!row || !TB.lineupSel) return;
  const id = +row.dataset.tbLu;
  const i = TB.lineupSel.indexOf(id);
  if (i >= 0) TB.lineupSel.splice(i, 1);
  else if (TB.lineupSel.length < TB.me.lineup_max) TB.lineupSel.push(id);
  else { showToast(`Ko'pi bilan ${TB.me.lineup_max} kishi`); return; }
  tbRerenderMyTeam();
});
