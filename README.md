# 🎮 eFootball Turnir Bot — Loyiha Xaritasi

> Bu fayl loyihaning "xaritasi". Har bir o'zgarishdan keyin shu fayl ham yangilanadi.
> Versiya: v0.2 (struktura: flat — static/ papkadan tashqari hammasi ildizda)

---

## 📌 Texnologiyalar

| Qism | Texnologiya |
|---|---|
| Bot | Python + python-telegram-bot |
| Backend API | Python + FastAPI (WebApp uchun ma'lumot beradi, bot jarayonidan alohida) |
| Web App | HTML/CSS/JS (`static/`, vanilla JS) |
| Baza | SQLite |

---

## 📂 Fayl tuzilmasi

> ⚠️ **STRUKTURA QARORI:** Backend (bot + API) fayllari **hammasi repo ildizida**, papkalarga bo'linmagan.
> Faqat frontend `static/` papkasida alohida joylashadi.

```
repo/
├── README.md                 ✅ shu fayl (xarita)
├── config.py                  ✅ yaratilgan — constant qiymatlar (+ WEBAPP_URL)
├── texts.py                    ✅ yaratilgan — 3 tilli matnlar (24 ta, UZ/RU/EN)
├── models.py                   ✅ yaratilgan — SQLite jadval sxemalari
├── queries.py                  ✅ yaratilgan — users/leagues/registrations CRUD
├── schedule.py                 ✅ yaratilgan — round-robin (circle method) generatsiya
├── main_menu.py                ✅ yaratilgan — /start, til tanlash, WebApp kirish tugmasi
├── main.py                     ✅ yaratilgan — bot ishga tushish nuqtasi (entrypoint)
├── api.py                      ← FastAPI backend (hali yo'q)
└── static/
    ├── index.html              ← Web App HTML — barcha 4 bo'lim shu yerda (hali yo'q)
    ├── style.css                ← Web App stillari (hali yo'q)
    └── script.js                 ← Web App JS mantig'i (hali yo'q)
```

**Ishga tushirish:** `python main.py`

---

## 🧩 Funksional xarita (4 ta asosiy tugma)

> ⚠️ **MUHIM ARXITEKTURA QARORI:** Botning o'zi faqat kirish nuqtasi.
> `/start` → til tanlash (UZ/RU/EN) → "🚀 Kirish" inline tugmasi → WebApp ochiladi.
> **Quyidagi 4 ta bo'limning barcha funksiyalari faqat WebApp (`static/`) ichida ishlaydi**,
> bot tomonida alohida reply keyboard yoki matn handlerlari YO'Q.

### 🏠 Asosiy
- Joriy/kelayotgan turnir ma'lumoti
- Turnirga ro'yxatdan o'tish
- Qoidalar/yo'riqnoma
- E'lonlar/yangiliklar

**Bog'liq fayllar:** `api.py` (`/leagues`, `/register` endpointlari), `queries.py`, `static/index.html` + `script.js` (Asosiy bo'lim)

### 🏆 Reyting
- Umumiy reyting jadvali (barcha o'yinchilar)
- Faqat joriy turnir reytingi
- G'oliblar tarixi (oldingi turnirlar)

**Bog'liq fayllar:** `api.py` (`/rating` endpointi), `queries.py` (reyting hisoblash), `static/index.html` + `script.js` (Reyting bo'lim)

### 👤 Profil
- Mening joriy reyting o'rnim
- Mening o'tgan o'yinlarim tarixi
- Ism/nickname tahrirlash
- Shaxsiy statistika (g'alaba/mag'lubiyat)

**Bog'liq fayllar:** `api.py` (`/profile` endpointi), `queries.py` (user jadvali), `static/index.html` + `script.js` (Profil bo'lim)

### 🎁 Sovrinlar
- Eng ko'p gol urgan ishtirokchiga — 🥇 Oltin Butsa
- Turnir g'olibiga — 🏆 Oltin To'p znachogi
- Pul emas, ramziy/jismoniy sovrinlar

