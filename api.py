"""
api.py — FastAPI backend, WebApp uchun ma'lumot beradi.

Ishga tushirish: uvicorn api:app --reload

Autentifikatsiya: Telegram WebApp initData orqali (HMAC-SHA256, bot tokeni bilan
imzolangan). Har bir so'rovda "X-Telegram-Init-Data" header yuborilishi kerak.

1-BOSQICH: faqat o'qish (GET) endpointlari. ✅
2-BOSQICH: POST /register, POST /profile/nickname, GET /matches/my,
           POST /match/submit-result, POST /match/confirm. ✅
"""

import hashlib
import hmac
import json
import logging
import time
from urllib.parse import parse_qsl, urlparse

import httpx
from fastapi import FastAPI, Header, HTTPException, Depends, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response, JSONResponse

from config import (
    BOT_TOKEN, ADMIN_TELEGRAM_IDS, LEAGUE_STATUS_IN_PROGRESS, TOTAL_MATCHDAYS,
    MATCHDAYS_PER_UNLOCK, WEBAPP_URL, MAX_SCORE,
    IP_RATE_LIMIT_MAX, IP_RATE_LIMIT_WINDOW,
    PHOTO_CACHE_TTL_SECONDS, PHOTO_CACHE_NEGATIVE_TTL_SECONDS, PHOTO_CACHE_MAX_ENTRIES,
)

# XAVFSIZLIK GUARD (audit B7): BOT_TOKEN bo'sh bo'lsa initData HMAC kaliti
# hammaga ma'lum qiymatdan hisoblanадi — istalgan kishi soxta initData yasay
# olardi. main.py buni tekshiradi, lekin API alohida (`uvicorn api:app`)
# ishga tushirilganda ham himoya bo'lishi shart.
if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN topilmadi — API ishga tushirilmaydi "
        "(initData tekshiruvi himoyasiz bo'lib qolardi)."
    )
from queries import (
    get_all_leagues, get_user_by_telegram_id, get_or_create_user,
    get_league_by_id, count_league_players, get_user_registration,
    register_user_to_league, update_user_nickname, get_taken_clubs,
    get_user_matches, submit_match_result, confirm_or_reject_match,
    admin_resolve_pending, get_admin_pending_matches,
    wc_admin_resolve_pending, wc_get_admin_pending_matches,
    get_all_users_with_registration, remove_user_completely,
    get_rejected_matches, admin_resolve_match, admin_fix_confirmed_match,
    admin_cancel_match,
    get_user_by_id, update_league_status, league_has_matches,
    get_league_members_for_notify, get_match_by_id,
    get_open_matchday, set_league_draw_date, delete_league_matches,
    get_played_results, restore_results_to_schedule,
    reopen_matchdays, auto_resolve_matches, get_deadline_passed_matchday,
    get_matchday_entry_locked, reopen_matchday_range, reset_awaiting_in_range,
    is_near_deadline,
    send_chat_message, get_chat_messages, count_unread_messages,
    touch_last_seen, set_typing, get_chat_state,
    wc_register_user, wc_get_user_registration, wc_get_taken_teams,
    wc_count_group_players,
    wc_get_user_matches, wc_get_match_by_id, wc_submit_match_result,
    wc_confirm_or_reject_match, wc_get_open_matchday,
    wc_admin_fix_confirmed_match, wc_admin_remove_player, wc_get_all_players,
    wc_admin_set_score, wc_admin_reset_match, wc_fix_missing_schedules,
    wc_start_all_today,
)
from schedule import generate_league_schedule, get_league_player_ids
from rating import calculate_league_rating, get_player_position
from notify import notify_members, notify_user
from texts import t
from membership import is_user_subscribed
from admin_roles import (
    is_super_admin, is_scope_admin, add_admin, remove_admin, list_admins,
    assign_league, unassign_league, get_admin_league_ids, can_manage_league,
    SCOPE_LEAGUE, SCOPE_WC, VALID_SCOPES,
)
from wc_chat import (
    wc_send_chat_message, wc_get_chat_messages, wc_count_unread_messages,
    wc_set_typing, wc_get_chat_state,
)
from config import REQUIRED_CHANNEL_USERNAME, REQUIRED_CHANNEL_URL, ADMIN_CONTACT_USERNAME

app = FastAPI(title="eFootball Turnir Bot API")


# MUSTAHKAMLIK: kutilmagan xatoda API yiqilmaydi — log'ga yoziladi,
# foydalanuvchiga toza JSON 500 qaytadi (traceback sizib chiqmaydi).
logger = logging.getLogger("api")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):
    logger.exception("Kutilmagan xato: %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Serverda kutilmagan xato yuz berdi. Keyinroq urinib ko'ring."},
    )

# WebApp boshqa origin'dan so'rov yuborgani uchun CORS kerak.
# MUSTAHKAMLIK: faqat o'z domenimizga ruxsat (WEBAPP_URL'dan olinadi).
# WEBAPP_URL o'rnatilmagan/standart bo'lsa — eski "*" holati saqlanadi (uzilish bo'lmasin).
_webapp_origin = None
if WEBAPP_URL and "example.com" not in WEBAPP_URL:
    _p = urlparse(WEBAPP_URL)
    if _p.scheme and _p.netloc:
        _webapp_origin = f"{_p.scheme}://{_p.netloc}"

