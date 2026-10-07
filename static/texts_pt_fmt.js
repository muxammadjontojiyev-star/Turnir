// texts_pt_fmt.js — SHAXSIY turnir formatlari va klub tanlash tarjimalari (2026-10-07).
// texts_pt.js dan KEYIN ulanadi: PT_TEXTS (zaxira) va TEXTS (joriy til) ga qo'shiladi.

const PT_FMT_TEXTS = {
  uz: {
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
    pt_size_fixed: "{n} ishtirokchi — ligadagi klublar soni",
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
    pt_size_fixed: "{n} участников — по числу клубов лиги",
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
    pt_size_fixed: "{n} players — one per club in the league",
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
