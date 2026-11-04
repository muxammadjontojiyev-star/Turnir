// =============================================================
//  shop_admin_cards.js — Admin → «🛒 DO'KON»: O'YIN KARTASI FONLARI SOTUVI kaliti (2026-11-04, faqat bosh admin)
//  O'chiq (standart): fonlar do'konda faqat bosh adminga ko'rinadi, u bepul qo'llab ko'radi; boshqalar ko'rmaydi.
//  Yoqilganda — hamma eF Tokenga sotib oladi. O'chirilsa — sotib olganlarda qoladi, yangi xarid yo'q.
//  API: GET/POST /shop/admin/cosmetics/card-sale {on} (cosmetics_api.py). shopAdmLoad o'raladi
//  (shop_admin_wallets.js dan KEYIN ulanadi). Global: apiFetch, escHtml, showToast.
// =============================================================

async function cardSaleAdmLoad() {
  const box = document.getElementById("cardsale-adm");
  if (!box) return;
  let on;
  try { on = !!(await apiFetch("/shop/admin/cosmetics/card-sale")).on; }
  catch (e) { box.innerHTML = `<div class="adm-pp-hint">${escHtml(e.message || "Xatolik")}</div>`; return; }
  box.innerHTML = `<div class="adm-pp-hint" style="margin-top:14px"><b>🃏 O'YIN KARTASI FONLARI — ${on ? "🟢 SOTUVDA" : "⚪ SOTUVDA EMAS"}</b><br>
      Divizion qur'a kartasida o'yinchi ustuni orqasidagi fon. ${on
        ? "Hamma Do'kon → Bezaklar'da eF Tokenga sotib oladi."
        : "Hozir faqat siz ko'rasiz va bepul qo'llab ko'ra olasiz (Do'kon → Bezaklar)."}</div>
    <button class="btn ${on ? "" : "btn--primary"}" id="btn-card-sale" style="width:100%;margin-top:6px">${on ? "Sotuvni to'xtatish" : "Sotuvni boshlash"}</button>`;
  document.getElementById("btn-card-sale").addEventListener("click", async (e) => {
    const q = on ? "O'yin kartasi fonlari sotuvi to'xtatilsinmi? Sotib olganlarda qoladi."
                 : "O'yin kartasi fonlari sotuvi boshlansinmi? Hamma do'konda ko'radi va sotib oladi.";
    if (!window.confirm(q)) return;
    e.target.disabled = true;                                 // ikki marta bosish (qoida #38)
    try {
      await apiFetch("/shop/admin/cosmetics/card-sale", { method: "POST", body: JSON.stringify({ on: !on }) });
      showToast("✅");
    } catch (err) {
      showToast("❌ " + err.message);
    }
    await cardSaleAdmLoad();
  });
}

if (typeof shopAdmLoad === "function") {
  const _cardSalePrevShopAdmLoad = shopAdmLoad;
  shopAdmLoad = async function () { await _cardSalePrevShopAdmLoad(); await cardSaleAdmLoad(); };   // eslint-disable-line no-global-assign
}
