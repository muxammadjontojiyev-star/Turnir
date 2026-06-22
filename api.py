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
from urllib.parse import parse_qsl

import httpx
from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response

from config import BOT_TOKEN, ADMIN_TELEGRAM_IDS
from queries import (
    get_all_leagues, get_user_by_telegram_id, get_or_create_user,
    get_league_by_id, count_league_players, get_user_registration,
    register_user_to_league, update_user_nickname, get_taken_clubs,
    get_user_matches, submit_match_result, confirm_or_reject_match,
    get_all_users_with_registration, remove_user_completely,
    get_rejected_matches, admin_resolve_match, admin_fix_confirmed_match,
    get_user_by_id,
)
from rating import calculate_league_rating, get_player_position

app = FastAPI(title="eFootball Turnir Bot API")

# WebApp boshqa origin'dan so'rov yuborgani uchun CORS kerak
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# static/ papkasini serve qilish — WebApp HTML/CSS/JS
app.mount("/webapp", StaticFiles(directory="static", html=True), name="static")


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

        if computed_hash != received_hash:
            raise ValueError("hash mos kelmadi")

        user_json = parsed.get("user")
        if not user_json:
            raise ValueError("user ma'lumoti topilmadi")

        return json.loads(user_json)

    except Exception as exc:
        raise HTTPException(status_code=401, detail="Noto'g'ri Telegram autentifikatsiya") from exc


def get_authenticated_user(x_telegram_init_data: str = Header(...)) -> dict:
    """
    FastAPI dependency: initData'ni tekshiradi va DB'dagi user yozuvini qaytaradi.

    Foydalanuvchi DB'da topilmasa — avtomatik yaratadi (nickname = first_name).
    """
    telegram_user = verify_telegram_init_data(x_telegram_init_data)
    telegram_id   = telegram_user["id"]
    first_name    = telegram_user.get("first_name", f"user_{telegram_id}")

    user = get_or_create_user(telegram_id, first_name)
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
    return get_or_create_user(telegram_id, first_name)


# ============ GET /leagues ============

@app.get("/leagues")
def list_leagues():
    """Barcha ligalarni va ularning to'lganlik holatini qaytaradi."""
    leagues = get_all_leagues()
    result = []
    for league in leagues:
        current_count = count_league_players(league["id"])
        result.append({
            "id": league["id"],
            "name": league["name"],
            "status": league["status"],
            "max_players": league["max_players"],
            "current_players": current_count,
            "is_full": current_count >= league["max_players"],
        })
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
        "matches": get_user_matches(user_id),
    }


# ============ GET /players/{user_id}/photo ============

@app.get("/players/{user_id}/photo")
async def get_player_photo(user_id: int):
    """
    O'yinchining Telegram profil rasmini qaytaradi (bot token orqali, proxy).

    Auth talab qilinmaydi — bu <img src> orqali yuklanadi (header yuborib bo'lmaydi)
    va rasm allaqachon ommaviy profil (reyting jadvalida ko'rinadigan o'yinchi)
    qismi. Bot token URL'da oshkor bo'lmasligi uchun rasm baytlari server orqali
    uzatiladi. Rasm yo'q, maxfiy yoki xato bo'lsa — 404 (frontend ism harfini ko'rsatadi).
    """
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
                raise HTTPException(status_code=404, detail="no_photo")

            # Eng kichik o'lchamni olamiz (avatar uchun yetarli, tez yuklanadi)
            file_id = photos[0][0]["file_id"]

            # 2) file_path olish
            r2 = await client.get(f"{base}/getFile", params={"file_id": file_id})
            file_path = r2.json().get("result", {}).get("file_path")
            if not file_path:
                raise HTTPException(status_code=404, detail="no_file_path")

            # 3) Haqiqiy rasmni yuklab olish
            r3 = await client.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}")
            if r3.status_code != 200:
                raise HTTPException(status_code=404, detail="photo_fetch_failed")

            media_type = r3.headers.get("content-type", "image/jpeg")
            return Response(content=r3.content, media_type=media_type)

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=404, detail="photo_unavailable")


# ============ GET /prizes/{league_id} ============

@app.get("/prizes/{league_id}")
def get_prizes(league_id: int):
    """Liga uchun sovrin holatini qaytaradi: eng ko'p gol urgan va joriy lider."""
    league = get_league_by_id(league_id)
    if league is None:
        raise HTTPException(status_code=404, detail="Liga topilmadi")

    rating = calculate_league_rating(league_id)

    top_scorer = max(rating, key=lambda p: p["goals_for"], default=None) if rating else None
    leader = rating[0] if rating else None

    return {
        "league": league["name"],
        "top_scorer": top_scorer,
        "current_leader": leader,
    }


# ============ POST /register ============

@app.post("/register")
def register(league_id: int, club_name: str | None = None, user: dict = Depends(get_authenticated_user)):
    """
    Foydalanuvchini ligaga ro'yxatdan o'tkazadi.

    Query param: league_id (int), club_name (str, ixtiyoriy)
    Xato holatlari: already_registered, league_full, league_not_found, club_taken → 400
    """
    success, reason = register_user_to_league(user["id"], league_id, club_name)
    if not success:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": "ok", "league_id": league_id}


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
    """Joriy foydalanuvchining barcha matchlarini qaytaradi."""
    matches = get_user_matches(user["id"])
    return {"user_id": user["id"], "matches": matches}


# ============ POST /match/submit-result ============

@app.post("/match/submit-result")
def submit_result(
    match_id: int,
    score1: int,
    score2: int,
    user: dict = Depends(get_authenticated_user),
):
    """
    Match natijasini kiritadi.

    Query params: match_id, score1, score2
    Faqat o'sha matchning player1 yoki player2 kira oladi.
    Xato holatlari: match_not_found, not_participant, already_submitted → 400
    """
    if score1 < 0 or score2 < 0:
        raise HTTPException(status_code=400, detail="score_negative")
    success, reason = submit_match_result(match_id, score1, score2, user["id"])
    if not success:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": "ok", "match_id": match_id}


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
    Xato holatlari: match_not_found, not_opponent, wrong_status, invalid_action → 400
    """
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
    success, reason = admin_resolve_match(match_id, action, score1, score2)
    if not success:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": "ok", "match_id": match_id, "action": action}


# ============ POST /admin/match/fix-confirmed ============

@app.post("/admin/match/fix-confirmed")
def admin_fix_confirmed(
    match_id: int,
    score1: int,
    score2: int,
    admin: dict = Depends(get_authenticated_admin),
):
    """
    Admin allaqachon 'confirmed' bo'lgan matchning noto'g'ri natijasini
    qo'lda tuzatadi (status o'zgarmaydi, faqat score yangilanadi).

    Query params: match_id, score1, score2
    Xato holatlari: match_not_found, wrong_status → 400
    """
    success, reason = admin_fix_confirmed_match(match_id, score1, score2)
    if not success:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": "ok", "match_id": match_id}
