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
    "crule_err_chat_need_both": {
        LANGUAGE_UZ: "💬 Natija kiritishdan oldin bot chatida raqibingiz bilan yozishing (ikkalangiz ham kamida 1 ta xabar).",
        LANGUAGE_RU: "💬 Перед вводом результата спишитесь с соперником в чате бота (оба — хотя бы 1 сообщение).",
        LANGUAGE_EN: "💬 Before entering a result, chat with your opponent in the bot chat (at least 1 message each).",
    },
    "crule_err_chat_opp_silent": {
        LANGUAGE_UZ: "💬 Raqibingiz bot chatida hali birorta xabar yozmagan — natija kiritib bo'lmaydi. U javob bermasa, "
                     "deadline'ga 30 daqiqa qolganda «⚠️ Raqib yozmadi / o'ynamadi» tugmasi orqali tex win (3:0) oling.",
        LANGUAGE_RU: "💬 Соперник ещё не написал ни одного сообщения в чате бота — результат внести нельзя. Если он не ответит, "
                     "за 30 минут до дедлайна получите техпобеду (3:0) кнопкой «⚠️ Соперник не ответил / не играл».",
        LANGUAGE_EN: "💬 Your opponent hasn't written a single message in the bot chat yet — no result can be entered. If they "
                     "don't reply, claim a tech win (3:0) via «⚠️ Opponent didn't reply / play» 30 minutes before the deadline.",
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
