"""
co_api.py — Konferensiya ligasi (KL) API endpointlari (FastAPI APIRouter).

Nega alohida fayl (qoida #19/#21): api.py 3000+ qator; KL endpointlari
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

logger = logging.getLogger("co_api")
router = APIRouter()


def get_authenticated_co_admin(x_telegram_init_data: str = Header(...)) -> dict:
    """
    KL admini: bosh admin YOKI 'co' scope'ga tayinlangan admin
    (get_authenticated_cl_admin bilan bir xil). Tayinlashni faqat bosh admin
    qiladi — mavjud /admin/roles/co endpointlari orqali (KL tabidan).
    """
    from admin_roles import SCOPE_CO
    return _authenticated_scope_admin(x_telegram_init_data, SCOPE_CO)


# ============ Kvalifikatsiya / ishtirokchilar ============

@router.get("/co/qualifiers")
def co_qualifiers(user: dict = Depends(get_authenticated_user)):
    """KL kvalifikantlari (oxirgi yakunlangan mavsum). me_qualified — so'rovchi kvalifikantmi."""
    from co_qualification import get_co_qualifiers, is_co_qualifier
    data = get_co_qualifiers()
    data["me_qualified"] = is_co_qualifier(user["telegram_id"], data["from_season"])
    return data


@router.get("/co/groups")
def co_groups(user: dict = Depends(get_authenticated_user)):
    """
    KL ishtirokchilari. Avval sinxron: kvalifikant yangi mavsumda istalgan klub
    bilan ro'yxatdan o'tgan bo'lsa — telegram_id orqali avtomatik qo'shiladi.
    me_participant — so'rovchi KL ishtirokchisimi.
    """
    from co_core import co_get_groups, co_sync_participants
    co_sync_participants()
    data = co_get_groups()
    data["me_participant"] = any(
        p["telegram_id"] == user["telegram_id"] for p in data["participants"]
    )
    return data


@router.get("/co/rating-all")
def co_rating_all(user: dict = Depends(get_authenticated_user)):
    """KL yagona umumiy reyting (javob shakli /cl/rating-all bilan bir xil)."""
    from co_core import CO_LEAGUE_GROUP, co_group_rating
    rows = co_group_rating(CO_LEAGUE_GROUP)
    groups = [{"group_number": CO_LEAGUE_GROUP, "rating": rows}] if rows else []
    return {"groups": groups}


@router.get("/co/cup-holder")
def co_cup_holder():
    """KL kubogi egasi (Sovrinlar sahifasi). Ochiq — /cl/cup-holder bilan bir xil."""
    from co_finalize import get_co_cup_holder
    return get_co_cup_holder()


# ============ Turlar ============

@router.get("/co/state")
def co_state(user: dict = Depends(get_authenticated_user)):
    """KL tur holati: started, current_matchday, total_matchdays, finished, stale."""
    from co_rounds import co_get_state
    return co_get_state()


@router.post("/co/draw")
def co_draw_endpoint(admin: dict = Depends(get_authenticated_super_admin)):
    """KL Swiss qur'asi (bosh admin). Xato: already_drawn, no_participants -> 400"""
    from co_core import co_draw, co_sync_participants
    co_sync_participants()
    success, result = co_draw()
    if not success:
        raise HTTPException(status_code=400, detail=result)
    return {"status": "ok", **result}


@router.post("/co/rounds/start")
def co_rounds_start(admin: dict = Depends(get_authenticated_super_admin)):
    """KL turlarini boshlash (bosh admin): 1-tur ochiladi. Xato: not_drawn, already_started -> 400"""
    from co_rounds import co_start_rounds
    success, result = co_start_rounds()
    if not success:
        raise HTTPException(status_code=400, detail=result)
    return {"status": "ok", **result}


@router.post("/co/admin/group/force-close")
def co_admin_group_force_close(admin: dict = Depends(get_authenticated_super_admin)):
    """
    Bosh admin liga bosqichini DARHOL yopadi (faqat bosqich tugagan bo'lsa).
    Xato: not_started, not_drawn, group_not_over, force_close_failed -> 400
    """
    from co_rounds import co_force_close_group
    ok, reason, info = co_force_close_group()
    if not ok:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": "ok", **info}


# ============ O'yinlar / natija ============

@router.get("/co/matches/my")
def co_my_matches(user: dict = Depends(get_authenticated_user)):
    """Foydalanuvchining KL o'yinlari (joriy mavsum) + tur holati."""
    from co_matches_queries import co_get_user_matches
    from co_rounds import co_get_state
    from season_prizes import get_league_season
    season = get_league_season()
    return {"me_id": user["id"],
            "state": co_get_state(season),
            "matches": co_get_user_matches(user["id"], season)}


@router.get("/co/matches/user/{target_id}")
def co_user_matches(target_id: int, user: dict = Depends(get_authenticated_user)):
    """Boshqa ishtirokchining KL o'yinlari (faqat o'qish; me_id yuborilmaydi)."""
    from co_matches_queries import co_get_user_matches
    from season_prizes import get_league_season
    return {"matches": co_get_user_matches(target_id, get_league_season())}


