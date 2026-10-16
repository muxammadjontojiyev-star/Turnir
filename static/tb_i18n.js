// =============================================================
//  tb_i18n.js — "TEAMLAR JANGI": rus/ingliz tarjimasi (2026-10-16, 3-bosqich)
//  Kod ichidagi matnlar o'zbekcha qoldi (asl manba); bu fayl ko'rsatishdan oldin
//  ularni APP.lang bo'yicha almashtiradi:
//    tbT(s)              — bitta matn (aniq moslik, so'ng TB_I18N_PATTERNS)
//    tbI18nApply(el)     — el ichidagi matn tugunlari va placeholder/title atributlari
//    tbToast / tbConfirm — showToast / confirm ning tarjimali varianti (tb*.js ishlatadi)
//  Admin ekranlari (tb_admin*.js) o'zbekcha qoladi — bosh admin uchun.
//  tb.js dan OLDIN ulanadi. Global: APP, showToast.
// =============================================================

const TB_I18N = {
  ru: {
    "Yuklanmoqda…": "Загрузка…", "Teamim": "Моя команда", "Jang": "Битва", "Jadval": "Таблица",
    "Teamlar": "Команды", "Admin": "Админ", "TEAMLAR JANGI": "БИТВА КОМАНД",
    "Jamoangizni yig'ing va jangga kiring": "Соберите команду и вступайте в бой",
    "Team ochasiz yoki do'stingiz teamiga taklif havolasi orqali qo'shilasiz.": "Создайте команду или вступите в команду друга по ссылке-приглашению.",
    "Ikki team bahsida o'yinchilar 1v1 o'ynaydi — ko'p g'alaba olgan team yutadi.": "В матче двух команд игроки играют 1 на 1 — побеждает команда с большим числом побед.",
    "Teamlar divizionlarda liga formatida bellashadi.": "Команды соревнуются в дивизионах в формате лиги.",
    "TEAM OCHISH": "СОЗДАТЬ КОМАНДУ", "Belgi": "Значок", "⚔️ Team ochish": "⚔️ Создать команду",
    "Team admin tasdig'idan keyin turnirda qatnashadi. A'zolarni hozirdan yig'ishingiz mumkin.": "Команда участвует в турнире после одобрения админом. Собирать участников можно уже сейчас.",
    "Do'stingiz teamiga qo'shilish uchun undan taklif havolasini so'rang.": "Чтобы вступить в команду друга, попросите у него ссылку-приглашение.",
    "⏳ Tasdiq kutilmoqda": "⏳ Ожидает одобрения", "✅ Tasdiqlangan": "✅ Одобрена", "❌ Rad etilgan": "❌ Отклонена",
    "Sardor:": "Капитан:", "A'ZO": "УЧАСТНИКИ", "ASOSIY TARKIB": "ОСНОВНОЙ СОСТАВ", "SARDOR": "КАПИТАН",
    "Sardor qilish": "Сделать капитаном", "Chiqarish": "Исключить",
    "Team admin tasdig'ini kutmoqda. Shu vaqtda a'zolarni yig'ib, tarkibni tuzib qo'ying.": "Команда ждёт одобрения админа. Пока соберите участников и составьте состав.",
    "Tarkib hali tuzilmagan": "Состав ещё не составлен", "Teamni tarqatish": "Распустить команду",
    "Teamdan chiqish": "Выйти из команды", "a'zo": "уч.", "Hozircha tasdiqlangan team yo'q": "Пока нет одобренных команд",
    "← Ro'yxatga qaytish": "← К списку", "Davom etish": "Продолжить",
    "Siz shu teamning a'zosisiz.": "Вы уже в этой команде.",
    "Siz boshqa teamdasiz. Qo'shilish uchun avval undan chiqing.": "Вы в другой команде. Чтобы вступить, сначала выйдите из неё.",
    "Bu team admin tomonidan rad etilgan.": "Эта команда отклонена администратором.",
    "⚔️ Teamga qo'shilish": "⚔️ Вступить в команду", "TEAMGA TAKLIF": "ПРИГЛАШЕНИЕ В КОМАНДУ", "Bo'limga o'tish": "Перейти в раздел",
    "✅ Chiqarildi": "✅ Исключён", "✅ Sardorlik topshirildi": "✅ Капитанство передано",
    "✅ Team ochildi! Endi a'zolarni taklif qiling": "✅ Команда создана! Теперь пригласите участников",
    "✅ Teamga qo'shildingiz": "✅ Вы вступили в команду", "Teamdan chiqdingiz": "Вы вышли из команды", "Team tarqatildi": "Команда распущена",
    "A'zo teamdan chiqarilsinmi?": "Исключить участника из команды?",
    "Sardorlik shu a'zoga topshirilsinmi? Siz oddiy a'zo bo'lib qolasiz.": "Передать капитанство этому участнику? Вы станете обычным участником.",
    "Teamdan chiqasizmi?": "Выйти из команды?",
    "Team butunlay tarqatilsinmi? Barcha a'zolar chiqariladi. Qaytarib bo'lmaydi!": "Распустить команду полностью? Все участники будут исключены. Это необратимо!",
    "TAKLIF HAVOLASI": "ССЫЛКА-ПРИГЛАШЕНИЕ",
    "Havolani do'stlaringizga yuboring — bosgan kishi teamingizga qo'shiladi.": "Отправьте ссылку друзьям — перешедший по ней вступит в вашу команду.",
    "🔗 Havolani olish": "🔗 Получить ссылку", "Tanlangan:": "Выбрано:", "Tozalash": "Очистить",
    "O'yinchini bosing — tarkibga qo'shiladi (bosish tartibi = tarkib tartibi). Qayta bossangiz olib tashlanadi.": "Нажмите на игрока — он попадёт в состав (порядок нажатий = порядок состава). Повторное нажатие убирает.",
    "💾 Tarkibni saqlash": "💾 Сохранить состав", "📤 Ulashish": "📤 Поделиться", "📋 Nusxalash": "📋 Копировать",
    "↻ Yangi havola (eskisi ishlamay qoladi)": "↻ Новая ссылка (старая перестанет работать)",
    "✅ Nusxalandi": "✅ Скопировано", "✅ Yangi havola tayyor": "✅ Новая ссылка готова", "✅ Asosiy tarkib saqlandi": "✅ Состав сохранён",
    "Yangi havola yaratilsinmi? Eski havola ishlamay qoladi.": "Создать новую ссылку? Старая перестанет работать.",
    "Mavsum hali e'lon qilinmagan": "Сезон ещё не объявлен", "Bu turda teamingiz dam oladi (raqib yo'q).": "В этом туре ваша команда отдыхает (нет соперника).",
    "Hozir ochiq o'yiningiz yo'q. Asosiy tarkibga kirgan o'yinchilar juftlanadi.": "Сейчас у вас нет открытой игры. В пары ставятся игроки основного состава.",
    "O'yinlar mavsum boshlangach shu yerda chiqadi.": "Игры появятся здесь после начала сезона.", "MENING O'YINIM": "МОЯ ИГРА",
    "⏳ Raqib tasdig'i kutilmoqda": "⏳ Ждём подтверждения соперника", "Raqib natija kiritdi:": "Соперник ввёл результат:",
    "(sizning hisobingiz birinchi)": "(ваш счёт первым)", "✅ Tasdiqlash": "✅ Подтвердить", "❌ Rad etish": "❌ Отклонить",
    "Siz": "Вы", "Raqib": "Соперник", "Natijani yuborish": "Отправить результат", "💬 Chat": "💬 Чат",
    "Juftliklar tur ochilganda tuziladi": "Пары формируются при открытии тура", "Team": "Команда",
    "O": "И", "G": "В", "D": "Н", "M": "П", "Och": "О", "1v1 g'alabalar farqi": "Разница побед 1 на 1",
    "Ochko: g'alaba 3 · durang 1. Teng bo'lsa: 1v1 g'alabalar farqi → gol farqi.": "Очки: победа 3 · ничья 1. При равенстве: разница побед 1 на 1 → разница мячей.",
    "Bu turda bahs yo'q": "В этом туре нет матчей", "Hisobni kiriting": "Введите счёт",
    "✅ Yuborildi — raqib tasdiqlaydi": "✅ Отправлено — соперник подтвердит", "✅ Tasdiqlandi": "✅ Подтверждено", "Rad etildi": "Отклонено",
    "Natija rad etilsinmi? Raqib qayta kiritadi.": "Отклонить результат? Соперник введёт заново.",
    // xatolar (TB_ERR)
    "Nom 3–24 belgidan iborat bo'lsin": "Название — от 3 до 24 символов",
    "Nomda faqat harf, raqam, probel va - . ' bo'lishi mumkin": "В названии допустимы только буквы, цифры, пробел и - . '",
    "Nomda nomaqbul so'z bor": "В названии недопустимое слово", "Belgini ro'yxatdan tanlang": "Выберите значок из списка",
    "Siz allaqachon boshqa teamdasiz": "Вы уже в другой команде", "Siz allaqachon shu teamdasiz": "Вы уже в этой команде",
    "Bu nom band — boshqasini tanlang": "Название занято — выберите другое", "Team topilmadi yoki havola eskirgan": "Команда не найдена или ссылка устарела",
    "Bu team admin tomonidan rad etilgan": "Эта команда отклонена администратором", "Siz teamda emassiz": "Вы не в команде",
    "Sardor chiqa olmaydi — avval sardorlikni topshiring yoki teamni tarqating": "Капитан не может выйти — сначала передайте капитанство или распустите команду",
    "Bu amal faqat sardorga ruxsat etilgan": "Это действие доступно только капитану", "A'zo topilmadi": "Участник не найден",
    "O'zingizni chiqara olmaysiz": "Нельзя исключить себя", "Asosiy tarkib soni chegaradan tashqarida": "Размер состава вне допустимых пределов",
    "Tarkibda takror o'yinchi bor": "В составе повторяется игрок", "Tarkibda teamga a'zo bo'lmagan o'yinchi bor": "В составе есть игрок не из команды",
    "Juda tez — biroz kuting": "Слишком быстро — подождите", "Team mavsumda qatnashgan — tarqatib/o'chirib bo'lmaydi": "Команда участвовала в сезоне — распустить/удалить нельзя",
    "Hisob 0–30 oralig'ida bo'lsin": "Счёт должен быть от 0 до 30", "O'yin topilmadi": "Игра не найдена", "Bu sizning o'yiningiz emas": "Это не ваша игра",
    "Tur yopilgan — natija kiritib bo'lmaydi": "Тур закрыт — ввести результат нельзя", "Natija allaqachon tasdiqlangan": "Результат уже подтверждён",
    "Tasdiqlanadigan natija yo'q": "Нет результата для подтверждения", "O'zingiz kiritgan natijani raqib tasdiqlaydi": "Ваш результат подтверждает соперник",
    "Faol mavsum yo'q": "Нет активного сезона", "Mavsum hali boshlanmagan": "Сезон ещё не начался",
    // 2026-10-16: ligalar
    "Team ochish uchun liga adminidan liga havolasini oling.": "Чтобы создать команду, получите ссылку на лигу у её админа.",
    "LIGA": "ЛИГА", "Liga:": "Лига:",
    "Siz allaqachon teamdasiz — yangi team ochish uchun avval undan chiqing": "Вы уже в команде — чтобы создать новую, сначала выйдите из неё",
    "Siz hali hech qaysi ligada emassiz": "Вы пока не состоите ни в одной лиге",
    "Liga topilmadi yoki havola eskirgan": "Лига не найдена или ссылка устарела",
    "Bu amal faqat liga adminiga ruxsat etilgan": "Это действие доступно только админу лиги",
    // 2026-10-16: logolar
    "TEAM LOGOSI": "ЛОГОТИП КОМАНДЫ", "Liga logosi": "Логотип лиги", "🖼 Galereyadan logo": "🖼 Логотип из галереи",
    "Logoni olib tashlash": "Удалить логотип", "Kvadrat rasm yaxshi chiqadi — markazi kesib olinadi.": "Лучше квадратное фото — обрезается по центру.",
    "✅ Logo yangilandi": "✅ Логотип обновлён", "Logo olib tashlandi": "Логотип удалён", "Logo olib tashlansinmi?": "Удалить логотип?",
    "Team logosini ochilgandan keyin galereyadan qo'yasiz.": "Логотип команды можно поставить из галереи после создания.",
    "Rasm juda katta": "Изображение слишком большое", "Rasm formati noto'g'ri (JPEG/PNG/WEBP)": "Неверный формат (JPEG/PNG/WEBP)", "Rasm tanlanmadi": "Изображение не выбрано",
  },
  en: {
    "Yuklanmoqda…": "Loading…", "Teamim": "My team", "Jang": "Battle", "Jadval": "Table",
    "Teamlar": "Teams", "Admin": "Admin", "TEAMLAR JANGI": "TEAM BATTLE",
    "Jamoangizni yig'ing va jangga kiring": "Build your team and join the battle",
    "Team ochasiz yoki do'stingiz teamiga taklif havolasi orqali qo'shilasiz.": "Create a team or join a friend's team via an invite link.",
    "Ikki team bahsida o'yinchilar 1v1 o'ynaydi — ko'p g'alaba olgan team yutadi.": "In a team match players play 1v1 — the team with more wins takes it.",
    "Teamlar divizionlarda liga formatida bellashadi.": "Teams compete in divisions in a league format.",
    "TEAM OCHISH": "CREATE A TEAM", "Belgi": "Badge", "⚔️ Team ochish": "⚔️ Create team",
    "Team admin tasdig'idan keyin turnirda qatnashadi. A'zolarni hozirdan yig'ishingiz mumkin.": "The team joins the tournament after admin approval. You can gather members right away.",
    "Do'stingiz teamiga qo'shilish uchun undan taklif havolasini so'rang.": "To join a friend's team, ask them for the invite link.",
    "⏳ Tasdiq kutilmoqda": "⏳ Awaiting approval", "✅ Tasdiqlangan": "✅ Approved", "❌ Rad etilgan": "❌ Rejected",
    "Sardor:": "Captain:", "A'ZO": "MEMBERS", "ASOSIY TARKIB": "STARTING LINEUP", "SARDOR": "CAPTAIN",
    "Sardor qilish": "Make captain", "Chiqarish": "Remove",
    "Team admin tasdig'ini kutmoqda. Shu vaqtda a'zolarni yig'ib, tarkibni tuzib qo'ying.": "The team is awaiting admin approval. Meanwhile, gather members and set the lineup.",
    "Tarkib hali tuzilmagan": "Lineup not set yet", "Teamni tarqatish": "Disband team",
    "Teamdan chiqish": "Leave team", "a'zo": "members", "Hozircha tasdiqlangan team yo'q": "No approved teams yet",
    "← Ro'yxatga qaytish": "← Back to list", "Davom etish": "Continue",
    "Siz shu teamning a'zosisiz.": "You are already in this team.",
    "Siz boshqa teamdasiz. Qo'shilish uchun avval undan chiqing.": "You are in another team. Leave it first to join.",
    "Bu team admin tomonidan rad etilgan.": "This team was rejected by the admin.",
    "⚔️ Teamga qo'shilish": "⚔️ Join team", "TEAMGA TAKLIF": "TEAM INVITE", "Bo'limga o'tish": "Go to section",
    "✅ Chiqarildi": "✅ Removed", "✅ Sardorlik topshirildi": "✅ Captaincy transferred",
    "✅ Team ochildi! Endi a'zolarni taklif qiling": "✅ Team created! Now invite members",
    "✅ Teamga qo'shildingiz": "✅ You joined the team", "Teamdan chiqdingiz": "You left the team", "Team tarqatildi": "Team disbanded",
    "A'zo teamdan chiqarilsinmi?": "Remove this member from the team?",
    "Sardorlik shu a'zoga topshirilsinmi? Siz oddiy a'zo bo'lib qolasiz.": "Transfer captaincy to this member? You will become a regular member.",
    "Teamdan chiqasizmi?": "Leave the team?",
    "Team butunlay tarqatilsinmi? Barcha a'zolar chiqariladi. Qaytarib bo'lmaydi!": "Disband the team completely? All members will be removed. This cannot be undone!",
    "TAKLIF HAVOLASI": "INVITE LINK",
    "Havolani do'stlaringizga yuboring — bosgan kishi teamingizga qo'shiladi.": "Send the link to friends — whoever opens it joins your team.",
    "🔗 Havolani olish": "🔗 Get link", "Tanlangan:": "Selected:", "Tozalash": "Clear",
    "O'yinchini bosing — tarkibga qo'shiladi (bosish tartibi = tarkib tartibi). Qayta bossangiz olib tashlanadi.": "Tap a player to add them (tap order = lineup order). Tap again to remove.",
    "💾 Tarkibni saqlash": "💾 Save lineup", "📤 Ulashish": "📤 Share", "📋 Nusxalash": "📋 Copy",
    "↻ Yangi havola (eskisi ishlamay qoladi)": "↻ New link (the old one stops working)",
    "✅ Nusxalandi": "✅ Copied", "✅ Yangi havola tayyor": "✅ New link ready", "✅ Asosiy tarkib saqlandi": "✅ Lineup saved",
    "Yangi havola yaratilsinmi? Eski havola ishlamay qoladi.": "Create a new link? The old one will stop working.",
    "Mavsum hali e'lon qilinmagan": "Season not announced yet", "Bu turda teamingiz dam oladi (raqib yo'q).": "Your team has a bye this round (no opponent).",
    "Hozir ochiq o'yiningiz yo'q. Asosiy tarkibga kirgan o'yinchilar juftlanadi.": "You have no open game now. Only lineup players are paired.",
    "O'yinlar mavsum boshlangach shu yerda chiqadi.": "Games will appear here once the season starts.", "MENING O'YINIM": "MY GAME",
    "⏳ Raqib tasdig'i kutilmoqda": "⏳ Waiting for opponent's confirmation", "Raqib natija kiritdi:": "Opponent submitted:",
    "(sizning hisobingiz birinchi)": "(your score first)", "✅ Tasdiqlash": "✅ Confirm", "❌ Rad etish": "❌ Reject",
    "Siz": "You", "Raqib": "Opponent", "Natijani yuborish": "Submit result", "💬 Chat": "💬 Chat",
    "Juftliklar tur ochilganda tuziladi": "Pairs are made when the round opens", "Team": "Team",
    "O": "P", "G": "W", "D": "D", "M": "L", "Och": "Pts", "1v1 g'alabalar farqi": "1v1 win difference",
    "Ochko: g'alaba 3 · durang 1. Teng bo'lsa: 1v1 g'alabalar farqi → gol farqi.": "Points: win 3 · draw 1. Tiebreak: 1v1 win difference → goal difference.",
    "Bu turda bahs yo'q": "No matches this round", "Hisobni kiriting": "Enter the score",
    "✅ Yuborildi — raqib tasdiqlaydi": "✅ Sent — opponent will confirm", "✅ Tasdiqlandi": "✅ Confirmed", "Rad etildi": "Rejected",
    "Natija rad etilsinmi? Raqib qayta kiritadi.": "Reject the result? The opponent will resubmit.",
    "Nom 3–24 belgidan iborat bo'lsin": "Name must be 3–24 characters",
    "Nomda faqat harf, raqam, probel va - . ' bo'lishi mumkin": "Only letters, digits, spaces and - . ' are allowed",
    "Nomda nomaqbul so'z bor": "The name contains an inappropriate word", "Belgini ro'yxatdan tanlang": "Choose a badge from the list",
    "Siz allaqachon boshqa teamdasiz": "You are already in another team", "Siz allaqachon shu teamdasiz": "You are already in this team",
    "Bu nom band — boshqasini tanlang": "Name taken — choose another", "Team topilmadi yoki havola eskirgan": "Team not found or link expired",
    "Bu team admin tomonidan rad etilgan": "This team was rejected by the admin", "Siz teamda emassiz": "You are not in a team",
    "Sardor chiqa olmaydi — avval sardorlikni topshiring yoki teamni tarqating": "The captain can't leave — transfer captaincy or disband the team first",
    "Bu amal faqat sardorga ruxsat etilgan": "Only the captain can do this", "A'zo topilmadi": "Member not found",
    "O'zingizni chiqara olmaysiz": "You can't remove yourself", "Asosiy tarkib soni chegaradan tashqarida": "Lineup size is out of range",
    "Tarkibda takror o'yinchi bor": "A player is repeated in the lineup", "Tarkibda teamga a'zo bo'lmagan o'yinchi bor": "The lineup has a non-member",
    "Juda tez — biroz kuting": "Too fast — please wait", "Team mavsumda qatnashgan — tarqatib/o'chirib bo'lmaydi": "The team played in a season — it can't be disbanded/deleted",
    "Hisob 0–30 oralig'ida bo'lsin": "Score must be 0–30", "O'yin topilmadi": "Game not found", "Bu sizning o'yiningiz emas": "This is not your game",
    "Tur yopilgan — natija kiritib bo'lmaydi": "Round closed — result can't be entered", "Natija allaqachon tasdiqlangan": "Result already confirmed",
    "Tasdiqlanadigan natija yo'q": "Nothing to confirm", "O'zingiz kiritgan natijani raqib tasdiqlaydi": "Your opponent confirms your submission",
    "Faol mavsum yo'q": "No active season", "Mavsum hali boshlanmagan": "Season hasn't started yet",
    "Team ochish uchun liga adminidan liga havolasini oling.": "To create a team, get the league link from its admin.",
    "LIGA": "LEAGUE", "Liga:": "League:",
    "Siz allaqachon teamdasiz — yangi team ochish uchun avval undan chiqing": "You're already in a team — leave it first to create a new one",
    "Siz hali hech qaysi ligada emassiz": "You're not in any league yet",
    "Liga topilmadi yoki havola eskirgan": "League not found or link expired",
    "Bu amal faqat liga adminiga ruxsat etilgan": "Only the league admin can do this",
    "TEAM LOGOSI": "TEAM LOGO", "Liga logosi": "League logo", "🖼 Galereyadan logo": "🖼 Logo from gallery",
    "Logoni olib tashlash": "Remove logo", "Kvadrat rasm yaxshi chiqadi — markazi kesib olinadi.": "A square image works best — the center is cropped.",
    "✅ Logo yangilandi": "✅ Logo updated", "Logo olib tashlandi": "Logo removed", "Logo olib tashlansinmi?": "Remove the logo?",
    "Team logosini ochilgandan keyin galereyadan qo'yasiz.": "You can set the team logo from your gallery after creating it.",
    "Rasm juda katta": "Image is too large", "Rasm formati noto'g'ri (JPEG/PNG/WEBP)": "Wrong image format (JPEG/PNG/WEBP)", "Rasm tanlanmadi": "No image selected",
  },
};

