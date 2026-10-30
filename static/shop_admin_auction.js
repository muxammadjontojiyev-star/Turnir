// =============================================================
//  shop_admin_auction.js — Admin → «🛒 DO'KON» ichida AUKSION boshqaruvi (faqat bosh admin, 2026-10-30)
//  Klubni sotuvga qo'yish (liga, klub, boshlang'ich narx, qadam, muddat), faol savdolar (bekor qilish),
//  oxirgi natijalar. shop_admin.js dagi shopAdmLoad'dan keyin #auc-adm ga chiziladi.
//  API: GET/POST /shop/admin/auction, POST /shop/admin/auction/{id}/cancel.
//  Global: shopAdmLoad (shop_admin.js), shopNum, shopToken, aucLeft (shop_auction.js), LEAGUE_CLUBS (api.js).
// =============================================================

const AUC_ADM = { busy: false, leagues: [] };
const AUC_ADM_HOURS = [6, 12, 24, 48, 72, 168];
const AUC_ADM_ERR = {
  bad_club: "Klub shu ligada topilmadi.", league_not_found: "Liga topilmadi.", bad_price: "Boshlang'ich narx noto'g'ri.",
  bad_step: "Qadam noto'g'ri.", bad_hours: "Muddat noto'g'ri.", club_on_auction: "Bu klub allaqachon savdoda yoki g'olibi bor (yangi mavsumni kutmoqda).",
  wrong_status: "Savdo allaqachon yakunlangan.", not_found: "Topilmadi.",
};
const AUC_ADM_ST = { ended: "keyingi mavsumni kutmoqda", applied: "klubga yozildi", failed: "yozilmadi, pul qaytdi", cancelled: "bekor qilindi" };

async function aucAdmLoad() {
  const box = document.getElementById("auc-adm");
  if (!box) return;
  try {
    const d = await apiFetch("/shop/admin/auction");
    AUC_ADM.leagues = d.leagues || [];
    box.innerHTML = aucAdmFormHtml() + aucAdmListHtml(d);
    aucAdmFillClubs();
  } catch (e) {
    box.innerHTML = `<div class="adm-pp-hint">${escHtml(e.message || "Xatolik")}</div>`;
  }
}

function aucAdmFormHtml() {
  const lg = AUC_ADM.leagues.map(l => `<option value="${Number(l.id)}">${escHtml(l.name)}</option>`).join("");
  const hrs = AUC_ADM_HOURS.map(h => `<option value="${h}" ${h === 24 ? "selected" : ""}>${h < 24 ? h + " soat" : h / 24 + " kun"}</option>`).join("");
  return `<div class="adm-pp-hint" style="margin-top:14px"><b>AUKSION</b> — klubni sotuvga qo'ying. G'olib keyingi liga mavsumi ochilganda shu klubga avtomatik yoziladi. Oxirgi daqiqalardagi taklif savdoni uzaytiradi.</div>
    <div class="auc-adm-form">
      <select class="modal-input" id="auc-adm-league">${lg}</select>
      <select class="modal-input" id="auc-adm-club"></select>
      <input class="modal-input" id="auc-adm-price" type="number" min="1" inputmode="numeric" placeholder="Boshlang'ich narx, eF">
      <input class="modal-input" id="auc-adm-step" type="number" min="1" inputmode="numeric" placeholder="Eng kam qadam, eF">
      <select class="modal-input" id="auc-adm-hours">${hrs}</select>
      <button class="btn btn--primary" data-auc-adm="create">🔨 Sotuvga qo'yish</button>
    </div>`;
}

function aucAdmFillClubs() {
  const sel = document.getElementById("auc-adm-league"), cl = document.getElementById("auc-adm-club");
  if (!sel || !cl) return;
  const name = (AUC_ADM.leagues.find(l => String(l.id) === sel.value) || {}).name;
  const clubs = (typeof LEAGUE_CLUBS !== "undefined" && LEAGUE_CLUBS[name]) || [];
  cl.innerHTML = clubs.map(c => `<option>${escHtml(c.name)}</option>`).join("");
}