@router.post("/co/match/submit-result")
def co_submit(match_id: int, score1: int, score2: int,
              user: dict = Depends(get_authenticated_user)):
    """KL natijasini kiritish. Faqat ochiq tur (server tekshiruvi — qoida #41)."""
    validate_scores(score1, score2)
    from co_matches_queries import co_get_match_by_id, co_submit_match_result
    from co_rounds import co_matchday_open
    match = co_get_match_by_id(match_id)
    if not match:
        raise HTTPException(status_code=400, detail="match_not_found")
    if not co_matchday_open(match["matchday"], match["season"]):
        raise HTTPException(status_code=400, detail="matchday_locked")
    success, reason = co_submit_match_result(match_id, score1, score2, user["id"])
    if not success:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": reason, "match_id": match_id}


@router.post("/co/match/confirm")
def co_confirm(match_id: int, accept: bool = True,
               user: dict = Depends(get_authenticated_user)):
    """KL natijani tasdiqlash (accept=True) yoki rad etish (False)."""
    from co_matches_queries import co_confirm_or_reject_match
    success, reason = co_confirm_or_reject_match(
        match_id, "confirm" if accept else "reject", user["id"])
    if not success:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": "ok", "match_id": match_id}


# ============ Profil / to'purarlar ============

@router.get("/co/profile")
def co_profile(user: dict = Depends(get_authenticated_user)):
    """KL profil kartochkasi — faqat SO'ROVCHINING o'zi (qoida #34)."""
    from co_profile import co_get_profile
    from season_prizes import get_league_season
    return co_get_profile(user["id"], get_league_season())


@router.get("/co/scorers")
def co_scorers(user: dict = Depends(get_authenticated_user)):
    """KL to'purarlari (confirmed o'yinlar bo'yicha urilgan gollar)."""
    from co_scorers import co_top_scorers
    from season_prizes import get_league_season
    return {"scorers": co_top_scorers(get_league_season())}


# ============ Chat (liga/ChL webchat modali bilan bir xil format) ============
# MUHIM: /co/matches/unread — /co/matches/{match_id}/... dan farqli yo'l (segment soni
# har xil), shuning uchun tartib to'qnashuvi yo'q.

async def notify_co_chat(notify: dict | None) -> None:
    """Raqibga chat bildirishnomasi (guruh va play-off chati uchun umumiy — qoida #26)."""
    if notify is None:
        return
    try:
        recipient = get_user_by_telegram_id(notify["recipient_telegram_id"])
        lang = recipient.get("language") if recipient else None
        await notify_user(
            notify["recipient_telegram_id"], "notify_chat_message", lang,
            open_button_key="btn_open_app",
            mode=t("mode_name_co", lang),
            preview=notify["text_preview"],
        )
    except Exception as exc:
        logger.warning("KL chat bildirishnomasi yuborilmadi: %s", exc)


@router.get("/co/matches/unread")
def co_unread(user: dict = Depends(get_authenticated_user)):
    """
    O'qilmagan KL chat xabarlari: {"total", "by_match"} (liga formati).
    Play-off xabarlari ham qo'shiladi — kalitlari "p{id}" (ChL bilan bir xil).
    """
    from co_chat import co_count_unread
    group = co_count_unread(user["id"], "group")
    po = co_count_unread(user["id"], "po")
    return {"total": group["total"] + po["total"],
            "by_match": {**group["by_match"], **po["by_match"]}}


@router.get("/co/matches/{match_id}/messages")
def co_chat_get(match_id: int, user: dict = Depends(get_authenticated_user)):
    from co_chat import co_get_messages
    msgs = co_get_messages(match_id, user["id"])
    if msgs is None:
        raise HTTPException(status_code=403, detail="chat_no_access")
    return {"messages": msgs}


@router.post("/co/matches/{match_id}/messages")
async def co_chat_send(match_id: int, text: str = Body(..., embed=True),
                       user: dict = Depends(get_authenticated_user)):
    """KL chatiga xabar. Body: {"text": "..."}. Raqibga bot bildirishnomasi."""
    from co_chat import co_send_message
    success, reason, notify = co_send_message(match_id, user["id"], text)
    if not success:
        raise HTTPException(status_code=400, detail=reason)
    await notify_co_chat(notify)
    return {"status": "ok", "profanity": contains_profanity(text)}


@router.post("/co/matches/{match_id}/typing")
def co_chat_typing(match_id: int, user: dict = Depends(get_authenticated_user)):
    from co_chat import co_set_typing
    if not co_set_typing(match_id, user["id"]):
        raise HTTPException(status_code=403, detail="chat_no_access")
    return {"status": "ok"}


@router.get("/co/matches/{match_id}/state")
def co_chat_state(match_id: int, user: dict = Depends(get_authenticated_user)):
    from co_chat import co_get_chat_state
    state = co_get_chat_state(match_id, user["id"])
    if state is None:
        raise HTTPException(status_code=403, detail="chat_no_access")
    return state
