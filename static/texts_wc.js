// texts_wc.js — Jahon Chempionati (World Cup) tarjimalari (2026-07-21).
//
// MUHIM: WC rejimi allaqachon deyarli TO'LIQ tarjimali edi — worldcup*.js
// fayllari `t.KALIT || "zaxira"` naqshini ishlatadi va 166 ta kalitdan 159 tasi
// app.js dagi TEXTS da uchala tilda mavjud. Shu sababli bu fayl KICHIK: faqat
// YETISHMAYOTGAN kalitlar qo'shiladi, mavjudlari ustidan YOZILMAYDI (qoida #07).
//
// index.html da app.js dan KEYIN, worldcup*.js dan OLDIN ulanadi.

const WC_TEXTS = {
  uz: {
    // worldcup_playoff.js ishlatadi, lekin TEXTS da yo'q edi (7 ta) —
    // kalit nomlari KOD ishlatayotgan nomlar bilan bir xil, shuning uchun
    // worldcup_playoff.js ga tegish shart emas, o'zi ishlaydi.
    confirmed_short:      "Tasdiqlandi",
    pending_short:        "Kutilmoqda",
    confirmed_done:       "✅ Tasdiqlandi",
    rejected_done:        "Rad etildi",
    result_sent:          "✅ Natija yuborildi",
    already_confirmed:    "Allaqachon tasdiqlangan",
    fill_scores:          "Hisobni kiriting",
    // worldcup_admin.js: o'yin turi tekshiruvi (qattiq yozilgan edi)
    wca_is_playoff:       "Bu play-off o'yini ✅",
    wca_is_group:         "Bu guruh o'yini ✅",
  },

  ru: {
    confirmed_short:      "Подтверждён",
    pending_short:        "Ожидание",
    confirmed_done:       "✅ Подтверждено",
    rejected_done:        "Отклонено",
    result_sent:          "✅ Результат отправлен",
    already_confirmed:    "Уже подтверждено",
    fill_scores:          "Введите счёт",
    wca_is_playoff:       "Это матч плей-офф ✅",
    wca_is_group:         "Это матч группового этапа ✅",
  },

  en: {
    confirmed_short:      "Confirmed",
    pending_short:        "Pending",
    confirmed_done:       "✅ Confirmed",
    rejected_done:        "Rejected",
    result_sent:          "✅ Result submitted",
    already_confirmed:    "Already confirmed",
    fill_scores:          "Enter the score",
    wca_is_playoff:       "This is a play-off match ✅",
    wca_is_group:         "This is a group match ✅",
  },
};

// TEXTS ga qo'shamiz (texts_division.js / texts_cl.js bilan bir xil usul)
if (typeof TEXTS !== "undefined") {
  for (const lang of ["uz", "ru", "en"]) {
    if (TEXTS[lang]) Object.assign(TEXTS[lang], WC_TEXTS[lang]);
  }
}

// Tarjima yordamchisi — APP.t dan oladi, topilmasa o'zbekcha zaxira (DT/CT kabi)
function WT(key) {
  if (typeof APP !== "undefined" && APP && APP.t && APP.t[key] !== undefined) return APP.t[key];
  if (WC_TEXTS.uz[key] !== undefined) return WC_TEXTS.uz[key];
  return "";
}
