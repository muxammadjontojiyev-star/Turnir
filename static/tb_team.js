// =============================================================
//  tb_team.js — "TEAMLAR JANGI": sardor bloklari (2026-10-15, 1-bosqich)
//  1) Taklif havolasi: olish, nusxalash, Telegram'da ulashish, yangilash.
//  2) Asosiy tarkib muharriri: a'zoni bosish — tarkibga qo'shadi/olib tashlaydi
//     (bosilish tartibi = tarkib tartibi), TB.me.lineup_min..max oralig'ida saqlanadi.
//  3) 2026-10-16: team logosi — galereyadan (tb_logo.js).
//  tb.js dan KEYIN ulanadi. Global: TB, tbAction, tbErr, tbWho, apiFetch, escHtml, showToast.
// =============================================================

// 2026-11-07: dizayn — sardor bloklari alohida panellar (tb_my.js plitkalari ochadi). Asosiy tarkib — tb_my.js
// (a'zolar ro'yxatidan «＋»); eski «bosib tanlash» muharriri olib tashlandi.
function tbCapInviteHtml() {
  return `
    <div class="card tb-invite">
      <div class="tb-hint">Havolani do'stlaringizga yuboring — bosgan kishi teamingizga qo'shiladi.</div>
      <div id="tb-invite-box"><button class="btn btn--primary" data-tb="invite">🔗 Havolani olish</button></div>
    </div>`;
}

function tbCapLogoHtml(t) {
  return `<div class="card">${tbLogoPickerHtml("team", t.id, t.logo_ver, t.emoji)}</div>`;
}

function tbBindCaptain() { /* bosishlar tbHandleClick -> tbCaptainClick orqali (delegation) */ }

function tbRerenderMyTeam() {
  const body = document.querySelector("#tb-root .tb-body");
  const scroll = window.scrollY;
  if (body && TB.me && TB.me.team) {
    body.innerHTML = tbMyTeamHtml(TB.me.team);
    if (TB._inviteLink) tbShowInvite(TB._inviteLink);
    tbI18nApply(body);
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
  tbI18nApply(box);
}

async function tbCopy(text) {
  try { await navigator.clipboard.writeText(text); tbToast("✅ Nusxalandi"); }
  catch (_) {
    const ta = document.createElement("textarea");
    ta.value = text; document.body.appendChild(ta); ta.select();
    try { document.execCommand("copy"); tbToast("✅ Nusxalandi"); } catch (__) { tbToast(text); }
    ta.remove();
  }
}

// tb.js tbHandleClick -> sardor amallari
function tbCaptainClick(a, btn) {
  const luBtn = btn.closest("[data-tb-lu]");
  if (a === "invite" || a === "invite-regen") {
    if (a === "invite-regen" && !tbConfirm("Yangi havola yaratilsinmi? Eski havola ishlamay qoladi.")) return;
    btn.disabled = true;
    apiFetch(a === "invite" ? "/tb/invite-link" : "/tb/invite/regen", a === "invite" ? undefined : { method: "POST" })
      .then(d => { tbShowInvite(d.link); if (a === "invite-regen") tbToast("✅ Yangi havola tayyor"); })
      .catch(e => { tbToast("❌ " + tbErr(e)); btn.disabled = false; });
  } else if (a === "invite-copy" && TB._inviteLink) {
    void tbCopy(TB._inviteLink);
  } else if (a === "invite-share" && TB._inviteLink) {
    const text = `⚔️ «${TB.me.team.name}» teamiga qo'shiling — Teamlar jangi!`;
    const url = `https://t.me/share/url?url=${encodeURIComponent(TB._inviteLink)}&text=${encodeURIComponent(text)}`;
    const tg = window.Telegram?.WebApp;
    if (tg?.openTelegramLink) tg.openTelegramLink(url); else window.open(url, "_blank");
  }
  void luBtn;
}