app.add_middleware(
    CORSMiddleware,
    allow_origins=[_webapp_origin] if _webapp_origin else ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# static/ papkasini serve qilish — WebApp HTML/CSS/JS
app.mount("/webapp", StaticFiles(directory="static", html=True), name="static")


# HTML fayllar (ayniqsa index.html) keshlanmasligi uchun no-cache header qo'shamiz.
# Sabab: Telegram WebView index.html'ni agressiv keshlaydi — yangilanish chiqsa ham
# eski HTML (va undagi eski ?v= versiyalari) yuklanib qolaveradi. HTML har safar
# yangi olinsa, undagi ?v= orqali CSS/JS to'g'ri yangilanadi (CSS/JS esa keshlanaveradi).
@app.middleware("http")
async def no_cache_for_html(request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path.endswith(".html") or path == "/webapp" or path == "/webapp/":
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


def validate_scores(score1: int, score2: int):
    """
    MUSTAHKAMLIK: gol qiymatlari umumiy tekshiruvi (barcha submit endpointlar uchun).
    Manfiy → 400 score_negative (eski xabar saqlangan),
    MAX_SCORE'dan katta → 400 score_too_big.
    """
    if score1 < 0 or score2 < 0:
        raise HTTPException(status_code=400, detail="score_negative")
    if score1 > MAX_SCORE or score2 > MAX_SCORE:
        raise HTTPException(status_code=400, detail="score_too_big")


def verify_telegram_init_data(init_data: str) -> dict:
    """
    Telegram WebApp initData'ni tekshiradi va ichidan foydalanuvchi ma'lumotini chiqaradi.

    Telegram hujjatlashtirilgan algoritmi:
    https://core.telegram.org/bots/webapps#validating-data-received-via-the-web-app

    Xato bo'lsa HTTPException(401) tashlaydi.
    """
    try:
        parsed = dict(parse_qsl(init_data))
        received_hash = parsed.pop("hash", None)
        if not received_hash:
            raise ValueError("hash topilmadi")

        data_check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(parsed.items())
        )

        secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        computed_hash = hmac.new(
            secret_key, data_check_string.encode(), hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(computed_hash, received_hash):
            raise ValueError("hash mos kelmadi")

        # Replay himoyasi: initData 24 soatdan eski bo'lsa — rad etiladi
        auth_date = int(parsed.get("auth_date", "0"))
        if auth_date <= 0 or (time.time() - auth_date) > 86400:
            raise ValueError("initData muddati o'tgan")

        user_json = parsed.get("user")
        if not user_json:
            raise ValueError("user ma'lumoti topilmadi")

        return json.loads(user_json)

    except Exception as exc:
        raise HTTPException(status_code=401, detail="Noto'g'ri Telegram autentifikatsiya") from exc


# MUSTAHKAMLIK: oddiy xotiradagi rate-limit (har bir user: 10 sekundda 40 so'rov).
# Oddiy foydalanishga xalaqit bermaydi, flood/skriptdan himoya qiladi.
RATE_LIMIT_MAX = 40
RATE_LIMIT_WINDOW = 10  # sekund
_rate_buckets: dict = {}
_ip_buckets: dict = {}


def _bucket_hit(buckets: dict, key, max_count: int, window: int) -> bool:
    """
    Umumiy rate-limit hisoblagichi (user va IP limitlari uchun bitta mantiq —
    qoida #26 DRY). True → limit oshib ketdi.
    """
    now = time.time()
    bucket = buckets.get(key)
    if bucket is None or now - bucket["start"] > window:
        buckets[key] = {"start": now, "count": 1}
        # Xotira o'smasligi uchun eski yozuvlarni vaqti-vaqti bilan tozalash
        if len(buckets) > 5000:
            for k in [k for k, b in buckets.items() if now - b["start"] > window]:
                buckets.pop(k, None)
        return False
    bucket["count"] += 1
    return bucket["count"] > max_count


def _check_rate_limit(telegram_id: int):
    if _bucket_hit(_rate_buckets, telegram_id, RATE_LIMIT_MAX, RATE_LIMIT_WINDOW):
        raise HTTPException(status_code=429, detail="too_many_requests")


# AUDIT A4: IP darajasidagi limit — auth'siz endpointlarni ham qamrab oladi
# (/players/{id}/photo, /rating, /leagues va h.k.). /webapp statik fayllari
# hisobga olinmaydi (sahifa yuklanishida ko'p fayl birdan keladi).
@app.middleware("http")
async def ip_rate_limit(request, call_next):
    path = request.url.path
    if not path.startswith("/webapp"):
        # Railway/proxy ortida haqiqiy IP X-Forwarded-For'ning birinchi qiymatida
        fwd = request.headers.get("x-forwarded-for", "")
        ip = fwd.split(",")[0].strip() if fwd else (
            request.client.host if request.client else "unknown"
        )
        if _bucket_hit(_ip_buckets, ip, IP_RATE_LIMIT_MAX, IP_RATE_LIMIT_WINDOW):
            return JSONResponse(status_code=429, content={"detail": "too_many_requests"})
    return await call_next(request)


def get_authenticated_user(x_telegram_init_data: str = Header(...)) -> dict:
    """
    FastAPI dependency: initData'ni tekshiradi va DB'dagi user yozuvini qaytaradi.

    Foydalanuvchi DB'da topilmasa — avtomatik yaratadi (nickname = first_name).
    Telegram @username initData'dan olinadi va DB'da saqlanadi/yangilanadi.
    """
    telegram_user = verify_telegram_init_data(x_telegram_init_data)
    telegram_id   = telegram_user["id"]
    _check_rate_limit(telegram_id)
    first_name    = telegram_user.get("first_name", f"user_{telegram_id}")
    username      = telegram_user.get("username")

    user = get_or_create_user(telegram_id, first_name, username)
    # Online holati uchun: foydalanuvchi ilovani ishlatgan har lahzada faollik vaqti yangilanadi
    try:
        touch_last_seen(telegram_id)
    except Exception as exc:
        # Online-holat yangilanmasa ham so'rov davom etadi, lekin jim yutmaymiz (qoida #44)
        logger.debug("touch_last_seen xatosi (tg=%s): %s", telegram_id, exc)
    return user


def get_authenticated_admin(x_telegram_init_data: str = Header(...)) -> dict:
    """
    FastAPI dependency: initData'ni tekshiradi va foydalanuvchining
    ADMIN_TELEGRAM_IDS ro'yxatida ekanini tasdiqlaydi.

    Admin emas bo'lsa — 403 qaytaradi.
    """
    telegram_user = verify_telegram_init_data(x_telegram_init_data)
    telegram_id = telegram_user["id"]

    if telegram_id not in ADMIN_TELEGRAM_IDS:
        raise HTTPException(status_code=403, detail="Sizda admin huquqi yo'q")

    first_name = telegram_user.get("first_name", f"user_{telegram_id}")
    username   = telegram_user.get("username")
    return get_or_create_user(telegram_id, first_name, username)


def _authenticated_scope_admin(x_telegram_init_data: str, scope: str) -> dict:
    """
    Berilgan scope ('league'/'wc') uchun admin huquqини tekshiradi.
    Bosh admin har doim o'tadi; oddiy admin faqat o'z scope'ida.
    Admin emas bo'lsa — 403. user yozuvini qaytaradi (telegram_id ham qo'shiladi).
    """
    telegram_user = verify_telegram_init_data(x_telegram_init_data)
    telegram_id = telegram_user["id"]
    if not is_scope_admin(telegram_id, scope):
        raise HTTPException(status_code=403, detail="Sizda admin huquqi yo'q")
    first_name = telegram_user.get("first_name", f"user_{telegram_id}")
    username   = telegram_user.get("username")
    user = get_or_create_user(telegram_id, first_name, username)
    user = dict(user)
    user["telegram_id"] = telegram_id
    return user


def get_authenticated_league_admin(x_telegram_init_data: str = Header(...)) -> dict:
    """Liga admin (bosh yoki liga scope admin). Natija tuzatish uchun."""
    return _authenticated_scope_admin(x_telegram_init_data, SCOPE_LEAGUE)


def get_authenticated_wc_admin(x_telegram_init_data: str = Header(...)) -> dict:
    """WC admin (bosh yoki wc scope admin). WC natija tuzatish uchun."""
    return _authenticated_scope_admin(x_telegram_init_data, SCOPE_WC)


def get_authenticated_super_admin(x_telegram_init_data: str = Header(...)) -> dict:
    """Faqat bosh admin (config.py). Admin tayinlash uchun."""
    telegram_user = verify_telegram_init_data(x_telegram_init_data)
    telegram_id = telegram_user["id"]
    if not is_super_admin(telegram_id):
        raise HTTPException(status_code=403, detail="Faqat bosh admin")
    first_name = telegram_user.get("first_name", f"user_{telegram_id}")
    username   = telegram_user.get("username")
    user = dict(get_or_create_user(telegram_id, first_name, username))
    user["telegram_id"] = telegram_id
    return user


def _authenticated_scope_admin(x_telegram_init_data: str, scope: str) -> dict:
    """
    2026-07-22: berilgan scope ('cl'/'division'/...) admini (bosh admin YOKI
    o'sha scope'ga tayinlangan oddiy admin). Talab 2 uchun umumiy yordamchi.
    """
    telegram_user = verify_telegram_init_data(x_telegram_init_data)
    telegram_id = telegram_user["id"]
    if not is_scope_admin(telegram_id, scope):
        raise HTTPException(status_code=403, detail="Ruxsat yo'q")
    first_name = telegram_user.get("first_name", f"user_{telegram_id}")
    username   = telegram_user.get("username")
    user = dict(get_or_create_user(telegram_id, first_name, username))
    user["telegram_id"] = telegram_id
    return user


def get_authenticated_cl_admin(x_telegram_init_data: str = Header(...)) -> dict:
    """ChL admini: bosh admin yoki 'cl' scope'ga tayinlangan admin."""
    from admin_roles import SCOPE_CL
    return _authenticated_scope_admin(x_telegram_init_data, SCOPE_CL)


def get_authenticated_div_admin(x_telegram_init_data: str = Header(...)) -> dict:
    """Divizion admini: bosh admin yoki 'division' scope'ga tayinlangan admin."""
    from admin_roles import SCOPE_DIVISION
    return _authenticated_scope_admin(x_telegram_init_data, SCOPE_DIVISION)


def _annotate_matches_locked(matches: list[dict]) -> list[dict]:
    """
    Har bir match'ga 'is_locked', 'entry_locked', 'near_deadline' (bool) qo'shadi.

    - is_locked: matchday hali OCHILMAGAN (get_open_matchday'dan katta) → True.
    - entry_locked: tur ochilgan, lekin ochilgandan keyin RESULT_ENTRY_DELAY_MINUTES
      (1s45daq) hali o'tmagan → True (hisob kiritib bo'lmaydi, biroz erta).
    - near_deadline: hozir 00:45–01:00 oralig'i → hisob kiritish VA rad etish yopiq.

    Frontend: is_locked → qulf; entry_locked → "kuting"; near_deadline → kiritish/rad o'chiq.
    open_matchday liga bo'yicha bir marta keshlanadi (samaradorlik uchun).
    """
    near_dl = is_near_deadline()  # vaqtga bog'liq, hamma match uchun bir xil
    open_cache: dict[int, int] = {}
    for m in matches:
        league_id = m.get("league_id")
        if league_id not in open_cache:
            open_cache[league_id] = get_open_matchday(league_id)
        matchday = m.get("matchday", 0)
        m["is_locked"] = matchday > open_cache[league_id]
        m["near_deadline"] = near_dl
        # Ochiq turlar uchun kechikishni tekshiramiz (yopiq turlar uchun keraksiz)
        if not m["is_locked"]:
            m["entry_locked"] = get_matchday_entry_locked(league_id, matchday)
        else:
            m["entry_locked"] = False
    return matches


# ============ GET /membership/check ============

@app.get("/membership/check")
async def check_membership(user: dict = Depends(get_authenticated_user)):
    """
    Joriy foydalanuvchining majburiy kanalga a'zoligini tekshiradi.

    WebApp ochilganda boshida bir marta chaqiriladi. A'zo bo'lmasa, frontend
    "kanalga a'zo bo'ling" ekranini ko'rsatadi.

    Qaytaradi: {subscribed: bool, channel_username, channel_url}
    """
    subscribed = await is_user_subscribed(user["telegram_id"])
    _admin_uname = ADMIN_CONTACT_USERNAME.lstrip("@")
    return {
        "subscribed": subscribed,
        "channel_username": REQUIRED_CHANNEL_USERNAME,
        "channel_url": REQUIRED_CHANNEL_URL,
        "admin_contact_username": "@" + _admin_uname,
        "admin_contact_url": "https://t.me/" + _admin_uname,
    }


# ============ GET /leagues ============

@app.get("/leagues")
def list_leagues():
    """
    Barcha ligalarni va ularning to'lganlik holatini qaytaradi.

    Ketma-ket ochilish: ligalar seed (id) tartibida ochiladi. Liga "is_locked"
    (navbatda yopiq) bo'ladi, agar undan OLDINGI (kichikroq id) ligalardan biri
    hali to'lmagan bo'lsa. Ya'ni faqat birinchi to'lmagan liga (va undan oldingi
    to'lganlar) ro'yxatga ochiq; keyingilari to'lmaguncha yopiq qoladi.
    """
    leagues = get_all_leagues()  # id (seed) tartibida
    result = []
    prev_all_full = True  # undan oldingi barcha ligalar to'lganmi
    for league in leagues:
        current_count = count_league_players(league["id"])
        is_full = current_count >= league["max_players"]
        has_draw = ("draw_date" in league.keys()) and (league["draw_date"] is not None)
        # Liga yopiq, agar undan oldingilardan biri to'lmagan bo'lsa
        is_locked = not prev_all_full
        result.append({
            "id": league["id"],
            "name": league["name"],
            "status": league["status"],
            "max_players": league["max_players"],
            "current_players": current_count,
            "is_full": is_full,
            "has_draw_date": has_draw,
            "is_locked": is_locked,
        })
        # Keyingi liga uchun: shu liga ham to'lган bo'lsagina ochiq bo'ladi
        prev_all_full = prev_all_full and is_full
    return result


# ============ GET /leagues/{league_id}/clubs ============

@app.get("/leagues/{league_id}/clubs")
def get_league_taken_clubs(league_id: int):
    """Shu ligada allaqachon band qilingan klub nomlari ro'yxatini qaytaradi."""
    league = get_league_by_id(league_id)
    if league is None:
        raise HTTPException(status_code=404, detail="league_not_found")
    return {"taken_clubs": get_taken_clubs(league_id)}


# ============ GET /rating/{league_id} ============

@app.get("/rating/{league_id}")
def get_league_rating(league_id: int):
    """Liga uchun to'liq reyting jadvalini qaytaradi (ball, gol farqi bo'yicha saralangan)."""
    league = get_league_by_id(league_id)
    if league is None:
        raise HTTPException(status_code=404, detail="Liga topilmadi")

    rating = calculate_league_rating(league_id)
    return {"league": league["name"], "rating": rating}


# ============ GET /profile ============

@app.get("/profile")
def get_profile(user: dict = Depends(get_authenticated_user)):
    """Joriy foydalanuvchining profil ma'lumotlarini qaytaradi."""
    registration = get_user_registration(user["id"])
    position_info = None

    if registration is not None:
        position_info = get_player_position(registration["league_id"], user["id"])

    return {
        "user_id": user["id"],
        "nickname": user["nickname"],
        "language": user["language"],
        "league_id": registration["league_id"] if registration else None,
        "club_name": registration["club_name"] if registration else None,
        "rating": position_info,
    }


# ============ GET /players/{user_id}/profile ============

@app.get("/players/{user_id}/profile")
def get_player_profile(user_id: int, viewer: dict = Depends(get_authenticated_user)):
    """
    Boshqa bir o'yinchining ommaviy profilini qaytaradi (reyting jadvalidan bosilganda).

    Joriy foydalanuvchining avtorizatsiyasini talab qiladi, lekin har qanday
    ro'yxatdan o'tgan foydalanuvchi boshqa o'yinchining profilini ko'ra oladi.
    Xato holatlari: user_not_found → 404
    """
    target = get_user_by_id(user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="user_not_found")

    registration = get_user_registration(user_id)
    position_info = None
    if registration is not None:
        position_info = get_player_position(registration["league_id"], user_id)

    return {
        "user_id": target["id"],
        "nickname": target["nickname"],
        "username": target["username"],
        "league_id": registration["league_id"] if registration else None,
        "club_name": registration["club_name"] if registration else None,
        "rating": position_info,
        "matches": _annotate_matches_locked(get_user_matches(user_id)),
    }


# ============ GET /players/{user_id}/photo ============

# Rasm keshi: user_id -> (expires_at, cached_at, content|None, media_type).
# content=None → "rasm yo'q" (negativ kesh, qisqa muddat).
_photo_cache: dict[int, tuple[float, float, bytes | None, str]] = {}


def _photo_cache_put(user_id: int, content: bytes | None, media_type: str) -> None:
    """Rasm/negativ natijani keshga yozadi; hajm chegarasidan oshsa tozalaydi."""
    now = time.time()
    ttl = PHOTO_CACHE_TTL_SECONDS if content is not None else PHOTO_CACHE_NEGATIVE_TTL_SECONDS
    _photo_cache[user_id] = (now + ttl, now, content, media_type)
    if len(_photo_cache) > PHOTO_CACHE_MAX_ENTRIES:
        # Avval muddati o'tganlarni tashlaymiz, yetmasa eng eskilarini
        expired = [k for k, v in _photo_cache.items() if v[0] <= now]
        for k in expired:
            _photo_cache.pop(k, None)
        while len(_photo_cache) > PHOTO_CACHE_MAX_ENTRIES:
            oldest = min(_photo_cache, key=lambda k: _photo_cache[k][1])
            _photo_cache.pop(oldest, None)


@app.get("/players/{user_id}/photo")
async def get_player_photo(user_id: int):
    """
    O'yinchining Telegram profil rasmini qaytaradi (bot token orqali, proxy).

    Auth talab qilinmaydi — bu <img src> orqali yuklanadi (header yuborib bo'lmaydi)
    va rasm allaqachon ommaviy profil (reyting jadvalida ko'rinadigan o'yinchi)
    qismi. Bot token URL'da oshkor bo'lmasligi uchun rasm baytlari server orqali
    uzatiladi. Rasm yo'q, maxfiy yoki xato bo'lsa — 404 (frontend ism harfini ko'rsatadi).
    """
    # AUDIT A4: kesh — har chaqiriqda Telegram API'ga 3 tagacha so'rov ketardi,
    # begona skript bot tokenining Telegram limitini yeb qo'yishi mumkin edi.
    # Topilgan rasm PHOTO_CACHE_TTL_SECONDS, "rasm yo'q" holati esa qisqa
    # (NEGATIVE_TTL) muddatga keshlanadi.
    now = time.time()
    cached = _photo_cache.get(user_id)
    if cached is not None and cached[0] > now:
        _, _, content, media_type = cached
        if content is None:
            raise HTTPException(status_code=404, detail="no_photo")
        return Response(content=content, media_type=media_type)

    target = get_user_by_id(user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="user_not_found")

    telegram_id = target["telegram_id"]
    base = f"https://api.telegram.org/bot{BOT_TOKEN}"

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            # 1) Profil rasmlari ro'yxati
            r1 = await client.get(
                f"{base}/getUserProfilePhotos",
                params={"user_id": telegram_id, "limit": 1},
            )
            data1 = r1.json()
            photos = data1.get("result", {}).get("photos", [])
            if not photos or not photos[0]:
                _photo_cache_put(user_id, None, "")
                raise HTTPException(status_code=404, detail="no_photo")

            # Eng kichik o'lchamni olamiz (avatar uchun yetarli, tez yuklanadi)
            file_id = photos[0][0]["file_id"]

            # 2) file_path olish
            r2 = await client.get(f"{base}/getFile", params={"file_id": file_id})
            file_path = r2.json().get("result", {}).get("file_path")
            if not file_path:
                _photo_cache_put(user_id, None, "")
                raise HTTPException(status_code=404, detail="no_file_path")

            # 3) Haqiqiy rasmni yuklab olish
            r3 = await client.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}")
            if r3.status_code != 200:
                _photo_cache_put(user_id, None, "")
                raise HTTPException(status_code=404, detail="photo_fetch_failed")

            media_type = r3.headers.get("content-type", "image/jpeg")
            _photo_cache_put(user_id, r3.content, media_type)
            return Response(content=r3.content, media_type=media_type)

    except HTTPException:
        raise
    except Exception:
        _photo_cache_put(user_id, None, "")
        raise HTTPException(status_code=404, detail="photo_unavailable")


# ============ GET /prizes/stars ============
# MUHIM: /prizes/{league_id} dan OLDIN e'lon qilinadi (FastAPI tartib bo'yicha
# moslashtiradi — aks holda "stars" league_id sifatida 422 berardi).

@app.get("/prizes/stars")
def prizes_stars():
    """
    Kubok yulduzchalari (2026-07-16): sovrin yutganlar useri yonidagi ★ soni.
    Faqat kuboklar (league_cup/wc_cup/cl_cup); oltin to'p va butsa mustasno.
    Hammaga ochiq — yulduzcha barcha ishtirokchilarga ko'rinishi kerak.
    """
    from prize_stars import get_cup_star_counts
    return get_cup_star_counts()


# ============ GET /prizes/{league_id} ============

@app.get("/prizes/{league_id}")
def get_prizes(league_id: int):
    """Liga uchun sovrin holatini qaytaradi: eng ko'p gol urgan va joriy lider."""
    league = get_league_by_id(league_id)
    if league is None:
        raise HTTPException(status_code=404, detail="Liga topilmadi")

    # Oltin butsa va Oltin to'p — IKKALASI HAM barcha ligalar bo'yicha umumiy hisoblanadi
    # (liga tanlansa o'zgarmaydi). Bir ishtirokchining (user_id) barcha ligalardagi
    # natijalari yig'iladi.
    overall = {}
    for lg in get_all_leagues():
        for p in calculate_league_rating(lg["id"]):
            agg = overall.get(p["user_id"])
            if agg is None:
                overall[p["user_id"]] = {
                    "user_id": p["user_id"],
                    "nickname": p["nickname"],
                    "username": p["username"],
                    "club_name": p["club_name"],
                    "points": p["points"],
                    "goals_for": p["goals_for"],
                    "goal_difference": p["goal_difference"],
                }
            else:
                agg["points"] += p["points"]
                agg["goals_for"] += p["goals_for"]
                agg["goal_difference"] += p["goal_difference"]

    # Oltin butsa: umumiy to'purarlar jadvalidagi 1-o'rin (eng ko'p gol urgan).
    # Tartib: gollar (goals_for) > achko (points) > gol farqi (goal_difference).
    top_scorer = max(
        overall.values(),
        key=lambda p: (p["goals_for"], p["points"], p["goal_difference"]),
        default=None,
    ) if overall else None

    # Oltin to'p: umumiy reyting jadvalidagi 1-o'rin (eng ko'p achko yiqqan).
    # Tartib: achko (points) > urilgan gollar (goals_for) > gol farqi (goal_difference).
    leader = max(
        overall.values(),
        key=lambda p: (p["points"], p["goals_for"], p["goal_difference"]),
        default=None,
    ) if overall else None

    # Liga Kubogi: SHU liganing reyting jadvalidagi 1-o'rin (faqat tanlangan liga).
    league_rating = calculate_league_rating(league_id)
    league_champion = league_rating[0] if league_rating else None

    return {
        "league": league["name"],
        "top_scorer": top_scorer,
        "current_leader": leader,
        "league_champion": league_champion,
    }


# ============ POST /register ============

@app.post("/register")
def register(league_id: int, club_name: str | None = None, user: dict = Depends(get_authenticated_user)):
    """
    Foydalanuvchini ligaga ro'yxatdan o'tkazadi.

    Ketma-ket ochilish qoidasi: agar bu ligadan OLDINGI (kichikroq id) ligalardan
    biri hali to'lmagan bo'lsa, ro'yxatdan o'tib bo'lmaydi (league_locked).

    Query param: league_id (int), club_name (str, ixtiyoriy)
    Xato holatlari: already_registered, league_full, league_not_found, club_taken,
                    league_locked → 400
    """
    # Ketma-ket ochilish — yopiq (navbati kelmagan) ligaga ro'yxat taqiqlanadi
    if _is_league_locked(league_id):
        raise HTTPException(status_code=400, detail="league_locked")

    success, reason = register_user_to_league(user["id"], league_id, club_name)
    if not success:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": "ok", "league_id": league_id}


def _is_league_locked(league_id: int) -> bool:
    """
    Liga "navbatda yopiq"mi: undan OLDINGI (kichikroq id) ligalardan biri hali
    to'lmagan bo'lsa True. list_leagues bilan bir xil mantiq (backend himoyasi).
    """
    for league in get_all_leagues():  # id (seed) tartibida
        if league["id"] == league_id:
            return False  # bu liga — birinchi to'lmagan yoki to'lgan, ochiq
        # undan oldingi liga to'lmagan bo'lsa, bu liga yopiq
        if count_league_players(league["id"]) < league["max_players"]:
            return True
    return False


# ============ WORLD CUP (Jahon Chempionati) — liga'dan alohida ============

@app.get("/wc/groups/{group_letter}/teams")
def wc_group_taken_teams(group_letter: str):
    """Shu World Cup guruhida band qilingan jamoa nomlari ro'yxati (auth shart emas)."""
    from wc_data import wc_is_valid_group, WC_TEAMS_PER_GROUP
    if not wc_is_valid_group(group_letter):
        raise HTTPException(status_code=404, detail="wc_invalid_group")
    return {
        "taken_teams": wc_get_taken_teams(group_letter),
        "count": wc_count_group_players(group_letter),
        "max": WC_TEAMS_PER_GROUP,
    }


@app.get("/wc/profile")
def wc_get_profile(user: dict = Depends(get_authenticated_user)):
    """
    Foydalanuvchining World Cup ro'yxati (group_letter, team_name) + guruh
    reytingidagi statistikasi (o'rin/g'alaba/durang/mag'lubiyat). Ro'yxatdan
    o'tmagan bo'lsa registered=False.
    """
    reg = wc_get_user_registration(user["id"])
    if reg is None:
        return {
            "registered": False, "group_letter": None, "team_name": None,
            "user_id": user["id"], "rating": None,
        }
    from wc_rating import get_wc_player_position
    pos = get_wc_player_position(reg["group_letter"], user["id"])
    return {
        "registered": True,
        "group_letter": reg["group_letter"],
        "team_name": reg["team_name"],
        "user_id": user["id"],
        "rating": pos,  # {position, wins, draws, losses, ...} yoki None
    }


@app.post("/wc/register")
def wc_register(group_letter: str, team_name: str, user: dict = Depends(get_authenticated_user)):
    """
    Foydalanuvchini World Cup'ga ro'yxatdan o'tkazadi (liga'dan mustaqil).

    Query param: group_letter (str "A".."L"), team_name (str)
    Xato holatlari: wc_already_registered, wc_group_full, wc_invalid_group,
                    wc_invalid_team, wc_team_taken → 400
    """
    success, reason = wc_register_user(user["id"], group_letter, team_name)
    if not success:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": "ok", "group_letter": group_letter, "team_name": team_name}


# ============ GET /wc/players/{user_id}/profile ============

@app.get("/wc/players/{user_id}/profile")
def wc_get_player_profile(user_id: int, viewer: dict = Depends(get_authenticated_user)):
    """
    Boshqa bir o'yinchining World Cup ommaviy profilini qaytaradi (WC reyting
    jadvalidan bosilganda). Liga'dagi /players/{user_id}/profile naqshiga mos,
    lekin WC ma'lumotlari bilan (guruh/jamoa/WC statistika/WC o'yinlari).

    Joriy foydalanuvchining avtorizatsiyasini talab qiladi; har qanday kirgan
    foydalanuvchi boshqa o'yinchining WC profilini ko'ra oladi.
    Xato holatlari: user_not_found → 404
    """
    target = get_user_by_id(user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="user_not_found")

    import queries
    reg = wc_get_user_registration(user_id)
    position_info = None
    if reg is not None:
        from wc_rating import get_wc_player_position
        position_info = get_wc_player_position(reg["group_letter"], user_id)

    return {
        "user_id": target["id"],
        "nickname": target["nickname"],
        "username": target["username"],
        "group_letter": reg["group_letter"] if reg else None,
        "team_name": reg["team_name"] if reg else None,
        "rating": position_info,
        "matches": _wc_annotate_locked(wc_get_user_matches(user_id)),
        "playoff_matches": queries.wc_playoff_get_user_matches(user_id),
    }


def _wc_annotate_locked(matches: list[dict]) -> list[dict]:
    """Har WC match'ga 'is_locked' (matchday hali ochilmaganmi) qo'shadi."""
    open_cache: dict[str, int] = {}
    for m in matches:
        g = m.get("group_letter")
        if g not in open_cache:
            open_cache[g] = wc_get_open_matchday(g)
        m["is_locked"] = m.get("matchday", 0) > open_cache[g]
    return matches


@app.get("/wc/matches/my")
def wc_my_matches(user: dict = Depends(get_authenticated_user)):
    """Foydalanuvchining World Cup o'yinlari (is_locked bilan)."""
    matches = wc_get_user_matches(user["id"])
    return {"matches": _wc_annotate_locked(matches)}


@app.get("/wc/rating/{group_letter}")
def wc_rating(group_letter: str):
    """World Cup guruh reyting jadvali (ball, gol farqi bo'yicha saralangan)."""
    from wc_data import wc_is_valid_group
    if not wc_is_valid_group(group_letter):
        raise HTTPException(status_code=404, detail="wc_invalid_group")
    from wc_rating import calculate_wc_group_rating
    return {"group": group_letter, "rating": calculate_wc_group_rating(group_letter)}


@app.get("/wc/top-scorers")
def wc_top_scorers():
    """World Cup to'p urarlari — barcha guruhlardan eng ko'p gol urganlar."""
    from wc_rating import calculate_wc_top_scorers
    return {"scorers": calculate_wc_top_scorers()}


@app.post("/wc/match/submit-result")
def wc_submit_result(
    match_id: int,
    score1: int,
    score2: int,
    user: dict = Depends(get_authenticated_user),
):
    """
    World Cup match natijasini kiritadi.

    Query params: match_id, score1, score2
    Xato holatlari: score_negative, match_not_found, not_participant,
                    already_submitted, matchday_locked → 400
    """
    validate_scores(score1, score2)
    success, reason = wc_submit_match_result(match_id, score1, score2, user["id"])
    if not success:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": "ok", "match_id": match_id, "reason": reason}


@app.post("/wc/match/confirm")
def wc_confirm(
    match_id: int,
    action: str,
    user: dict = Depends(get_authenticated_user),
):
    """
    World Cup natijani tasdiqlaydi yoki rad etadi.

    Query params: match_id, action ("confirm" yoki "reject")
    Xato holatlari: match_not_found, not_opponent, wrong_status, invalid_action → 400
    """
    success, reason = wc_confirm_or_reject_match(match_id, action, user["id"])
    if not success:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": "ok", "match_id": match_id, "action": action}


# ============ POST /wc/admin/match/fix-confirmed ============

@app.post("/wc/admin/match/fix-confirmed")
def wc_admin_fix_confirmed(
    match_id: int,
    score1: int,
    score2: int,
    admin: dict = Depends(get_authenticated_wc_admin),
):
    """
    WC admin (bosh yoki WC scope admin) allaqachon 'confirmed' bo'lgan WC
    matchning noto'g'ri natijasini qo'lda tuzatadi (status o'zgarmaydi).

    Query params: match_id, score1, score2
    Xato holatlari: match_not_found, wrong_status → 400
    """
    validate_scores(score1, score2)  # AUDIT B2: admin xatosi ham reytingni buzmasin
    success, reason = wc_admin_fix_confirmed_match(match_id, score1, score2)
    if not success:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": "ok", "match_id": match_id}


# ============ WC CHAT ============

@app.get("/wc/matches/{match_id}/messages")
def wc_get_match_messages(match_id: int, is_playoff: int = 0, user: dict = Depends(get_authenticated_user)):
    """WC aktiv match xabarlari (vaqt tartibida). is_playoff=1 → play-off. Access yo'q → 403."""
    is_playoff = 1 if is_playoff else 0  # AUDIT B8: faqat 0/1
    messages = wc_get_chat_messages(match_id, user["telegram_id"], is_playoff)
    if messages is None:
        raise HTTPException(status_code=403, detail="chat_no_access")
    return {"match_id": match_id, "messages": messages}


@app.post("/wc/matches/{match_id}/messages")
async def wc_post_match_message(
    match_id: int,
    text: str = Body(..., embed=True),
    is_playoff: int = 0,
    user: dict = Depends(get_authenticated_user),
):
    """WC aktiv match raqibiga xabar yuboradi. Body: {"text": "..."}. is_playoff=1 → play-off."""
    is_playoff = 1 if is_playoff else 0  # AUDIT B8: faqat 0/1
    ok, reason, notify = wc_send_chat_message(match_id, user["telegram_id"], text, is_playoff)
    if not ok:
        if reason == "empty":
            raise HTTPException(status_code=400, detail="empty")
        raise HTTPException(status_code=403, detail="chat_no_access")

    if notify is not None:
        try:
            recipient = get_user_by_telegram_id(notify["recipient_telegram_id"])
            lang = recipient.get("language") if recipient else None
            await notify_user(
                notify["recipient_telegram_id"],
                "notify_chat_message",
                lang,
                open_button_key="btn_open_app",
                mode=t("mode_name_worldcup", lang),
                preview=notify["text_preview"],
            )
        except Exception as exc:
            # Xabar DB'ga yozildi — bot bildirishnomasi yiqilsa javobni buzmaymiz,
            # lekin log qoldiramiz (qoida #44)
            logger.warning("Chat bot bildirishnomasi yuborilmadi: %s", exc)

    return {"ok": True}


@app.get("/wc/matches/unread")
def wc_get_unread_counts(user: dict = Depends(get_authenticated_user)):
    """WC o'qilmagan chat xabarlari soni."""
    return wc_count_unread_messages(user["telegram_id"])


@app.post("/wc/matches/{match_id}/typing")
def wc_post_typing(match_id: int, is_playoff: int = 0, user: dict = Depends(get_authenticated_user)):
    """WC chatda 'yozmoqda' signali. is_playoff=1 → play-off."""
    is_playoff = 1 if is_playoff else 0  # AUDIT B8: faqat 0/1
    ok = wc_set_typing(match_id, user["telegram_id"], is_playoff)
    if not ok:
        raise HTTPException(status_code=403, detail="chat_no_access")
    return {"ok": True}


@app.get("/wc/matches/{match_id}/state")
def wc_get_match_state(match_id: int, is_playoff: int = 0, user: dict = Depends(get_authenticated_user)):
    """WC raqibning chat holati (online / yozmoqda / oxirgi ko'rinish). is_playoff=1 → play-off."""
    is_playoff = 1 if is_playoff else 0  # AUDIT B8: faqat 0/1
    state = wc_get_chat_state(match_id, user["telegram_id"], is_playoff)
    if state is None:
        raise HTTPException(status_code=403, detail="chat_no_access")
    return state


# ============ GET /wc/admin/players ============

@app.get("/wc/admin/players")
def wc_admin_list_players(admin: dict = Depends(get_authenticated_super_admin)):
    """WC ishtirokchilari ro'yxati (faqat bosh admin — o'yinchi chiqarish uchun)."""
    return {"players": wc_get_all_players()}


# ============ DELETE /wc/admin/players/{user_id} ============

@app.delete("/wc/admin/players/{user_id}")
def wc_admin_delete_player(user_id: int, admin: dict = Depends(get_authenticated_super_admin)):
    """
    WC o'yinchini ro'yxatdan chiqaradi (faqat bosh admin) — FAQAT guruh
    hali to'lmagan (o'yinlar yaratilmagan) bo'lsa.

    Xato holatlari: not_registered, group_started → 400
    """
    success, reason = wc_admin_remove_player(user_id)
    if not success:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": "ok", "user_id": user_id}


# ============ POST /wc/admin/match/set-score ============

@app.get("/wc/admin/match/{match_id}/info")
def wc_admin_match_info(
    match_id: int,
    is_playoff: int = 0,
    admin: dict = Depends(get_authenticated_wc_admin),
):
    """
    JCH admin formasi uchun jonli ma'lumot (2026-07-04): Match ID kiritilganda
    frontend qaysi o'yin ekanini (jamoalar -> bayroqlar) ko'rsatadi.
    is_playoff=1 bo'lsa setka o'yini (wc_playoff_matches), aks holda guruh.
    Jamoa nomi WC ro'yxatidan (wc_registrations) olinadi.
    """
    is_playoff = 1 if is_playoff else 0

    # MUHIM: `queries` moduli api.py da global import qilinmagan (faqat `from
    # queries import (...)` bilan ayrim funksiyalar olingan). Shuning uchun
    # bu yerda LOKAL import shart — aks holda `queries.get_connection()`
    # NameError beradi va endpoint 500 qaytaradi (2026-07-13 xatosi shu edi).
    import queries

    # Jamoa nomlari bracket bilan BIR XIL usulda — wc_registrations JOIN
    # (guruh ham, play-off ham; registration o'chirilgan chekka holatda NULL).
    #
    # MUHIM (2026-07-13): admin checkbox'ni noto'g'ri qo'ysa (guruh o'yiniga
    # "Play-off" belgilansa yoki aksincha) ilgari 404 qaytar edi va formada
    # bayroq o'rniga "?" chiqardi. Endi tanlangan jadvalda topilmasa IKKINCHI
    # jadval ham tekshiriladi va javobda haqiqiy is_playoff qaytariladi —
    # bayroqlar baribir ko'rinadi.
    def _fetch(table: str):
        conn = queries.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                f"""
                SELECT p.id, p.player1_id, p.player2_id, p.score1, p.score2, p.status,
                       r1.team_name AS team1, r2.team_name AS team2
                FROM {table} p
                LEFT JOIN wc_registrations r1 ON r1.user_id = p.player1_id
                LEFT JOIN wc_registrations r2 ON r2.user_id = p.player2_id
                WHERE p.id = ?
                """,
                (match_id,),
            )
            return cursor.fetchone()
        finally:
            conn.close()

    primary = "wc_playoff_matches" if is_playoff else "wc_matches"
    fallback = "wc_matches" if is_playoff else "wc_playoff_matches"

    row = _fetch(primary)
    if row is None:
        row = _fetch(fallback)
        if row is not None:
            is_playoff = 0 if is_playoff else 1   # aslida boshqa turdagi o'yin ekan

    if row is None:
        raise HTTPException(status_code=404, detail="match_not_found")

    return {
        "id": row["id"],
        "team1": row["team1"],
        "team2": row["team2"],
        "score1": row["score1"],
        "score2": row["score2"],
        "status": row["status"],
        "is_playoff": is_playoff,
    }


