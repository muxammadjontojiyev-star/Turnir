// =============================================================
//  texts_crule.js — chat qoidalari matnlari (2026-11-07): tex win chat bo'yicha, «boshqa vaqtga kelishish».
//  crT(key, vars) — joriy til (APP.lang), bo'lmasa o'zbekcha. crErr(e) — server kodi → matn.
// =============================================================

const CRULE_TEXTS = {
  uz: {
    cr_tech_title: "RAQIB YOZMADI / O'YNAMADI",
    cr_big_toast: "📸 Yirik hisob — o'yinning Match History skrinshotini yuklang. Hisob bir xil bo'lsa, natija darhol tasdiqlanadi.",
    cr_tech_rule: "Bot faqat shu o'yinning BOT ichidagi chatini tekshiradi (Telegram shaxsiy yozishmasi hisobga olinmaydi). "
      + "Tex win (3:0) uchun: raqibning oxirgi xabaridan keyin unga 3 xil vaqtda yozgan bo'lishingiz kerak, oralig'i kamida "
      + "40 daqiqa; deadline'ga 30 daqiqa qolganda yozilganlari sanalmaydi. Raqib sizga 3 marta yozib, siz javob bermagan "
      + "bo'lsangiz — tex win sizga berilmaydi. "
      + "Yoki: chatdagi oxirgi xabar sizniki (raqibga javob), u deadline'ga 30 daqiqa qolishidan oldin yozilgan va raqib "
      + "kamida 30 daqiqa javob bermagan bo'lsa — tex win sizga.",
    cr_tech_wait: "Raqib javob bermasa, tugma {t} dan ishlaydi",
    cr_tech_deadline: "Deadline: {d}", cr_tech_opens: "Tugma ochiladi: {t}", cr_tech_attempts: "Sizning urinishlaringiz: {n} / 3",
    cr_tech_take: "✅ 3:0 olish", cr_tech_done: "✅ Texnik g'alaba yozildi: 3:0", cr_close: "Yopish", cr_wait: "⏳ Tekshirilmoqda…",
    cr_ag_btn: "📅 Boshqa vaqtga kelishish", cr_ag_hint: "Toshkent vaqti. Qabul qilinsa — shu vaqtgacha hech kim natija kirita olmaydi.",
    cr_ag_send: "Taklif qilish", cr_ag_now: "Hozir o'ynaymiz", cr_ag_cancel: "Bekor qilish",
    cr_ag_mine: "⏳ Taklifingiz: {at} — raqib javobi kutilmoqda", cr_ag_theirs: "📅 Raqib taklifi: {at}",
    cr_ag_accept: "✅ Qabul", cr_ag_decline: "❌ Rad", cr_ag_locked: "🔒 Kelishildi: {at} gacha natija kiritilmaydi",
    cr_ag_other: "Boshqa vaqt", cr_ag_sent: "📅 Taklif yuborildi", cr_ag_ok: "✅ Kelishildi",
    cr_ag_late: "⚠️ Bu vaqt deadline'dan keyin: deadline'da o'yin 0:0 yopiladi, o'ynagach hisobni admin o'zgartiradi.",
    cr_err: {
      tech_has_result: "Bu o'yinga natija allaqachon kiritilgan",
      agree_locked: "Siz raqib bilan boshqa vaqtga kelishgansiz — shu vaqtgacha natija kiritilmaydi",
      tech_no_deadline: "Bu o'yinda deadline belgilanmagan — tex win berilmaydi",
      tech_too_early: "Tex win deadline'ga 30 daqiqa qolganda ochiladi",
      tech_too_late: "Deadline o'tib ketdi",
      tech_you_ignored: "Raqibingiz sizga 3 xil vaqtda yozgan, siz javob bermagansiz — tex win sizga berilmaydi",
      tech_opp_replied: "Raqibingiz chatda javob bergan — tex win yo'q. Uning oxirgi xabaridan keyin yana 3 xil vaqtda yozing",
      tech_need_attempts: "Raqibga bot chatida 3 xil vaqtda (oralig'i kamida 40 daqiqa) yozmagansiz",
      tech_wait_reply: "Raqibingizda javob berish uchun hali vaqt bor — 30 daqiqa o'tishini kuting",
      agree_in_past: "Bu vaqt o'tib ketgan", agree_too_far: "Juda uzoq vaqt (ko'pi bilan 7 kun)", agree_bad_time: "Vaqtni tanlang",
      agree_has_result: "Bu o'yinga natija kiritilgan — kelishuv kerak emas", agree_not_found: "Taklif topilmadi yoki eskirgan",
      not_participant: "Siz bu o'yin ishtirokchisi emassiz",
    },
  },
  ru: {
    cr_tech_title: "СОПЕРНИК НЕ ОТВЕТИЛ / НЕ ИГРАЛ",
    cr_big_toast: "📸 Крупный счёт — загрузите скриншот Match History. Если счёт совпадёт, результат сразу подтвердится.",
    cr_tech_rule: "Бот проверяет только чат этого матча ВНУТРИ бота (личная переписка в Telegram не учитывается). "
      + "Для техпобеды (3:0): после последнего сообщения соперника вы написали ему 3 раза в разное время, с интервалом "
      + "от 40 минут; сообщения за 30 минут до дедлайна не учитываются. Если соперник писал вам 3 раза, а вы не ответили — "
      + "техпобеда вам не присуждается. "
      + "Или: последнее сообщение в чате ваше (ответ сопернику), написано раньше чем за 30 минут до дедлайна, и соперник "
      + "не отвечает минимум 30 минут — техпобеда ваша.",
    cr_tech_wait: "Если соперник не ответит, кнопка сработает с {t}",
    cr_tech_deadline: "Дедлайн: {d}", cr_tech_opens: "Кнопка откроется: {t}", cr_tech_attempts: "Ваши попытки: {n} / 3",
    cr_tech_take: "✅ Получить 3:0", cr_tech_done: "✅ Техпобеда записана: 3:0", cr_close: "Закрыть", cr_wait: "⏳ Проверка…",
    cr_ag_btn: "📅 Договориться о другом времени", cr_ag_hint: "Время Ташкента. Если примут — до этого времени никто не внесёт результат.",
    cr_ag_send: "Предложить", cr_ag_now: "Играем сейчас", cr_ag_cancel: "Отменить",
    cr_ag_mine: "⏳ Ваше предложение: {at} — ждём ответа", cr_ag_theirs: "📅 Предложение соперника: {at}",
    cr_ag_accept: "✅ Принять", cr_ag_decline: "❌ Отклонить", cr_ag_locked: "🔒 Договорились: до {at} результат не вносится",
    cr_ag_other: "Другое время", cr_ag_sent: "📅 Предложение отправлено", cr_ag_ok: "✅ Договорились",
    cr_ag_late: "⚠️ Это время после дедлайна: в дедлайн матч закроется 0:0, после игры счёт меняет админ.",
    cr_err: {
      tech_has_result: "Результат этого матча уже внесён",
      agree_locked: "Вы договорились с соперником о другом времени — до него результат не вносится",
      tech_no_deadline: "У этого матча нет дедлайна — техпобеда не присуждается",
      tech_too_early: "Техпобеда открывается за 30 минут до дедлайна",
      tech_too_late: "Дедлайн уже прошёл",
      tech_you_ignored: "Соперник писал вам 3 раза в разное время, а вы не ответили — техпобеда вам не присуждается",
      tech_opp_replied: "Соперник ответил в чате — техпобеды нет. Напишите ещё 3 раза после его последнего сообщения",
      tech_need_attempts: "Вы не написали сопернику в чате бота 3 раза (с интервалом от 40 минут)",
      tech_wait_reply: "У соперника ещё есть время ответить — подождите 30 минут",
      agree_in_past: "Это время уже прошло", agree_too_far: "Слишком далеко (не более 7 дней)", agree_bad_time: "Выберите время",
      agree_has_result: "Результат уже внесён — договорённость не нужна", agree_not_found: "Предложение не найдено или устарело",
      not_participant: "Вы не участник этого матча",
    },
  },
  en: {
    cr_tech_title: "OPPONENT DIDN'T REPLY / PLAY",
    cr_big_toast: "📸 Big score — upload the Match History screenshot. If the score matches, the result is confirmed right away.",
    cr_tech_rule: "The bot checks only this match's chat INSIDE the bot (private Telegram chats don't count). "
      + "For a tech win (3:0): after your opponent's last message you must have written to them at 3 different times, at "
      + "least 40 minutes apart; messages in the last 30 minutes before the deadline don't count. If your opponent wrote "
      + "to you 3 times and you didn't reply, you don't get the tech win. "
      + "Or: the last message in the chat is yours (a reply to your opponent), written before the 30-minutes-to-deadline mark, "
      + "and your opponent hasn't replied for at least 30 minutes — the tech win is yours.",
    cr_tech_wait: "If your opponent doesn't reply, the button works from {t}",
    cr_tech_deadline: "Deadline: {d}", cr_tech_opens: "Button opens: {t}", cr_tech_attempts: "Your attempts: {n} / 3",
    cr_tech_take: "✅ Take 3:0", cr_tech_done: "✅ Tech win recorded: 3:0", cr_close: "Close", cr_wait: "⏳ Checking…",
    cr_ag_btn: "📅 Agree on another time", cr_ag_hint: "Tashkent time. If accepted, nobody can enter a result before then.",
    cr_ag_send: "Propose", cr_ag_now: "Play now", cr_ag_cancel: "Cancel",
    cr_ag_mine: "⏳ Your proposal: {at} — waiting for reply", cr_ag_theirs: "📅 Opponent's proposal: {at}",
    cr_ag_accept: "✅ Accept", cr_ag_decline: "❌ Decline", cr_ag_locked: "🔒 Agreed: no result before {at}",
    cr_ag_other: "Another time", cr_ag_sent: "📅 Proposal sent", cr_ag_ok: "✅ Agreed",
    cr_ag_late: "⚠️ This is after the deadline: the match closes 0:0 at the deadline; after you play, an admin changes the score.",
    cr_err: {
      tech_has_result: "A result has already been entered for this match",
      agree_locked: "You agreed with your opponent on another time — no result before then",
      tech_no_deadline: "This match has no deadline — no tech win",
      tech_too_early: "The tech win opens 30 minutes before the deadline",
      tech_too_late: "The deadline has passed",
      tech_you_ignored: "Your opponent wrote to you at 3 different times and you didn't reply — no tech win for you",
      tech_opp_replied: "Your opponent replied in the chat — no tech win. Write 3 more times after their last message",
      tech_need_attempts: "You haven't written to your opponent in the bot chat at 3 different times (40+ minutes apart)",
      tech_wait_reply: "Your opponent still has time to reply — wait 30 minutes",
      agree_in_past: "That time has passed", agree_too_far: "Too far ahead (7 days max)", agree_bad_time: "Pick a time",
      agree_has_result: "A result is already entered — no agreement needed", agree_not_found: "Proposal not found or outdated",
      not_participant: "You're not a participant in this match",
    },
  },
};

function crT(key, vars) {
  const L = (typeof APP !== "undefined" && CRULE_TEXTS[APP.lang]) || CRULE_TEXTS.uz;
  let s = L[key] ?? CRULE_TEXTS.uz[key] ?? key;
  if (vars) for (const k of Object.keys(vars)) s = s.split(`{${k}}`).join(String(vars[k]));
  return s;
}
function crErr(e) {
  const raw = String((e && e.message) || e || "");
  const code = raw.split("|")[0];
  const L = (typeof APP !== "undefined" && CRULE_TEXTS[APP.lang]) || CRULE_TEXTS.uz;
  return "❌ " + ((L.cr_err || {})[code] || CRULE_TEXTS.uz.cr_err[code] || raw);
}
