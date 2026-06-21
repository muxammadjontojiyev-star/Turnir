# 🎮 eFootball Turnir Bot — Loyiha Xaritasi

> Bu fayl loyihaning "xaritasi". Har bir o'zgarishdan keyin shu fayl ham yangilanadi.
> Versiya: v0.3 (struktura: flat — static/ papkadan tashqari hammasi ildizda)

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
├── rating.py                   ✅ yaratilgan — liga reyting jadvalini hisoblash
├── api.py                      ✅ yaratilgan — FastAPI backend (1- va 2-bosqich: 9 ta endpoint)
├── requirements.txt             ✅ yaratilgan — python-telegram-bot, fastapi, uvicorn
├── main_menu.py                ✅ yaratilgan — /start, til tanlash, WebApp kirish tugmasi
├── main.py                     ✅ yaratilgan — bot ishga tushish nuqtasi (entrypoint)
└── static/
    ├── index.html              ✅ yaratilgan — Web App HTML, barcha 4 bo'lim shu yerda
    ├── style.css                ✅ yaratilgan — Web App stillari
    ├── app.js                   ✅ yaratilgan — init, i18n (til tizimi), navigatsiya, eventlar
    └── api.js                   ✅ yaratilgan — backend API chaqiruvlari
```

**Ishga tushirish:**
- Bot: `python main.py`
- API: `uvicorn api:app --reload`

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

**Bog'liq fayllar:** `api.py` (`GET /leagues` ✅, `POST /register` ✅), `queries.py`, `static/index.html` + `app.js` + `api.js` (Asosiy bo'lim)

### 🏆 Reyting
- Umumiy reyting jadvali (barcha o'yinchilar)
- Faqat joriy turnir reytingi
- G'oliblar tarixi (oldingi turnirlar)

**Bog'liq fayllar:** `api.py` (`GET /rating/{league_id}` ✅ tayyor), `rating.py` (ball/gol farqi hisoblash), `static/index.html` + `app.js` + `api.js` (Reyting bo'lim)

### 👤 Profil
- Mening joriy reyting o'rnim
- Mening o'tgan o'yinlarim tarixi
- Ism/nickname tahrirlash
- Shaxsiy statistika (g'alaba/mag'lubiyat)

**Bog'liq fayllar:** `api.py` (`GET /profile` ✅, `POST /profile/nickname` ✅, `GET /matches/my` ✅, `POST /match/submit-result` ✅, `POST /match/confirm` ✅), `queries.py`, `rating.py`, `static/index.html` + `app.js` + `api.js` (Profil bo'lim)

### 🎁 Sovrinlar
- Eng ko'p gol urgan ishtirokchiga — 🥇 Oltin Butsa
- Turnir g'olibiga — 🏆 Oltin To'p znachogi
- Pul emas, ramziy/jismoniy sovrinlar

**Bog'liq fayllar:** `api.py` (`GET /prizes/{league_id}` ✅ tayyor), `rating.py`, `static/index.html` + `app.js` + `api.js` (Sovrinlar bo'lim)

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
- [x] `rating.py` yaratildi — reyting hisoblash mantig'i (test qilindi)
- [x] `api.py` — 1-bosqich: `GET /leagues`, `/rating/{id}`, `/profile`, `/prizes/{id}` + initData auth (test qilindi)
- [x] `api.py` — 2-bosqich: `POST /register`, `/profile/nickname`, `GET /matches/my`, `POST /match/submit-result`, `POST /match/confirm`
- [x] `static/index.html`, `style.css`, `app.js`, `api.js` yaratildi
- [x] Til almashtirish tugmasi (`#header-lang`) ishlaydigan qilindi — bosilganda UZ→RU→EN ketma-ket almashadi (`app.js`)

---

## 📦 Dependencies (kerakli kutubxonalar)

