// texts_pt_wc.js — SHAXSIY "Jahon chempionati" pley-offi: rasmiy JCh qoidasi va setkani qayta tuzish (2026-10-30).
// texts_pt.js / texts_pt_ui.js 200–300 qatorga yetgani uchun alohida fayl (qoida #21). Ulardan KEYIN ulanadi.

const PT_WC_TEXTS = {
  uz: {
    pt_wc_hint:          "Pley-offga {size} kishi chiqadi: barcha guruh g'oliblari, barcha 2-o'rinlar va eng yaxshi {thirds} ta 3-o'rin (o'yin boshiga ochko, so'ng gol farqi bo'yicha).",
    pt_wc_hint2:         "Pley-offga {size} kishi chiqadi: barcha guruh g'oliblari va barcha 2-o'rinlar.",
    pt_sum_wc:           "{g} ta guruh · pley-off {stage}dan: g'oliblar, 2-o'rinlar + eng yaxshi {thirds} ta 3-o'rin",
    pt_ko_rebuild_note:  "Bu setka eski qoida bilan tuzilgan — 2-o'rinlar va eng yaxshi 3-o'rinlar chiqmay qolgan. Pley-offda hali natija yo'q, shuning uchun setkani rasmiy JCh qoidasi bilan qayta tuzish mumkin ({size} kishi).",
    pt_ko_rebuild_btn:   "🔄 Setkani qayta tuzish",
    pt_ko_rebuild_ask:   "Joriy pley-off o'yinlari va ularning chati o'chiriladi, setka yangi qoida bilan qayta tuziladi. Ishtirokchilarga xabar boradi. Pley-off muddatini keyin qayta belgilaysiz. Davom etilsinmi?",
    pt_ko_rebuilt:       "Setka qayta tuzildi. Endi pley-off muddatini belgilang.",
    pt_err_ko_results:   "Pley-offda natija kiritilgan — setkani qayta tuzib bo'lmaydi.",
    pt_err_ko_same:      "Setka allaqachon yangi qoida bo'yicha tuzilgan.",
    pt_err_ko_rebuild:   "Hozir setkani qayta tuzib bo'lmaydi.",
    pt_rules_wc_line:    "Pley-offga guruh g'oliblari, 2-o'rinlar va (setkani to'ldirish uchun) eng yaxshi 3-o'rinlar chiqadi — rasmiy JCh kabi.",
  },
  ru: {
    pt_wc_hint:          "В плей-офф выходят {size} игроков: все победители групп, все вторые места и {thirds} лучших третьих мест (по очкам за матч, затем по разнице мячей).",
    pt_wc_hint2:         "В плей-офф выходят {size} игроков: все победители групп и все вторые места.",
    pt_sum_wc:           "Групп: {g} · плей-офф с этапа {stage}: победители, вторые места + {thirds} лучших третьих",
    pt_ko_rebuild_note:  "Эта сетка составлена по старому правилу — вторые места и лучшие третьи места не попали в неё. В плей-офф ещё нет результатов, поэтому сетку можно пересобрать по правилу официального ЧМ ({size} игроков).",
    pt_ko_rebuild_btn:   "🔄 Пересобрать сетку",
    pt_ko_rebuild_ask:   "Текущие матчи плей-офф и их чат будут удалены, сетка будет составлена заново по новому правилу. Участники получат уведомление. Срок плей-офф нужно будет задать заново. Продолжить?",
    pt_ko_rebuilt:       "Сетка пересобрана. Теперь задайте срок плей-офф.",
    pt_err_ko_results:   "В плей-офф уже есть результаты — пересобрать сетку нельзя.",
    pt_err_ko_same:      "Сетка уже составлена по новому правилу.",
    pt_err_ko_rebuild:   "Сейчас пересобрать сетку нельзя.",
    pt_rules_wc_line:    "В плей-офф выходят победители групп, вторые места и (чтобы заполнить сетку) лучшие третьи места — как на официальном ЧМ.",
  },
  en: {
    pt_wc_hint:          "{size} players reach the play-off: all group winners, all runners-up and the {thirds} best third places (by points per match, then goal difference).",
    pt_wc_hint2:         "{size} players reach the play-off: all group winners and all runners-up.",
    pt_sum_wc:           "{g} groups · play-off from the {stage}: winners, runners-up + {thirds} best third places",
    pt_ko_rebuild_note:  "This bracket was built with the old rule — runners-up and the best third places were left out. There are no play-off results yet, so the bracket can be rebuilt with the official World Cup rule ({size} players).",
    pt_ko_rebuild_btn:   "🔄 Rebuild the bracket",
    pt_ko_rebuild_ask:   "Current play-off matches and their chat will be deleted and the bracket rebuilt with the new rule. Players will be notified. You'll need to set the play-off deadline again. Continue?",
    pt_ko_rebuilt:       "Bracket rebuilt. Now set the play-off deadline.",
    pt_err_ko_results:   "Play-off results have been entered — the bracket can't be rebuilt.",
    pt_err_ko_same:      "The bracket already follows the new rule.",
    pt_err_ko_rebuild:   "The bracket can't be rebuilt right now.",
    pt_rules_wc_line:    "Group winners, runners-up and (to fill the bracket) the best third places reach the play-off — like the official World Cup.",
  },
};

// JCh standart qoidalari: pt_rules_default (texts_pt_ui.js), 3-qatori (pley-off) — pt_rules_wc_line
const PT_RULES_PLAYOFF_LINE = 2;
for (const lang of ["uz", "ru", "en"]) {
  const base = typeof PT_UI_TEXTS !== "undefined" && PT_UI_TEXTS[lang] && PT_UI_TEXTS[lang].pt_rules_default;
  if (base) {
    const lines = base.split("\n");
    lines[PT_RULES_PLAYOFF_LINE] = PT_WC_TEXTS[lang].pt_rules_wc_line;
    PT_WC_TEXTS[lang].pt_rules_default_wc = lines.join("\n");
  }
  if (typeof PT_TEXTS !== "undefined" && PT_TEXTS[lang]) Object.assign(PT_TEXTS[lang], PT_WC_TEXTS[lang]);
  if (typeof TEXTS !== "undefined" && TEXTS[lang]) Object.assign(TEXTS[lang], PT_WC_TEXTS[lang]);
}
