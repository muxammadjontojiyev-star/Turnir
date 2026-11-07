// =============================================================
//  tb_i18n2.js — "TEAMLAR JANGI": 2026-11-07 yangi dizayn matnlari (ru/en). tb_i18n.js ga qo'shiladi (u 300 qatordan
//  oshmasligi uchun alohida). tb_i18n.js dan KEYIN, tb.js dan OLDIN ulanadi. Global: TB_I18N, TB_I18N_PATTERNS.
// =============================================================

Object.assign(TB_I18N.ru, {
  "Taklif qilish": "Пригласить", "Asosiy tarkib": "Основной состав", "A'zolar": "Участники", "Team logosi": "Логотип команды",
  "Do'stlarni chaqiring": "Позовите друзей", "Galereyadan": "Из галереи", "⚠️ Xavfli amallar": "⚠️ Опасные действия",
  "Team butunlay o'chadi, barcha a'zolar chiqariladi. Mavsum davomida tarqatib bo'lmaydi.":
    "Команда удаляется полностью, все участники исключаются. Во время сезона распустить нельзя.",
  "Teamga qo'shilish": "Вступить в команду", "O'z teamingizni ochish": "Создать свою команду",
  "Do'stingizdan taklif havolasini so'rang yoki pastdagi teamlar sardoriga yozing.":
    "Попросите ссылку у друга или напишите капитану одной из команд ниже.",
  "Pastdagi formada team nomini yozing.": "Введите название команды в форме ниже.",
  "Liga adminidan liga havolasini oling.": "Получите ссылку лиги у её админа.",
  "QO'SHILISH MUMKIN BO'LGAN TEAMLAR": "КОМАНДЫ, В КОТОРЫЕ МОЖНО ВСТУПИТЬ",
  "Yoqqan teamning sardoriga yozing — u sizga taklif havolasini yuboradi.":
    "Напишите капитану понравившейся команды — он пришлёт вам ссылку-приглашение.",
  "✈️ Yozish": "✈️ Написать", "Siz hali hech qaysi ligada emassiz": "Вы пока не состоите ни в одной лиге",
  "Sardor bilan bog'lanib bo'lmaydi": "С капитаном нельзя связаться", "Chiqarish": "Исключить",
});
Object.assign(TB_I18N.en, {
  "Taklif qilish": "Invite", "Asosiy tarkib": "Starting lineup", "A'zolar": "Members", "Team logosi": "Team logo",
  "Do'stlarni chaqiring": "Call your friends", "Galereyadan": "From gallery", "⚠️ Xavfli amallar": "⚠️ Danger zone",
  "Team butunlay o'chadi, barcha a'zolar chiqariladi. Mavsum davomida tarqatib bo'lmaydi.":
    "The team is deleted completely and all members are removed. It can't be disbanded during a season.",
  "Teamga qo'shilish": "Join a team", "O'z teamingizni ochish": "Create your own team",
  "Do'stingizdan taklif havolasini so'rang yoki pastdagi teamlar sardoriga yozing.":
    "Ask a friend for an invite link or message a captain of one of the teams below.",
  "Pastdagi formada team nomini yozing.": "Enter a team name in the form below.",
  "Liga adminidan liga havolasini oling.": "Get the league link from its admin.",
  "QO'SHILISH MUMKIN BO'LGAN TEAMLAR": "TEAMS YOU CAN JOIN",
  "Yoqqan teamning sardoriga yozing — u sizga taklif havolasini yuboradi.":
    "Message the captain of a team you like — they'll send you an invite link.",
  "✈️ Yozish": "✈️ Message", "Siz hali hech qaysi ligada emassiz": "You're not in any league yet",
  "Sardor bilan bog'lanib bo'lmaydi": "The captain can't be contacted", "Chiqarish": "Remove",
});
TB_I18N_PATTERNS.unshift(
  [/^(\d+) kishi$/, "$1 чел.", "$1 people"],
  [/^Ikki team bahsida o'yinchilar 1v1 o'ynaydi — ko'p g'alaba olgan team yutadi\. Asosiy tarkib: (\d+)–(\d+) kishi\.$/,
    "В матче двух команд игроки играют 1 на 1 — побеждает команда с большим числом побед. Основной состав: $1–$2 игроков.",
    "In a match between two teams players play 1v1 — the team with more wins wins. Starting lineup: $1–$2 players."],
);
