// =============================================================
//  shop_admin_wallets.js — Admin → «🛒 DO'KON»: ENG KO'P eF TOKENI BORLAR (top-10, faqat bosh admin, 2026-11-01)
//  Jami muomaladagi eF Token va egalari soni ham. API: GET /shop/admin/wallets/top (wallet.wallet_top).
//  shop_admin.js dagi shopAdmLoad qayta tayinlash orqali o'raladi (shop_admin_auction.js dan KEYIN ulanadi).
//  Global: apiFetch, escHtml, shopNum, shopToken (shop.js).
// =============================================================

const WALLET_MEDALS = ["🥇", "🥈", "🥉"];

async function walletAdmLoad() {
  const box = document.getElementById("wallet-adm");
  if (!box) return;
  try {
    const d = await apiFetch("/shop/admin/wallets/top");
    const rows = (d.top || []).map((r, i) => {
      const who = r.username ? "@" + r.username : (r.nickname || "—");
      return `<div class="shop-adm-order-who" style="display:flex;gap:8px;align-items:center;padding:6px 0;border-bottom:1px solid rgba(255,255,255,.06)">
          <span style="min-width:26px;text-align:center">${WALLET_MEDALS[i] || (i + 1) + "."}</span>
          <span style="flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escHtml(who)}
            <small style="opacity:.6">· ID ${escHtml(r.telegram_id)}</small></span>
          <b style="white-space:nowrap">${shopToken("shop-tk shop-tk--xs")} ${shopNum(r.balance)}</b>
        </div>`;
    }).join("");
    box.innerHTML = `<div class="adm-pp-hint" style="margin-top:14px"><b>💰 ENG KO'P eF TOKENI BORLAR (TOP-10)</b><br>
        Muomalada jami: <b>${shopNum(d.total || 0)} eF</b> · egalari: <b>${shopNum(d.holders || 0)}</b> kishi.
        Auksiondagi muzlatilgan takliflar balansga kirmaydi.</div>
      ${rows || `<div class="adm-pp-hint">Hali hech kimda eF Token yo'q.</div>`}`;
  } catch (e) {
    box.innerHTML = `<div class="adm-pp-hint">${escHtml(e.message || "Xatolik")}</div>`;
  }
}

if (typeof shopAdmLoad === "function") {
  const _walletPrevShopAdmLoad = shopAdmLoad;
  shopAdmLoad = async function () { await _walletPrevShopAdmLoad(); await walletAdmLoad(); };   // eslint-disable-line no-global-assign
}
