// =============================================================
//  guide_bot_uz.js — yo'l ko'rsatuvchi robot «Robi» matnlari: O'ZBEKCHA (asl manba, 2026-11-03).
//  Ko'rsatuvchi — guide_bot.js. Har sahifa (kontekst): hint — birinchi kirishda chiqadigan qisqa
//  so'z, say — Robi navbat bilan aytadigan gaplar. **qalin** qo'llab-quvvatlanadi.
//  ⚠️ Raqamlar koddagi sozlamalar bilan mos (guide_uz.js, config.py, season_rewards.py, *_core.py).
//  Sozlama o'zgarsa — shu yerda va guide_bot_ru.js / guide_bot_en.js da ham yangilang.
// =============================================================

var GBOT_I18N = window.GBOT_I18N || {};
window.GBOT_I18N = GBOT_I18N;

GBOT_I18N.uz = {
  ui: {
    name: "Robi", role: "yo'l ko'rsatuvchingiz", next: "Keyingisi ›", prev: "‹ Ortga", again: "🔁 Boshidan",
    more: "📖 Batafsil", bye: "👋 Rahmat, Robi!", bye_reply: "Arzimaydi! Kerak bo'lsam — shu yerdaman 😊",
    hide: "Yashirish", close: "Yopish", sound_on: "🔊", sound_off: "🔇", speak: "🗣",
  },
  hub: {
    hint: "Salom! Men Robi 🤖 Bo'limlar haqida aytib beraymi? Meni bosing!",
    say: [
      "Salom! 👋 Men **Robi** — shu botdagi yo'l ko'rsatuvchingizman. Bu yerda 3 ta katta bo'lim bor. Keling, birma-bir tanishtiraman!",
      "🏆 **Rasmiy turnirlar** — botning asosiy musobaqalari: Ligalar, Chempionlar ligasi, Yevropa ligasi, Konferensiya ligasi, Osiyo ChL, Divizion va Jahon chempionati. Ularni bot o'zi o'tkazadi.",
      "Rasmiy turnirlarda qoidalar hamma uchun bir xil, umumiy reyting bor, g'oliblarga kubok, sovrin va 🪙 **eF Token** beriladi. Eng jiddiy bellashuvlar shu yerda! 💪",
      "🎟 **Shaxsiy turnirlar** — bu yerda tashkilotchi **sizsiz**! Do'stlaringiz yoki guruhingiz uchun yopiq turnir tuzasiz: formatni, kishi sonini va muddatni o'zingiz tanlaysiz.",
      "Do'stlaringizni **taklif havolasi** orqali chaqirasiz — faqat havolani olganlar qo'shiladi. Jadval, pley-off va chempionni bot o'zi hisoblaydi, siz faqat o'ynaysiz 😉",
      "🛡 **Teamlar jangi** — yakka emas, **jamoa bo'lib** o'ynaysiz. Team tuzasiz yoki do'stingiz teamiga qo'shilasiz. Ikki team bahsida o'yinchilar 1v1 o'ynaydi, ko'p g'alaba olgan team yutadi.",
      "Qisqasi, farqi bunday: 🏆 **Rasmiy** — bot tashkil qiladi, hamma uchun ochiq. 🎟 **Shaxsiy** — siz tashkil qilasiz, faqat taklif qilinganlar uchun. 🛡 **Teamlar** — jamoaviy bellashuv.",
      "Yana ikki sir 🤫 ⚡ tugmasi — **Tezkor o'yin**: kutmasdan hoziroq raqib topib o'ynaysiz. 📖 **Qo'llanma** esa barcha qoidalarni batafsil aytadi. Savol tug'ilsa — meni bosing!",
    ],
  },
  modes: {
    hint: "Rejimlar bir-biriga qanday bog'langanini ko'rsataymi? 🔗",
    say: [
      "Bu — **Rasmiy turnirlar** 🏆 Bu yerdagi rejimlar bir-biriga zanjirdek bog'langan. Qani, qanday bog'langanini ko'rsataman! 🔗",
      "⚽ **Ligalar** — hammasi shu yerdan boshlanadi. Bitta klub tanlaysiz va mavsum davomida ligadagi har bir raqib bilan uy va mehmonda o'ynaysiz. Ligalar 4 mintaqada: Yevropa, Osiyo, Janubiy va Shimoliy Amerika.",
      "Ligadagi o'rningiz — kuboklarga chipta 🎫 Yevropa ligalarining eng yaxshilari **Chempionlar ligasi**ga, keyingilari **Yevropa ligasi**ga, ulardan keyingilari **Konferensiya ligasi**ga yo'llanma oladi.",
      "Osiyo ligalarida (O'zbekiston, Saudiya, BAA, Yaponiya) 1–8-o'rinlar **Osiyo Chempionlar ligasi**ga chiqadi. Amerika ligalari hozircha kuboklarga yo'llanma bermaydi.",
      "Yo'llanmalar **liga mavsumi yakunlangach** beriladi. Ya'ni ligada qanchalik yuqori o'rin olsangiz — shunchalik kuchli kubokda o'ynaysiz! 🌟",
      "📅 **Divizion** — kundalik rejim: har kuni ro'yxatdan o'tasiz, bot tasodifiy raqib beradi, ballar reytingda yig'iladi. Mavsum oxirida reytingdagi **TOP-48** — **Jahon chempionati**ga yo'llanma oladi! 🌍",
      "🌍 **Jahon chempionati** — 48 ta terma jamoa: guruhlar, so'ng pley-off. Unga faqat Divizion orqali kiriladi — shuning uchun Divizionni tashlab qo'ymang 😉",
      "Har bir rejimda yaxshi o'ynasangiz — kubok, sovrin va 🪙 **eF Token** olasiz. Tokenlar do'kon va auksionda ishlatiladi. Rejimni tanlang — ichida ham men bor, o'sha rejim haqida aytib beraman! 🤖",
    ],
  },
  league: {
    hint: "Ligalar haqida aytib beraymi? Bosing! ⚽",
    say: [
      "Ligalarga xush kelibsiz! ⚽ Bu — botning asosiy rejimi: bir mavsum davomida bitta klub bilan o'ynaysiz.",
      "Yuqoridagi tablardan mintaqani tanlang: Yevropa, Osiyo, J. va Sh. Amerika. Ligalar **navbat bilan** ochiladi — oldingisi to'lmaguncha keyingisi yopiq turadi 🔒",
      "Ochiq ligada bo'sh klubni tanlang. Liga to'lgach qur'a tashlanadi va turlar boshlanadi: har kuni **23:30** da **2 ta** yangi tur ochiladi ⏰",
      "G'alaba — **3** ochko, durang — **1**. Natijani raqibingiz tasdiqlaydi. Natija tur ochilgandan **1 soat 45 daqiqa** o'tgach kiritiladi.",
      "Mavsum oxiridagi o'rningiz kuboklarga yo'llanma beradi: Yevropa ligalaridan — ChL, YeL va Konferensiya ligasi, Osiyo ligalaridan — Osiyo ChL. Yuqori o'rin — kattaroq kubok! 🏆",
      "Sovrinlar ham bor: g'olibga **Oltin to'p**, eng ko'p gol urganga **Oltin butsa**, o'rningizga qarab 🪙 **eF Token** (1-o'ringa — 300).",
      "Bitta iltimos 🙏 mavsumni **oxirigacha o'ynang**. Tashlab ketsangiz, mukofot olmaysiz va keyingi mavsumda klubni boshqalardan 24 soat keyin tanlaysiz.",
    ],
  },
  cl: {
    hint: "Chempionlar ligasi haqida aytib beraymi? ⭐",
    say: [
      "⭐ **Chempionlar ligasi** — Yevropaning eng kuchli kubogi! Bu yerga Yevropa ligalarining eng yaxshi o'yinchilari keladi: jami **36** kishi.",
      "Qanday kiriladi? Liga mavsumi yakunidagi o'rningizga qarab: katta 5 ligada 1–4-o'rin, kichikroq ligalarda 1–3, 1–2 yoki faqat 1-o'rin. Yo'llanma **sizga** beriladi — klub almashsangiz ham qolasiz.",
      "Avval **liga bosqichi**: hamma bitta jadvalda, har kim **8** ta turli raqib bilan o'ynaydi. Kuniga **1** tur, deadline **23:30**.",
      "**1–8**-o'rinlar to'g'ridan 1/8 finalga chiqadi, **9–24**-o'rinlar pley-off raundida o'ynaydi. So'ng 1/8, chorak, yarim final va final! 🔥",
      "Qanchalik uzoqqa borsangiz, shuncha ko'p 🪙 eF Token. Chempionga — **500**! Omad! 🍀",
    ],
  },
  el: {
    hint: "Yevropa ligasi haqida aytib beraymi? 🟠",
    say: [
      "🟠 **Yevropa ligasi** — Yevropaning ikkinchi kubogi. Bu yerga Chempionlar ligasiga sal yetmay qolganlar keladi: jami **36** kishi.",
      "Qanday kiriladi? Yevropa ligalarida ChL o'rinlaridan keyingi o'rinlar: katta 5 ligada 5–8-o'rin, boshqalarida 4–6, 3–4 yoki 2-o'rin.",
      "Format ChL kabi: **liga bosqichi** — har kim **8** ta turli raqib bilan, kuniga **1** tur, deadline **23:30**.",
      "**1–8**-o'rinlar to'g'ridan 1/8 finalga, **9–24**-o'rinlar pley-off raundiga. So'ng chorak, yarim final va final! 🔥",
      "Chempionga — **350** 🪙 eF Token. Ligada yanada yuqori o'rin olsangiz — keyingi mavsumda ChL'da ko'rishamiz! 😉",
    ],
  },
  co: {
    hint: "Konferensiya ligasi haqida aytib beraymi? 🟢",
    say: [
      "🟢 **Konferensiya ligasi** — Yevropaning uchinchi kubogi. Yevropa ligasidan keyingi o'rinlar shu yerda bellashadi: jami **36** kishi.",
      "Qanday kiriladi? Katta 5 ligada 9–12-o'rin, boshqalarida 7–9, 5–6 yoki 3-o'rin — liga mavsumi yakunida.",
      "Liga bosqichi bu yerda qisqaroq: har kim **6** ta turli raqib bilan o'ynaydi. Kuniga **1** tur, deadline **23:30**.",
      "So'ng pley-off: 1/8, chorak, yarim final va final. Har bir g'alaba — kubokka bir qadam! 🏆",
      "Chempionga — **250** 🪙 eF Token. Bu kubok — katta kuboklarga zinapoya! 🪜",
    ],
  },
  ac: {
    hint: "Osiyo Chempionlar ligasi haqida aytib beraymi? 🌏",
    say: [
      "🌏 **Osiyo Chempionlar ligasi** — Osiyoning eng kuchli kubogi! Jami **32** kishi.",
      "Qanday kiriladi? O'zbekiston Superligasi, Saudi Pro Liga, UAE Pro Liga va J1 Liga'ning **1–8**-o'rinlari — liga mavsumi yakunida.",
      "Avval **liga bosqichi**: hamma bitta jadvalda, har kim **8** ta turli raqib bilan. Kuniga **1** tur, deadline **23:30**.",
      "**1–8**-o'rinlar to'g'ridan 1/8 finalga, **9–24**-o'rinlar pley-off raundiga. So'ng chorak, yarim final va final! 🔥",
      "Chempionga — **350** 🪙 eF Token. Osiyo chempioni bo'lish — katta sharaf! 🏅",
    ],
  },
  division: {
    hint: "Divizion qanday ishlashini aytib beraymi? 📅",
    say: [
      "📅 **Divizion** — har kungi jang! Bu yerda klub tanlash yo'q: har kuni ro'yxatdan o'tasiz va bot sizga **tasodifiy raqib** beradi.",
      "Kun tartibi: **17:00–20:00** — ro'yxatdan o'tish, **20:00** — qur'a, ertasi kuni **16:00** gacha — o'yin va natija ⏰",
      "Ball: g'alaba **+15**, durang **+10**, mag'lubiyat **−10**. Hamma **1500** balldan boshlaydi. Vaqtida o'ynalmagan o'yin — 0:0 durang.",
      "Kishilar toq bo'lsa, bittangiz raqibsiz qolasiz — xafa bo'lmang, **baraban** aylantirib 5, 10 yoki 15 ball olasiz 🎡",
      "Eng muhimi: mavsum yakunida reytingdagi **TOP-48** — **Jahon chempionati**ga yo'llanma oladi! 🌍 Har kuni qatnashing — ballar yig'ilaveradi.",
    ],
  },
  wc: {
    hint: "Jahon chempionati haqida aytib beraymi? 🌍",
    say: [
      "🌍 **Jahon chempionati**ga xush kelibsiz! Bu yerda klub emas, **terma jamoa** bilan o'ynaysiz. Jami **48** kishi: **12** guruh, har guruhda 4 kishi.",
      "Kim qatnashadi? Faqat **Divizion** mavsumi reytingining **TOP-48**'i. Ro'yxat har mavsum yangilanadi — Divizionda yaxshi o'ynang! 💪",
      "Terma jamoangizni tanlang — u guruhingizni belgilaydi. Guruhda **3** tur: kuniga **1** tur, deadline **23:30**.",
      "Pley-offga **32** kishi chiqadi: guruh g'oliblari, ikkinchilar va **8** ta eng yaxshi uchinchi o'rin. So'ng 1/16 finaldan finalgacha! 🏆",
      "Bosqichga qarab 🪙 eF Token (chempionga — **500**) va JCh **Oltin butsasi**. Vatan sharafi uchun! 🇺🇿",
    ],
  },
  pt: {
    hint: "O'z turniringizni qanday tuzishni ko'rsataymi? 🎟",
    say: [
      "🎟 **Shaxsiy turnirlar**! Bu yerda siz — tashkilotchisiz. Do'stlar, guruh yoki jamoangiz uchun o'z turniringizni tuzasiz.",
      "**«+ Yangi turnir yaratish»**ni bosing va formatni tanlang: Liga, Chempionlar ligasi, Yevropa ligasi, Jahon chempionati yoki Erkin format (guruhlar + pley-off).",
      "Necha kishilik bo'lishini tanlang, so'ng **taklif havolasini** do'stlaringizga yuboring — bosgan kishi turnirga qo'shiladi 🔗",
      "Joylar to'lgach **«Turnirni boshlash»**. Jadval, pley-off va chempionni bot o'zi hisoblaydi. Siz tur muddatini belgilaysiz, nizolarni hal qilasiz va yordamchi admin tayinlay olasiz 👑",
      "Rasmiy turnirlardan farqi: qoidalarni **tashkilotchi** belgilaydi va turnir faqat taklif qilinganlar uchun. Do'stlaringiz bilan maroqli bellashing! 😄",
    ],
  },
  tb: {
    hint: "Teamlar jangi haqida aytib beraymi? 🛡",
    say: [
      "🛡 **Teamlar jangi** — bu yerda yakka emas, **jamoa bo'lib** kurashamiz! Ikki team bahsida o'yinchilar 1v1 o'ynaydi, ko'p g'alaba olgan team yutadi.",
      "Team ochish uchun liga adminidan **liga havolasini** oling. Do'stingiz teamiga qo'shilmoqchimisiz? Sardordan **taklif havolasini** so'rang 🔗",
      "Sardor **asosiy tarkibni** tuzadi. Tur ochilganda (kuniga **1** tur, deadline **23:30**) tarkibdagilar raqib teamdan 1v1 juftlanadi — raqibingiz **«Jang»** tabida.",
      "Natijani **yakun ekrani skrinshoti** bilan kiriting — skrinshotsiz qabul qilinmaydi 📸 Tarkibi yetmagan team texnik mag'lubiyat oladi.",
      "Bahs uchun: g'alaba — **3** ochko, durang — **1**. Teamdoshlaringizni qo'llab-quvvatlang — birga kuchlimiz! 🤝",
    ],
  },
};