@app.post("/wc/admin/match/set-score")
def wc_admin_match_set_score(
    match_id: int,
    score1: int,
    score2: int,
    is_playoff: int = 0,
    admin: dict = Depends(get_authenticated_wc_admin),
):
    """
    WC admin (bosh yoki biriktirilgan) har qanday holatdagi WC matchning
    natijasini to'g'ri songa o'zgartiradi (status → confirmed). O'yinchilar
    o'ynamasdan noto'g'ri kiritgan natijani tuzatish uchun.

    Query params: match_id, score1, score2, is_playoff (0=guruh, 1=play-off)
    Xato: match_not_found → 400
    """
    validate_scores(score1, score2)  # AUDIT B2
    is_playoff = 1 if is_playoff else 0  # AUDIT B8: faqat 0/1
    success, reason = wc_admin_set_score(match_id, score1, score2, is_playoff)
    if not success:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": "ok", "match_id": match_id}


# ============ POST /wc/admin/match/reset ============

@app.post("/wc/admin/match/reset")
def wc_admin_match_reset(
    match_id: int,
    is_playoff: int = 0,
    admin: dict = Depends(get_authenticated_wc_admin),
):
    """
    WC admin (bosh yoki biriktirilgan) noto'g'ri kiritilgan WC natijani BEKOR
    qiladi: o'yin qayta 'pending' (— : —) holatiga qaytadi, o'yinchilar
    qaytadan kiritishi mumkin.

    Query param: match_id, is_playoff (0=guruh, 1=play-off)
    Xato: match_not_found, already_pending → 400
    """
    is_playoff = 1 if is_playoff else 0  # AUDIT B8: faqat 0/1
    success, reason = wc_admin_reset_match(match_id, is_playoff)
    if not success:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": "ok", "match_id": match_id}


