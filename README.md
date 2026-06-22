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
├── notify.py                   ✅ yaratilgan — bot orqali inline (push) xabar yuborish (httpx → Telegram sendMessage)
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
- ⚽ To'p urarlar tabi — barcha ligalar bo'yicha umumiy eng ko'p gol urganlar ro'yxati (✅ qo'shildi)

**Bog'liq fayllar:** `api.py` (`GET /rating/{league_id}` ✅ tayyor — to'p urarlar uchun ham shu endpoint ishlatiladi, yangi endpoint yo'q), `rating.py` (ball/gol farqi/gol soni hisoblash), `static/index.html` + `app.js` + `api.js` (Reyting bo'lim)

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
- [x] Admin panel (4 funksiya): o'yinchini chiqarish, rad etilgan natijalarni hal qilish, tasdiqlangan natijani Match ID orqali tuzatish, liga to'lganda qur'a o'tkazish. Faqat `config.py` `ADMIN_TELEGRAM_IDS`dagi foydalanuvchilarga ko'rinadi (Profil bo'limida).
- [x] Reyting jadvalida klub qatoriga bosilganda — o'sha o'yinchining to'liq profili modal oynada ochiladi (statistika + o'yinlar tarixi + Telegram link). Sovrinlardagi g'olib ismiga bosilganda — Telegram chati.

---

## 📦 Dependencies (kerakli kutubxonalar)

