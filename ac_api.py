"""
ac_api.py — Osiyo Chempionlar ligasi (OChL) API endpointlari (FastAPI APIRouter).

Nega alohida fayl (qoida #19/#21): api.py 3000+ qator; OChL endpointlari
bir joyda jamlanadi. api.py OXIRIDA app.include_router(router) qilinadi.

Import tartibi: bu modul api.py ning eng oxiridan import qilinadi — o'sha
paytda get_authenticated_user / get_authenticated_super_admin allaqachon
e'lon qilingan bo'ladi (api modul sys.modules'da), shuning uchun aylanma
import xavfsiz. api.py'dagi auth/rate-limit dependency'lari qayta ishlatiladi
(DRY, qoida #26) — ChL endpointlari bilan bir xil himoya.
"""

import logging

from fastapi import APIRouter, Body, Depends, Header, HTTPException

from api import (
    _authenticated_scope_admin,
    get_authenticated_super_admin,
    get_authenticated_user,
    validate_scores,
)
from notify import notify_user
from profanity import contains_profanity
from queries import get_user_by_telegram_id
from texts import t

logger = logging.getLogger("ac_api")
router = APIRouter()


def get_authenticated_ac_admin(x_telegram_init_data: str = Header(...)) -> dict:
    """
    OChL admini: bosh admin YOKI 'ac' scope'ga tayinlangan admin
    (get_authenticated_cl_admin bilan bir xil). Tayinlashni faqat bosh admin
    qiladi — mavjud /admin/roles/ac endpointlari orqali (OChL tabidan).
    """
    from admin_roles import SCOPE_AC
    return _authenticated_scope_admin(x_telegram_init_data, SCOPE_AC)


# ============ Kvalifikatsiya / ishtirokchilar ============

@router.get("/ac/qualifiers")
def ac_qualifiers(user: dict = Depends(get_authenticated_user)):
    """OChL kvalifikantlari (oxirgi yakunlangan mavsum). me_qualified — so'rovchi kvalifikantmi."""
    from ac_qualification import get_ac_qualifiers, is_ac_qualifier
    data = get_ac_qualifiers()
    data["me_qualified"] = is_ac_qualifier(user["telegram_id"], data["from_season"])
    return data


@router.get("/ac/groups")
def ac_groups(user: dict = Depends(get_authenticated_user)):
    """
    OChL ishtirokchilari. Avval sinxron: kvalifikant yangi mavsumda istalgan klub
    bilan ro'yxatdan o'tgan bo'lsa — telegram_id orqali avtomatik qo'shiladi.
    me_participant — so'rovchi OChL ishtirokchisimi.
    """
    from ac_core import ac_get_groups, ac_sync_participants
    ac_sync_participants()
    data = ac_get_groups()
    data["me_participant"] = any(
        p["telegram_id"] == user["telegram_id"] for p in data["participants"]
    )
    return data


@router.get("/ac/rating-all")
def ac_rating_all(user: dict = Depends(get_authenticated_user)):
    """OChL yagona umumiy reyting (javob shakli /cl/rating-all bilan bir xil)."""
    from ac_core import AC_LEAGUE_GROUP, ac_group_rating
    rows = ac_group_rating(AC_LEAGUE_GROUP)
    groups = [{"group_number": AC_LEAGUE_GROUP, "rating": rows}] if rows else []
    return {"groups": groups}


@router.get("/ac/cup-holder")
def ac_cup_holder():
    """OChL kubogi egasi (Sovrinlar sahifasi). Ochiq — /cl/cup-holder bilan bir xil."""
    from ac_finalize import get_ac_cup_holder
    return get_ac_cup_holder()


# ============ Turlar ============

@router.get("/ac/state")
def ac_state(user: dict = Depends(get_authenticated_user)):
    """OChL tur holati: started, current_matchday, total_matchdays, finished, stale."""
    from ac_rounds import ac_get_state
    return ac_get_state()


@router.post("/ac/draw")
def ac_draw_endpoint(admin: dict = Depends(get_authenticated_super_admin)):
    """OChL Swiss qur'asi (bosh admin). Xato: already_drawn, no_participants -> 400"""
    from ac_core import ac_draw, ac_sync_participants
    ac_sync_participants()
    success, result = ac_draw()
    if not success:
        raise HTTPException(status_code=400, detail=result)
    return {"status": "ok", **result}


@router.post("/ac/rounds/start")
def ac_rounds_start(admin: dict = Depends(get_authenticated_super_admin)):
    """OChL turlarini boshlash (bosh admin): 1-tur ochiladi. Xato: not_drawn, already_started -> 400"""
    from ac_rounds import ac_start_rounds
    success, result = ac_start_rounds()
    if not success:
        raise HTTPException(status_code=400, detail=result)
    return {"status": "ok", **result}


@router.post("/ac/admin/group/force-close")
def ac_admin_group_force_close(admin: dict = Depends(get_authenticated_super_admin)):
    """
    Bosh admin liga bosqichini DARHOL yopadi (faqat bosqich tugagan bo'lsa).
    Xato: not_started, not_drawn, group_not_over, force_close_failed -> 400
    """
    from ac_rounds import ac_force_close_group
    ok, reason, info = ac_force_close_group()
    if not ok:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": "ok", **info}


# ============ O'yinlar / natija ============

@router.get("/ac/matches/my")
def ac_my_matches(user: dict = Depends(get_authenticated_user)):
    """Foydalanuvchining OChL o'yinlari (joriy mavsum) + tur holati."""
    from ac_matches_queries import ac_get_user_matches
    from ac_rounds import ac_get_state
    from season_prizes import get_league_season
    season = get_league_season()
    return {"me_id": user["id"],
            "state": ac_get_state(season),
            "matches": ac_get_user_matches(user["id"], season)}


