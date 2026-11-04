// =============================================================
//  texts_pcard.js — SHAXSIY O'YINCHI KARTASI matnlari (2026-11-04, player_card.js / player_card_edit.js)
//  TEXTS[lang] ga qo'shiladi (api.js dan KEYIN ulanadi).
// =============================================================

const PCARD_TEXTS = {
  uz: {
    pc_title: "MENING KARTAM", pc_player_title: "O'YINCHI KARTASI",
    pc_edit: "⚙️ Kartani sozlash", pc_edit_title: "KARTANI SOZLASH",
    pc_pos: "Pozitsiya", pc_country: "Davlat", pc_none: "Ko'rsatilmasin",
    pc_save: "Saqlash", pc_cancel: "Bekor qilish", pc_saved: "✅ Karta saqlandi",
    pc_err: "❌ Saqlanmadi, qayta urinib ko'ring",
    pc_ovr_hint: "Reyting (OVR) Divizion joriy mavsumidagi o'yinlaringizdan avtomatik hisoblanadi: g'alabalar, gol farqi va o'yinlar soni. Yangi mavsumda yana 60 dan boshlanadi.",
    pc_games: "{n} o'yin · {w} g'alaba", pc_tap_close: "Yopish uchun bosing",
  },
  ru: {
    pc_title: "МОЯ КАРТОЧКА", pc_player_title: "КАРТОЧКА ИГРОКА",
    pc_edit: "⚙️ Настроить карточку", pc_edit_title: "НАСТРОЙКА КАРТОЧКИ",
    pc_pos: "Позиция", pc_country: "Страна", pc_none: "Не показывать",
    pc_save: "Сохранить", pc_cancel: "Отмена", pc_saved: "✅ Карточка сохранена",
    pc_err: "❌ Не сохранено, попробуйте ещё раз",
    pc_ovr_hint: "Рейтинг (OVR) считается автоматически по вашим матчам текущего сезона Дивизиона: победы, разница голов и число матчей. В новом сезоне снова начинается с 60.",
    pc_games: "{n} матчей · {w} побед", pc_tap_close: "Нажмите, чтобы закрыть",
  },
  en: {
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
