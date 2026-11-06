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
        LANGUAGE_UZ: "🧾 {mode} · o'yin #{match}: katta hisob skrinshot bilan yuborildi ({score}). {where}",
        LANGUAGE_RU: "🧾 {mode} · матч #{match}: крупный счёт отправлен со скриншотом ({score}). {where}",
        LANGUAGE_EN: "🧾 {mode} · match #{match}: a big score was sent with a screenshot ({score}). {where}",
    },
    "mshot_admin_dispute": {
        LANGUAGE_UZ: "⚠️ {mode} · o'yin #{match}: skrinshotli natijaga ({score}) raqib e'tiroz bildirdi. {where}",
        LANGUAGE_RU: "⚠️ {mode} · матч #{match}: соперник оспорил результат со скриншотом ({score}). {where}",
        LANGUAGE_EN: "⚠️ {mode} · match #{match}: the opponent disputed a screenshot result ({score}). {where}",
    },
    "mshot_admin_tech": {
        LANGUAGE_UZ: "⚠️ {mode} · o'yin #{match}: «Raqib yozmadi / o'ynamadi — texnik g'alaba» so'rovi. {where}",
        LANGUAGE_RU: "⚠️ {mode} · матч #{match}: заявка «Соперник не ответил / не играл — техпобеда». {where}",
        LANGUAGE_EN: "⚠️ {mode} · match #{match}: «Opponent didn't reply / play — tech win» request. {where}",
    },
    "mshot_where_league": {
        LANGUAGE_UZ: "Ko'rish: Admin panel → «📸 SKRINSHOT VA TEXNIK G'ALABA».",
        LANGUAGE_RU: "Где: Админ-панель → «📸 СКРИНШОТЫ И ТЕХПОБЕДЫ».",
        LANGUAGE_EN: "Where: Admin panel → «📸 SCREENSHOTS & TECH WINS».",
    },
    "mshot_where_mode": {
        LANGUAGE_UZ: "Ko'rish: o'sha rejim → Admin bo'limi → «📸 SKRINSHOT VA TEXNIK G'ALABA».",
        LANGUAGE_RU: "Где: этот режим → раздел «Админ» → «📸 СКРИНШОТЫ И ТЕХПОБЕДЫ».",
        LANGUAGE_EN: "Where: that mode → Admin tab → «📸 SCREENSHOTS & TECH WINS».",
    },
    "mshot_mode_league": {LANGUAGE_UZ: "Liga", LANGUAGE_RU: "Лига", LANGUAGE_EN: "League"},
    "mshot_mode_wc": {LANGUAGE_UZ: "JCh", LANGUAGE_RU: "ЧМ", LANGUAGE_EN: "WC"},
    "mshot_mode_wc_po": {LANGUAGE_UZ: "JCh pley-off", LANGUAGE_RU: "ЧМ плей-офф", LANGUAGE_EN: "WC play-off"},
    "mshot_mode_cl": {LANGUAGE_UZ: "ChL", LANGUAGE_RU: "ЛЧ", LANGUAGE_EN: "CL"},
    "mshot_mode_cl_po": {LANGUAGE_UZ: "ChL pley-off", LANGUAGE_RU: "ЛЧ плей-офф", LANGUAGE_EN: "CL play-off"},
    "mshot_mode_el": {LANGUAGE_UZ: "YeL", LANGUAGE_RU: "ЛЕ", LANGUAGE_EN: "EL"},
    "mshot_mode_el_po": {LANGUAGE_UZ: "YeL pley-off", LANGUAGE_RU: "ЛЕ плей-офф", LANGUAGE_EN: "EL play-off"},
    "mshot_mode_ac": {LANGUAGE_UZ: "OChL", LANGUAGE_RU: "АЛЧ", LANGUAGE_EN: "ACL"},
    "mshot_mode_ac_po": {LANGUAGE_UZ: "OChL pley-off", LANGUAGE_RU: "АЛЧ плей-офф", LANGUAGE_EN: "ACL play-off"},
    "mshot_mode_co": {LANGUAGE_UZ: "KL", LANGUAGE_RU: "ЛК", LANGUAGE_EN: "ECL"},
    "mshot_mode_co_po": {LANGUAGE_UZ: "KL pley-off", LANGUAGE_RU: "ЛК плей-офф", LANGUAGE_EN: "ECL play-off"},
    "mshot_mode_div": {LANGUAGE_UZ: "Divizion", LANGUAGE_RU: "Дивизион", LANGUAGE_EN: "Division"},
    "mshot_mode_pt": {LANGUAGE_UZ: "Xususiy turnir", LANGUAGE_RU: "Частный турнир", LANGUAGE_EN: "Private tournament"},
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
    "mshot_notify_await": {
        LANGUAGE_UZ: "📸 Raqibingiz natijani Match History skrinshoti bilan yubordi: {score} (sizning golingiz birinchi).\n"
                     "Skrinshotdagi niknameingiz: «{nick}». Ilovani oching va tasdiqlang — niknameingiz ham saqlanadi.",
        LANGUAGE_RU: "📸 Соперник отправил результат скриншотом Match History: {score} (ваши голы первыми).\n"
                     "Ваш ник на скриншоте: «{nick}». Откройте приложение и подтвердите — ник тоже сохранится.",
        LANGUAGE_EN: "📸 Your opponent submitted a result with a Match History screenshot: {score} (your goals first).\n"
                     "Your nickname on it: «{nick}». Open the app to confirm — your nickname will be saved too.",
    },
    "mshot_notify_await_ok": {
        LANGUAGE_UZ: "✅ Raqibingiz skrinshotli natijani tasdiqladi: {score}.",
        LANGUAGE_RU: "✅ Соперник подтвердил результат со скриншотом: {score}.",
        LANGUAGE_EN: "✅ Your opponent confirmed the screenshot result: {score}.",
    },
    "efnick_link_request": {
        LANGUAGE_UZ: "🔗 {who} sizning eFootball niknameingizni o'z akkauntiga ulamoqchi. Bu sizning ikkinchi Telegram akkauntingizmi? "
                     "Ilovani ochib tasdiqlang yoki rad eting.",
        LANGUAGE_RU: "🔗 {who} хочет привязать ваш ник eFootball к своему аккаунту. Это ваш второй Telegram-аккаунт? "
                     "Откройте приложение, чтобы подтвердить или отклонить.",
        LANGUAGE_EN: "🔗 {who} wants to link your eFootball nickname to their account. Is this your second Telegram account? "
                     "Open the app to confirm or reject.",
    },
    "efnick_link_ok": {
        LANGUAGE_UZ: "✅ eFootball nikname akkauntingizga ulandi (shu mavsum uchun).",
        LANGUAGE_RU: "✅ Ник eFootball привязан к вашему аккаунту (на этот сезон).",
        LANGUAGE_EN: "✅ The eFootball nickname is linked to your account (for this season).",
    },
    "efnick_link_no": {
        LANGUAGE_UZ: "❌ Nikname egasi ulashni rad etdi. O'zingizning eFootball niknameingizni kiriting.",
        LANGUAGE_RU: "❌ Владелец ника отклонил привязку. Укажите свой ник eFootball.",
        LANGUAGE_EN: "❌ The nickname owner rejected the link. Enter your own eFootball nickname.",
    },
    "mshot_notify_fixed": {
        LANGUAGE_UZ: "🛠 Admin e'tirozni ko'rib chiqdi va natijani tuzatdi: {score}.",
        LANGUAGE_RU: "🛠 Админ рассмотрел спор и исправил результат: {score}.",
        LANGUAGE_EN: "🛠 An admin reviewed the dispute and fixed the result: {score}.",
    },
}
