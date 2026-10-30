// =============================================================
//  shop_auction.js — Do'kon → «Auksion» tabi (2026-10-30)
//  Bosh admin sotuvga qo'ygan liga klublari uchun muddatli kim oshdi savdosi (eF Token).
//  G'olib keyingi liga mavsumida shu klubga avtomatik yoziladi. Taklif summasi muzlatiladi,
//  oshirilsa qaytadi; oxirgi daqiqalarda taklif tushsa savdo uzayadi (server: snipe_minutes).
//  API: GET /shop/auction, POST /shop/auction/{id}/bid {amount}.
//  Global: SHOP, shopT, shopNum, shopToken, shopRender (shop.js), LEAGUE_CLUBS (api.js), apiFetch, escHtml, showToast.
// =============================================================

const AUC = { data: null, loadedAt: 0, timer: null, busy: false };
const AUC_TICK_MS = 1000;

function aucClubLogo(league, club) {
  const list = (typeof LEAGUE_CLUBS !== "undefined" && LEAGUE_CLUBS[league]) || [];
  const c = list.find(x => x.name === club);
  return c ? `<img src="${escHtml(c.logo)}" alt="" class="auc-logo" onerror="this.style.visibility='hidden'">` : `<span class="auc-logo auc-logo--ph">⚽</span>`;
}

function aucWho(u, nick) { return u ? "@" + u : (nick || ""); }

function aucLeft(sec) {
  if (sec <= 0) return shopT("auc_ending");
  const d = Math.floor(sec / 86400), h = Math.floor(sec % 86400 / 3600), m = Math.floor(sec % 3600 / 60), s = sec % 60;
  const p = n => String(n).padStart(2, "0");
  return d ? shopT("auc_left_d", { d, h }) : `${p(h)}:${p(m)}:${p(s)}`;
}

async function aucLoad() {
  try {
    AUC.data = await apiFetch("/shop/auction");
    AUC.loadedAt = Date.now();
    if (SHOP.data) SHOP.data.balance = AUC.data.balance;
  } catch (e) {
    if (!AUC.data) AUC.data = { error: true };
  }
  if (SHOP.tab === "auction") shopRender();
  aucStartTimer();
}

function aucStartTimer() {
  clearInterval(AUC.timer);
  AUC.timer = setInterval(() => {
    const els = document.querySelectorAll("#shop-root [data-auc-left]");
    if (!els.length) { clearInterval(AUC.timer); return; }
    const passed = Math.floor((Date.now() - AUC.loadedAt) / 1000);
    let expired = false;
    els.forEach(el => {
      const left = Number(el.dataset.aucLeft) - passed;
      el.textContent = aucLeft(left);
      el.classList.toggle("auc-hot", left < (AUC.data.snipe_minutes || 5) * 60);
      if (left <= 0) expired = true;
    });
    if (expired && !AUC.busy) { AUC.busy = true; setTimeout(() => { AUC.busy = false; void aucLoad(); }, 2000); }
  }, AUC_TICK_MS);
}

