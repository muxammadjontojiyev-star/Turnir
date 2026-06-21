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

from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import BOT_TOKEN
from queries import (
    get_all_leagues, get_user_by_telegram_id, get_or_create_user,
    get_league_by_id, count_league_players, get_user_registration,
    register_user_to_league, update_user_nickname, get_taken_clubs,
    get_user_matches, submit_match_result, confirm_or_reject_match,
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
