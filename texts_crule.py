"""
texts_crule.py — chat qoidalari (tex win chat bo'yicha, kelishuv, qo'lda natija sharti) bot matnlari (2026-11-07).
texts.TEXTS ga qo'shiladi. {mode} — rejim nomi (mshot_mode_*), {at}/{until} — Toshkent vaqti «dd.mm HH:MM».
"""

from config import LANGUAGE_EN, LANGUAGE_RU, LANGUAGE_UZ

CRULE_TEXTS = {
    # ---- qo'lda natija rad etilganda (chat_gate.py; xato matni sifatida qaytadi) ----
    "crule_err_agree_locked": {
        LANGUAGE_UZ: "🔒 Siz raqibingiz bilan {until} ga kelishgansiz — shu vaqtgacha natija kiritilmaydi.",
        LANGUAGE_RU: "🔒 Вы договорились с соперником на {until} — до этого времени результат не вносится.",
        LANGUAGE_EN: "🔒 You agreed with your opponent on {until} — no result can be entered before then.",
    },
    "crule_err_room_not_sent": {
        LANGUAGE_UZ: "🎮 Natija kiritish uchun bot chatida xona ID almashilgan bo'lishi kerak: xona ochgan o'yinchi "
                     "«🎮 Xona ID yuborish» tugmasini bosadi, raqibi chatda ID ni bosib nusxalaydi. O'ynalmagan bo'lsa — "
                     "deadline'ga 30 daqiqa qolganda «⚠️ Raqib yozmadi / o'ynamadi» orqali tex win (3:0).",
        LANGUAGE_RU: "🎮 Чтобы внести результат, в чате бота нужно обменяться ID комнаты: создавший комнату нажимает "
                     "«🎮 Отправить ID комнаты», соперник нажимает на ID в чате (копирует). Если матча не было — за 30 минут "
                     "до дедлайна техпобеда (3:0) кнопкой «⚠️ Соперник не ответил / не играл».",
        LANGUAGE_EN: "🎮 To enter a result, a room ID must be exchanged in the bot chat: whoever creates the room taps "
                     "«🎮 Send room ID», the opponent taps the ID in the chat (copies it). If there was no match — a 3:0 "
                     "tech win via «⚠️ Opponent didn't reply / play» 30 minutes before the deadline.",
    },
    "crule_err_room_opp_not_copied": {
        LANGUAGE_UZ: "🎮 Siz xona ID yubordingiz, lekin raqibingiz uni hali chatdan nusxalamagan. U ilovada chatni ochib "
                     "ID ni bossin — keyin natija kiritiladi.",
        LANGUAGE_RU: "🎮 Вы отправили ID комнаты, но соперник ещё не скопировал его из чата. Пусть он откроет чат "
                     "в приложении и нажмёт на ID — после этого результат можно внести.",
        LANGUAGE_EN: "🎮 You sent the room ID, but your opponent hasn't copied it from the chat yet. They should open "
                     "the chat in the app and tap the ID — then the result can be entered.",
    },
    "crule_err_room_you_not_copied": {
        LANGUAGE_UZ: "🎮 Raqibingiz xona ID yuborgan, lekin siz uni chatdan nusxalamagansiz. Bot chatini oching va "
                     "ID ni bosing (nusxalanadi) — keyin natijani kiriting.",
        LANGUAGE_RU: "🎮 Соперник отправил ID комнаты, но вы не скопировали его из чата. Откройте чат бота и нажмите "
                     "на ID (скопируется) — затем внесите результат.",
        LANGUAGE_EN: "🎮 Your opponent sent the room ID, but you haven't copied it from the chat. Open the bot chat and "
                     "tap the ID (it copies) — then enter the result.",
    },
    "notify_room_code_app": {
        LANGUAGE_UZ: "🎮 {mode}: raqibingiz xona ochdi va xona ID yubordi.\nIlovani ochib, bot chatidagi ID ni bosing — "
                     "u nusxalanadi. Natija kiritish uchun ID aynan chatdan nusxalangan bo'lishi kerak.",
        LANGUAGE_RU: "🎮 {mode}: соперник создал комнату и отправил ID.\nОткройте приложение и нажмите на ID в чате бота — "
                     "он скопируется. Для ввода результата ID должен быть скопирован именно из чата.",
        LANGUAGE_EN: "🎮 {mode}: your opponent created a room and sent the ID.\nOpen the app and tap the ID in the bot chat — "
                     "it copies. To enter a result, the ID must be copied from the chat itself.",
    },
    # ---- kelishuv ----
    "crule_notify_agree_proposed": {
        LANGUAGE_UZ: "📅 {mode}: raqibingiz o'yinni {at} da o'ynashni taklif qildi. Ilovada chatni ochib «Qabul» yoki "
                     "«Rad» bosing. Qabul qilsangiz, shu vaqtgacha hech kim natija kirita olmaydi.",
        LANGUAGE_RU: "📅 {mode}: соперник предлагает сыграть матч {at}. Откройте чат в приложении и нажмите «Принять» "
                     "или «Отклонить». Если примете — до этого времени никто не сможет внести результат.",
        LANGUAGE_EN: "📅 {mode}: your opponent proposes to play the match at {at}. Open the chat in the app and tap "
                     "«Accept» or «Decline». If you accept, nobody can enter a result before then.",
    },
    "crule_notify_agree_accepted": {
        LANGUAGE_UZ: "✅ {mode}: raqibingiz {at} ga rozi bo'ldi. Shu vaqtgacha natija kiritilmaydi.",
        LANGUAGE_RU: "✅ {mode}: соперник согласился на {at}. До этого времени результат не вносится.",
        LANGUAGE_EN: "✅ {mode}: your opponent agreed to {at}. No result can be entered before then.",
    },
    "crule_notify_agree_late": {
        LANGUAGE_UZ: "⚠️ Bu vaqt tur deadline'idan keyin: deadline'da o'yin 0:0 yopiladi. O'ynagach, hisobni admin "
                     "orqali o'zgartirasiz.",
        LANGUAGE_RU: "⚠️ Это время после дедлайна тура: в дедлайн матч закроется 0:0. После игры счёт меняется через админа.",
        LANGUAGE_EN: "⚠️ This time is after the round deadline: the match closes 0:0 at the deadline. After you play, "
                     "the score is changed via an admin.",
    },
    "crule_notify_agree_declined": {
        LANGUAGE_UZ: "❌ {mode}: raqibingiz {at} vaqtini rad etdi. Chatda boshqa vaqt taklif qiling.",
        LANGUAGE_RU: "❌ {mode}: соперник отклонил время {at}. Предложите другое время в чате.",
        LANGUAGE_EN: "❌ {mode}: your opponent declined {at}. Propose another time in the chat.",
    },
    # ---- tex win (bot chat bo'yicha o'zi beradi) ----
    "crule_notify_tech_lost": {
        LANGUAGE_UZ: "⚠️ {mode}: siz bot chatida raqibingizga javob bermadingiz (u 3 xil vaqtda yozgan). "
                     "Bot texnik mag'lubiyat yozdi: 0:3.",
        LANGUAGE_RU: "⚠️ {mode}: вы не ответили сопернику в чате бота (он писал 3 раза в разное время). "
                     "Бот засчитал техническое поражение: 0:3.",
        LANGUAGE_EN: "⚠️ {mode}: you didn't reply to your opponent in the bot chat (they wrote at 3 different times). "
                     "The bot recorded a technical defeat: 0:3.",
    },
    "crule_admin_tech": {
        LANGUAGE_UZ: "ℹ️ {mode} · o'yin #{match}: bot chat yozishmasi bo'yicha texnik g'alaba berdi — {winner} 3:0. "
                     "Xato bo'lsa, rejim admin bo'limida hisobni tuzating.",
        LANGUAGE_RU: "ℹ️ {mode} · матч #{match}: бот засчитал техпобеду по переписке в чате — {winner} 3:0. "
                     "Если это ошибка, исправьте счёт в админ-разделе режима.",
        LANGUAGE_EN: "ℹ️ {mode} · match #{match}: the bot awarded a tech win based on the chat — {winner} 3:0. "
                     "If wrong, fix the score in the mode's admin section.",
    },
}