**Bog'liq fayllar:** `api.py` (`/prizes` endpointi), `queries.py` (statistika so'rovlari), `static/index.html` + `script.js` (Sovrinlar bo'lim)

---

## 🌍 Til tizimi

Barcha matnlar `texts.py` da markazlashtirilgan, 3 tilda: **UZ / RU / EN**.
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

**Jadval generatsiyasi:** Liga 20 kishiga to'lganda, `schedule.py` dagi circle method algoritmi avtomatik 380 ta match yaratadi (2 × 19 tur = 38 matchday).

---

## ✅ Status

- [x] Talablar aniqlandi (4 tugma va ichidagi funksiyalar)
- [x] Texnologiya tanlandi
- [x] Arxitektura qarori: bot = kirish nuqtasi, WebApp = barcha funksiyalar, FastAPI = backend
- [x] Struktura qarori: flat (static/ papkadan tashqari hammasi ildizda)
- [x] DB sxema tasdiqlandi
- [x] `config.py` yaratildi (+ WEBAPP_URL placeholder)
- [x] `models.py` yaratildi
- [x] `queries.py` yaratildi (users, leagues, registrations CRUD)
- [x] `schedule.py` yaratildi (round-robin circle method, 380 match generatsiyasi)
- [x] `texts.py` yaratildi (3 til — 24 ta matn, UZ/RU/EN)
- [x] `main.py` yaratildi (entrypoint)
- [x] `main_menu.py` yaratildi — /start, til tanlash, WebApp kirish tugmasi (test qilindi)
- [ ] `api.py` (FastAPI backend) yaratildi
- [ ] `static/index.html`, `style.css`, `script.js` yaratildi

---

## 📦 Dependencies (kerakli kutubxonalar)

| Kutubxona | Qayerda ishlatiladi | Status |
|---|---|---|
| `python-telegram-bot` | `main.py`, `main_menu.py` | ✅ Ishlatilmoqda, `requirements.txt`ga qo'shilishi kerak (hali yaratilmagan) |
| `fastapi` + `uvicorn` | `api.py` | ⚠️ Hali ishlatilmagan, `api.py` yaratilganda qo'shiladi |

---

## 📝 O'zgarishlar tarixi

| Sana | O'zgarish |
|---|---|
| 2026-06-21 | Loyiha boshlandi, README xarita yaratildi |
| 2026-06-21 | DB format tasdiqlandi: 2 liga (LaLiga/Premier), 20 o'yinchi, round-robin 2 marta, 38 kun |
| 2026-06-21 | `config.py`, `models.py`, `queries.py`, `schedule.py` yaratildi va test qilindi (dastlab `bot/db/` ichida) |
| 2026-06-21 | `texts.py` (23 ta matn, 3 til) va `keyboards.py` (4 tugma) yaratildi va test qilindi |
| 2026-06-21 | `main.py` (entrypoint) yaratildi |
| 2026-06-21 | **Arxitektura o'zgardi:** bot endi faqat /start + til tanlash + WebApp kirish tugmasi. `keyboards.py` o'chirildi (hech qayerda ishlatilmagan edi, xavfsiz o'chirildi) |
| 2026-06-21 | `webapp/` nomi `static/` ga o'zgartirildi, ichida index.html + style.css + script.js (3 alohida fayl) bo'ladi |
| 2026-06-21 | Backend qarori: FastAPI (`api.py`) — WebApp uchun ma'lumot beruvchi alohida backend, bot jarayonidan mustaqil |
| 2026-06-21 | `main_menu.py` yaratildi va test qilindi: /start → til tanlash (inline) → "🚀 Kirish" WebApp tugmasi. `texts.py`ga `enter_webapp` kaliti (3 til) qo'shildi |
| 2026-06-21 | **STRUKTURA O'ZGARDI (GitHub'dagi haqiqiy holatga moslash):** `bot/`, `bot/db/`, `bot/handlers/` ichki papkalari olib tashlandi. Endi barcha backend fayllari (`config.py`, `texts.py`, `models.py`, `queries.py`, `schedule.py`, `main_menu.py`, `main.py`) repo ildizida, flat holda. Faqat `static/` alohida papka. Barcha import qatorlari (`from bot.config import` → `from config import` va h.k.) shunga moslab to'g'rilandi va qayta test qilindi. `keyboards.py` foydalanuvchi tomonidan GitHub'dan o'chiriladi. |
