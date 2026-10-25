// =============================================================
//  tb_proof.js — "TEAMLAR JANGI": natija skrinshoti (2026-10-25, 3-bosqich)
//  Natija kiritishda yakun ekrani skrinshoti MAJBURIY (server ham tekshiradi: proof_required).
//  Oqim: rasm tanlanadi -> siqiladi (chat_images.js chatCompressImage) -> o'yin chatiga yuboriladi
//  (POST /chat/image, mode "tb" — chatda dalil bo'lib qoladi, raqibga bot orqali boradi)
//  -> qaytgan token bilan POST /tb/game/submit (proof_token).
//  Tasdiqlovchi raqib natija ostida skrinshotni ko'radi (bosilsa to'liq ekran — chatImgLightbox).
//  tb_season.js chaqiradi: tbProofPickHtml, tbProofViewHtml, tbProofHas, tbProofSubmit.
//  Global: TB_ERR, TB_I18N, apiFetch, escHtml, tbToast, tbErr, tbsPost, chatCompressImage.
// =============================================================

const TBP = { files: {}, previews: {}, tokens: {} };     // game_id -> File / objectURL / yuborilgan token

function tbProofHas(gid) { return !!TBP.files[gid]; }

function tbProofPickHtml(gid) {
  const on = !!TBP.files[gid];
  return `<label class="tb-proof-pick${on ? " is-on" : ""}">
      <input type="file" accept="image/*" hidden data-tbs-proof="${gid}">
      ${on ? `<img src="${TBP.previews[gid]}" alt="">` : ""}
      <span>${on ? "✅ Skrinshot tanlandi — almashtirish" : "📷 Yakun ekrani skrinshoti (majburiy)"}</span>
    </label>
    <div class="tb-hint tb-hint--center">Skrinshotda hisob va ikkala o'yinchining niki ko'rinsin.</div>`;
}

// Raqib (va natijani kiritgan o'zi) — tasdiqlashdan oldin skrinshot
function tbProofViewHtml(g) {
  if (!g.proof_token) return "";
  return `<div class="tb-proof-view"><span class="webchat-img webchat-img--loading" data-chat-img="${escHtml(g.proof_token)}">📷</span>
      <div class="tb-hint tb-hint--center">Natija skrinshoti — kattalashtirish uchun bosing</div></div>`;
}

document.addEventListener("change", (e) => {
  const inp = e.target.closest ? e.target.closest("#tb-root [data-tbs-proof]") : null;
  if (!inp) return;
  const gid = +inp.dataset.tbsProof, file = inp.files && inp.files[0];
  if (!file) return;
  if (TBP.previews[gid]) URL.revokeObjectURL(TBP.previews[gid]);
  TBP.files[gid] = file;
  TBP.previews[gid] = URL.createObjectURL(file);
  delete TBP.tokens[gid];                                  // yangi rasm — qayta yuboriladi
  const label = inp.closest(".tb-proof-pick");
  if (label) label.outerHTML = tbProofPickHtml(gid).split("</label>")[0] + "</label>";
});

async function tbProofSubmit(gid, mine, opp, btn) {
  const file = TBP.files[gid];
  if (!file) { tbToast("Avval yakun ekrani skrinshotini tanlang"); return; }
  btn.disabled = true;
  try {
    if (!TBP.tokens[gid]) {                                  // takroriy urinishda o'sha rasm qayta yuborilmaydi
      const image_base64 = await chatCompressImage(file);
      const r = await apiFetch("/chat/image", { method: "POST",
        body: JSON.stringify({ match_id: gid, mode: "tb", image_base64 }) });
      TBP.tokens[gid] = r.token;
    }
  } catch (e) {
    tbToast("❌ " + tbErr(e));
    btn.disabled = false;
    return;
  }
  await tbsPost("/tb/game/submit", { game_id: gid, my_score: mine, opp_score: opp, proof_token: TBP.tokens[gid] },
    "✅ Yuborildi — raqib tasdiqlaydi", btn);
  if (!btn.isConnected) {                                    // muvaffaqiyat — karta qayta chizildi
    if (TBP.previews[gid]) URL.revokeObjectURL(TBP.previews[gid]);
    delete TBP.files[gid]; delete TBP.previews[gid]; delete TBP.tokens[gid];
  }
}

// ---------------- Xato kodlari va tarjima ----------------
Object.assign(TB_ERR, {
  proof_required: "Natija skrinshoti majburiy — yakun ekranini yuklang",
  image_too_large: "Rasm juda katta", bad_image: "Rasm formati noto'g'ri (JPEG/PNG/WEBP)",
  too_many_images: "Bu o'yinda rasm chegarasiga yetdingiz",
});
Object.assign(TB_I18N.ru, {
  "✅ Skrinshot tanlandi — almashtirish": "✅ Скриншот выбран — заменить",
  "📷 Yakun ekrani skrinshoti (majburiy)": "📷 Скриншот итогов матча (обязательно)",
  "Skrinshotda hisob va ikkala o'yinchining niki ko'rinsin.": "На скриншоте должны быть видны счёт и ники обоих игроков.",
  "Natija skrinshoti — kattalashtirish uchun bosing": "Скриншот результата — нажмите, чтобы увеличить",
  "Avval yakun ekrani skrinshotini tanlang": "Сначала выберите скриншот итогов матча",
  "Natija skrinshoti majburiy — yakun ekranini yuklang": "Скриншот результата обязателен — загрузите экран итогов",
  "Bu o'yinda rasm chegarasiga yetdingiz": "В этой игре достигнут лимит изображений",
});
Object.assign(TB_I18N.en, {
  "✅ Skrinshot tanlandi — almashtirish": "✅ Screenshot selected — replace",
  "📷 Yakun ekrani skrinshoti (majburiy)": "📷 Final screen screenshot (required)",
  "Skrinshotda hisob va ikkala o'yinchining niki ko'rinsin.": "The screenshot must show the score and both players' nicknames.",
  "Natija skrinshoti — kattalashtirish uchun bosing": "Result screenshot — tap to enlarge",
  "Avval yakun ekrani skrinshotini tanlang": "Select the final screen screenshot first",
  "Natija skrinshoti majburiy — yakun ekranini yuklang": "A result screenshot is required — upload the final screen",
  "Bu o'yinda rasm chegarasiga yetdingiz": "Image limit reached for this match",
});