@app.get("/wc/admin/match/pending")
def wc_admin_pending_list(admin: dict = Depends(get_authenticated_wc_admin)):
    """Katta hisob (admin_pending) tufayli admin tasdig'ini kutayotgan WC guruh o'yinlari."""
    return {"matches": wc_get_admin_pending_matches()}


@app.post("/wc/admin/match/pending/resolve")
def wc_admin_pending_resolve(
    match_id: int,
    action: str,
    admin: dict = Depends(get_authenticated_wc_admin),
):
    """
    WC admin katta hisobli guruh o'yinini tasdiqlaydi (confirm) yoki rad etadi (reject).
    Query params: match_id, action ('confirm'|'reject').
    """
    success, reason = wc_admin_resolve_pending(match_id, action)
    if not success:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": "ok"}


# ============ POST /wc/admin/fix-schedules ============

@app.post("/wc/admin/fix-schedules")
def wc_admin_fix_schedules(admin: dict = Depends(get_authenticated_super_admin)):
    """
    Bosh admin: to'lgan (4 jamoa) lekin o'yinlari yaratilmagan WC guruhlarini
    topib, jadval generatsiya qiladi (bug tuzatish). Mavjud o'yinlarga tegmaydi.

    Qaytaradi: {fixed: [...], skipped_not_full: [...], already_ok: [...]}
    """
    result = wc_fix_missing_schedules()
    return {"status": "ok", **result}


# ============ POST /wc/admin/start-today ============

@app.post("/wc/admin/start-today")
def wc_admin_start_today(admin: dict = Depends(get_authenticated_super_admin)):
    """
    Bosh admin: barcha o'yinli WC guruhlarga BUGUNDAN start beradi (draw_date =
    hozir). Matchday-lock bugundan: bugun matchday 1-2 ochiq, ertaga 23:30 da
    matchday 3 ochiladi (liga kabi).

    Qaytaradi: {started: [...]}
    """
    result = wc_start_all_today()
    return {"status": "ok", **result}


# ============ WC PLAY-OFF ============

@app.get("/wc/playoff/status")
def wc_playoff_status():
    """Play-off holati: boshlanganmi va 32 jamoa tayyormi (admin tugmasi uchun)."""
    import queries
    from wc_playoff import wc_get_qualified_teams
    started = queries.wc_playoff_is_started()
    result = {"started": started}
    if not started:
        q = wc_get_qualified_teams()
        result["ready"] = q["ready"]
        result["reason"] = q["reason"]
    return result


@app.post("/wc/admin/playoff/start")
def wc_admin_playoff_start(admin: dict = Depends(get_authenticated_super_admin)):
    """
    Bosh admin play-off'ni boshlaydi: 32 jamoani saralaydi va bracketni yaratadi.
    Barcha 12 guruh tugagan bo'lishi shart.

    Xato: already_started, not_ready, group_X_incomplete → 400
    """
    from wc_playoff import wc_playoff_start
    result = wc_playoff_start()
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["reason"])
    return {"status": "ok", "created": result["created"]}


@app.get("/wc/playoff/my-matches")
def wc_playoff_my_matches(user: dict = Depends(get_authenticated_user)):
    """O'yinchining play-off matchlari (ochiq bosqichlargacha, ketma-ket)."""
    import queries
    matches = queries.wc_playoff_get_user_matches(user["id"])
    return {"matches": matches, "open_round_index": queries.wc_playoff_get_open_round_index()}