@router.get("/ac/matches/user/{target_id}")
def ac_user_matches(target_id: int, user: dict = Depends(get_authenticated_user)):
    """Boshqa ishtirokchining OChL o'yinlari (faqat o'qish; me_id yuborilmaydi)."""
    from ac_matches_queries import ac_get_user_matches
    from season_prizes import get_league_season
    return {"matches": ac_get_user_matches(target_id, get_league_season())}


@router.post("/ac/match/submit-result")
def ac_submit(match_id: int, score1: int, score2: int,
              user: dict = Depends(get_authenticated_user)):
    """OChL natijasini kiritish. Faqat ochiq tur (server tekshiruvi — qoida #41)."""
    validate_scores(score1, score2)
    from ac_matches_queries import ac_get_match_by_id, ac_submit_match_result
    from ac_rounds import ac_matchday_open
    match = ac_get_match_by_id(match_id)
    if not match:
        raise HTTPException(status_code=400, detail="match_not_found")
    if not ac_matchday_open(match["matchday"], match["season"]):
        raise HTTPException(status_code=400, detail="matchday_locked")
    success, reason = ac_submit_match_result(match_id, score1, score2, user["id"])
    if not success:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": reason, "match_id": match_id}


@router.post("/ac/match/confirm")
def ac_confirm(match_id: int, accept: bool = True,
               user: dict = Depends(get_authenticated_user)):
    """OChL natijani tasdiqlash (accept=True) yoki rad etish (False)."""
    from ac_matches_queries import ac_confirm_or_reject_match
    success, reason = ac_confirm_or_reject_match(
        match_id, "confirm" if accept else "reject", user["id"])
    if not success:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": "ok", "match_id": match_id}


# ============ Profil / to'purarlar ============

@router.get("/ac/profile")
def ac_profile(user: dict = Depends(get_authenticated_user)):
    """OChL profil kartochkasi — faqat SO'ROVCHINING o'zi (qoida #34)."""
    from ac_profile import ac_get_profile
    from season_prizes import get_league_season
    return ac_get_profile(user["id"], get_league_season())


@router.get("/ac/scorers")
def ac_scorers(user: dict = Depends(get_authenticated_user)):
    """OChL to'purarlari (confirmed o'yinlar bo'yicha urilgan gollar)."""
    from ac_scorers import ac_top_scorers
    from season_prizes import get_league_season
    return {"scorers": ac_top_scorers(get_league_season())}


# ============ Chat (liga/ChL webchat modali bilan bir xil format) ============
# MUHIM: /ac/matches/unread — /ac/matches/{match_id}/... dan farqli yo'l (segment soni
# har xil), shuning uchun tartib to'qnashuvi yo'q.

async def notify_ac_chat(notify: dict | None) -> None:
    """Raqibga chat bildirishnomasi (guruh va play-off chati uchun umumiy — qoida #26)."""
    if notify is None:
        return
    try:
        recipient = get_user_by_telegram_id(notify["recipient_telegram_id"])
        lang = recipient.get("language") if recipient else None
        await notify_user(
            notify["recipient_telegram_id"], "notify_chat_message", lang,
            open_button_key="btn_open_app",
            mode=t("mode_name_ac", lang),
            preview=notify["text_preview"],
        )
    except Exception as exc:
        logger.warning("OChL chat bildirishnomasi yuborilmadi: %s", exc)


@router.get("/ac/matches/unread")
def ac_unread(user: dict = Depends(get_authenticated_user)):
    """
    O'qilmagan OChL chat xabarlari: {"total", "by_match"} (liga formati).
    Play-off xabarlari ham qo'shiladi — kalitlari "p{id}" (ChL bilan bir xil).
    """
    from ac_chat import ac_count_unread
    group = ac_count_unread(user["id"], "group")
    po = ac_count_unread(user["id"], "po")
    return {"total": group["total"] + po["total"],
            "by_match": {**group["by_match"], **po["by_match"]}}


@router.get("/ac/matches/{match_id}/messages")
def ac_chat_get(match_id: int, user: dict = Depends(get_authenticated_user)):
    from ac_chat import ac_get_messages
    msgs = ac_get_messages(match_id, user["id"])
    if msgs is None:
        raise HTTPException(status_code=403, detail="chat_no_access")
    return {"messages": msgs}


@router.post("/ac/matches/{match_id}/messages")
async def ac_chat_send(match_id: int, text: str = Body(..., embed=True),
                       user: dict = Depends(get_authenticated_user)):
    """OChL chatiga xabar. Body: {"text": "..."}. Raqibga bot bildirishnomasi."""
    from ac_chat import ac_send_message
    success, reason, notify = ac_send_message(match_id, user["id"], text)
    if not success:
        raise HTTPException(status_code=400, detail=reason)
    await notify_ac_chat(notify)
    return {"status": "ok", "profanity": contains_profanity(text)}


@router.post("/ac/matches/{match_id}/typing")
def ac_chat_typing(match_id: int, user: dict = Depends(get_authenticated_user)):
    from ac_chat import ac_set_typing
    if not ac_set_typing(match_id, user["id"]):
        raise HTTPException(status_code=403, detail="chat_no_access")
    return {"status": "ok"}


@router.get("/ac/matches/{match_id}/state")
def ac_chat_state(match_id: int, user: dict = Depends(get_authenticated_user)):
    from ac_chat import ac_get_chat_state
    state = ac_get_chat_state(match_id, user["id"])
    if state is None:
        raise HTTPException(status_code=403, detail="chat_no_access")
    return state
