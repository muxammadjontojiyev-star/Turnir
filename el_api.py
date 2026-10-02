"""
el_api.py — Yevropa ligasi (YeL) API endpointlari (FastAPI APIRouter).

Nega alohida fayl (qoida #19/#21): api.py 3000+ qator; YeL endpointlari
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

logger = logging.getLogger("el_api")
router = APIRouter()


def get_authenticated_el_admin(x_telegram_init_data: str = Header(...)) -> dict:
    """
    YeL admini: bosh admin YOKI 'el' scope'ga tayinlangan admin
    (get_authenticated_cl_admin bilan bir xil). Tayinlashni faqat bosh admin
    qiladi — mavjud /admin/roles/el endpointlari orqali (YeL tabidan).
    """
    from admin_roles import SCOPE_EL
    return _authenticated_scope_admin(x_telegram_init_data, SCOPE_EL)


# ============ Kvalifikatsiya / ishtirokchilar ============

@router.get("/el/qualifiers")
def el_qualifiers(user: dict = Depends(get_authenticated_user)):
    """YeL kvalifikantlari (oxirgi yakunlangan mavsum). me_qualified — so'rovchi kvalifikantmi."""
    from el_qualification import get_el_qualifiers, is_el_qualifier
    data = get_el_qualifiers()
    data["me_qualified"] = is_el_qualifier(user["telegram_id"], data["from_season"])
    return data


@router.get("/el/groups")
def el_groups(user: dict = Depends(get_authenticated_user)):
    """
    YeL ishtirokchilari. Avval sinxron: kvalifikant yangi mavsumda istalgan klub
    bilan ro'yxatdan o'tgan bo'lsa — telegram_id orqali avtomatik qo'shiladi.
    me_participant — so'rovchi YeL ishtirokchisimi.
    """
    from el_core import el_get_groups, el_sync_participants
    el_sync_participants()
    data = el_get_groups()
    data["me_participant"] = any(
        p["telegram_id"] == user["telegram_id"] for p in data["participants"]
    )
    return data


@router.get("/el/rating-all")
def el_rating_all(user: dict = Depends(get_authenticated_user)):
    """YeL yagona umumiy reyting (javob shakli /cl/rating-all bilan bir xil)."""
    from el_core import EL_LEAGUE_GROUP, el_group_rating
    rows = el_group_rating(EL_LEAGUE_GROUP)
    groups = [{"group_number": EL_LEAGUE_GROUP, "rating": rows}] if rows else []
    return {"groups": groups}


@router.get("/el/cup-holder")
def el_cup_holder():
    """YeL kubogi egasi (Sovrinlar sahifasi). Ochiq — /cl/cup-holder bilan bir xil."""
    from el_finalize import get_el_cup_holder
    return get_el_cup_holder()


# ============ Turlar ============

@router.get("/el/state")
def el_state(user: dict = Depends(get_authenticated_user)):
    """YeL tur holati: started, current_matchday, total_matchdays, finished, stale."""
    from el_rounds import el_get_state
    return el_get_state()


@router.post("/el/draw")
def el_draw_endpoint(admin: dict = Depends(get_authenticated_super_admin)):
    """YeL Swiss qur'asi (bosh admin). Xato: already_drawn, no_participants -> 400"""
    from el_core import el_draw, el_sync_participants
    el_sync_participants()
    success, result = el_draw()
    if not success:
        raise HTTPException(status_code=400, detail=result)
    return {"status": "ok", **result}


@router.post("/el/rounds/start")
def el_rounds_start(admin: dict = Depends(get_authenticated_super_admin)):
    """YeL turlarini boshlash (bosh admin): 1-tur ochiladi. Xato: not_drawn, already_started -> 400"""
    from el_rounds import el_start_rounds
    success, result = el_start_rounds()
    if not success:
        raise HTTPException(status_code=400, detail=result)
    return {"status": "ok", **result}


@router.post("/el/admin/group/force-close")
def el_admin_group_force_close(admin: dict = Depends(get_authenticated_super_admin)):
    """
    Bosh admin liga bosqichini DARHOL yopadi (faqat bosqich tugagan bo'lsa).
    Xato: not_started, not_drawn, group_not_over, force_close_failed -> 400
    """
    from el_rounds import el_force_close_group
    ok, reason, info = el_force_close_group()
    if not ok:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": "ok", **info}


# ============ O'yinlar / natija ============

@router.get("/el/matches/my")
def el_my_matches(user: dict = Depends(get_authenticated_user)):
    """Foydalanuvchining YeL o'yinlari (joriy mavsum) + tur holati."""
    from el_matches_queries import el_get_user_matches
    from el_rounds import el_get_state
    from season_prizes import get_league_season
    season = get_league_season()
    return {"me_id": user["id"],
            "state": el_get_state(season),
            "matches": el_get_user_matches(user["id"], season)}


@router.get("/el/matches/user/{target_id}")
def el_user_matches(target_id: int, user: dict = Depends(get_authenticated_user)):
    """Boshqa ishtirokchining YeL o'yinlari (faqat o'qish; me_id yuborilmaydi)."""
    from el_matches_queries import el_get_user_matches
    from season_prizes import get_league_season
    return {"matches": el_get_user_matches(target_id, get_league_season())}