function aucAdmListHtml(d) {
  const who = l => l.leader_username ? "@" + l.leader_username : (l.leader_nickname || "—");
  const act = (d.active || []).map(l => `<div class="shop-adm-order">
      <div class="shop-adm-order-top"><b>${escHtml(l.club_name)}</b><span>· ${escHtml(l.league_name)} · #${Number(l.id)}</span></div>
      <div class="shop-adm-order-who">${l.current_bid != null ? `${shopNum(l.current_bid)} eF — ${escHtml(who(l))}` : `boshlang'ich ${shopNum(l.start_price)} eF, taklif yo'q`}
        · takliflar: ${Number(l.bids_count)} · tugaydi: ${escHtml(l.ends_local || l.ends_at)}</div>
      <button class="btn btn--ghost" data-auc-adm="cancel" data-id="${Number(l.id)}">✖ Bekor qilish</button>
    </div>`).join("");
  const rec = (d.recent || []).map(l => `<div class="shop-adm-order-who">#${Number(l.id)} ${escHtml(l.club_name)} (${escHtml(l.league_name)}) —
      ${l.winner_user_id ? `${escHtml(who(l))}, ${shopNum(l.current_bid)} eF` : "takliflarsiz"} · ${escHtml(AUC_ADM_ST[l.status] || l.status)}</div>`).join("");
  return `<div class="adm-pp-hint" style="margin-top:10px"><b>Faol savdolar</b></div>${act || `<div class="adm-pp-hint">Faol savdo yo'q.</div>`}
    ${rec ? `<div class="adm-pp-hint" style="margin-top:10px"><b>Oxirgi natijalar</b></div>${rec}` : ""}`;
}

async function aucAdmAction(btn) {
  if (AUC_ADM.busy) return;
  const a = btn.dataset.aucAdm;
  let path, body = null;
  if (a === "create") {
    const v = id => document.getElementById(id).value;
    body = { league_id: Number(v("auc-adm-league")), club_name: v("auc-adm-club"), start_price: Number(v("auc-adm-price")),
             min_step: Number(v("auc-adm-step")), hours: Number(v("auc-adm-hours")) };
    if (!window.confirm(`${body.club_name} — ${shopNum(body.start_price)} eF dan, qadam ${shopNum(body.min_step)} eF. Sotuvga qo'yilsinmi?`)) return;
    path = "/shop/admin/auction";
  } else if (a === "cancel") {
    if (!window.confirm("Savdo bekor qilinsinmi? Yetakchining eF Tokeni qaytariladi.")) return;
    path = `/shop/admin/auction/${encodeURIComponent(btn.dataset.id)}/cancel`;
  } else return;
  AUC_ADM.busy = true;
  btn.disabled = true;
  try {
    await apiFetch(path, { method: "POST", body: body ? JSON.stringify(body) : undefined });
    showToast("✅ Saqlandi");
  } catch (e) {
    showToast("❌ " + (AUC_ADM_ERR[e.message] || e.message));
  } finally {
    AUC_ADM.busy = false;
    btn.disabled = false;
  }
  await aucAdmLoad();
}

document.addEventListener("click", (e) => {
  const b = e.target.closest ? e.target.closest("[data-auc-adm]") : null;
  if (b && document.getElementById("auc-adm")?.contains(b)) void aucAdmAction(b);
});
document.addEventListener("change", (e) => { if (e.target.id === "auc-adm-league") aucAdmFillClubs(); });

// shop_admin.js: bo'lim ochilganda / Admin sahifasida — buyurtmalar va paketlardan keyin auksion ham yuklanadi
if (typeof shopAdmLoad === "function") {
  const _aucPrevShopAdmLoad = shopAdmLoad;
  shopAdmLoad = async function () { await _aucPrevShopAdmLoad(); await aucAdmLoad(); };   // eslint-disable-line no-global-assign
}