function shopAuctionHtml() {
  const d = AUC.data;
  if (!d) return `<div class="shop-loading">…</div>`;
  if (d.error) return `<div class="card shop-empty">${escHtml(shopT("shop_err_generic"))}</div>`;
  const block = d.block ? `<div class="card auc-block">⚠️ ${escHtml(shopT("auc_block_" + d.block))}</div>` : "";
  const lots = (d.lots || []).map(l => {
    const lead = l.current_bid != null
      ? (l.is_leader ? `<span class="auc-me">${escHtml(shopT("auc_you_lead"))}</span>` : escHtml(aucWho(l.leader_username, l.leader_nickname)))
      : escHtml(shopT("auc_no_bids"));
    return `<div class="card auc-lot ${l.is_leader ? "auc-lot--lead" : ""}">
        <div class="auc-head">${aucClubLogo(l.league_name, l.club_name)}
          <div class="auc-title"><b>${escHtml(l.club_name)}</b><small>${escHtml(l.league_name)}</small></div>
          <div class="auc-timer"><small>${escHtml(shopT("auc_left"))}</small><span data-auc-left="${Number(l.left_s) || 0}">${escHtml(aucLeft(Number(l.left_s) || 0))}</span></div>
        </div>
        <div class="auc-grid">
          <div><small>${escHtml(shopT(l.current_bid != null ? "auc_current" : "auc_start"))}</small><b>${shopToken("shop-tk shop-tk--xs")} ${shopNum(l.current_bid ?? l.start_price)}</b></div>
          <div><small>${escHtml(shopT("auc_leader"))}</small><span>${lead}</span></div>
          <div><small>${escHtml(shopT("auc_bids"))}</small><span>${Number(l.bids_count) || 0}</span></div>
        </div>
        ${l.is_leader ? "" : `<div class="auc-bid">
          <input class="modal-input" type="number" inputmode="numeric" min="${Number(l.min_bid)}" step="${Number(l.min_step)}" value="${Number(l.min_bid)}" data-auc-amount="${Number(l.id)}" ${d.block ? "disabled" : ""}>
          <button class="btn btn--primary" data-auc-bid="${Number(l.id)}" ${d.block ? "disabled" : ""}>${escHtml(shopT("auc_bid_btn"))}</button>
        </div>
        <div class="auc-min">${escHtml(shopT("auc_min", { min: shopNum(l.min_bid), step: shopNum(l.min_step) }))}</div>`}
      </div>`;
  }).join("");
  const ended = (d.ended || []).map(e => `
    <div class="auc-ended">${aucClubLogo(e.league_name, e.club_name)}
      <div class="auc-title"><b>${escHtml(e.club_name)}</b><small>${escHtml(e.league_name)}</small></div>
      <div class="auc-ended-res">${e.winner_user_id
        ? `${e.is_winner ? `<span class="auc-me">${escHtml(shopT("auc_you_won"))}</span>` : escHtml(aucWho(e.leader_username, e.leader_nickname))}
           <small>${shopNum(e.current_bid)} eF · ${escHtml(shopT("auc_st_" + e.status))}</small>`
        : `<small>${escHtml(shopT("auc_no_bids"))}</small>`}</div>
    </div>`).join("");
  return `${block}
    <div class="auc-rules">${escHtml(shopT("auc_rules", { m: d.snipe_minutes }))}</div>
    <div class="section-label">${escHtml(shopT("auc_active"))}</div>
    ${lots || `<div class="card shop-empty">${escHtml(shopT("auc_none"))}</div>`}
    ${ended ? `<div class="section-label">${escHtml(shopT("auc_ended"))}</div><div class="card auc-ended-list">${ended}</div>` : ""}`;
}

function aucErr(e) {
  const code = e && e.message;
  const known = ["lot_not_found", "ended", "already_leader", "leading_other", "already_won", "bid_too_low", "bad_amount", "insufficient"];
  return shopT(known.includes(code) ? "auc_err_" + code : "shop_err_generic");
}

async function aucBid(lotId) {
  if (AUC.busy) return;                                  // ikki marta yuborish (qoida #38)
  const inp = document.querySelector(`#shop-root [data-auc-amount="${lotId}"]`);
  const amount = Math.trunc(Number(inp && inp.value));
  const lot = (AUC.data.lots || []).find(l => Number(l.id) === Number(lotId));
  if (!lot || !amount || amount < lot.min_bid) { showToast(shopT("auc_err_bid_too_low")); return; }
  if (amount > (AUC.data.balance || 0)) { showToast(shopT("auc_err_insufficient")); return; }
  if (!window.confirm(shopT("auc_confirm", { amount: shopNum(amount), club: lot.club_name }))) return;
  AUC.busy = true;
  try {
    const r = await apiFetch(`/shop/auction/${encodeURIComponent(lotId)}/bid`, { method: "POST", body: JSON.stringify({ amount }) });
    showToast(shopT(r.extended ? "auc_ok_extended" : "auc_ok", { m: AUC.data.snipe_minutes }));
  } catch (e) {
    showToast(aucErr(e));
  } finally {
    AUC.busy = false;
  }
  await aucLoad();
}

document.addEventListener("click", (e) => {
  const b = e.target.closest ? e.target.closest("[data-auc-bid]") : null;
  if (b && document.getElementById("shop-root")?.contains(b)) void aucBid(b.dataset.aucBid);
});