@router.post("/el/match/submit-result")
def el_submit(match_id: int, score1: int, score2: int,
              user: dict = Depends(get_authenticated_user)):
    """YeL natijasini kiritish. Faqat ochiq tur (server tekshiruvi — qoida #41)."""
    validate_scores(score1, score2)
    from el_matches_queries import el_get_match_by_id, el_submit_match_result
    from el_rounds import el_matchday_open
    match = el_get_match_by_id(match_id)
    if not match:
        raise HTTPException(status_code=400, detail="match_not_found")
    if not el_matchday_open(match["matchday"], match["season"]):
        raise HTTPException(status_code=400, detail="matchday_locked")
    success, reason = el_submit_match_result(match_id, score1, score2, user["id"])
    if not success:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": reason, "match_id": match_id}


@router.post("/el/match/confirm")
def el_confirm(match_id: int, accept: bool = True,
               user: dict = Depends(get_authenticated_user)):
    """YeL natijani tasdiqlash (accept=True) yoki rad etish (False)."""
    from el_matches_queries import el_confirm_or_reject_match
    success, reason = el_confirm_or_reject_match(
        match_id, "confirm" if accept else "reject", user["id"])
    if not success:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": "ok", "match_id": match_id}


# ============ Profil / to'purarlar ============

@router.get("/el/profile")
def el_profile(user: dict = Depends(get_authenticated_user)):
    """YeL profil kartochkasi — faqat SO'ROVCHINING o'zi (qoida #34)."""
    from el_profile import el_get_profile
    from season_prizes import get_league_season
    return el_get_profile(user["id"], get_league_season())


@router.get("/el/scorers")
def el_scorers(user: dict = Depends(get_authenticated_user)):
    """YeL to'purarlari (confirmed o'yinlar bo'yicha urilgan gollar)."""
    from el_scorers import el_top_scorers
    from season_prizes import get_league_season
    return {"scorers": el_top_scorers(get_league_season())}


# ============ Chat (liga/ChL webchat modali bilan bir xil format) ============
# MUHIM: /el/matches/unread — /el/matches/{match_id}/... dan farqli yo'l (segment soni
# har xil), shuning uchun tartib to'qnashuvi yo'q.

async def notify_el_chat(notify: dict | None) -> None:
    """Raqibga chat bildirishnomasi (guruh va play-off chati uchun umumiy — qoida #26)."""
    if notify is None:
        return
    try:
        recipient = get_user_by_telegram_id(notify["recipient_telegram_id"])
        lang = recipient.get("language") if recipient else None
        await notify_user(
            notify["recipient_telegram_id"], "notify_chat_message", lang,
            open_button_key="btn_open_app",
            mode=t("mode_name_el", lang),
            preview=notify["text_preview"],
        )
    except Exception as exc:
        logger.warning("YeL chat bildirishnomasi yuborilmadi: %s", exc)


@router.get("/el/matches/unread")
def el_unread(user: dict = Depends(get_authenticated_user)):
    """
    O'qilmagan YeL chat xabarlari: {"total", "by_match"} (liga formati).
    Play-off xabarlari ham qo'shiladi — kalitlari "p{id}" (ChL bilan bir xil).
    """
    from el_chat import el_count_unread
    group = el_count_unread(user["id"], "group")
    po = el_count_unread(user["id"], "po")
    return {"total": group["total"] + po["total"],
            "by_match": {**group["by_match"], **po["by_match"]}}


@router.get("/el/matches/{match_id}/messages")
def el_chat_get(match_id: int, user: dict = Depends(get_authenticated_user)):
    from el_chat import el_get_messages
    msgs = el_get_messages(match_id, user["id"])
    if msgs is None:
        raise HTTPException(status_code=403, detail="chat_no_access")
    return {"messages": msgs}


@router.post("/el/matches/{match_id}/messages")
async def el_chat_send(match_id: int, text: str = Body(..., embed=True),
                       user: dict = Depends(get_authenticated_user)):
    """YeL chatiga xabar. Body: {"text": "..."}. Raqibga bot bildirishnomasi."""
    from el_chat import el_send_message
    success, reason, notify = el_send_message(match_id, user["id"], text)
    if not success:
        raise HTTPException(status_code=400, detail=reason)
    await notify_el_chat(notify)
    return {"status": "ok", "profanity": contains_profanity(text)}


@router.post("/el/matches/{match_id}/typing")
def el_chat_typing(match_id: int, user: dict = Depends(get_authenticated_user)):
    from el_chat import el_set_typing
    if not el_set_typing(match_id, user["id"]):
        raise HTTPException(status_code=403, detail="chat_no_access")
    return {"status": "ok"}


@router.get("/el/matches/{match_id}/state")
def el_chat_state(match_id: int, user: dict = Depends(get_authenticated_user)):
    from el_chat import el_get_chat_state
    state = el_get_chat_state(match_id, user["id"])
    if state is None:
        raise HTTPException(status_code=403, detail="chat_no_access")
    return state
