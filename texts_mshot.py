"""
texts_mshot.py — skrinshotli natija va texnik g'alaba bot xabarlari (2026-11-06). texts.TEXTS ga qo'shiladi.
"""

from config import LANGUAGE_EN, LANGUAGE_RU, LANGUAGE_UZ

MSHOT_TEXTS = {
    "mshot_notify_applied": {
        LANGUAGE_UZ: "📸 Raqibingiz Match History skrinshoti bilan natija yubordi: {score} (sizning golingiz birinchi). "
                     "Bot ikkalangizning eFootball niknameingizni tekshirib, natijani yozdi.\n"
                     "Noto'g'ri bo'lsa, {hours} soat ichida ilovada «E'tiroz» tugmasini bosing.",
        LANGUAGE_RU: "📸 Соперник отправил результат со скриншотом Match History: {score} (ваши голы первыми). "
                     "Бот проверил ваши ники eFootball и записал результат.\n"
                     "Если это неверно, нажмите «Оспорить» в приложении в течение {hours} ч.",
        LANGUAGE_EN: "📸 Your opponent submitted a result with a Match History screenshot: {score} (your goals first). "
                     "The bot checked both eFootball nicknames and recorded it.\n"
                     "If it's wrong, tap «Dispute» in the app within {hours} h.",
    },
    "mshot_admin_pending": {
        LANGUAGE_UZ: "🧾 Katta hisobli natija skrinshot bilan yuborildi ({score}). Admin panel → «📸 Skrinshot va texnik g'alaba» bo'limida ko'ring.",
        LANGUAGE_RU: "🧾 Крупный счёт отправлен со скриншотом ({score}). Админ-панель → «📸 Скриншоты и техпобеды».",
        LANGUAGE_EN: "🧾 A big-score result was submitted with a screenshot ({score}). Admin panel → «📸 Screenshots & tech wins».",
    },
    "mshot_admin_dispute": {
        LANGUAGE_UZ: "⚠️ Skrinshot bilan yozilgan natijaga ({score}) raqib e'tiroz bildirdi. Admin panel → «📸 Skrinshot va texnik g'alaba».",
        LANGUAGE_RU: "⚠️ Соперник оспорил результат со скриншотом ({score}). Админ-панель → «📸 Скриншоты и техпобеды».",
        LANGUAGE_EN: "⚠️ A screenshot result ({score}) was disputed. Admin panel → «📸 Screenshots & tech wins».",
    },
    "mshot_admin_tech": {
        LANGUAGE_UZ: "⚠️ Yangi «Raqib o'ynamadi — texnik g'alaba» so'rovi. Admin panel → «📸 Skrinshot va texnik g'alaba».",
        LANGUAGE_RU: "⚠️ Новая заявка «Соперник не играл — техпобеда». Админ-панель → «📸 Скриншоты и техпобеды».",
        LANGUAGE_EN: "⚠️ New «Opponent didn't play — tech win» request. Admin panel → «📸 Screenshots & tech wins».",
    },
    "mshot_notify_tech_claim": {
        LANGUAGE_UZ: "⚠️ Raqibingiz siz o'yinga chiqmaganingiz uchun texnik g'alaba so'radi. Admin yozishmalarni tekshiradi. "
                     "O'ynashga tayyor bo'lsangiz, hoziroq raqibingizga yozing.",
        LANGUAGE_RU: "⚠️ Соперник запросил техническую победу, так как вы не вышли на матч. Админ проверит переписку. "
                     "Если готовы играть — напишите сопернику прямо сейчас.",
        LANGUAGE_EN: "⚠️ Your opponent requested a technical win because you didn't show up. An admin will review the chat. "
                     "If you're ready to play, message your opponent now.",
    },
    "mshot_notify_tech_ok": {
        LANGUAGE_UZ: "✅ Texnik g'alaba so'rovingiz tasdiqlandi — natija 3:0 sizning foydangizga.",
        LANGUAGE_RU: "✅ Заявка на техпобеду одобрена — 3:0 в вашу пользу.",
        LANGUAGE_EN: "✅ Your tech-win request was approved — 3:0 in your favour.",
    },
    "mshot_notify_tech_no": {
        LANGUAGE_UZ: "❌ Texnik g'alaba so'rovingiz rad etildi.",
        LANGUAGE_RU: "❌ Заявка на техпобеду отклонена.",
        LANGUAGE_EN: "❌ Your tech-win request was rejected.",
    },
    "mshot_notify_tech_lost": {
        LANGUAGE_UZ: "❌ O'yinga chiqmaganingiz uchun sizga texnik mag'lubiyat (0:3) berildi.",
        LANGUAGE_RU: "❌ Вам засчитано техническое поражение (0:3) за неявку.",
        LANGUAGE_EN: "❌ You were given a technical loss (0:3) for not showing up.",
    },
    "mshot_notify_set_nick": {
        LANGUAGE_UZ: "🎮 Raqibingiz natijani skrinshot bilan yubormoqchi, lekin siz eFootball niknameingizni kiritmagansiz. "
                     "Ilova → Profil → «eFOOTBALL NIKNAMEINGIZ» bo'limida kiriting (eFootball → Extras, rasmingiz ostidagi nom).",
        LANGUAGE_RU: "🎮 Соперник хочет отправить результат скриншотом, но вы не указали ник eFootball. "
                     "Приложение → Профиль → «ВАШ НИК В eFOOTBALL» (eFootball → Extras, имя под фото).",
        LANGUAGE_EN: "🎮 Your opponent wants to submit the result by screenshot, but you haven't set your eFootball nickname. "
                     "App → Profile → «YOUR eFOOTBALL NICKNAME» (eFootball → Extras, the name under your picture).",
    },
    "mshot_notify_fixed": {
        LANGUAGE_UZ: "🛠 Admin e'tirozni ko'rib chiqdi va natijani tuzatdi: {score}.",
        LANGUAGE_RU: "🛠 Админ рассмотрел спор и исправил результат: {score}.",
        LANGUAGE_EN: "🛠 An admin reviewed the dispute and fixed the result: {score}.",
    },
}