| Kutubxona | Qayerda ishlatiladi | Status |
|---|---|---|
| `python-telegram-bot` | `main.py`, `main_menu.py` | ✅ Ishlatilmoqda, `requirements.txt`ga qo'shildi |
| `fastapi` + `uvicorn` | `api.py` | ✅ Ishlatilmoqda, `requirements.txt`ga qo'shildi |
| `httpx` | `api.py` (photo proxy), `notify.py` (inline xabar) | ✅ Ishlatilmoqda, `requirements.txt`da mavjud |

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
| 2026-06-22 | **Reyting bo'limi: username ko'rsatish + podium dizayni.** Backend (`rating.py`, `queries.py`, `models.py`, `api.py`) allaqachon `username` maydonini to'liq qo'llab-quvvatlagan edi. Frontend o'zgarishlari: `api.js` — `renderRatingTable()` endi top-3 uchun podium blokini (`renderPodiumPlayer()`) va 4+ uchun jadval (ayrim qatorini) ko'rsatadi. O'yinchi katagi: katta `@username` + kichik `nickname` (yo'q bo'lsa faqat nickname). `index.html` — `#podium-wrap` div + `#rating-rest-card` (jadval uchun). `style.css` — `.podium`, `.pod-player`, `.pod-avatar`, `.pod-stand-1/2/3`, `.pod-username`, `.pod-nickname`, `.pod-pts`, `.player-cell`, `.player-username`, `.player-nickname` stillari qo'shildi. |
| 2026-06-22 | **ADMIN PANEL qo'shildi (3 funksiya, klub/username tizimi ustiga).** Profil bo'limida, faqat `config.py` `ADMIN_TELEGRAM_IDS`dagi (admin: 6829293074) foydalanuvchilarga ko'rinadigan panel. **(1)** O'yinchini chiqarish — to'liq o'chiradi (user + registration + barcha matchlari). **(2)** Rad etilgan (`rejected`) natijalarni hal qilish — natija belgilash (`set_result`→`confirmed`) yoki qayta tiklash (`reset`→`pending`). **(3)** Tasdiqlangan (`confirmed`) natijani Match ID orqali tuzatish (status o'zgarmaydi, faqat score). `queries.py`: `get_all_users_with_registration` (username+club_name bilan), `remove_user_completely`, `get_rejected_matches`, `admin_resolve_match`, `admin_fix_confirmed_match`. `api.py`: `get_authenticated_admin` dependency (403 agar admin emas) + 5 endpoint (`GET /admin/players`, `DELETE /admin/players/{id}`, `GET /admin/rejected-matches`, `POST /admin/match/resolve`, `POST /admin/match/fix-confirmed`). `index.html`/`style.css`: Admin panel UI + `#modal-admin-resolve`. `app.js`: `data-i18n-placeholder` qo'llab-quvvatlash, `cycleLanguage` til o'zgarganda joriy bo'limni qayta yuklaydi, 3 tilga 14 yangi matn. `api.js`: admin funksiyalari + "Mening o'yinlarim"da match ID (`#42`) ko'rsatildi. Cache versiya `e`→`f`. |
| 2026-06-22 | **Sovrinlardagi g'olib ismiga Telegram chat linki.** Sovrinlar bo'limida (Oltin Butsa, Oltin To'p) g'olibning ismi `@username` ko'rinishida (allaqachon shunday edi), endi unga bosilganda o'sha odamning Telegram chati (`https://t.me/username`, yangi tabda) ochiladi. Faqat `api.js` `renderPrizeClub()` o'zgartirildi: username bor bo'lsa `<a class="prize-holder-link">`, bo'lmasa eski `<span>` (nickname, bosilmaydi). `style.css`: `.prize-holder-link` (color: inherit, hover'da underline). Bu Profil bo'limidagi mavjud Telegram link naqshi bilan izchil. Cache versiya `f`→`g`. **Eslatma:** foydalanuvchida Telegram username bo'lmasa, nickname ko'rinadi va bosilmaydi (chunki t.me faqat username bilan ishlaydi). |
| 2026-06-22 | **Reyting jadvalida o'yinchi profilini ko'rish (modal).** Reyting jadvalida biror klub/o'yinchi qatoriga bosilganda — o'sha o'yinchining to'liq profili alohida modal oynada ochiladi: avatar (ism harfi — boshqa odamning Telegram rasmi WebApp'da yo'q), klub logosi/nomi, statistika (o'rin/g'alaba/durang/mag'lubiyat), o'yinlar tarixi (faqat ko'rish, tugmasiz), va Telegram username linki (mavjud bo'lsa). `queries.py`: yangi `get_user_by_id(user_id)`. `api.py`: yangi `GET /players/{user_id}/profile` (auth talab qiladi, har qanday kirgan foydalanuvchi ko'ra oladi; `user_id`, `username`, `matches` bilan). `index.html`: `#modal-player` (kengroq, scroll bilan). `style.css`: `.modal-box--wide`, `.modal-close-btn`, `.card--profile-modal`, `.rating-row` cursor. `api.js`: `renderRatingTable()` qatorga `data-user-id`+click qo'shdi, `openPlayerModal`/`closePlayerModal`/`renderPlayerModal`/`renderPlayerMatchItem`. `app.js`: 3 tilga `player_matches` matni, modal yopish listenerlari. Cache versiya `g`→`h`. |
| 2026-06-22 | **O'yinchi profili: modal → to'liq bo'lim.** Foydalanuvchi so'roviga ko'ra, boshqa o'yinchi profili endi kichik modal o'rniga to'liq bo'lim (`#section-player`) sifatida ochiladi (header + pastki navigatsiya ko'rinib turadi). Yuqori chap burchakda `← Ortga` tugmasi (reyting bo'limiga qaytaradi). Reyting qatoriga bosilishi bilan profil ochiladi (oldingidek). `index.html`: `#modal-player` div o'chirildi, `</main>` ichida yangi `<section id="section-player">` qo'shildi. `style.css`: modal klasslari (`.modal-box--wide`, `.modal-close-btn`, `.card--profile-modal`) o'chirildi, `.back-btn` + `.back-btn-arrow` qo'shildi. `api.js`: `openPlayerModal()` endi `navigateTo("player")`, `closePlayerModal()` endi `navigateTo("rating")`. `app.js`: 3 tilga `back` matni, `bindEvents` `#btn-player-back` listeneri (eski modal listenerlari o'rniga). Cache versiya `h`→`i`. |
| 2026-06-22 | **O'yinchi profilida Telegram rasmi (bot proxy).** Boshqa o'yinchi profilida endi uning Telegram profil rasmi ko'rsatiladi (mavjud va maxfiy bo'lmasa). Telegram boshqa odam rasmini WebApp'ga to'g'ridan-to'g'ri bermagani uchun, bot token orqali serverda olinadi: `api.py` yangi `GET /players/{user_id}/photo` (async, `httpx` bilan: getUserProfilePhotos → getFile → rasm baytlarini proxy qiladi). **Auth yo'q** (chunki `<img src>` header yubora olmaydi; rasm ommaviy profil qismi). Bot token URL'da oshkor bo'lmaydi — faqat rasm baytlari uzatiladi. Rasm yo'q/maxfiy/xato → 404, frontend ism harfiga tushadi (`img.onload` orqali silliq almashtirish). `requirements.txt`ga `httpx` qo'shildi. `api.js`: `renderPlayerModal()` avatar uchun `<img src="/players/{id}/photo">`. Username link allaqachon bor edi (Telegram chatiga). Cache versiya `i`→`j`. **Eslatma:** rasm har doim ishlamaydi — foydalanuvchi rasmsiz yoki maxfiy bo'lsa ism harfi ko'rinadi. Photo endpoint auth'siz, rate-limit yo'q (kichik loyiha uchun yetarli). |
| 2026-06-22 | **O'yinchi profilida nickname o'rniga username.** Boshqa o'yinchi profilida (klub nomi ostidagi qator) endi nickname o'rniga faqat `@username` (cyan link, bosilsa Telegram chatiga o'tadi) ko'rsatiladi. Username bo'lmasa — "Username yo'q" (kulrang, bosilmaydi). `api.js`: `renderPlayerModal()` username qatori soddalashtirildi (nickname endi bu qatorda ko'rsatilmaydi; yuqoridagi katta yozuvda klub nomi/nickname qoladi). `app.js`: 3 tilga `no_username` matni. `style.css`: `.profile-no-username` (kulrang). Cache versiya `j`→`k`. |
| 2026-06-22 | **BUG FIX: username DB'ga hech qachon yozilmas edi.** `users.username` ustuni mavjud edi va `rating.py`/frontend uni o'qiyotgan edi, lekin `get_or_create_user()` uni **hech qachon yozmasdi** — shuning uchun barcha foydalanuvchilarda username `NULL` bo'lib, profilda doim "Username yo'q" ko'rinardi. Tuzatish: `queries.py` `get_or_create_user(telegram_id, nickname, username=None)` — yangi user yaratganda username yoziladi, mavjud user'da o'zgargan bo'lsa yangilanadi (initData'da username yo'q bo'lsa eski qiymat NULL'ga o'chirilmaydi). `api.py`: `get_authenticated_user` va `get_authenticated_admin` endi initData'dan `telegram_user.get("username")` olib uzatadi. To'rt holatda (yangi+username, mavjud+None, username o'zgargan, yangi+username yo'q) test qilindi. **Eslatma:** mavjud foydalanuvchilar uchun username keyingi marta WebApp ochilganda avtomatik yoziladi (har bir auth'da yangilanadi). Frontend o'zgarmadi — u allaqachon username'ni to'g'ri ko'rsatadi. |
| 2026-06-22 | **Admin: avto qur'a (liga to'lganda).** `schedule.py`dagi `generate_league_schedule()` allaqachon yozilgan edi, lekin hech qayerdan chaqirilmasdi — endi admin panelda chaqiriladigan qildik. `queries.py`: yangi `league_has_matches(league_id)` (qur'a allaqachon o'tkazilganini tekshiradi). `api.py`: yangi `POST /admin/league/{league_id}/draw` (faqat admin) — liga to'lmagan bo'lsa `league_not_full` (400), allaqachon match mavjud bo'lsa `already_drawn` (400) qaytaradi (ikkinchi marta qur'a qilib, kiritilgan natijalarni yo'qotib qo'ymaslik uchun — qayta qur'a hozircha qo'llab-quvvatlanmaydi); aks holda `generate_league_schedule()` chaqirib 380 match yaratadi va liga statusini `in_progress`ga o'tkazadi. `index.html`: admin panelga `#admin-draw-list` (har bir liga uchun holat + tugma). `api.js`: `renderAdminDraw()`, `runLeagueDraw()`, `loadAdminPanel()` ichida chaqiriladi. `app.js`: 3 tilga (uz/ru/en) `admin_draw_title`, `admin_draw_button`, `admin_draw_confirm`, `admin_draw_success`, `admin_draw_not_full`, `admin_draw_already`. `style.css`: `.admin-draw-btn` + `:disabled` holati. Cache versiya `k`→`l`. |
| 2026-06-22 | **Reyting bo'limi: "To'p urarlar" tabi qo'shildi.** Ligalar tablari yonida doimiy "⚽ To'p urarlar" tabi — bosilganda barcha ligalar bo'yicha umumiy (LaLiga + Premier Liga birlashtirilgan) eng ko'p gol urganlar ro'yxati ko'rsatiladi, liga ro'yxati kabi jadval ko'rinishida (#, o'yinchi, liga, gol). Yangi backend endpoint qo'shilmadi — mavjud `GET /rating/{league_id}` (har biri allaqachon `goals_for` qaytaradi) barcha ligalar uchun parallel chaqirilib, frontendda birlashtirilib gol bo'yicha saralanadi. `index.html`: `#rating-card` (mavjud reyting jadvali, id qo'shildi) yonida yangi `#top-scorers-card` (4 ustunli jadval, boshida `hidden`). `app.js`: `APP.ratingTab` state ("league"/"top_scorers"), 3 tilga `tab_top_scorers`, `th_league`, `th_goals_col`. `api.js`: `renderRatingFilter()` ligalar tugmalaridan keyin "To'p urarlar" tugmasini ham chizadi; yangi `showRatingCard()` (ikki jadval orasida almashtiradi), `loadTopScorers()` (barcha ligalardan `/rating/{id}` yig'ib birlashtiradi), `renderTopScorersTable()` (gol bo'yicha saralab chizadi, qatorga bosilganda mavjud `openPlayerModal()` orqali profil ochiladi). Cache versiya `k`→`l`. |
| 2026-06-22 | **Inline (push) bildirishnomalar + Home'da natija kiritish.** Bot endi muayyan hodisalarda foydalanuvchilarga Telegram'da xabar yuboradi (har biri o'z tilida, `users.language`). Yangi `notify.py`: `httpx` orqali Telegram `sendMessage` (botning polling jarayoniga tegmaydi, API thread'idan ishlaydi; xato jim yutiladi). `texts.py`: `notify_draw_done` ({league} bilan), `notify_result_submitted` (3 til). `queries.py`: `get_league_members_for_notify(league_id)` (telegram_id+language). `api.py`: **(1)** `/admin/league/{id}/draw` endi `async` — qur'a o'tkazilgach liga ishtirokchilariga "Qur'a tashlandi" yuboradi; **(2)** `/match/submit-result` endi `async` — natija kiritilgach raqibga (natija kiritmagan tomonga) "Natija kiritildi, tasdiqlaysizmi?" yuboradi. Tasdiqlash WebApp'da qilinadi (xabarda tugma yo'q). **Home'da natija kiritish:** `index.html` Home bo'limiga `#home-matches-section` qo'shildi; `api.js` `loadHomeMatches()` (Profildagi `renderMatchItem` mantig'ini qayta ishlatadi), `bindMatchActions()` (Profil+Home umumiy event yordamchisi), `refreshMatchViews()` (natija o'zgarganda ikkala ro'yxatni izchil yangilaydi). `app.js`: 3 tilga `home_my_matches`. `httpx` allaqachon `requirements.txt`da (yangi dependency yo'q). Cache versiya `l`→`m`. |
| 2026-06-22 | **Sovrin ikonlari rasm bilan almashtirildi.** Sovrinlar bo'limidagi 🥇 (Oltin Butsa) va 🏆 (Oltin To'p) emojilari o'rniga foydalanuvchi bergan haqiqiy sovrin rasmlari qo'yildi: `static/golden-boot.png`, `static/golden-ball.png` (256px, oq fon shaffof qilingan, ~60-95KB). `index.html`: `.prize-icon` ichida emoji o'rniga `<img class="prize-icon-img">`. `style.css`: `.prize-icon-img` (56×56, object-fit:contain). Cache versiya `m`→`n`. |




