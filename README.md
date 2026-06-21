# 🎮 eFootball Turnir Bot — Loyiha Xaritasi

> Bu fayl loyihaning "xaritasi". Har bir o'zgarishdan keyin shu fayl ham yangilanadi.
> Versiya: v0.1 (loyiha boshlanish bosqichi)

---

## 📌 Texnologiyalar

| Qism | Texnologiya |
|---|---|
| Bot | Python + python-telegram-bot |
| Web App | HTML/CSS/JS (bitta index.html, vanilla JS) |
| Baza | SQLite |

---

## 📂 Fayl tuzilmasi (rejalashtirilgan)

```
efootball-bot/
├── README.md                 ← shu fayl (xarita)
├── bot/
│   ├── __init__.py             ✅ yaratilgan
│   ├── main.py                ← bot ishga tushish nuqtasi (hali yo'q)
│   ├── handlers/
│   │   ├── main_menu.py        ← 🏠 Asosiy tugma handlerlari (hali yo'q)
│   │   ├── rating.py            ← 🏆 Reyting tugma handlerlari (hali yo'q)
│   │   ├── profile.py           ← 👤 Profil tugma handlerlari (hali yo'q)
│   │   └── prizes.py            ← 🎁 Sovrinlar tugma handlerlari (hali yo'q)
│   ├── db/
│   │   ├── __init__.py          ✅ yaratilgan
│   │   ├── models.py            ✅ yaratilgan — jadval sxemalari
│   │   ├── queries.py           ✅ yaratilgan — users/leagues/registrations CRUD
│   │   └── schedule.py          ✅ yaratilgan — round-robin generatsiya
│   ├── keyboards.py           ✅ yaratilgan — 4 ta pastki tugma
│   ├── texts.py                ✅ yaratilgan — 3 tilli matnlar (23 ta)
│   └── config.py               ✅ yaratilgan — constant qiymatlar
└── webapp/
    └── index.html              ← Web App (hali yo'q)
```

---

## 🧩 Funksional xarita (4 ta asosiy tugma)

### 🏠 Asosiy
- Joriy/kelayotgan turnir ma'lumoti
- Turnirga ro'yxatdan o'tish
- Qoidalar/yo'riqnoma
- E'lonlar/yangiliklar

**Bog'liq fayllar:** `handlers/main_menu.py`, `db/queries.py` (turnir va e'lon jadvallari), `webapp/index.html` (Asosiy bo'lim)

### 🏆 Reyting
- Umumiy reyting jadvali (barcha o'yinchilar)
- Faqat joriy turnir reytingi
- G'oliblar tarixi (oldingi turnirlar)

**Bog'liq fayllar:** `handlers/rating.py`, `db/queries.py` (reyting hisoblash), `webapp/index.html` (Reyting bo'lim)

### 👤 Profil
- Mening joriy reyting o'rnim
- Mening o'tgan o'yinlarim tarixi
- Ism/nickname tahrirlash
- Shaxsiy statistika (g'alaba/mag'lubiyat)

**Bog'liq fayllar:** `handlers/profile.py`, `db/queries.py` (user jadvali), `webapp/index.html` (Profil bo'lim)

### 🎁 Sovrinlar
- Eng ko'p gol urgan ishtirokchiga — 🥇 Oltin Butsa
- Turnir g'olibiga — 🏆 Oltin To'p znachogi
- Pul emas, ramziy/jismoniy sovrinlar

**Bog'liq fayllar:** `handlers/prizes.py`, `db/queries.py` (statistika so'rovlari), `webapp/index.html` (Sovrinlar bo'lim)

---

## 🌍 Til tizimi

Barcha matnlar `bot/texts.py` da markazlashtirilgan, 3 tilda: **UZ / RU / EN**.
Foydalanuvchi tanlagan til DB'da saqlanadi (`users.language` maydoni) va WebApp ham shu tilga moslashadi.

> Qoida #22 ga ko'ra: yangi har qanday matn qo'shilganda — albatta 3 tilga tarjima qilinadi.

---

## 🗄️ Ma'lumotlar bazasi (✅ tasdiqlangan, yaratilgan)

**Format:** 2 ta liga (LaLiga, Premier Liga), har birida 20 ta o'yinchi, round-robin (har kim har kim bilan 2 marta), 38 kunlik (matchday) turnir. Natijalarni o'yinchining o'zi kiritadi, raqibi tasdiqlaydi/rad etadi.

| Jadval | Maydonlar | Izoh |
|---|---|---|
| `users` | id, telegram_id, nickname, language, registered_at | |
| `leagues` | id, name, max_players, status | name: "LaLiga"/"Premier Liga" |
| `registrations` | id, user_id, league_id, registered_at | UNIQUE(user_id) — bitta user faqat bitta ligaga |
| `matches` | id, league_id, matchday, player1_id, player2_id, score1, score2, submitted_by, status | matchday: 1-38, status: pending/awaiting_confirmation/confirmed/rejected |
| `prizes` | league_id, top_scorer_user_id, winner_user_id | Oltin Butsa (eng ko'p gol), Oltin To'p (g'olib) |

**Jadval generatsiyasi:** Liga 20 kishiga to'lganda, `bot/db/schedule.py` dagi circle method algoritmi avtomatik 380 ta match yaratadi (2 × 19 tur = 38 matchday).

---

## ✅ Status

- [x] Talablar aniqlandi (4 tugma va ichidagi funksiyalar)
- [x] Texnologiya tanlandi
- [x] DB sxema tasdiqlandi
- [x] `config.py` yaratildi
- [x] `db/models.py` yaratildi
- [x] `db/queries.py` yaratildi (users, leagues, registrations CRUD)
- [x] `db/schedule.py` yaratildi (round-robin circle method, 380 match generatsiyasi)
- [x] `texts.py` yaratildi (3 til — 23 ta matn, UZ/RU/EN)
- [x] `keyboards.py` yaratildi (4 ta pastki tugma)
- [ ] Handlerlar yaratildi
- [ ] `index.html` yaratildi

---

## 📦 Dependencies (kerakli kutubxonalar)

| Kutubxona | Qayerda ishlatiladi | Status |
|---|---|---|
| `python-telegram-bot` | `keyboards.py`, kelajakdagi handlerlar | ⚠️ `requirements.txt`ga qo'shilishi kerak (hali yaratilmagan) |

---

## 📝 O'zgarishlar tarixi

| Sana | O'zgarish |
|---|---|
| 2026-06-21 | Loyiha boshlandi, README xarita yaratildi |
| 2026-06-21 | DB format tasdiqlandi: 2 liga (LaLiga/Premier), 20 o'yinchi, round-robin 2 marta, 38 kun |
| 2026-06-21 | `config.py`, `db/models.py`, `db/queries.py`, `db/schedule.py` yaratildi va test qilindi |
| 2026-06-21 | `texts.py` (23 ta matn, 3 til) va `keyboards.py` (4 tugma) yaratildi va test qilindi |