@app.get("/wc/playoff/bracket")
def wc_playoff_bracket():
    """To'liq play-off setkasi (barcha bosqichlar, o'yinchi nomlari bilan)."""
    import queries
    if not queries.wc_playoff_is_started():
        return {"started": False, "rounds": {}}
    conn = queries.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT p.id, p.round, p.position, p.player1_id, p.player2_id,
               p.score1, p.score2, p.status,
               u1.nickname AS p1_nick, u1.username AS p1_user, r1.team_name AS p1_team,
               u2.nickname AS p2_nick, u2.username AS p2_user, r2.team_name AS p2_team
        FROM wc_playoff_matches p
        LEFT JOIN users u1 ON u1.id = p.player1_id
        LEFT JOIN users u2 ON u2.id = p.player2_id
        LEFT JOIN wc_registrations r1 ON r1.user_id = p.player1_id
        LEFT JOIN wc_registrations r2 ON r2.user_id = p.player2_id
        ORDER BY p.position
        """
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    # Bosqichlarga ajratamiz
    rounds = {}
    for m in rows:
        rounds.setdefault(m["round"], []).append(m)
    return {"started": True, "rounds": rounds, "open_round_index": queries.wc_playoff_get_open_round_index()}


@app.get("/wc/playoff/champion")
def wc_playoff_champion():
    """Play-off chempioni (final g'olibi). Final tugamagan bo'lsa champion=null."""
    import queries
    champion = queries.wc_playoff_get_champion()
    return {"champion": champion}


# ============ SOVRINLAR (mavsum) ============

@app.get("/season/current")
def season_current():
    """
    Joriy mavsum raqamlari. Liga va WC mavsumi ALOHIDA.
    `season` — orqaga moslik uchun liga mavsumi (eski frontend uni o'qiydi).
    """
    from season_prizes import get_league_season, get_wc_season
    league = get_league_season()
    return {"season": league, "league_season": league, "wc_season": get_wc_season()}


@app.get("/season/prizes/preview")
def season_prizes_preview(admin: dict = Depends(get_authenticated_super_admin)):
    """Joriy sovrin egalarini oldindan ko'rsatadi (SAQLAMAYDI, liga+WC). Bosh admin."""
    from season_prizes import calculate_season_prizes, get_league_season, get_wc_season
    return {
        "league_season": get_league_season(),
        "wc_season": get_wc_season(),
        "prizes": calculate_season_prizes(),
    }


@app.post("/season/finalize")
def season_finalize(admin: dict = Depends(get_authenticated_super_admin)):
    """
    Bosh admin LIGA mavsumini yakunlaydi: liga sovrinlari (oltin to'p/butsa,
    liga kubogi) hisoblanib saqlanadi, liga mavsum raqami oshadi. Qaytarib bo'lmaydi.
    (WC mavsumi bundan mustaqil — /season/wc/finalize.)
    """
    from season_prizes import finalize_league_season
    result = finalize_league_season()
    if result.get("already"):
        # AUDIT A3: tugma takror bosildi — dublikat yozilmadi, mavsum oshmadi
        raise HTTPException(status_code=400, detail="already_finalized")
    return {"status": "ok", "season": result["season"], "counts": result["counts"]}


@app.post("/season/wc/finalize")
def season_wc_finalize(admin: dict = Depends(get_authenticated_super_admin)):
    """
    Bosh admin WC mavsumini yakunlaydi: play-off chempioni (WC kubogi)
    saqlanadi, WC mavsum raqami oshadi. Qaytarib bo'lmaydi.
    (Liga mavsumidan mustaqil.)
    """
    from season_prizes import finalize_wc_season
    result = finalize_wc_season()
    if result.get("already"):
        raise HTTPException(status_code=400, detail="already_finalized")
    return {"status": "ok", "season": result["season"], "counts": result["counts"]}


@app.get("/users/{user_id}/prizes")
def user_prizes(user_id: int):
    """Foydalanuvchining barcha sovrinlari (mavsum bo'yicha)."""
    from season_prizes import get_user_prizes
    return {"prizes": get_user_prizes(user_id)}



@app.get("/season/celebration")
def season_celebration(user: dict = Depends(get_authenticated_user)):
    """
    Mavsum yakuni tabrik oynasi (bir martalik).
    show=True bo'lsa frontend modal ko'rsatadi (sovrindorga salyut,
    boshqalarga sovrindorlar ro'yxati).
    """
    from season_celebration import get_celebration
    return get_celebration(user["telegram_id"])


@app.post("/season/celebration/seen")
def season_celebration_seen(user: dict = Depends(get_authenticated_user)):
    """Tabrik oynasi ko'rildi — qayta ko'rsatilmaydi (idempotent)."""
    from season_celebration import mark_celebration_seen
    return mark_celebration_seen(user["telegram_id"])


@app.get("/cl/qualifiers")
def cl_qualifiers(user: dict = Depends(get_authenticated_user)):
    """
    Chempionlar ligasi kvalifikantlari (oxirgi yakunlangan mavsum bo'yicha).
    me_qualified — so'rovchi ishtirokchi ChL'ga chiqqanmi.
    """
    from cl_qualification import get_cl_qualifiers, is_cl_qualifier
    data = get_cl_qualifiers()
    data["me_qualified"] = is_cl_qualifier(user["telegram_id"], data["from_season"])
    return data


@app.get("/cl/groups")
def cl_groups(user: dict = Depends(get_authenticated_user)):
    """
    ChL guruhlari va ishtirokchilari. Avval sinxron (kvalifikant yangi mavsumda
    ro'yxatdan o'tgan bo'lsa — avtomatik qo'shiladi), so'ng ro'yxat qaytadi.
    me_participant — so'rovchi ChL ishtirokchisimi.
    """
    from cl_core import cl_sync_participants, cl_get_groups
    cl_sync_participants()
    data = cl_get_groups()
    data["me_participant"] = any(
        p["telegram_id"] == user["telegram_id"] for p in data["participants"]
    )
    return data


@app.get("/cl/rating/{group_number}")
def cl_rating(group_number: int, user: dict = Depends(get_authenticated_user)):
    """ChL guruh reyting jadvali (ball > gol farqi > urilgan gol)."""
    if not 1 <= group_number <= 8:
        raise HTTPException(status_code=400, detail="invalid_group")
    from cl_core import cl_group_rating
    return {"group_number": group_number, "rating": cl_group_rating(group_number)}


@app.get("/cl/rating-all")
def cl_rating_all(user: dict = Depends(get_authenticated_user)):
    """Barcha 8 guruh reytingi birdaniga (Reyting 'Guruhlar' tabi — hammasi ketma-ket)."""
    from cl_core import cl_group_rating
    groups = []
    for n in range(1, 9):
        rows = cl_group_rating(n)
        if rows:
            groups.append({"group_number": n, "rating": rows})
    return {"groups": groups}


@app.get("/cl/participants/all")
def cl_participants_all(admin: dict = Depends(get_authenticated_super_admin)):
    """Joriy mavsumdagi barcha ChL ishtirokchilari (admin almashtirish uchun)."""
    from cl_participant_admin import cl_list_all_participants
    return {"participants": cl_list_all_participants()}


@app.get("/cl/participants/orphans")
def cl_participants_orphans(admin: dict = Depends(get_authenticated_super_admin)):
    """
    ChL ishtirokchilaridan users jadvalida MAVJUD BO'LMAGANLARINI qaytaradi
    (o'chirilgan akkountlar). Admin ularni yangi akkountga bog'lash uchun ko'radi.
    """
    from cl_participant_admin import cl_list_orphan_participants
    return {"orphans": cl_list_orphan_participants()}


@app.post("/cl/participant/reassign")
def cl_participant_reassign(
    old_user_id: int = Body(..., embed=True),
    new_telegram_id: int = Body(..., embed=True),
    admin: dict = Depends(get_authenticated_super_admin),
):
    """
    O'chirilgan akkount (old_user_id — orphans ro'yxatidan) o'rniga yangi akkountni
    bog'laydi. Eski Telegram ID kerak emas.
    Xato: new_user_not_found, nothing_to_reassign, new_already_participant → 400
    """
    from cl_participant_admin import cl_reassign_participant
    success, result = cl_reassign_participant(old_user_id, new_telegram_id)
    if not success:
        raise HTTPException(status_code=400, detail=result)
    return {"status": "ok", **result}


# ============================================================
#  ISHTIROKCHINI ALMASHTIRISH — BARCHA REJIMLAR (2026-07-16)
#  ChL naqshi liga/WC/Divizionga kengaytirildi (participant_admin.py).
#  FAQAT BOSH ADMIN. Qur'a natijasiga ta'sir qilmaydi — jadval joyida
#  qoladi, faqat player_id yangi akkountga ko'chiriladi.
# ============================================================

@app.get("/league/participants/all")
def league_participants_all(admin: dict = Depends(get_authenticated_super_admin)):
    """Barcha liga ishtirokchilari (admin almashtirish dropdown'i uchun)."""
    from participant_admin import league_list_participants
    return {"participants": league_list_participants()}


@app.post("/league/participant/reassign")
def league_participant_reassign(
    old_user_id: int = Body(..., embed=True),
    new_telegram_id: int = Body(..., embed=True),
    admin: dict = Depends(get_authenticated_super_admin),
):
    """Liga ishtirokchisini yangi akkountga bog'laydi (faqat bosh admin)."""
    from participant_admin import league_reassign_participant
    success, result = league_reassign_participant(old_user_id, new_telegram_id)
    if not success:
        raise HTTPException(status_code=400, detail=result)
    return {"status": "ok", **result}


@app.post("/league/participants/swap")
def league_participants_swap(
    user_id_a: int = Body(..., embed=True),
    user_id_b: int = Body(..., embed=True),
    admin: dict = Depends(get_authenticated_super_admin),
):
    """
    2026-07-16: Ikki liga ishtirokchisini O'ZARO almashtiradi (masalan,
    LaLiga <-> Bundesliga). Qur'aga ta'sir qilmaydi — o'rin (liga, klub,
    jadval, natijalar) joyida qoladi, faqat odamlar almashadi. Faqat bosh admin.
    """
    from participant_admin import league_swap_participants
    success, result = league_swap_participants(user_id_a, user_id_b)
    if not success:
        raise HTTPException(status_code=400, detail=result)
    return {"status": "ok", **result}


@app.get("/wc/participants/all")
def wc_participants_all(admin: dict = Depends(get_authenticated_super_admin)):
    """Barcha WC ishtirokchilari (admin almashtirish dropdown'i uchun)."""
    from participant_admin import wc_list_participants
    return {"participants": wc_list_participants()}


@app.post("/wc/admin/playoff/swap")
def wc_admin_playoff_swap(
    match_a_id: int = Body(..., embed=True),
    slot_a: int = Body(..., embed=True),
    match_b_id: int = Body(..., embed=True),
    slot_b: int = Body(..., embed=True),
    admin: dict = Depends(get_authenticated_super_admin),
):
    """
    2026-07-22: WC play-off setkada ikki pozitsiyadagi ishtirokchini O'ZARO
    almashtiradi (1/16, 1/8, ... aralash). Faqat bosh admin. Faqat natija
    kiritilmagan (pending, hisobsiz) pozitsiyalar — natija bor bo'lsa admin
    avval bekor qilishi kerak (has_result xatosi). slot: 1=player1, 2=player2.
    """
    from wc_playoff_swap import wc_playoff_swap_positions
    success, result = wc_playoff_swap_positions(match_a_id, slot_a, match_b_id, slot_b)
    if not success:
        raise HTTPException(status_code=400, detail=result)
    return {"status": "ok", **result}


@app.post("/wc/participant/reassign")
def wc_participant_reassign(
    old_user_id: int = Body(..., embed=True),
    new_telegram_id: int = Body(..., embed=True),
    admin: dict = Depends(get_authenticated_super_admin),
):
    """WC ishtirokchisini yangi akkountga bog'laydi (faqat bosh admin)."""
    from participant_admin import wc_reassign_participant
    success, result = wc_reassign_participant(old_user_id, new_telegram_id)
    if not success:
        raise HTTPException(status_code=400, detail=result)
    return {"status": "ok", **result}


@app.get("/div/participants/all")
def div_participants_all(admin: dict = Depends(get_authenticated_super_admin)):
    """Divizionda qatnashgan barcha ishtirokchilar (admin almashtirish uchun)."""
    from participant_admin import div_list_participants
    return {"participants": div_list_participants()}


@app.post("/div/participant/reassign")
def div_participant_reassign(
    old_user_id: int = Body(..., embed=True),
    new_telegram_id: int = Body(..., embed=True),
    admin: dict = Depends(get_authenticated_super_admin),
):
    """Divizion ishtirokchisini yangi akkountga bog'laydi (faqat bosh admin)."""
    from participant_admin import div_reassign_participant
    success, result = div_reassign_participant(old_user_id, new_telegram_id)
    if not success:
        raise HTTPException(status_code=400, detail=result)
    return {"status": "ok", **result}


@app.get("/cl/admin/match/{match_id}/info")
def cl_admin_match_info(match_id: int, is_playoff: int = 0,
                        admin: dict = Depends(get_authenticated_cl_admin)):
    """
    Match ID bo'yicha ChL o'yin ma'lumoti (admin 'Match ID orqali tuzatish' formasi):
    o'yinchilar, klublar (logo uchun), joriy hisob, tur. Topilmasa 404.
    2026-07-22 (talab 1): is_playoff=1 → play-off o'yini (cl_playoff_matches),
    WC namunasidek. Noto'g'ri checkbox himoyasi: tanlangan jadvalda topilmasa
    ikkinchisi ham tekshiriladi (fallback), javobda HAQIQIY is_playoff qaytadi.
    """
    from cl_admin_fix import cl_admin_get_match_info, cl_admin_po_get_match_info
    if is_playoff:
        info = cl_admin_po_get_match_info(match_id) or cl_admin_get_match_info(match_id)
    else:
        info = cl_admin_get_match_info(match_id) or cl_admin_po_get_match_info(match_id)
    if info is None:
        raise HTTPException(status_code=404, detail="match_not_found")
    info.setdefault("is_playoff", 0)   # guruh info'da bo'lmaydi — 0 qo'yamiz
    return info


@app.post("/cl/admin/match/set-result")
def cl_admin_set_result(match_id: int, score1: int, score2: int,
                        is_playoff: int = 0,
                        admin: dict = Depends(get_authenticated_cl_admin)):
    """
    Admin: ChL natijasini o'rnatish/tuzatish (istalgan statusdan -> confirmed).
    2026-07-22 (talab 1): is_playoff=1 → play-off; 2-o'yin/final bo'lsa g'olib
    keyingi bosqichga ko'chadi. Xato: match_not_found / draw_not_allowed /
    aggregate_draw_not_allowed → 400.
    """
    validate_scores(score1, score2)
    if is_playoff:
        from cl_admin_fix import cl_admin_po_set_result
        success, reason = cl_admin_po_set_result(match_id, score1, score2)
    else:
        from cl_admin_fix import cl_admin_set_result as _set
        success, reason = _set(match_id, score1, score2)
    if not success:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": "ok", "match_id": match_id}


@app.post("/cl/admin/match/cancel")
def cl_admin_match_cancel(match_id: int, is_playoff: int = 0,
                          admin: dict = Depends(get_authenticated_cl_admin)):
    """
    2026-07-16: Admin ChL natijasini BEKOR QILADI — o'yin natija kiritilmagan
    holatga (pending, hisob NULL) qaytadi. Liga/WC/Divizion bilan bir xil oqim.
    2026-07-22 (talab 1): is_playoff=1 → play-off o'yini.
    """
    if is_playoff:
        from cl_admin_fix import cl_admin_po_cancel_match
        success, reason = cl_admin_po_cancel_match(match_id)
    else:
        from cl_admin_fix import cl_admin_cancel_match
        success, reason = cl_admin_cancel_match(match_id)
    if not success:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": "ok", "match_id": match_id}


@app.post("/cl/schedule/rebuild")
def cl_schedule_rebuild(
    force: bool = Body(False, embed=True),
    admin: dict = Depends(get_authenticated_super_admin),
):
    """
    ChL kalendarini qayta quradi (ikki doira: uy + mehmon, to'g'ri tur raqamlari).
    force=True — natijalarni saqlab qayta quradi (buzuq kalendarni tuzatish uchun).
    Xato: not_drawn, results_exist, rebuild_failed → 400/500
    """
    from cl_schedule_fix import cl_rebuild_schedule
    try:
        success, result = cl_rebuild_schedule(force=force)
    except Exception as exc:
        logger.exception("ChL kalendar qayta qurishda xato")
        raise HTTPException(status_code=500, detail=f"rebuild_failed: {exc}")
    if not success:
        raise HTTPException(status_code=400, detail=result)
    return {"status": "ok", **result}


@app.post("/cl/rounds/start")
def cl_rounds_start(admin: dict = Depends(get_authenticated_super_admin)):
    """
    ChL turlarini boshlash (faqat bosh admin): 1-tur ochiladi.
    Keyingi turlar har kuni 23:30 (Toshkent) da avtomatik ochiladi (cl_rounds.cl_tick).
    Xato: not_drawn, already_started → 400
    """
    from cl_rounds import cl_start_rounds
    success, result = cl_start_rounds()
    if not success:
        raise HTTPException(status_code=400, detail=result)
    return {"status": "ok", **result}


@app.get("/cl/scorers")
def cl_scorers(user: dict = Depends(get_authenticated_user)):
    """ChL to'purarlari: barcha guruhlar bo'yicha urilgan gollar (confirmed o'yinlar)."""
    from season_prizes import get_league_season
    from cl_scorers import cl_top_scorers
    return {"scorers": cl_top_scorers(get_league_season())}


@app.get("/cl/state")
def cl_state(user: dict = Depends(get_authenticated_user)):
    """ChL tur holati: started, current_matchday, total_matchdays."""
    from cl_rounds import cl_get_state
    return cl_get_state()


@app.get("/cl/profile")
def cl_profile(user: dict = Depends(get_authenticated_user)):
    """
    ChL profil kartochkasi (faqat SO'ROVCHINING o'zi — qoida #34):
    nickname, klub, guruh, guruhdagi o'rni va statistikasi.
    Avatar: GET /players/{user_id}/photo (alohida, mavjud endpoint).
    """
    from season_prizes import get_league_season
    from cl_profile import cl_get_profile
    return cl_get_profile(user["id"], get_league_season())


@app.get("/cl/matches/my")
def cl_my_matches(user: dict = Depends(get_authenticated_user)):
    """Foydalanuvchining ChL o'yinlari (joriy mavsum)."""
    from season_prizes import get_league_season
    from cl_matches_queries import cl_get_user_matches
    from cl_rounds import cl_get_state
    season = get_league_season()
    return {"me_id": user["id"],
            "state": cl_get_state(season),
            "matches": cl_get_user_matches(user["id"], season)}


@app.get("/cl/matches/user/{target_id}")
def cl_user_matches(target_id: int, user: dict = Depends(get_authenticated_user)):
    """
    Boshqa ishtirokchining ChL o'yinlari (faqat o'qish — reyting profilida ko'rish uchun).
    me_id yuborilmaydi (bu boshqa odam); natija kiritish tugmalari ko'rinmaydi.
    """
    from season_prizes import get_league_season
    from cl_matches_queries import cl_get_user_matches
    season = get_league_season()
    return {"matches": cl_get_user_matches(target_id, season)}


@app.post("/cl/match/submit-result")
def cl_submit(match_id: int, score1: int, score2: int,
              user: dict = Depends(get_authenticated_user)):
    """ChL o'yin natijasini kiritish (WC oqimi bilan bir xil)."""
    validate_scores(score1, score2)
    from cl_matches_queries import cl_get_match_by_id, cl_submit_match_result
    from cl_rounds import cl_matchday_open
    match = cl_get_match_by_id(match_id)
    if not match:
        raise HTTPException(status_code=400, detail="match_not_found")
    if not cl_matchday_open(match["matchday"], match["season"]):
        raise HTTPException(status_code=400, detail="matchday_locked")
    success, reason = cl_submit_match_result(match_id, score1, score2, user["id"])
    if not success:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": reason, "match_id": match_id}


@app.post("/cl/match/confirm")
def cl_confirm(match_id: int, accept: bool = True,
               user: dict = Depends(get_authenticated_user)):
    """ChL natijani tasdiqlash (accept=True) yoki rad etish (False)."""
    from cl_matches_queries import cl_confirm_or_reject_match
    success, reason = cl_confirm_or_reject_match(
        match_id, "confirm" if accept else "reject", user["id"])
    if not success:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": "ok", "match_id": match_id}


@app.get("/cl/matches/{match_id}/messages")
def cl_chat_get(match_id: int, user: dict = Depends(get_authenticated_user)):
    """ChL o'yin chati xabarlari — liga/divizion chat formati (webchat modal)."""
    from cl_chat import cl_get_messages
    msgs = cl_get_messages(match_id, user["id"])
    if msgs is None:
        raise HTTPException(status_code=403, detail="chat_no_access")
    return {"messages": msgs}


@app.post("/cl/matches/{match_id}/messages")
async def cl_chat_send(match_id: int, text: str = Body(..., embed=True),
                       user: dict = Depends(get_authenticated_user)):
    """ChL o'yin chatiga xabar yuborish. Body: {"text": "..."} (divizion oqimi bilan bir xil)."""
    from cl_chat import cl_send_message
    success, reason, notify = cl_send_message(match_id, user["id"], text)
    if not success:
        raise HTTPException(status_code=400, detail=reason)

    if notify is not None:
        try:
            recipient = get_user_by_telegram_id(notify["recipient_telegram_id"])
            lang = recipient.get("language") if recipient else None
            await notify_user(
                notify["recipient_telegram_id"],
                "notify_chat_message",
                lang,
                open_button_key="btn_open_app",
                mode=t("mode_name_cl", lang),
                preview=notify["text_preview"],
            )
        except Exception as exc:
            logger.warning("ChL chat bildirishnomasi yuborilmadi: %s", exc)

    return {"status": "ok"}


@app.post("/cl/matches/{match_id}/typing")
def cl_chat_typing(match_id: int, user: dict = Depends(get_authenticated_user)):
    """'Yozmoqda' signali (liga chat bilan bir xil)."""
    from cl_chat import cl_set_typing
    if not cl_set_typing(match_id, user["id"]):
        raise HTTPException(status_code=403, detail="chat_no_access")
    return {"status": "ok"}


@app.get("/cl/matches/{match_id}/state")
def cl_chat_state(match_id: int, user: dict = Depends(get_authenticated_user)):
    """ChL raqibning chat holati (online / yozmoqda / oxirgi ko'rinish)."""
    from cl_chat import cl_get_chat_state
    state = cl_get_chat_state(match_id, user["id"])
    if state is None:
        raise HTTPException(status_code=403, detail="chat_no_access")
    return state


@app.get("/cl/matches/unread")
def cl_get_unread_counts(user: dict = Depends(get_authenticated_user)):
    """2026-07-19: ChL o'qilmagan chat xabarlari (qizil rozetka) —
    liga /matches/unread bilan bir xil format: {"total", "by_match"}.
    2026-07-21: play-off chati ham qo'shiladi (kalitlar "p{id}", WC naqshi)."""
    from cl_chat import cl_count_unread
    from cl_playoff_chat import cl_po_count_unread
    group = cl_count_unread(user["id"])
    po = cl_po_count_unread(user["id"])
    return {"total": group["total"] + po["total"],
            "by_match": {**group["by_match"], **po["by_match"]}}


# --- ChL PLAY-OFF chati (2026-07-21, guruh /cl/matches/{id}/... bilan bir xil oqim) ---

@app.get("/cl/playoff/matches/{match_id}/messages")
def cl_po_chat_messages(match_id: int, user: dict = Depends(get_authenticated_user)):
    """Play-off o'yin chatidagi xabarlar (ochilganda o'qilgan deb belgilanadi)."""
    from cl_playoff_chat import cl_po_get_messages
    messages = cl_po_get_messages(match_id, user["id"])
    if messages is None:
        raise HTTPException(status_code=403, detail="chat_no_access")
    return {"messages": messages}


@app.post("/cl/playoff/matches/{match_id}/messages")
async def cl_po_chat_send(match_id: int, text: str = Body(..., embed=True),
                          user: dict = Depends(get_authenticated_user)):
    """Play-off chatiga xabar yuborish. Body: {"text": "..."} (guruh oqimi bilan bir xil)."""
    from cl_playoff_chat import cl_po_send_message
    success, reason, notify = cl_po_send_message(match_id, user["id"], text)
    if not success:
        raise HTTPException(status_code=400, detail=reason)

    if notify is not None:
        try:
            recipient = get_user_by_telegram_id(notify["recipient_telegram_id"])
            lang = recipient.get("language") if recipient else None
            await notify_user(
                notify["recipient_telegram_id"],
                "notify_chat_message",
                lang,
                open_button_key="btn_open_app",
                mode=t("mode_name_cl", lang),
                preview=notify["text_preview"],
            )
        except Exception as exc:
            logger.warning("ChL play-off chat bildirishnomasi yuborilmadi: %s", exc)

    return {"status": "ok"}


@app.post("/cl/playoff/matches/{match_id}/typing")
def cl_po_chat_typing(match_id: int, user: dict = Depends(get_authenticated_user)):
    """Play-off chatida 'yozmoqda' signali."""
    from cl_playoff_chat import cl_po_set_typing
    if not cl_po_set_typing(match_id, user["id"]):
        raise HTTPException(status_code=403, detail="chat_no_access")
    return {"status": "ok"}


@app.get("/cl/playoff/matches/{match_id}/state")
def cl_po_chat_state(match_id: int, user: dict = Depends(get_authenticated_user)):
    """Play-off chat header holati (online/typing/last_seen)."""
    from cl_playoff_chat import cl_po_get_chat_state
    state = cl_po_get_chat_state(match_id, user["id"])
    if state is None:
        raise HTTPException(status_code=403, detail="chat_no_access")
    return state


# ============ ChL PLAY-OFF (2026-07-20) ============

@app.get("/cl/playoff/status")
def cl_playoff_status(user: dict = Depends(get_authenticated_user)):
    """Play-off boshlanganmi (frontend setka ko'rsatish sharti)."""
    from cl_playoff import cl_po_is_started
    return {"started": cl_po_is_started()}


@app.post("/cl/admin/playoff/start")
def cl_admin_playoff_start(admin: dict = Depends(get_authenticated_super_admin)):
    """
    Bosh admin play-off'ni boshlaydi: har guruhdan top-2 → 1/8 (8 juftlik, 1-o'yinlar).
    Xato: already_started, not_drawn, groups_not_finished, group_N_incomplete → 400
    """
    from cl_playoff import cl_po_start
    success, result = cl_po_start()
    if not success:
        raise HTTPException(status_code=400, detail=result)
    return {"status": "ok", **result}


@app.get("/cl/playoff/bracket")
def cl_playoff_bracket(user: dict = Depends(get_authenticated_user)):
    """To'liq setka (Reyting sahifasi): juftliklar, 2 o'yin hisobi, agregat, chempion."""
    from cl_playoff import cl_po_bracket
    return cl_po_bracket()


@app.get("/cl/playoff/my-matches")
def cl_playoff_my_matches(user: dict = Depends(get_authenticated_user)):
    """Foydalanuvchining play-off o'yinlari (Profil sahifasi)."""
    from cl_playoff import cl_po_my_matches
    return cl_po_my_matches(user["id"])


@app.get("/cl/playoff/user/{target_id}/matches")
def cl_playoff_user_matches(target_id: int,
                            user: dict = Depends(get_authenticated_user)):
    """
    Boshqa ishtirokchining play-off o'yinlari (talab 3) — faqat o'qish.
    Setka juftligiga bosilib ochilgan profil sahifasida ko'rsatiladi.
    me_id yuborilmaydi (bu boshqa odam; natija tugmalari ko'rinmaydi).
    """
    from cl_playoff import cl_po_user_matches
    return cl_po_user_matches(target_id)


@app.post("/cl/playoff/submit-result")
def cl_playoff_submit(match_id: int, score1: int, score2: int,
                      user: dict = Depends(get_authenticated_user)):
    """
    Play-off o'yin natijasini kiritish. Final durang bo'lmaydi; 2-o'yinda
    agregat teng bo'lishi taqiqlanadi (o'yin ichida penalti hal qiladi).
    Xato: not_found, not_participant, wrong_status, draw_not_allowed,
    aggregate_draw_not_allowed → 400
    """
    validate_scores(score1, score2)
    from cl_playoff_results import cl_po_submit_result
    success, reason = cl_po_submit_result(match_id, score1, score2, user["id"])
    if not success:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": reason, "match_id": match_id}


@app.post("/cl/playoff/confirm-result")
def cl_playoff_confirm(match_id: int, accept: bool = True,
                       user: dict = Depends(get_authenticated_user)):
    """
    Play-off natijasini tasdiqlash/rad etish. Tasdiqda: 1-o'yin → 2-o'yin
    ochiladi; 2-o'yin → agregat g'olibi keyingi bosqichga o'tadi.
    """
    from cl_playoff_results import cl_po_confirm_result
    success, reason = cl_po_confirm_result(match_id, user["id"], accept)
    if not success:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": reason, "match_id": match_id}


@app.post("/cl/draw")
def cl_draw_endpoint(admin: dict = Depends(get_authenticated_super_admin)):
    """
    ChL guruh qur'asi (faqat bosh admin): sinxron + 8 guruh × 4 + kalendar.
    Xato: already_drawn, no_participants → 400
    """
    from cl_core import cl_sync_participants, cl_draw
    cl_sync_participants()
    success, result = cl_draw()
    if not success:
        raise HTTPException(status_code=400, detail=result)
    return {"status": "ok", **result}


# ============ DIVIZION (3-tab) ============

@app.get("/div/status")
def div_status(user: dict = Depends(get_authenticated_user)):
    """
    Divizion asosiy holati: ro'yxat oynasi (17:00-20:00), bugungi ro'yxat,
    mening bugungi o'yinim (qur'adan keyin — raqib useri/username bilan).
    """
    from division import div_registration_window, div_day_registrations, div_get_my_match
    win = div_registration_window()
    regs = div_day_registrations(win["day"])
    my_match = div_get_my_match(user["id"], win["day"])
    from division import div_my_stats, div_my_matches
    from division_season import div_current_season
    return {
        "window": win,
        # 2026-07-21: joriy mavsum (1 oy) — {number, start, end, total_days,
        # day_index (necha kun bo'ldi), days_left (qolgan kun)}
        "season": div_current_season(),
        "registrations": regs,
        "me_registered": any(r["telegram_id"] == user["telegram_id"] for r in regs),
        "my_match": my_match,
        "me_id": user["id"],
        "me_nickname": user["nickname"],
        "me_username": user.get("username"),
        "is_admin": is_super_admin(user["telegram_id"])
                    or is_scope_admin(user["telegram_id"], "division"),
        "is_super": is_super_admin(user["telegram_id"]),  # admin tayinlash oynasi uchun
        "stats": div_my_stats(user["id"]),
        "history": div_my_matches(user["id"]),
    }


@app.post("/div/register")
def div_register_endpoint(user: dict = Depends(get_authenticated_user)):
    """Bugungi Divizion ro'yxatiga yozilish (faqat 17:00-20:00)."""
    from division import div_register
    success, reason = div_register(user["id"], user["telegram_id"], user["nickname"])
    if not success:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": "ok"}


@app.get("/div/rating")
def div_rating_endpoint(user: dict = Depends(get_authenticated_user)):
    """Umumiy Divizion reytingi (+15/+10/-10 achko yig'indisi)."""
    from division import div_rating
    return {"rating": div_rating(), "me_id": user["id"]}


@app.get("/div/scorers")
def div_scorers_endpoint(user: dict = Depends(get_authenticated_user)):
    """Divizion 'To'p urarlar' tabi: eng ko'p gol urgan ishtirokchilar."""
    from division import div_scorers
    return {"scorers": div_scorers(), "me_id": user["id"]}


@app.get("/div/calendar")
def div_calendar(month: str | None = None,
                 user: dict = Depends(get_authenticated_user)):
    """
    Profil kalendari: foydalanuvchi qaysi kunlari Divizionga ro'yxatdan o'tgan.
    month="YYYY-MM" (bo'lmasa — joriy oy). Ro'yxatdan o'tilgan kunlar yashil.
    """
    # month validatsiyasi (SQL LIKE'ga tushadi — formatni qat'iy tekshiramiz)
    if month is not None:
        parts = month.split("-")
        ok = (len(parts) == 2 and len(parts[0]) == 4 and len(parts[1]) == 2
              and parts[0].isdigit() and parts[1].isdigit()
              and 1 <= int(parts[1]) <= 12)
        if not ok:
            raise HTTPException(status_code=400, detail="month formati: YYYY-MM")
    from division import div_registration_days
    return div_registration_days(user["id"], month)


@app.get("/div/player/{player_id}/profile")
def div_player_profile(player_id: int, month: str | None = None,
                      user: dict = Depends(get_authenticated_user)):
    """
    Boshqa ishtirokchining Divizion profili (reyting/tarix qatoriga bosilganda):
    ism, username, statistika (g'alaba foizi) va o'yin tarixi.
    Faqat ommaviy turnir ma'lumotlari — reytingda ko'rinadigan narsalar.
    """
    from queries_users import get_user_by_id
    from division import div_my_stats, div_my_matches, div_registration_days
    target = get_user_by_id(player_id)
    if target is None:
        raise HTTPException(status_code=404, detail="user_not_found")
    return {
        "user_id": target["id"],
        "nickname": target["nickname"],
        "username": target["username"],
        "stats": div_my_stats(player_id),          # ichida umumiy ball (rating) ham bor
        "history": div_my_matches(player_id, limit=20),
        "calendar": div_registration_days(player_id, month),   # ro'yxat kalendari
    }


@app.post("/div/match/submit-result")
def div_submit_endpoint(match_id: int, score1: int, score2: int,
                        user: dict = Depends(get_authenticated_user)):
    """Divizion o'yin natijasini kiritish (deadline 23:30 gacha)."""
    validate_scores(score1, score2)
    from division import div_submit_result
    success, reason = div_submit_result(match_id, score1, score2, user["id"])
    if not success:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": reason, "match_id": match_id}


@app.post("/div/match/confirm")
def div_confirm_endpoint(match_id: int, accept: bool = True,
                         user: dict = Depends(get_authenticated_user)):
    """Divizion natijasini tasdiqlash/rad etish."""
    from division import div_confirm_or_reject
    success, reason = div_confirm_or_reject(
        match_id, "confirm" if accept else "reject", user["id"])
    if not success:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": "ok", "match_id": match_id}


@app.get("/div/matches/{match_id}/messages")
def div_chat_get(match_id: int, user: dict = Depends(get_authenticated_user)):
    """Divizion o'yin chati xabarlari — liga chat formati (webchat modal)."""
    from division_chat import div_get_messages
    msgs = div_get_messages(match_id, user["id"])
    if msgs is None:
        raise HTTPException(status_code=403, detail="chat_no_access")
    return {"messages": msgs}


@app.post("/div/matches/{match_id}/messages")
async def div_chat_send(match_id: int, text: str = Body(..., embed=True),
                        user: dict = Depends(get_authenticated_user)):
    """
    Divizion o'yin chatiga xabar yuborish. Body: {"text": "..."}.

    Xabar yozilgach raqibga bot orqali bildirishnoma boradi (liga/WC bilan bir xil):
    qaysi rejimdan kelgani ("Divizion") va ilovani ochish tugmasi bilan.
    """
    from division_chat import div_send_message
    success, reason, notify = div_send_message(match_id, user["id"], text)
    if not success:
        raise HTTPException(status_code=400, detail=reason)

    # Bot bildirishnomasi (raqibga). Xato bo'lsa ham xabar yozilgan — javobni buzmaymiz.
    if notify is not None:
        try:
            recipient = get_user_by_telegram_id(notify["recipient_telegram_id"])
            lang = recipient.get("language") if recipient else None
            await notify_user(
                notify["recipient_telegram_id"],
                "notify_chat_message",
                lang,
                open_button_key="btn_open_app",
                mode=t("mode_name_division", lang),
                preview=notify["text_preview"],
            )
        except Exception as exc:
            logger.warning("Divizion chat bildirishnomasi yuborilmadi: %s", exc)

    return {"status": "ok"}


@app.post("/div/matches/{match_id}/typing")
def div_chat_typing(match_id: int, user: dict = Depends(get_authenticated_user)):
    """'Yozmoqda' signali (liga chat bilan bir xil)."""
    from division_chat import div_set_typing
    if not div_set_typing(match_id, user["id"]):
        raise HTTPException(status_code=403, detail="chat_no_access")
    return {"status": "ok"}


@app.get("/div/matches/{match_id}/state")
def div_chat_state(match_id: int, user: dict = Depends(get_authenticated_user)):
    """Raqib chat holati (online / yozmoqda / oxirgi ko'rinish)."""
    from division_chat import div_get_chat_state
    state = div_get_chat_state(match_id, user["id"])
    if state is None:
        raise HTTPException(status_code=403, detail="chat_no_access")
    return state


@app.get("/div/matches/unread")
def div_get_unread_counts(user: dict = Depends(get_authenticated_user)):
    """2026-07-19: Divizion o'qilmagan chat xabarlari (qizil rozetka) —
    liga /matches/unread bilan bir xil format: {"total", "by_match"}."""
    from division_chat import div_count_unread
    return div_count_unread(user["id"])


# --- Divizion admin (faqat bosh admin, Divizion tabidagi panel) ---

@app.get("/div/admin/matches")
def div_admin_matches(day: str | None = None,
                      admin: dict = Depends(get_authenticated_div_admin)):
    """
    Divizion o'yinlari (admin). day=None -> bugungi; day='all' -> barcha kunlar
    (oxirgi 100) — o'tgan kunlardagi tasdiqlangan natijalarni tuzatish uchun.
    """
    from division import div_admin_list_matches
    return {"matches": div_admin_list_matches(day), "day": day or "today"}


@app.post("/div/admin/match/set-result")
def div_admin_set(match_id: int, score1: int, score2: int,
                  admin: dict = Depends(get_authenticated_div_admin)):
    """Admin: natijani o'rnatish/tuzatish (istalgan statusdan -> confirmed)."""
    validate_scores(score1, score2)
    from division import div_admin_set_result
    success, reason = div_admin_set_result(match_id, score1, score2)
    if not success:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": "ok", "match_id": match_id}


@app.get("/div/admin/match/{match_id}/info")
def div_admin_match_info_endpoint(
        match_id: int, admin: dict = Depends(get_authenticated_div_admin)):
    """
    Match ID bo'yicha o'yin ma'lumoti (admin 'Match ID orqali tuzatish' formasi:
    ID yozilganda o'yinchilar va joriy hisob ko'rinadi). Topilmasa 404.
    """
    from division import div_admin_match_info
    info = div_admin_match_info(match_id)
    if info is None:
        raise HTTPException(status_code=404, detail="match_not_found")
    return info


@app.post("/div/admin/match/cancel")
def div_admin_cancel(match_id: int,
                     admin: dict = Depends(get_authenticated_div_admin)):
    """Admin: natijani bekor qilish — o'yin pending'ga qaytadi, qayta kiritiladi."""
    from division import div_admin_cancel_match
    success, reason = div_admin_cancel_match(match_id)
    if not success:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": "ok", "match_id": match_id}


@app.post("/div/admin/ban")
async def div_admin_ban(
    user_id: int = Body(..., embed=True),
    days: int = Body(..., embed=True),
    admin: dict = Depends(get_authenticated_super_admin),
):
    """
    2026-07-17: Admin qoidabuzar ishtirokchiga KUNLIK ban beradi (faqat bosh
    admin). Ban davomida ishtirokchi Divizion ro'yxatidan o'ta olmaydi;
    kalendarida ban kunlari qizil ko'rinadi; telegramiga xabar boradi.
    Xatolar: invalid_days, user_not_found.
    """
    from division_bans import div_ban_user
    success, result = div_ban_user(user_id, days)
    if not success:
        raise HTTPException(status_code=400, detail=result)

    # Telegram xabari — yuborilmasa ham ban kuchda qoladi (log yoziladi, qoida #44)
    if result.get("telegram_id"):
        try:
            await notify_user(result["telegram_id"], "notify_div_ban",
                              result.get("language"),
                              days=result["days"], until=result["until_day"])
        except Exception as exc:
            logger.warning("Divizion ban xabari yuborilmadi (tg=%s): %s",
                           result["telegram_id"], exc)
    return {"status": "ok", "until_day": result["until_day"],
            "start_day": result["start_day"], "days": result["days"]}


@app.post("/div/admin/match/resolve")
def div_admin_resolve(match_id: int, accept: bool = True,
                      admin: dict = Depends(get_authenticated_div_admin)):
    """
    Admin: katta hisob (admin_pending) qarori — liga admin oqimi kabi.
    accept=True tasdiqlaydi, accept=False rad etadi (pending'ga qaytadi).
    """
    from division import div_admin_resolve_pending
    success, reason = div_admin_resolve_pending(match_id, accept)
    if not success:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": "ok", "match_id": match_id}


@app.post("/wc/playoff/submit-result")
def wc_playoff_submit(
    match_id: int,
    score1: int,
    score2: int,
    user: dict = Depends(get_authenticated_user),
):
    """
    Play-off match natijasini kiritadi. Durang qabul qilinmaydi (g'olib aniq shart).
    Xato: draw_not_allowed, not_open, not_participant, ... → 400
    """
    validate_scores(score1, score2)
    import queries
    success, reason = queries.wc_playoff_submit_result(match_id, score1, score2, user["id"])
    if not success:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": "ok", "match_id": match_id}


@app.post("/wc/playoff/confirm-result")
def wc_playoff_confirm(
    match_id: int,
    accept: bool = True,
    user: dict = Depends(get_authenticated_user),
):
    """
    Play-off natijasini tasdiqlaydi (accept=True) yoki rad etadi (False).
    Tasdiqlansa g'olib keyingi bosqichga o'tadi.
    """
    import queries
    success, reason = queries.wc_playoff_confirm_result(match_id, user["id"], accept)
    if not success:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": "ok", "match_id": match_id}


# ============ ADMIN BOSHQARUV (faqat bosh admin) ============

@app.get("/admin/roles/{scope}")
def admin_list_roles(scope: str, admin: dict = Depends(get_authenticated_super_admin)):
    """
    Berilgan scope ('league'/'wc'/'cl'/'division') uchun tayinlangan oddiy adminlar ro'yxati.
    Faqat bosh admin ko'ra oladi.
    Xato: invalid_scope → 400
    """
    if scope not in VALID_SCOPES:
        raise HTTPException(status_code=400, detail="invalid_scope")
    return {"scope": scope, "admins": list_admins(scope)}


@app.post("/admin/roles/{scope}")
def admin_add_role(scope: str, telegram_id: int, admin: dict = Depends(get_authenticated_super_admin)):
    """
    Yangi oddiy admin tayinlaydi (berilgan scope uchun). Faqat bosh admin.
    Tayinlangan admin faqat o'sha scope'da natija tuzata oladi.

    Query param: telegram_id (int)
    Xato: invalid_scope, already_admin, cannot_add_super → 400
    """
    if scope not in VALID_SCOPES:
        raise HTTPException(status_code=400, detail="invalid_scope")
    success, reason = add_admin(telegram_id, scope, admin["telegram_id"])
    if not success:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": "ok", "telegram_id": telegram_id, "scope": scope}


@app.delete("/admin/roles/{scope}/{telegram_id}")
def admin_remove_role(scope: str, telegram_id: int, admin: dict = Depends(get_authenticated_super_admin)):
    """
    Oddiy adminni scope'idan o'chiradi (faqat bosh admin).
    Xato: invalid_scope, not_found → 400
    """
    if scope not in VALID_SCOPES:
        raise HTTPException(status_code=400, detail="invalid_scope")
    if not remove_admin(telegram_id, scope):
        raise HTTPException(status_code=400, detail="not_found")
    return {"status": "ok", "telegram_id": telegram_id, "scope": scope}


# ============ ADMIN-LIGA BIRIKTIRISH (faqat bosh admin) ============

@app.get("/admin/leagues/all")
def admin_all_leagues(admin: dict = Depends(get_authenticated_super_admin)):
    """Barcha ligalar ro'yxati (admin biriktirish UI uchun). Faqat bosh admin."""
    leagues = get_all_leagues()
    return {"leagues": [{"id": lg["id"], "name": lg["name"]} for lg in leagues]}


@app.get("/admin/roles/league/{telegram_id}/leagues")
def admin_get_admin_leagues(telegram_id: int, admin: dict = Depends(get_authenticated_super_admin)):
    """Liga adminiga biriktirilgan liga ID'lari. Faqat bosh admin."""
    return {"telegram_id": telegram_id, "league_ids": get_admin_league_ids(telegram_id)}


@app.post("/admin/roles/league/{telegram_id}/leagues/{league_id}")
def admin_assign_league(telegram_id: int, league_id: int, admin: dict = Depends(get_authenticated_super_admin)):
    """
    Liga adminiga ligani biriktiradi (faqat bosh admin).
    Xato: not_league_admin, league_not_found, already_assigned → 400
    """
    success, reason = assign_league(telegram_id, league_id, admin["telegram_id"])
    if not success:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": "ok", "telegram_id": telegram_id, "league_id": league_id}


@app.delete("/admin/roles/league/{telegram_id}/leagues/{league_id}")
def admin_unassign_league(telegram_id: int, league_id: int, admin: dict = Depends(get_authenticated_super_admin)):
    """Liga adminidan ligani olib tashlaydi (faqat bosh admin)."""
    if not unassign_league(telegram_id, league_id):
        raise HTTPException(status_code=400, detail="not_found")
    return {"status": "ok", "telegram_id": telegram_id, "league_id": league_id}


@app.get("/admin/whoami")
def admin_whoami(x_telegram_init_data: str = Header(...)):
    """
    Joriy foydalanuvchining admin holatini qaytaradi (frontend panel ko'rsatish uchun).
    is_super: bosh admin (config); is_league_admin / is_wc_admin: scope adminlar.
    """
    telegram_user = verify_telegram_init_data(x_telegram_init_data)
    tid = telegram_user["id"]
    from admin_roles import SCOPE_CL, SCOPE_DIVISION
    return {
        "is_super": is_super_admin(tid),
        "is_league_admin": is_scope_admin(tid, SCOPE_LEAGUE),
        "is_wc_admin": is_scope_admin(tid, SCOPE_WC),
        "is_cl_admin": is_scope_admin(tid, SCOPE_CL),
        "is_div_admin": is_scope_admin(tid, SCOPE_DIVISION),
    }


# ============ POST /profile/nickname ============

@app.post("/profile/nickname")
def change_nickname(nickname: str, user: dict = Depends(get_authenticated_user)):
    """
    Foydalanuvchi nickname'ini yangilaydi.

    Query param: nickname (str, 2-20 belgi)
    """
    nickname = nickname.strip()
    if len(nickname) < 2 or len(nickname) > 20:
        raise HTTPException(status_code=400, detail="nickname_invalid_length")
    update_user_nickname(user["id"], nickname)
    return {"status": "ok", "nickname": nickname}


# ============ GET /matches/my ============

@app.get("/matches/my")
def get_my_matches(user: dict = Depends(get_authenticated_user)):
    """Joriy foydalanuvchining barcha matchlarini qaytaradi (is_locked bilan)."""
    matches = _annotate_matches_locked(get_user_matches(user["id"]))
    return {"user_id": user["id"], "matches": matches}


# ============ Chat (aktiv match raqibi bilan) ============

@app.get("/matches/{match_id}/messages")
def get_match_messages(match_id: int, user: dict = Depends(get_authenticated_user)):
    """
    Aktiv match xabarlarini qaytaradi (vaqt tartibida). Raqib yuborgan
    o'qilmagan xabarlar "o'qilgan" deb belgilanadi (ikkita ✓ uchun).
    Access yo'q (begona/tugagan match) → 403.
    """
    messages = get_chat_messages(match_id, user["telegram_id"])
    if messages is None:
        raise HTTPException(status_code=403, detail="chat_no_access")
    return {"match_id": match_id, "messages": messages}


@app.post("/matches/{match_id}/messages")
async def post_match_message(
    match_id: int,
    text: str = Body(..., embed=True),
    user: dict = Depends(get_authenticated_user),
):
    """
    Aktiv match raqibiga matnli xabar yuboradi.
    Body: {"text": "..."}
    Xatolar: empty (bo'sh matn) → 400, no_access (begona/tugagan) → 403.

    Muvaffaqiyatda, raqib chatni faol kuzatmayotgan bo'lsa (anti-spam: 1 daqiqada
    bir marta), unga bot orqali "Raqib sizga ilovadan xabar yubordi" bildirishnomasi
    yuboriladi (xabar matnining qisqa ko'rinishi bilan).
    """
    ok, reason, notify = send_chat_message(match_id, user["telegram_id"], text)
    if not ok:
        if reason == "empty":
            raise HTTPException(status_code=400, detail="empty")
        raise HTTPException(status_code=403, detail="chat_no_access")

    # Bot bildirishnomasi (raqibga). Xato bo'lsa ham xabar yuborilgan — javobni buzmaymiz.
    if notify is not None:
        try:
            recipient = get_user_by_telegram_id(notify["recipient_telegram_id"])
            lang = recipient.get("language") if recipient else None
            await notify_user(
                notify["recipient_telegram_id"],
                "notify_chat_message",
                lang,
                open_button_key="btn_open_app",      # ilovani tez ochish tugmasi
                mode=t("mode_name_league", lang),    # qaysi rejimdan — aniq ko'rsatiladi
                preview=notify["text_preview"],
            )
        except Exception as exc:
            # Xabar DB'ga yozildi — bot bildirishnomasi yiqilsa javobni buzmaymiz,
            # lekin log qoldiramiz (qoida #44)
            logger.warning("Chat bot bildirishnomasi yuborilmadi: %s", exc)

    return {"ok": True}


@app.get("/matches/unread")
def get_unread_counts(user: dict = Depends(get_authenticated_user)):
    """
    O'qilmagan chat xabarlari soni (qizil rozetka uchun).
    Qaytaradi: {"total": int, "by_match": {match_id: count, ...}}
    """
    return count_unread_messages(user["telegram_id"])


@app.post("/matches/{match_id}/typing")
def post_typing(match_id: int, user: dict = Depends(get_authenticated_user)):
    """Foydalanuvchi shu match chatida 'yozmoqda' signalini yuboradi."""
    ok = set_typing(match_id, user["telegram_id"])
    if not ok:
        raise HTTPException(status_code=403, detail="chat_no_access")
    return {"ok": True}


@app.get("/matches/{match_id}/state")
def get_match_state(match_id: int, user: dict = Depends(get_authenticated_user)):
    """
    Raqibning chat holatini qaytaradi (online / yozmoqda / oxirgi ko'rinish).
    Access yo'q → 403.
    """
    state = get_chat_state(match_id, user["telegram_id"])
    if state is None:
        raise HTTPException(status_code=403, detail="chat_no_access")
    return state


# ============ POST /match/submit-result ============

@app.post("/match/submit-result")
async def submit_result(
    match_id: int,
    score1: int,
    score2: int,
    user: dict = Depends(get_authenticated_user),
):
    """
    Match natijasini kiritadi.

    Query params: match_id, score1, score2
    Faqat o'sha matchning player1 yoki player2 kira oladi.

    Natija muvaffaqiyatli kiritilgach, raqibga (natija kiritmagan tomonga)
    "Natija kiritildi, tasdiqlaysizmi?" inline xabari yuboriladi (uning tilida).

    Xato holatlari: match_not_found, not_participant, already_submitted,
                    matchday_locked (tur hali ochilmagan) → 400
    """
    validate_scores(score1, score2)

    # Matchday qulfi: faqat ochilgan turlarning natijasini kiritish mumkin.
    # Har kuni 01:00 (Toshkent) da bitta yangi tur ochiladi (get_open_matchday).
    match = get_match_by_id(match_id)
    if match is None:
        raise HTTPException(status_code=400, detail="match_not_found")
    open_matchday = get_open_matchday(match["league_id"])
    if match["matchday"] > open_matchday:
        raise HTTPException(status_code=400, detail="matchday_locked")

    # Hisob kiritish kechikishi: tur ochilgandan keyin 1s45daq o'tmagan bo'lsa,
    # natija kiritib bo'lmaydi (o'ynalmagan o'yinga darrov yolg'on natija oldini olish).
    # Rad etilgan natijani qayta kiritish ham shu cheklovga bo'ysunadi.
    if get_matchday_entry_locked(match["league_id"], match["matchday"]):
        raise HTTPException(status_code=400, detail="entry_too_early")

    # Deadline (01:00) ga 15 daqiqa qolganda (00:45 dan keyin) yangi hisob kiritib
    # bo'lmaydi — o'rtacha o'yin 8-15 daqiqa, oxirgi 15 daqiqada boshlab bo'lmaydi.
    if is_near_deadline():
        raise HTTPException(status_code=400, detail="entry_near_deadline")

    success, reason = submit_match_result(match_id, score1, score2, user["id"])
    if not success:
        raise HTTPException(status_code=400, detail=reason)

    # Katta hisob (admin_pending) — raqib tasdig'i kutilmaydi, admin ko'rib chiqadi.
    # Shuning uchun raqibga tasdiqlash so'rovi YUBORILMAYDI.
    if reason != "ok_admin_pending":
        # Raqibga (natija kiritmagan tomonga) tasdiqlash so'rovi yuboramiz
        match = get_match_by_id(match_id)
        if match is not None:
            opponent_id = match["player2_id"] if user["id"] == match["player1_id"] else match["player1_id"]
            opponent = get_user_by_id(opponent_id)
            if opponent is not None:
                await notify_user(
                    opponent["telegram_id"],
                    "notify_result_submitted",
                    opponent.get("language"),
                )

    return {"status": "ok", "match_id": match_id, "reason": reason}


# ============ POST /match/confirm ============

@app.post("/match/confirm")
def confirm_result(
    match_id: int,
    action: str,
    user: dict = Depends(get_authenticated_user),
):
    """
    Raqib tomonidan natijani tasdiqlaydi yoki rad etadi.

    Query params: match_id, action ("confirm" yoki "reject")
    Xato holatlari: match_not_found, not_opponent, wrong_status, invalid_action,
                    reject_near_deadline → 400
    """
    # Deadline (01:00) ga 15 daqiqa qolganda (00:45 dan keyin) RAD ETIB bo'lmaydi —
    # 00:45 gacha kiritilgan to'g'ri hisob himoyalanadi (raqib oxirgi daqiqada rad
    # qilib turnir oqimini buzolmaydi). Tasdiqlash esa har doim mumkin.
    if action == "reject" and is_near_deadline():
        raise HTTPException(status_code=400, detail="reject_near_deadline")

    success, reason = confirm_or_reject_match(match_id, action, user["id"])
    if not success:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": "ok", "match_id": match_id, "action": action}


# ============ GET /admin/players ============

@app.get("/admin/players")
def admin_list_players(admin: dict = Depends(get_authenticated_admin)):
    """Barcha foydalanuvchilarni ro'yxatdan o'tgan ligasi va klubi bilan qaytaradi (faqat admin)."""
    return get_all_users_with_registration()


# ============ DELETE /admin/players/{user_id} ============

@app.delete("/admin/players/{user_id}")
def admin_remove_player(user_id: int, admin: dict = Depends(get_authenticated_admin)):
    """
    Foydalanuvchini butunlay o'chiradi: user, registration va barcha matchlari (faqat admin).

    Xato holatlari: user_not_found → 404
    """
    success, reason = remove_user_completely(user_id)
    if not success:
        raise HTTPException(status_code=404, detail=reason)
    return {"status": "ok", "removed_user_id": user_id}


# ============ GET /admin/rejected-matches ============

@app.get("/admin/rejected-matches")
def admin_list_rejected_matches(admin: dict = Depends(get_authenticated_admin)):
    """Statusi 'rejected' bo'lgan barcha matchlarni qaytaradi (faqat admin)."""
    return get_rejected_matches()


# ============ POST /admin/match/resolve ============

@app.post("/admin/match/resolve")
def admin_resolve_rejected_match(
    match_id: int,
    action: str,
    score1: int | None = None,
    score2: int | None = None,
    admin: dict = Depends(get_authenticated_admin),
):
    """
    Admin 'rejected' holatdagi matchni hal qiladi.

    Query params: match_id, action ("set_result" yoki "reset"), score1, score2 (set_result uchun shart)
    Xato holatlari: match_not_found, wrong_status, invalid_action, score_missing → 400
    """
    if score1 is not None and score2 is not None:
        validate_scores(score1, score2)  # AUDIT B2 (set_result holati)
    success, reason = admin_resolve_match(match_id, action, score1, score2)
    if not success:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": "ok", "match_id": match_id, "action": action}


# ============ POST /admin/match/fix-confirmed ============

@app.get("/admin/match/{match_id}/info")
def admin_match_info(
    match_id: int,
    admin: dict = Depends(get_authenticated_league_admin),
):
    """
    Admin formalari uchun qisqa ma'lumot (2026-07-04): Match ID kiritilganda
    frontend qaysi o'yin ekanini (klublar -> logolar) jonli ko'rsatadi.
    """
    match = get_match_by_id(match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="match_not_found")
    reg1 = get_user_registration(match["player1_id"])
    reg2 = get_user_registration(match["player2_id"])
    p1 = get_user_by_id(match["player1_id"])
    p2 = get_user_by_id(match["player2_id"])
    return {
        "id": match["id"],
        "club1": reg1["club_name"] if reg1 else None,
        "club2": reg2["club_name"] if reg2 else None,
        "nickname1": p1["nickname"] if p1 else None,
        "nickname2": p2["nickname"] if p2 else None,
        "score1": match["score1"],
        "score2": match["score2"],
        "status": match["status"],
    }


@app.get("/admin/match/pending")
def admin_pending_list(admin: dict = Depends(get_authenticated_league_admin)):
    """Katta hisob (admin_pending) tufayli admin tasdig'ini kutayotgan liga o'yinlari."""
    return {"matches": get_admin_pending_matches()}


@app.post("/admin/match/pending/resolve")
def admin_pending_resolve(
    match_id: int,
    action: str,
    admin: dict = Depends(get_authenticated_league_admin),
):
    """
    Bosh/liga admin katta hisobli o'yinni tasdiqlaydi (confirm) yoki rad etadi (reject).
    Query params: match_id, action ('confirm'|'reject').
    """
    success, reason = admin_resolve_pending(match_id, action)
    if not success:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": "ok"}


@app.post("/admin/match/fix-confirmed")
def admin_fix_confirmed(
    match_id: int,
    score1: int,
    score2: int,
    admin: dict = Depends(get_authenticated_league_admin),
):
    """
    Admin allaqachon 'confirmed' bo'lgan matchning noto'g'ri natijasini
    qo'lda tuzatadi (status o'zgarmaydi, faqat score yangilanadi).

    Query params: match_id, score1, score2
    Xato holatlari: match_not_found, wrong_status, league_not_allowed → 400/403
    """
    # Liga admini faqat o'ziga biriktirilgan ligani tuzata oladi (bosh admin — hammasini)
    match = get_match_by_id(match_id)
    if match is None:
        raise HTTPException(status_code=400, detail="match_not_found")
    if not can_manage_league(admin["telegram_id"], match["league_id"]):
        raise HTTPException(status_code=403, detail="league_not_allowed")

    validate_scores(score1, score2)  # AUDIT B2: admin xatosi ham reytingni buzmasin
    success, reason = admin_fix_confirmed_match(match_id, score1, score2)
    if not success:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": "ok", "match_id": match_id}


# ============ POST /admin/match/cancel ============

@app.post("/admin/match/cancel")
def admin_match_cancel(
    match_id: int,
    admin: dict = Depends(get_authenticated_league_admin),
):
    """
    2026-07-16: Admin NATIJANI BEKOR QILADI — o'yin natija kiritilmagan
    holatga qaytadi (pending, hisob NULL). Divizion/WC'dagi bekor qilish
    bilan bir xil oqim. Liga admini faqat o'z ligasini (bosh admin — hammasini).
    Query params: match_id. Xato: match_not_found, league_not_allowed.
    """
    match = get_match_by_id(match_id)
    if match is None:
        raise HTTPException(status_code=400, detail="match_not_found")
    if not can_manage_league(admin["telegram_id"], match["league_id"]):
        raise HTTPException(status_code=403, detail="league_not_allowed")

    success, reason = admin_cancel_match(match_id)
    if not success:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": "ok", "match_id": match_id}


# ============ POST /admin/league/{league_id}/draw ============

@app.post("/admin/league/{league_id}/draw")
async def admin_draw_league(league_id: int, admin: dict = Depends(get_authenticated_admin)):
    """
    Liga uchun qur'a o'tkazadi: barcha 380 ta matchni avtomatik generatsiya qiladi
    (round-robin, schedule.py) va liga statusini 'in_progress'ga o'tkazadi (faqat admin).

    Faqat liga to'lgan bo'lsa ishlaydi. Qur'a faqat bir marta o'tkaziladi —
    allaqachon match mavjud bo'lsa, qayta qur'a qilinmaydi (natijalarni
    yo'qotib qo'ymaslik uchun).

    Qur'a o'tkazilgach, liganing barcha ishtirokchilariga (har biri o'z tilida)
    "Qur'a tashlandi" inline xabari yuboriladi.

    Xato holatlari: league_not_found → 404, league_not_full, already_drawn → 400
    """
    league = get_league_by_id(league_id)
    if league is None:
        raise HTTPException(status_code=404, detail="league_not_found")

    current_count = count_league_players(league_id)
    if current_count < league["max_players"]:
        raise HTTPException(status_code=400, detail="league_not_full")

    if league_has_matches(league_id):
        raise HTTPException(status_code=400, detail="already_drawn")

    player_ids = get_league_player_ids(league_id)
    matches_created = generate_league_schedule(league_id, player_ids)
    update_league_status(league_id, LEAGUE_STATUS_IN_PROGRESS)
    # Qur'a sanasini yozamiz — shu sanadan boshlab har kuni bitta tur ochiladi.
    # 1-tur bugun ochiq, keyingilari har kuni 01:00 (Toshkent) da.
    set_league_draw_date(league_id)

    # Ishtirokchilarga "Qur'a tashlandi" bildirishnomasini yuboramiz (har biri o'z tilida)
    members = get_league_members_for_notify(league_id)
    await notify_members(members, "notify_draw_done", league=league["name"])

    return {"status": "ok", "league_id": league_id, "matches_created": matches_created}


# ============ POST /admin/league/{league_id}/start ============

@app.post("/admin/league/{league_id}/start")
async def admin_start_league(league_id: int, admin: dict = Depends(get_authenticated_admin)):
    """
    Turnirni boshlaydi: draw_date'ni BUGUNGA o'rnatadi (faqat admin).

    XAVFSIZ — mavjud jadval va kiritilgan natijalar SAQLANADI. Bu, qur'a allaqachon
    o'tkazilgan (matchlar bor), lekin draw_date yo'q ligalar uchun (eski qur'alar):
    draw_date'siz hamma tur yopiq qoladi, shuning uchun uni bugunga o'rnatib turnirni
    boshlaymiz — bugun 1-tur ochiq, keyingilari har kuni 01:00 (Toshkent) da.

    Ishtirokchilarga "1-tur ochildi" xabari yuboriladi.

    Xato holatlari: league_not_found → 404, no_matches (qur'a o'tkazilmagan) → 400
    """
    league = get_league_by_id(league_id)
    if league is None:
        raise HTTPException(status_code=404, detail="league_not_found")

    if not league_has_matches(league_id):
        raise HTTPException(status_code=400, detail="no_matches")

    update_league_status(league_id, LEAGUE_STATUS_IN_PROGRESS)
    set_league_draw_date(league_id)  # = bugun (turnir mintaqasi)

    # Avtomatik 0:0 tasdiqlangan turlarni qayta ochamiz (toza boshlanish).
    # Qo'lda kiritilgan haqiqiy natijalar (0:0 emas) SAQLANADI.
    # Bugundan boshlanganda faqat MATCHDAYS_PER_UNLOCK ta tur ochiq, qolgani yopiq —
    # shuning uchun butun jadval bo'ylab avtomatik 0:0 larni tozalaymiz.
    reopened = reopen_matchdays(league_id, TOTAL_MATCHDAYS)

    members = get_league_members_for_notify(league_id)
    await notify_members(members, "notify_matchday_open", matchday=1)

    return {"status": "ok", "league_id": league_id, "reopened": reopened}


# ============ POST /admin/league/{league_id}/redraw ============

@app.post("/admin/league/{league_id}/redraw")
async def admin_redraw_league(
    league_id: int,
    keep_results: bool = False,
    admin: dict = Depends(get_authenticated_admin),
):
    """
    Qayta qur'a: eski jadvalni o'chirib, yangidan qur'a tashlaydi (faqat admin).

    keep_results=False (default): barcha natijalar O'CHIRILADI (toza qayta qur'a).
    keep_results=True: kiritilgan natijalar SAQLANADI — yangi jadvaldagi o'sha
        juftlik o'yiniga ko'chiriladi. Liga to'lib (masalan 19→20 kishi), yangi
        o'yinchini jadvalga qo'shish kerak bo'lganda ishlatiladi.

    Faqat liga to'lgan bo'lsa ishlaydi.

    Xato holatlari: league_not_found → 404, league_not_full → 400
    """
    league = get_league_by_id(league_id)
    if league is None:
        raise HTTPException(status_code=404, detail="league_not_found")

    current_count = count_league_players(league_id)
    if current_count < league["max_players"]:
        raise HTTPException(status_code=400, detail="league_not_full")

    # keep_results bo'lsa — eski natijalarni saqlab olamiz
    played = get_played_results(league_id) if keep_results else []

    # Eski jadvalni o'chirib, yangidan qur'a tashlaymiz
    delete_league_matches(league_id)
    player_ids = get_league_player_ids(league_id)
    matches_created = generate_league_schedule(league_id, player_ids)
    update_league_status(league_id, LEAGUE_STATUS_IN_PROGRESS)
    set_league_draw_date(league_id)  # = bugun

    # Saqlangan natijalarni yangi jadvalga ko'chiramiz
    restored = restore_results_to_schedule(league_id, played) if keep_results else 0

    members = get_league_members_for_notify(league_id)
    await notify_members(members, "notify_draw_done", league=league["name"])

    return {
        "status": "ok",
        "league_id": league_id,
        "matches_created": matches_created,
        "results_restored": restored,
    }


@app.post("/admin/league/{league_id}/reopen-auto")
async def admin_reopen_auto(league_id: int, admin: dict = Depends(get_authenticated_admin)):
    """
    Turnirni BUGUNDAN qayta boshlaydi: draw_date'ni bugunga qo'yadi va avtomatik
    0:0 tasdiqlangan turlarni qayta 'pending' qiladi.

    - draw_date = bugun → bugun MATCHDAYS_PER_UNLOCK ta tur ochiq, qolgani yopiq;
      keyingilari har kuni 01:00 da ochiladi.
    - Avtomatik 0:0 tasdiqlangan turlar → pending (qaytadan o'ynaladi).
    - Qo'lda kiritilgan haqiqiy natijalar (0:0 emas) SAQLANADI — tegilmaydi.

    Xato holatlari: league_not_found → 404
    """
    league = get_league_by_id(league_id)
    if league is None:
        raise HTTPException(status_code=404, detail="league_not_found")

    # draw_date'ni bugunga qo'yamiz — shundagina "bugun faqat 1-2 tur ochiq" bo'ladi
    set_league_draw_date(league_id)

    # Butun jadval bo'ylab avtomatik 0:0 confirmed turlarni qaytaramiz.
    # reopen_matchdays faqat score 0:0 confirmed'larni oladi (qo'lda natijalarga tegmaydi).
    reopened = reopen_matchdays(league_id, TOTAL_MATCHDAYS)

    return {"status": "ok", "league_id": league_id, "reopened": reopened}


@app.post("/admin/league/{league_id}/resolve-open")
async def admin_resolve_open(league_id: int, admin: dict = Depends(get_authenticated_admin)):
    """
    Ligani 1 KUN oldinga suradi: bugun deadline o'tgan turlarga QO'SHIMCHA yana bir
    kunlik (MATCHDAYS_PER_UNLOCK ta) turni darrov tasdiqlaydi. LaLiga kabi 1 kun
    orqada qolgan ligani boshqalarga tenglashtirish uchun.

    Misol: LaLiga 1 kun orqada (bugun hech narsa deadline o'tmagan, deadline=0).
    Bu tugma 0 + MATCHDAYS_PER_UNLOCK = 2 turni (1-2) tasdiqlaydi. 3-4 TEGILMAYDI.

    - pending → 0:0 durang, confirmed.
    - awaiting_confirmation → kiritilgan natija, confirmed.
    - confirmed/rejected → tegilmaydi.

    Xato holatlari: league_not_found → 404
    """
    league = get_league_by_id(league_id)
    if league is None:
        raise HTTPException(status_code=404, detail="league_not_found")

    # Bugun deadline o'tgan turlar + yana bir kunlik blok (ligani 1 kun oldinga surish).
    deadline_md = get_deadline_passed_matchday(league_id)
    up_to = deadline_md + MATCHDAYS_PER_UNLOCK
    # Ochiq turlardan oshmasin (yopiq turlarni tasdiqlamaymiz)
    open_md = get_open_matchday(league_id)
    if up_to > open_md:
        up_to = open_md
    if up_to < 1:
        return {"status": "ok", "league_id": league_id, "resolved": 0, "up_to": 0}

    resolved = auto_resolve_matches(league_id, up_to)
    total = resolved["pending_resolved"] + resolved["awaiting_resolved"]
    return {
        "status": "ok",
        "league_id": league_id,
        "up_to": up_to,
        "resolved": total,
        "pending_resolved": resolved["pending_resolved"],
        "awaiting_resolved": resolved["awaiting_resolved"],
    }


@app.post("/admin/league/{league_id}/undo-resolve")
async def admin_undo_resolve(league_id: int, admin: dict = Depends(get_authenticated_admin)):
    """
    Bugun OCHIQ, lekin deadline o'tMAGAN turlardagi avtomatik 0:0 tasdiqlarni
    bekor qiladi (qayta 'pending'). draw_date'ga TEGMAYDI — deadline o'tib
    tasdiqlangan turlar (masalan 1-2) va qo'lda natijalar SAQLANADI.

    Masalan LaLiga: 1-2 (deadline o'tgan) tasdiq qoladi, 3-4 (bugun ochiq) noto'g'ri
    0:0 tasdiqlangan bo'lsa → qayta pending (o'yinchilar bugun o'ynaydi).

    Xato holatlari: league_not_found → 404
    """
    league = get_league_by_id(league_id)
    if league is None:
        raise HTTPException(status_code=404, detail="league_not_found")

    deadline_md = get_deadline_passed_matchday(league_id)  # bugun tasdiq bo'lishi kerak (1-2)
    open_md = get_open_matchday(league_id)                 # bugun ochiq (3-4 ham)

    # (deadline_md, open_md] oralig'idagi xato natijalarni qaytaramiz:
    #  - 0:0 avtomatik CONFIRMED (auto-resolve qilingan)
    #  - awaiting_confirmation (kimdir kiritgan, raqib tasdiqlamagan — o'ynalmagan o'yin)
    # Tasdiqlangan haqiqiy (0:0 emas) natijalar SAQLANADI.
    reopened = 0
    if open_md > deadline_md:
        reopened += reopen_matchday_range(league_id, deadline_md, open_md)
        reopened += reset_awaiting_in_range(league_id, deadline_md, open_md)

    return {"status": "ok", "league_id": league_id, "reopened": reopened,
            "from_md": deadline_md, "to_md": open_md}
