// texts_pt_fmt.js — SHAXSIY turnir formatlari va klub tanlash tarjimalari (2026-10-07).
// texts_pt.js dan KEYIN ulanadi: PT_TEXTS (zaxira) va TEXTS (joriy til) ga qo'shiladi.

const PT_FMT_TEXTS = {
  uz: {
    pt_adm_sec_big: "⚠️ KATTA HISOBLAR",
    pt_big_hint: "Bir tomon {n} tadan ko'p gol kiritsa, natija avtomatik tasdiqlanmaydi — siz tasdiqlaysiz yoki rad etasiz.",
    pt_big_decide_hint: "Katta hisob — tasdiqlaysizmi?",
    pt_big_ok: "Tasdiqlash", pt_big_no: "Rad etish",
    pt_big_wait: "Katta hisob — tashkilotchi/admin tasdig'i kutilmoqda",
    pt_big_no_ask: "Katta hisob rad etilsinmi? Natija o'chadi (tur yopilgan bo'lsa — 0:0).",
    pt_big_ok_toast: "Natija tasdiqlandi", pt_big_no_toast: "Natija rad etildi",
    pt_big_submit_ask: "Hisobda {n} tadan ko'p gol bor — natija tashkilotchi/admin tasdig'iga yuboriladi. Davom etasizmi?",
    pt_big_sent: "Natija admin tasdig'iga yuborildi",
    pt_big_next: "Tasdiq kutayotgan katta hisoblar: {n}",
    pt_big_open: "⚠️ Ko'rib chiqish",
    pt_adm_sec_delete: "🗑 TURNIRNI O'CHIRISH",
    pt_del_hint: "Muddati o'tgan yoki xato ochilgan turnirni butunlay o'chirish. Barcha a'zolar, o'yinlar va chat o'chadi, qaytarib bo'lmaydi.",
    pt_del_btn: "Turnirni o'chirish",
    pt_del_ask: "«{name}» turnirini butunlay o'chirasizmi? Buni qaytarib bo'lmaydi.",
    pt_del_ask_paid: "⚠️ Turnir uchun to'langan summa qaytarilmaydi.",
    pt_del_ask_running: "⚠️ Turnir boshlangan — barcha o'yinlar va natijalar o'chadi, ishtirokchilarga xabar boradi.",
    pt_deleted: "Turnir o'chirildi",
    pt_sum_leagues: "{k} ta liga · {n} klub · {rounds} tur · har liga o'z chempioni",
    pt_sum_classic2: "guruhda uy + mehmon, pley-offda javob o'yini (final — 1 o'yin)",
    pt_leagues_hint: "Bir nechta liga tanlash mumkin — har liga alohida jadval va chempion. Har qo'shimcha liga: +{price} so'm.",
    pt_legs_label_classic: "O'yinlar: 1 martalik yoki javob o'yini bilan",
    pt_price_extra: "+{n} liga × {price} so'm",
    pt_legs_2_short: "2 doira", pt_n_leagues: "{n} liga",
    pt_leg_n: "{n}-o'yin", pt_aggregate: "Umumiy hisob", pt_first_leg: "1-o'yin",
    pt_err_first_leg: "Avval 1-o'yin natijasi tasdiqlanishi kerak.",
    pt_err_aggregate: "Ikki o'yin yig'indisi teng bo'lmasligi kerak — penalti 2-o'yin ichida, yakuniy hisobni kiriting.",
    pt_rules_default_classic2:
      "Guruhlarda 4 kishi, har kim har kim bilan 2 marta (uy + mehmon) o'ynaydi.\n" +
      "G'alaba — 3 ochko, durang — 1, mag'lubiyat — 0. Ochko teng bo'lsa: gollar farqi, so'ng urilgan gollar.\n" +
      "Pley-offga guruh g'oliblari va eng yaxshi 2-o'rinlar chiqadi.\n" +
      "Pley-offda ikki o'yin (javob o'yini) — g'olib yig'indi bo'yicha; teng bo'lsa penalti 2-o'yin ichida. Final — 1 o'yin, durangsiz.\n" +
      "Natijani o'yinchilardan biri kiritadi, raqib tasdiqlaydi. Kelishmovchilikni tashkilotchi hal qiladi.\n" +
      "Guruh bosqichida tur muddati o'tgach tasdiqlanmagan natijalar tasdiqlanadi, o'ynalmagan o'yinlar 0:0.\n" +
      "Xona ID va kelishuvlar — o'yin chatida. Raqibingizga hurmat bilan munosabatda bo'ling.",
    pt_fmt_league: "Liga", pt_fmt_cl: "Chempionlar ligasi", pt_fmt_el: "Yevropa ligasi",
    pt_fmt_wc: "Jahon chempionati", pt_fmt_classic: "Erkin format",
    pt_fmt_league_sub: "LaLiga, Premier Liga… — har kim klub tanlaydi, yagona jadval",
    pt_fmt_cl_sub: "8–36 kishi · yagona jadval + pley-off",
    pt_fmt_el_sub: "8–36 kishi · yagona jadval + pley-off",
    pt_fmt_wc_sub: "8–48 kishi · terma jamoalar, guruhlar + pley-off",
    pt_fmt_classic_sub: "8–128 kishi · 4 kishilik guruhlar + pley-off",
    pt_step_format: "Formatni tanlang", pt_step_league: "Ligani tanlang", pt_step_details: "Turnir ma'lumotlari",
    pt_legs_label: "Har bir juftlik necha marta o'ynaydi", pt_legs_1: "1 doira", pt_legs_2: "2 doira (uy + mehmon)",
    pt_league_clubs: "{n} klub",
    pt_size_fixed: "{n} ishtirokchi — tanlangan liga(lar)dagi klublar soni",
    pt_sum_league: "{n} klub · {rounds} tur · jadval birinchisi chempion",
    pt_sum_cl: "{rounds} tur yagona jadval · top-{q} to'g'ridan {stage}ga, {from}–{to}-o'rinlar pley-off raundida",
    pt_team_hint_club: "Har bir ishtirokchi qo'shilayotganda o'z klubini tanlaydi (bitta klub — bitta kishi).",
    pt_team_hint_wc: "Har bir ishtirokchi qo'shilayotganda terma jamoa tanlaydi (bitta jamoa — bitta kishi).",
    pt_team_busy: "band", pt_team_search: "🔍 Qidirish…", pt_team_none: "Hech narsa topilmadi",
    pt_team_pick_club: "Klubingizni tanlang", pt_team_pick_wc: "Terma jamoangizni tanlang",
    pt_team_my_club: "SIZNING KLUBINGIZ", pt_team_my_wc: "SIZNING TERMA JAMOANGIZ",
    pt_team_change: "O'zgartirish", pt_team_save: "Tanlash", pt_team_saved: "Saqlandi",
    pt_err_team_taken: "Bu jamoani boshqa ishtirokchi tanlab bo'ldi — boshqasini tanlang.",
    pt_join_format: "Format",
    pt_block_teams: "{n} kishi hali klub/jamoa tanlamagan — hamma tanlagach boshlash mumkin.",
    pt_block_league: "Liga to'lishi kerak: {n}/{max}. Har bir klubga bitta ishtirokchi.",
    pt_block_even: "Hozir {n} kishi — juft son bo'lishi kerak (har turda hamma o'ynaydi).",
    pt_next_teams: "Hamma klubini tanlashi kerak",
    pt_hero_rounds: "TURLAR",
    pt_table_done: "Liga bosqichi yakunlandi.",
    pt_seg_table: "Jadval", pt_prof_table: "Jadval · #{pos}",
    pt_prize_hint_league: "Oxirgi turdan keyin jadval birinchisi chempion bo'ladi.",
    pt_stage_po: "PLEY-OFF RAUNDI", pt_stage_po_n: "Pley-off raundi {n}",
    pt_po_hint: "Top-{q} to'g'ridan setkaga ({size} kishi), {from}–{to}-o'rinlar pley-off raundida (1 o'yin) o'ynaydi.",
    pt_col_w: "G", pt_col_d: "D", pt_col_l: "M",
    pt_zone_champ: "Chempion", pt_zone_direct: "To'g'ridan setkaga (top-{q})", pt_zone_po: "Pley-off raundi ({from}–{to})",
    pt_start_hint_league: "Liga to'lishi ({max} kishi) va hamma klub tanlagan bo'lishi kerak. Boshlangach tarkib o'zgarmaydi.",
    pt_start_hint_cl: "Kamida {min} kishi, juft son va hamma klub tanlagan bo'lishi kerak. Boshlangach tarkib o'zgarmaydi.",
    pt_rules_default_league:
      "Har kim tanlangan ligadagi bitta klub bilan o'ynaydi; hamma bir jadvalda.\n" +
      "Har kim har kim bilan 1 yoki 2 marta (uy + mehmon) o'ynaydi — tashkilotchi tanlagan.\n" +
      "G'alaba — 3 ochko, durang — 1, mag'lubiyat — 0. Ochko teng bo'lsa: gollar farqi, so'ng urilgan gollar.\n" +
      "Oxirgi tur yopilgach jadval birinchisi chempion bo'ladi.\n" +
      "Natijani o'yinchilardan biri kiritadi, raqib tasdiqlaydi. Kelishmovchilikni tashkilotchi hal qiladi.\n" +
      "Tur muddati o'tgach tasdiqlanmagan natijalar tasdiqlanadi, o'ynalmagan o'yinlar 0:0.\n" +
      "Xona ID va kelishuvlar — o'yin chatida. Raqibingizga hurmat bilan munosabatda bo'ling.",
    pt_rules_default_cl:
      "Hamma bitta jadvalda; har turda har kim o'ynaydi, bir raqib bilan ikki marta uchrashilmaydi.\n" +
      "G'alaba — 3 ochko, durang — 1, mag'lubiyat — 0. Ochko teng bo'lsa: gollar farqi, so'ng urilgan gollar.\n" +
      "Jadvalning yuqori qismi to'g'ridan pley-off setkasiga, keyingilari pley-off raundiga chiqadi.\n" +
      "Pley-offda bitta o'yin, durang bo'lmaydi — penalti o'yin ichida o'ynaladi, yakuniy hisob kiritiladi.\n" +
      "Natijani o'yinchilardan biri kiritadi, raqib tasdiqlaydi. Kelishmovchilikni tashkilotchi hal qiladi.\n" +
      "Jadval bosqichida tur muddati o'tgach tasdiqlanmagan natijalar tasdiqlanadi, o'ynalmaganlar 0:0.\n" +
      "Xona ID va kelishuvlar — o'yin chatida. Raqibingizga hurmat bilan munosabatda bo'ling.",
  },
  ru: {
    pt_adm_sec_big: "⚠️ КРУПНЫЕ СЧЕТА",
    pt_big_hint: "Если одна сторона забила больше {n}, результат не подтверждается автоматически — вы подтверждаете или отклоняете.",
    pt_big_decide_hint: "Крупный счёт — подтвердить?",
    pt_big_ok: "Подтвердить", pt_big_no: "Отклонить",
    pt_big_wait: "Крупный счёт — ждёт подтверждения организатора/админа",
    pt_big_no_ask: "Отклонить крупный счёт? Результат удалится (если тур закрыт — 0:0).",
    pt_big_ok_toast: "Результат подтверждён", pt_big_no_toast: "Результат отклонён",
    pt_big_submit_ask: "В счёте больше {n} голов — результат уйдёт на подтверждение организатору/админу. Продолжить?",
    pt_big_sent: "Результат отправлен на подтверждение",
    pt_big_next: "Крупные счета ждут подтверждения: {n}",
    pt_big_open: "⚠️ Рассмотреть",
    pt_adm_sec_delete: "🗑 УДАЛИТЬ ТУРНИР",
    pt_del_hint: "Полностью удалить просроченный или ошибочно созданный турнир. Участники, матчи и чат удаляются безвозвратно.",
    pt_del_btn: "Удалить турнир",
    pt_del_ask: "Удалить турнир «{name}» навсегда? Это нельзя отменить.",
    pt_del_ask_paid: "⚠️ Оплаченная сумма не возвращается.",
    pt_del_ask_running: "⚠️ Турнир уже начался — все матчи и результаты будут удалены, участники получат уведомление.",
    pt_deleted: "Турнир удалён",
    pt_sum_leagues: "{k} лиги · {n} клубов · {rounds} туров · в каждой лиге свой чемпион",
    pt_sum_classic2: "в группах дома + в гостях, в плей-офф ответный матч (финал — 1 матч)",
    pt_leagues_hint: "Можно выбрать несколько лиг — у каждой своя таблица и чемпион. Каждая доп. лига: +{price} сум.",
    pt_legs_label_classic: "Матчи: один или с ответным",
    pt_price_extra: "+{n} лиг × {price} сум",
    pt_legs_2_short: "2 круга", pt_n_leagues: "{n} лиги",
    pt_leg_n: "матч {n}", pt_aggregate: "Общий счёт", pt_first_leg: "1-й матч",
    pt_err_first_leg: "Сначала должен быть подтверждён 1-й матч.",
    pt_err_aggregate: "Сумма двух матчей не может быть равной — пенальти внутри 2-го матча, введите итоговый счёт.",
    pt_rules_default_classic2:
      "В группах по 4 человека, каждый играет с каждым 2 раза (дома + в гостях).\n" +
      "Победа — 3 очка, ничья — 1, поражение — 0. При равенстве очков: разница мячей, затем забитые.\n" +
      "В плей-офф выходят победители групп и лучшие вторые места.\n" +
      "В плей-офф два матча (ответный) — победитель по сумме; при равенстве пенальти внутри 2-го матча. Финал — 1 матч без ничьих.\n" +
      "Результат вносит один из игроков, соперник подтверждает. Споры решает организатор.\n" +
      "В группах после срока тура неподтверждённые результаты подтверждаются, несыгранные матчи — 0:0.\n" +
      "ID комнаты и договорённости — в чате матча. Уважайте соперника.",
    pt_fmt_league: "Лига", pt_fmt_cl: "Лига чемпионов", pt_fmt_el: "Лига Европы",
    pt_fmt_wc: "Чемпионат мира", pt_fmt_classic: "Свободный формат",
    pt_fmt_league_sub: "LaLiga, Premier Liga… — каждый выбирает клуб, общая таблица",
    pt_fmt_cl_sub: "8–36 игроков · общая таблица + плей-офф",
    pt_fmt_el_sub: "8–36 игроков · общая таблица + плей-офф",
    pt_fmt_wc_sub: "8–48 игроков · сборные, группы + плей-офф",
    pt_fmt_classic_sub: "8–128 игроков · группы по 4 + плей-офф",
    pt_step_format: "Выберите формат", pt_step_league: "Выберите лигу", pt_step_details: "Данные турнира",
    pt_legs_label: "Сколько раз играет каждая пара", pt_legs_1: "1 круг", pt_legs_2: "2 круга (дома + в гостях)",
    pt_league_clubs: "{n} клубов",
    pt_size_fixed: "{n} участников — по числу клубов выбранных лиг",
    pt_sum_league: "{n} клубов · {rounds} туров · чемпион — первый в таблице",
    pt_sum_cl: "{rounds} туров общей таблицы · топ-{q} сразу в {stage}, места {from}–{to} — раунд плей-офф",
    pt_team_hint_club: "Каждый участник при вступлении выбирает свой клуб (один клуб — один игрок).",
    pt_team_hint_wc: "Каждый участник при вступлении выбирает сборную (одна сборная — один игрок).",
    pt_team_busy: "занят", pt_team_search: "🔍 Поиск…", pt_team_none: "Ничего не найдено",
    pt_team_pick_club: "Выберите свой клуб", pt_team_pick_wc: "Выберите свою сборную",
    pt_team_my_club: "ВАШ КЛУБ", pt_team_my_wc: "ВАША СБОРНАЯ",
    pt_team_change: "Изменить", pt_team_save: "Выбрать", pt_team_saved: "Сохранено",
    pt_err_team_taken: "Эту команду уже выбрал другой участник — выберите другую.",
    pt_join_format: "Формат",
    pt_block_teams: "{n} чел. ещё не выбрали клуб/сборную — старт после выбора всеми.",
    pt_block_league: "Лига должна заполниться: {n}/{max}. Один участник на каждый клуб.",
    pt_block_even: "Сейчас {n} чел. — нужно чётное число (в каждом туре играют все).",
    pt_next_teams: "Все должны выбрать клуб",
    pt_hero_rounds: "ТУРЫ",
    pt_table_done: "Общий этап завершён.",
    pt_seg_table: "Таблица", pt_prof_table: "Таблица · #{pos}",
    pt_prize_hint_league: "После последнего тура чемпионом станет первый в таблице.",
    pt_stage_po: "РАУНД ПЛЕЙ-ОФФ", pt_stage_po_n: "Раунд плей-офф {n}",
    pt_po_hint: "Топ-{q} сразу в сетку ({size} игроков), места {from}–{to} играют раунд плей-офф (1 матч).",
    pt_col_w: "В", pt_col_d: "Н", pt_col_l: "П",
    pt_zone_champ: "Чемпион", pt_zone_direct: "Сразу в сетку (топ-{q})", pt_zone_po: "Раунд плей-офф ({from}–{to})",
    pt_start_hint_league: "Лига должна заполниться ({max} чел.), и все должны выбрать клуб. После старта состав не меняется.",
    pt_start_hint_cl: "Минимум {min} чел., чётное число, и все должны выбрать клуб. После старта состав не меняется.",
    pt_rules_default_league:
      "Каждый играет одним клубом выбранной лиги; все в одной таблице.\n" +
      "Каждый с каждым 1 или 2 раза (дома + в гостях) — как выбрал организатор.\n" +
      "Победа — 3 очка, ничья — 1, поражение — 0. При равенстве очков: разница мячей, затем забитые.\n" +
      "После последнего тура чемпионом становится первый в таблице.\n" +
      "Результат вносит один из игроков, соперник подтверждает. Споры решает организатор.\n" +
      "После срока тура неподтверждённые результаты подтверждаются, несыгранные матчи — 0:0.\n" +
      "ID комнаты и договорённости — в чате матча. Уважайте соперника.",
    pt_rules_default_cl:
      "Все в одной таблице; в каждом туре играют все, с одним соперником дважды не встречаются.\n" +
      "Победа — 3 очка, ничья — 1, поражение — 0. При равенстве очков: разница мячей, затем забитые.\n" +
      "Верх таблицы выходит сразу в сетку плей-офф, следующие места — в раунд плей-офф.\n" +
      "В плей-офф один матч без ничьих — пенальти играются внутри матча, вносится итоговый счёт.\n" +
      "Результат вносит один из игроков, соперник подтверждает. Споры решает организатор.\n" +
      "На общем этапе после срока тура неподтверждённые результаты подтверждаются, несыгранные — 0:0.\n" +
      "ID комнаты и договорённости — в чате матча. Уважайте соперника.",
  },
  en: {
    pt_adm_sec_big: "⚠️ BIG SCORES",
    pt_big_hint: "If one side scores more than {n}, the result isn't confirmed automatically — you approve or reject it.",
    pt_big_decide_hint: "Big score — approve it?",
    pt_big_ok: "Approve", pt_big_no: "Reject",
    pt_big_wait: "Big score — waiting for the organizer/admin",
    pt_big_no_ask: "Reject the big score? The result is cleared (0:0 if the round is closed).",
    pt_big_ok_toast: "Result approved", pt_big_no_toast: "Result rejected",
    pt_big_submit_ask: "More than {n} goals — the result goes to the organizer/admin for approval. Continue?",
    pt_big_sent: "Result sent for approval",
    pt_big_next: "Big scores awaiting approval: {n}",
    pt_big_open: "⚠️ Review",
    pt_adm_sec_delete: "🗑 DELETE TOURNAMENT",
    pt_del_hint: "Permanently delete an expired or mistakenly created tournament. Members, matches and chat are removed for good.",
    pt_del_btn: "Delete tournament",
    pt_del_ask: "Delete «{name}» permanently? This can't be undone.",
    pt_del_ask_paid: "⚠️ The amount paid for the tournament is not refunded.",
    pt_del_ask_running: "⚠️ The tournament has started — all matches and results will be deleted and players notified.",
    pt_deleted: "Tournament deleted",
    pt_sum_leagues: "{k} leagues · {n} clubs · {rounds} rounds · each league has its own champion",
    pt_sum_classic2: "home + away in groups, two-legged play-off ties (final — 1 match)",
    pt_leagues_hint: "You can pick several leagues — each has its own table and champion. Each extra league: +{price} UZS.",
    pt_legs_label_classic: "Matches: single or with a return leg",
    pt_price_extra: "+{n} league(s) × {price} UZS",
    pt_legs_2_short: "2 legs", pt_n_leagues: "{n} leagues",
    pt_leg_n: "leg {n}", pt_aggregate: "Aggregate", pt_first_leg: "1st leg",
    pt_err_first_leg: "The 1st leg must be confirmed first.",
    pt_err_aggregate: "The aggregate can't be level — penalties are in the 2nd leg, enter the final score.",
    pt_rules_default_classic2:
      "Groups of 4, everyone plays everyone twice (home + away).\n" +
      "Win — 3 points, draw — 1, loss — 0. Tied on points: goal difference, then goals scored.\n" +
      "Group winners and the best runners-up reach the play-off.\n" +
      "Play-off ties are two-legged — the winner is decided on aggregate; if level, penalties in the 2nd leg. The final is 1 match, no draws.\n" +
      "One player enters the result, the opponent confirms it. The organizer settles disputes.\n" +
      "In the group stage, after the round deadline unconfirmed results are confirmed, unplayed matches end 0:0.\n" +
      "Room ID and arrangements go in the match chat. Respect your opponent.",
    pt_fmt_league: "League", pt_fmt_cl: "Champions League", pt_fmt_el: "Europa League",
    pt_fmt_wc: "World Cup", pt_fmt_classic: "Free format",
    pt_fmt_league_sub: "LaLiga, Premier Liga… — everyone picks a club, one table",
    pt_fmt_cl_sub: "8–36 players · one table + play-off",
    pt_fmt_el_sub: "8–36 players · one table + play-off",
    pt_fmt_wc_sub: "8–48 players · national teams, groups + play-off",
    pt_fmt_classic_sub: "8–128 players · groups of 4 + play-off",
    pt_step_format: "Choose a format", pt_step_league: "Choose a league", pt_step_details: "Tournament details",
    pt_legs_label: "How many times each pair plays", pt_legs_1: "Single round", pt_legs_2: "Double round (home + away)",
    pt_league_clubs: "{n} clubs",
    pt_size_fixed: "{n} players — one per club in the chosen league(s)",
    pt_sum_league: "{n} clubs · {rounds} rounds · top of the table is champion",
    pt_sum_cl: "{rounds}-round league table · top {q} go straight to the {stage}, places {from}–{to} play a play-off round",
    pt_team_hint_club: "Each player picks their own club when joining (one club per player).",
    pt_team_hint_wc: "Each player picks a national team when joining (one team per player).",
    pt_team_busy: "taken", pt_team_search: "🔍 Search…", pt_team_none: "Nothing found",
    pt_team_pick_club: "Pick your club", pt_team_pick_wc: "Pick your national team",
    pt_team_my_club: "YOUR CLUB", pt_team_my_wc: "YOUR NATIONAL TEAM",
    pt_team_change: "Change", pt_team_save: "Select", pt_team_saved: "Saved",
    pt_err_team_taken: "Another player already took this team — pick another one.",
    pt_join_format: "Format",
    pt_block_teams: "{n} player(s) haven't picked a club/team yet — start once everyone has.",
    pt_block_league: "The league must be full: {n}/{max}. One player per club.",
    pt_block_even: "{n} players now — the count must be even (everyone plays each round).",
    pt_next_teams: "Everyone must pick a club",
    pt_hero_rounds: "ROUNDS",
    pt_table_done: "The league phase is over.",
    pt_seg_table: "Table", pt_prof_table: "Table · #{pos}",
    pt_prize_hint_league: "After the last round the top of the table becomes champion.",
    pt_stage_po: "PLAY-OFF ROUND", pt_stage_po_n: "Play-off round {n}",
    pt_po_hint: "Top {q} go straight to the bracket ({size} players), places {from}–{to} play a play-off round (1 match).",
    pt_col_w: "W", pt_col_d: "D", pt_col_l: "L",
    pt_zone_champ: "Champion", pt_zone_direct: "Straight to bracket (top {q})", pt_zone_po: "Play-off round ({from}–{to})",
    pt_start_hint_league: "The league must be full ({max} players) and everyone must pick a club. The line-up is locked after the start.",
    pt_start_hint_cl: "At least {min} players, an even number, and everyone must pick a club. The line-up is locked after the start.",
    pt_rules_default_league:
      "Everyone plays as one club from the chosen league; all in one table.\n" +
      "Everyone plays everyone once or twice (home + away) — as the organizer chose.\n" +
      "Win — 3 points, draw — 1, loss — 0. Tied on points: goal difference, then goals scored.\n" +
      "After the last round the top of the table is champion.\n" +
      "One player enters the result, the opponent confirms it. The organizer settles disputes.\n" +
      "After the round deadline unconfirmed results are confirmed and unplayed matches end 0:0.\n" +
      "Room ID and arrangements go in the match chat. Respect your opponent.",
    pt_rules_default_cl:
      "Everyone is in one table; everyone plays every round and never meets the same opponent twice.\n" +
      "Win — 3 points, draw — 1, loss — 0. Tied on points: goal difference, then goals scored.\n" +
      "The top of the table goes straight to the play-off bracket, the next places play a play-off round.\n" +
      "Play-off games are single matches with no draws — penalties are played in-game, enter the final score.\n" +
      "One player enters the result, the opponent confirms it. The organizer settles disputes.\n" +
      "In the league phase, after the round deadline unconfirmed results are confirmed, unplayed ones end 0:0.\n" +
      "Room ID and arrangements go in the match chat. Respect your opponent.",
  },
};

for (const lang of ["uz", "ru", "en"]) {
  if (typeof PT_TEXTS !== "undefined" && PT_TEXTS[lang]) Object.assign(PT_TEXTS[lang], PT_FMT_TEXTS[lang]);
  if (typeof TEXTS !== "undefined" && TEXTS[lang]) Object.assign(TEXTS[lang], PT_FMT_TEXTS[lang]);
}
