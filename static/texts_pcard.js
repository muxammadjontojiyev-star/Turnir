// =============================================================
//  texts_pcard.js — SHAXSIY O'YINCHI KARTASI matnlari (2026-11-04, player_card.js / player_card_edit.js)
//  TEXTS[lang] ga qo'shiladi (api.js dan KEYIN ulanadi).
// =============================================================

const PCARD_TEXTS = {
  uz: {
    pc_photo: "Karta rasmi", pc_photo_pick: "📷 Rasm yuklash", pc_photo_del: "Olib tashlash",
    pc_photo_hint: "Bo'yingiz to'liq ko'rinadigan rasm tanlang — fonni o'zimiz olib tashlaymiz. Kuniga 5 marta.",
    pc_photo_busy: "Rasm tayyorlanmoqda: fon olib tashlanmoqda… 10–30 soniya.", pc_photo_wait: "⏳ Tayyorlanmoqda…",
    pc_photo_ok: "✅ Rasm qo'yildi", pc_photo_ok_plain: "✅ Rasm qo'yildi (odam aniqlanmadi — fon bilan)",
    pc_photo_err_too_big: "❌ Rasm juda katta", pc_photo_err_bad_image: "❌ Bu rasm fayli emas",
    pc_photo_err_too_small: "❌ Rasm juda kichik", pc_photo_err_daily_limit: "❌ Bugun 5 marta yukladingiz, ertaga urinib ko'ring",
    pc_admin_del: "🗑 Rasmni o'chirish (admin)", pc_admin_del_q: "Bu ishtirokchining karta rasmi o'chirilsinmi?",
    pc_title: "MENING KARTAM", pc_player_title: "O'YINCHI KARTASI",
    pc_edit: "⚙️ Kartani sozlash", pc_edit_title: "KARTANI SOZLASH",
    pc_pos: "Pozitsiya", pc_country: "Davlat", pc_none: "Ko'rsatilmasin",
    pc_save: "Saqlash", pc_cancel: "Bekor qilish", pc_saved: "✅ Karta saqlandi",
    pc_err: "❌ Saqlanmadi, qayta urinib ko'ring",
    pc_ovr_hint: "Reyting (OVR) Divizion joriy mavsumidagi o'yinlaringizdan avtomatik hisoblanadi: g'alabalar, gol farqi va o'yinlar soni. Yangi mavsumda yana 60 dan boshlanadi.",
    pc_games: "{n} o'yin · {w} g'alaba", pc_tap_close: "Yopish uchun bosing",
  },
  ru: {
    pc_photo: "Фото карточки", pc_photo_pick: "📷 Загрузить фото", pc_photo_del: "Убрать",
    pc_photo_hint: "Выберите фото в полный рост — фон уберём сами. До 5 раз в день.",
    pc_photo_busy: "Фото обрабатывается: убираем фон… 10–30 секунд.", pc_photo_wait: "⏳ Обработка…",
    pc_photo_ok: "✅ Фото установлено", pc_photo_ok_plain: "✅ Фото установлено (человек не найден — с фоном)",
    pc_photo_err_too_big: "❌ Фото слишком большое", pc_photo_err_bad_image: "❌ Это не изображение",
    pc_photo_err_too_small: "❌ Фото слишком маленькое", pc_photo_err_daily_limit: "❌ Сегодня уже 5 загрузок, попробуйте завтра",
    pc_admin_del: "🗑 Удалить фото (админ)", pc_admin_del_q: "Удалить фото карточки этого участника?",
    pc_title: "МОЯ КАРТОЧКА", pc_player_title: "КАРТОЧКА ИГРОКА",
    pc_edit: "⚙️ Настроить карточку", pc_edit_title: "НАСТРОЙКА КАРТОЧКИ",
    pc_pos: "Позиция", pc_country: "Страна", pc_none: "Не показывать",
    pc_save: "Сохранить", pc_cancel: "Отмена", pc_saved: "✅ Карточка сохранена",
    pc_err: "❌ Не сохранено, попробуйте ещё раз",
    pc_ovr_hint: "Рейтинг (OVR) считается автоматически по вашим матчам текущего сезона Дивизиона: победы, разница голов и число матчей. В новом сезоне снова начинается с 60.",
    pc_games: "{n} матчей · {w} побед", pc_tap_close: "Нажмите, чтобы закрыть",
  },
  en: {
    pc_photo: "Card photo", pc_photo_pick: "📷 Upload photo", pc_photo_del: "Remove",
    pc_photo_hint: "Pick a full-body photo — we remove the background. Up to 5 times a day.",
    pc_photo_busy: "Processing photo: removing background… 10–30 seconds.", pc_photo_wait: "⏳ Processing…",
    pc_photo_ok: "✅ Photo set", pc_photo_ok_plain: "✅ Photo set (no person found — kept background)",
    pc_photo_err_too_big: "❌ Photo is too large", pc_photo_err_bad_image: "❌ This is not an image",
    pc_photo_err_too_small: "❌ Photo is too small", pc_photo_err_daily_limit: "❌ 5 uploads today already, try tomorrow",
    pc_admin_del: "🗑 Delete photo (admin)", pc_admin_del_q: "Delete this participant's card photo?",
    pc_title: "MY CARD", pc_player_title: "PLAYER CARD",
    pc_edit: "⚙️ Customize card", pc_edit_title: "CUSTOMIZE CARD",
    pc_pos: "Position", pc_country: "Country", pc_none: "Don't show",
    pc_save: "Save", pc_cancel: "Cancel", pc_saved: "✅ Card saved",
    pc_err: "❌ Not saved, please try again",
    pc_ovr_hint: "Rating (OVR) is calculated automatically from your matches in the current Division season: wins, goal difference and games played. It starts again from 60 each new season.",
    pc_games: "{n} games · {w} wins", pc_tap_close: "Tap to close",
  },
};

for (const lang of ["uz", "ru", "en"]) {
  if (typeof TEXTS !== "undefined" && TEXTS[lang]) Object.assign(TEXTS[lang], PCARD_TEXTS[lang]);
}