| Kutubxona | Qayerda ishlatiladi | Status |
|---|---|---|
| `python-telegram-bot` | `main.py`, `main_menu.py` | ✅ Ishlatilmoqda, `requirements.txt`ga qo'shildi |
| `fastapi` + `uvicorn` | `api.py` | ✅ Ishlatilmoqda, `requirements.txt`ga qo'shildi |

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
| 2026-06-21 | `rating.py` yaratildi — reyting hisoblash (3 ball g'alaba, 1 ball durang, gol farqi bo'yicha saralash), test ma'lumotlari bilan tekshirildi |
| 2026-06-21 | `api.py` yaratildi (1-bosqich): Telegram `initData` HMAC-SHA256 autentifikatsiyasi + `GET /leagues`, `/rating/{league_id}`, `/profile`, `/prizes/{league_id}`. To'g'ri va soxta initData bilan test qilindi (soxta → 401). `requirements.txt` yaratildi. |
| 2026-06-21 | `api.py` 2-bosqichi yakunlandi: `POST /register`, `/profile/nickname`, `GET /matches/my`, `POST /match/submit-result`, `POST /match/confirm` qo'shildi. `static/index.html`, `style.css`, `app.js`, `api.js` yaratildi (4 ta WebApp bo'limi to'liq ishlaydi). README xarita shu haqiqiy holatga moslab yangilandi (v0.2 → v0.3). |
| 2026-06-22 | **Klub tanlash qo'shildi:** Liga tanlanganidan keyin o'sha liganing 20 ta klubini logo va nomi bilan alifbo tartibida ko'rsatish. Foydalanuvchi klub tanlasa register tugmasi faollashadi. Bir mavsumda faqat bir marta ro'yxatdan o'tish (allaqachon ro'yxatdan o'tgan bo'lsa klublar disabled ko'rinadi). `LEAGUE_CLUBS` statik ma'lumoti `api.js`ga qo'shildi. `APP.selectedClub` state'i `app.js`ga qo'shildi. 3 ta yangi i18n kaliti (uz/ru/en): `clubs_in_league`, `select_club`, `already_in_season`. `style.css`ga `.clubs-list`, `.club-item`, `.club-logo` stillari. `index.html`ga `#clubs-section` div. |
| 2026-06-22 | **Profil avatar/badge o'zgartirildi:** Profil bo'limida doira ichidagi harf o'rniga Telegram profil rasmi (`APP.currentUser.photo_url`) qo'yildi (rasm bo'lmasa — harf, zaxira sifatida). Ism o'rnida klub nomi ko'rsatish mantig'i saqlandi. O'ng tomondagi qalamcha (✏️, nickname tahrirlash) tugmasi olib tashlandi, o'rniga faqat ko'rsatish uchun (bosilmaydigan) tanlangan klub logosi (`#profile-club-badge`) qo'yildi. `index.html`: `#btn-edit-nickname` → `#profile-club-badge`. `app.js`: shu tugma uchun `addEventListener` qatori olib tashlandi. `api.js`: `renderProfile()` yangilandi. **Eslatma:** nickname tahrirlash modali (`openNicknameModal`, `saveNickname`) kodda qoldi, lekin uni ochadigan tugma yo'q — hozircha ishlatilmaydi. |
| 2026-06-22 | **Klub band qilish (anti-dublikat) va ro'yxat xulq-atvori:** `registrations` jadvaliga `club_name` ustuni qo'shildi (`models.py`). `queries.py`: yangi `get_taken_clubs(league_id)`; `register_user_to_league()` endi `club_name` qabul qiladi va band klubni `"club_taken"` sababi bilan rad etadi (backend darajasidagi himoya, race condition uchun ham). `api.py`: yangi `GET /leagues/{league_id}/clubs` (band klublar ro'yxati, auth shart emas); `/register` `club_name` qabul qiladi; `/profile` javobida `club_name` qaytaradi. `api.js`: `renderClubsForLeague()` async qilindi, band klublarni backenddan olib `disabled` qiladi (CSS'da mavjud bo'lgan `.club-item.disabled` ishlatiladi); klub bosilganda klublar ro'yxati endi yashirilmaydi, foydalanuvchi fikridan qaytib boshqa klub tanlay oladi (faqat muvaffaqiyatli Register'dan keyin yashiriladi); `registerToLeague()` `club_taken` xatosini ushlab ro'yxatni yangilaydi. `app.js`: 3 tilga (uz/ru/en) yangi `club_taken` matni qo'shildi. |
| 2026-06-22 | **To'liq ekran rejimi (Telegram WebApp fullscreen):** `app.js`dagi `init()` ichida `tg.expand()`dan keyin `tg.requestFullscreen()` chaqirildi (mavjud bo'lsa — `typeof` tekshiruvi bilan, eski Telegram versiyalarida xato bermasligi uchun). Bot API 8.0+ talab qilinadi, eski versiyalarda oddiy `expand()` ishlayveradi. `style.css`: `.header`ga `env(safe-area-inset-top)` padding qo'shildi — to'liq ekranda header qurilma status bari/notch ostida qolib ketmasligi uchun. **Eslatma:** pastki navigatsiya panelida (`.bottom-nav`) hozircha safe-area moslamasi qo'shilmadi — amalda muammo chiqsa alohida so'rab tuzatish kerak. |
| 2026-06-22 | **To'liq ekran rejimi BEKOR QILINDI:** Foydalanuvchi ko'rinishni yoqtirmadi. `app.js`dagi `tg.requestFullscreen()` chaqiruvi va `style.css`dagi `.header`ning `env(safe-area-inset-top)` padding'i olib tashlandi, ikkala fayl ham oldingi (faqat `tg.expand()` ishlatadigan) holatiga qaytarildi. |