// [regex, ru, en] — $1, $2... guruhlar
const TB_I18N_PATTERNS = [
  [/^❌ (.+)$/s, (m) => "❌ " + tbT(m[1]), (m) => "❌ " + tbT(m[1])],
  [/^Xato: (.*)$/s, "Ошибка: $1", "Error: $1"],
  [/^Sardor asosiy tarkibni tuzadi \((\d+)–(\d+) kishi\)\.$/, "Капитан составляет основной состав ($1–$2 игроков).", "The captain sets the starting lineup ($1–$2 players)."],
  [/^Team nomi \((\d+)–(\d+) belgi\)$/, "Название команды ($1–$2 символов)", "Team name ($1–$2 characters)"],
  [/^🏆 (\d+)-mavsum · (\d+)-divizion chempioni$/, "🏆 Сезон $1 · чемпион $2-го дивизиона", "🏆 Season $1 · Division $2 champion"],
  [/^Sabab: (.*)$/s, "Причина: $1", "Reason: $1"],
  [/^Sardor: (.*)$/s, "Капитан: $1", "Captain: $1"],
  [/^Liga admini: (.*)$/s, "Админ лиги: $1", "League admin: $1"],
  [/^Asosiy tarkib to'liq emas: (\d+)\/(\d+)\. Tarkibni tuzing\.$/, "Состав неполный: $1/$2. Составьте состав.", "Lineup incomplete: $1/$2. Set the lineup."],
  [/^Asosiy tarkib to'liq emas: (\d+)\/(\d+)\. Sardor tarkibni tuzishi kerak\.$/, "Состав неполный: $1/$2. Капитан должен составить состав.", "Lineup incomplete: $1/$2. The captain must set it."],
  [/^ASOSIY TARKIB \((\d+)\)$/, "ОСНОВНОЙ СОСТАВ ($1)", "STARTING LINEUP ($1)"],
  [/^A'ZOLAR \((\d+)\)$/, "УЧАСТНИКИ ($1)", "MEMBERS ($1)"],
  [/^TASDIQLANGAN TEAMLAR \((\d+)\)$/, "ОДОБРЕННЫЕ КОМАНДЫ ($1)", "APPROVED TEAMS ($1)"],
  [/^Tarkib uchun kamida (\d+) a'zo kerak — hozir (\d+) ta\. Ko'proq do'st taklif qiling\.$/, "Для состава нужно минимум $1 участников — сейчас $2. Пригласите больше друзей.", "The lineup needs at least $1 members — you have $2. Invite more friends."],
  [/^Ko'pi bilan (\d+) kishi$/, "Не больше $1 игроков", "At most $1 players"],
  [/^⚔️ «(.+)» teamiga qo'shiling — Teamlar jangi!$/, "⚔️ Вступайте в команду «$1» — Битва команд!", "⚔️ Join team «$1» — Team Battle!"],
  [/^(\d+)-mavsum · qur'a o'tkazildi, turlar tez orada boshlanadi$/, "Сезон $1 · жеребьёвка проведена, туры скоро начнутся", "Season $1 · draw done, rounds start soon"],
  [/^(\d+)-mavsum yakunlangan$/, "Сезон $1 завершён", "Season $1 finished"],
  [/^(\d+)-mavsum · (\d+)\/(\d+)-tur · deadline 23:30$/, "Сезон $1 · тур $2/$3 · дедлайн 23:30", "Season $1 · round $2/$3 · deadline 23:30"],
  [/^TEAMIMNING BAHSI \((\d+)-TUR\)$/, "МАТЧ МОЕЙ КОМАНДЫ ($1-Й ТУР)", "MY TEAM'S MATCH (ROUND $1)"],
  [/^(\d+)-tur · (\d+)-juftlik$/, "$1-й тур · пара $2", "Round $1 · pair $2"],
  [/^Texnik natija: ikkala teamning tarkibi yetmadi$/, "Техническое: у обеих команд не хватило состава", "Technical: both lineups were short"],
  [/^Texnik natija: (.+) tarkibi yetmadi$/s, "Техническое: у «$1» не хватило состава", "Technical: «$1» lineup was short"],
  [/^(\d+)-divizion$/, "$1-й дивизион", "Division $1"],
  [/^Yuqori divizionga ko'tariladi \((\d+)\)$/, "Повышение в высший дивизион ($1)", "Promoted to the higher division ($1)"],
  [/^Quyi divizionga tushadi \((\d+)\)$/, "Понижение в низший дивизион ($1)", "Relegated to the lower division ($1)"],
  [/^(\d+)-tur$/, "$1-й тур", "Round $1"],
  [/^Natija: Siz (\d+) : (\d+) Raqib\. Yuborilsinmi\?$/, "Результат: Вы $1 : $2 Соперник. Отправить?", "Result: You $1 : $2 Opponent. Send?"],
];

function tbLang() { return (typeof APP !== "undefined" && APP.lang) || "uz"; }

function tbT(s) {
  const lang = tbLang();
  if (lang === "uz" || s == null) return s;
  const dict = TB_I18N[lang] || {};
  if (Object.prototype.hasOwnProperty.call(dict, s)) return dict[s];
  const li = lang === "ru" ? 1 : 2;
  for (const p of TB_I18N_PATTERNS) {
    const m = String(s).match(p[0]);
    if (!m) continue;
    const rep = p[li];
    return typeof rep === "function" ? rep(m) : String(s).replace(p[0], rep);
  }
  return s;
}

function tbI18nApply(root) {
  if (!root || tbLang() === "uz") return;
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const nodes = [];
  while (walker.nextNode()) nodes.push(walker.currentNode);
  for (const n of nodes) {
    const raw = n.nodeValue, trimmed = raw.trim();
    if (!trimmed || !/[A-Za-z']/.test(trimmed)) continue;
    const tr = tbT(trimmed);
    if (tr !== trimmed) n.nodeValue = raw.replace(trimmed, tr);
  }
  root.querySelectorAll("[placeholder],[title]").forEach(el => {
    for (const a of ["placeholder", "title"]) {
      const v = el.getAttribute(a);
      if (v) { const tr = tbT(v); if (tr !== v) el.setAttribute(a, tr); }
    }
  });
}

function tbToast(msg) { showToast(tbT(msg)); }
function tbConfirm(msg) { return window.confirm(tbT(msg)); }

// ---- Xato kodlari -> o'zbekcha matn (tb.js dan ko'chirildi, 2026-10-16); tbT ularni tarjima qiladi ----
const TB_ERR = {
  bad_name_len: "Nom 3–24 belgidan iborat bo'lsin",
  bad_name_chars: "Nomda faqat harf, raqam, probel va - . ' bo'lishi mumkin",
  bad_name_profanity: "Nomda nomaqbul so'z bor",
  bad_emoji: "Belgini ro'yxatdan tanlang",
  already_in_team: "Siz allaqachon boshqa teamdasiz",
  already_member: "Siz allaqachon shu teamdasiz",
  name_taken: "Bu nom band — boshqasini tanlang",
  not_found: "Team topilmadi yoki havola eskirgan",
  rejected: "Bu team admin tomonidan rad etilgan",
  not_in_team: "Siz teamda emassiz",
  captain_cannot_leave: "Sardor chiqa olmaydi — avval sardorlikni topshiring yoki teamni tarqating",
  not_captain: "Bu amal faqat sardorga ruxsat etilgan",
  member_not_found: "A'zo topilmadi",
  cannot_remove_self: "O'zingizni chiqara olmaysiz",
  lineup_size: "Asosiy tarkib soni chegaradan tashqarida",
  lineup_duplicate: "Tarkibda takror o'yinchi bor",
  lineup_not_member: "Tarkibda teamga a'zo bo'lmagan o'yinchi bor",
  bot_username_missing: "Bot nomi sozlanmagan (BOT_USERNAME)",
  too_many_requests: "Juda tez — biroz kuting",
  // 2026-10-16 (2-bosqich)
  in_active_season: "Team mavsumda qatnashgan — tarqatib/o'chirib bo'lmaydi",
  bad_score: "Hisob 0–30 oralig'ida bo'lsin",
  game_not_found: "O'yin topilmadi",
  not_your_game: "Bu sizning o'yiningiz emas",
  round_closed: "Tur yopilgan — natija kiritib bo'lmaydi",
  already_confirmed: "Natija allaqachon tasdiqlangan",
  nothing_to_confirm: "Tasdiqlanadigan natija yo'q",
  own_submission: "O'zingiz kiritgan natijani raqib tasdiqlaydi",
  no_season: "Faol mavsum yo'q",
  active_exists: "Faol mavsum bor — avval uni yakunlang",
  not_enough_teams: "Qatnasha oladigan team kamida 2 ta bo'lishi kerak",
  bad_division_size: "Divizion hajmi 4–20 oralig'ida bo'lsin",
  already_started: "Turlar allaqachon boshlangan",
  not_running: "Mavsum hali boshlanmagan",
  all_rounds_done: "Barcha turlar o'tib bo'lgan",
  // 2026-10-16 (ligalar)
  league_not_found: "Liga topilmadi yoki havola eskirgan",
  league_name_taken: "Bu liga nomi band",
  admin_not_found: "Bunday foydalanuvchi topilmadi (botga /start bosgan bo'lishi kerak)",
  league_not_empty: "Ligada teamlar yoki mavsumlar bor — o'chirib bo'lmaydi",
  bad_lineup_limits: "Tarkib chegaralari noto'g'ri (3–30, kamida ≤ ko'pi bilan)",
  not_league_admin: "Bu amal faqat liga adminiga ruxsat etilgan",
  // 2026-10-16: logolar
  image_too_large: "Rasm juda katta",
  bad_image: "Rasm formati noto'g'ri (JPEG/PNG/WEBP)",
  empty_image: "Rasm tanlanmadi",
};
function tbErr(e) { return TB_ERR[e && e.message] || ("Xato: " + (e && e.message || "")); }
