// =============================================================
//  tb_public.js — "TEAMLAR JANGI": TEAMI YO'QLAR UCHUN OCHIQ LIGALAR TEAMLARI (2026-11-07, egasi: bosh admin tanlagan
//  liga teamlari teamga qo'shilmoqchi bo'lganlarga ko'rinsin; teami yo'qlar sardorning Telegram chatiga yoza olsin).
//  «Teamim» (teami yo'q) va «Teamlar» (ligasi yo'q) ekranlarida #tb-public-box ga chiziladi.
//  Backend: GET /tb/public-teams (tb_api_public.py). «✈️ Sardorga yozish» — t.me/<username> (bo'lmasa tg://user?id=).
//  Global: TB, apiFetch, escHtml, tbLogo, tbWho, tbI18nApply, tbToast.
// =============================================================

const TBPUB = { data: null, at: 0 };
const TBPUB_TTL_MS = 60 * 1000;

function tbPublicBoxHtml() {
  return `<div id="tb-public-box"></div>`;
}

function tbPublicHtml(groups) {
  if (!groups || !groups.length) return "";
  return `<div class="section-label">QO'SHILISH MUMKIN BO'LGAN TEAMLAR</div>
    <div class="tb-hint tb-pub-hint">Yoqqan teamning sardoriga yozing — u sizga taklif havolasini yuboradi.</div>
    ${groups.map(g => `
      <div class="tb-pub-league">${tbLogo("league", g.league.id, g.league.logo_ver, g.league.emoji, "tb-logo--xs")} <b>${escHtml(g.league.name)}</b></div>
      <div class="card tb-pub-list">${g.teams.map(t => `
        <div class="tb-pub-row">
          <span class="tb-row-emoji">${tbLogo("team", t.id, t.logo_ver, t.emoji)}</span>
          <span class="tb-pub-info"><b>${escHtml(t.name)}</b>
            <span>Sardor: ${escHtml(tbWho({ username: t.captain_username, nickname: t.captain_nickname }))} · ${Number(t.members_count)} a'zo</span></span>
          ${t.captain_username || t.captain_tg
            ? `<button class="tb-pub-msg" data-tb-capmsg="${escHtml(t.captain_username || "")}" data-tb-captg="${Number(t.captain_tg) || ""}">✈️ Yozish</button>` : ""}
        </div>`).join("")}</div>`).join("")}`;
}

async function tbPublicMount() {
  const box = document.getElementById("tb-public-box");
  if (!box) return;
  if (!TBPUB.data || Date.now() - TBPUB.at > TBPUB_TTL_MS) {
    try { TBPUB.data = (await apiFetch("/tb/public-teams")).leagues || []; TBPUB.at = Date.now(); }
    catch (_) { TBPUB.data = []; }
  }
  const el = document.getElementById("tb-public-box");
  if (!el) return;
  el.innerHTML = tbPublicHtml(TBPUB.data);
  tbI18nApply(el);
}

function tbOpenCaptainChat(username, tgId) {
  const w = window.Telegram?.WebApp;
  if (username) {
    const link = `https://t.me/${encodeURIComponent(String(username).replace(/^@/, ""))}`;
    if (w?.openTelegramLink) { try { w.openTelegramLink(link); return; } catch (_) { /* pastdagi zaxira */ } }
    window.open(link, "_blank");
  } else if (tgId) {
    const link = `tg://user?id=${encodeURIComponent(tgId)}`;
    if (w?.openLink) { try { w.openLink(link); return; } catch (_) { /* pastdagi zaxira */ } }
    window.open(link, "_blank");
  } else tbToast("Sardor bilan bog'lanib bo'lmaydi");
}

document.addEventListener("click", (e) => {
  const b = e.target.closest ? e.target.closest("#tb-root [data-tb-capmsg]") : null;
  if (!b) return;
  e.preventDefault();
  tbOpenCaptainChat(b.dataset.tbCapmsg, b.dataset.tbCaptg);
});
