"""
pt_api_chat.py — SHAXSIY turnir: o'yin chati + tashkilotchi natija tuzatishi (4b, APIRouter).
Chat endpointlari api.js openWebChat kutgan shaklda (prefiks /pt/matches).
"""

import logging

from fastapi import APIRouter, Body, Depends, HTTPException

from api import get_authenticated_user, validate_scores
from profanity import contains_profanity

logger = logging.getLogger("pt_api_chat")
router = APIRouter()


@router.get("/pt/matches/unread")
def pt_unread(user: dict = Depends(get_authenticated_user)):
    from pt_chat import pt_count_unread
    return pt_count_unread(user["id"])


@router.get("/pt/matches/{match_id}/messages")
def pt_chat_get(match_id: int, user: dict = Depends(get_authenticated_user)):
    from pt_chat import pt_get_messages
    msgs = pt_get_messages(match_id, user["id"])
    if msgs is None:
        raise HTTPException(status_code=403, detail="chat_no_access")
    return {"messages": msgs}


@router.post("/pt/matches/{match_id}/messages")
async def pt_chat_send(match_id: int, text: str = Body(..., embed=True),
                       user: dict = Depends(get_authenticated_user)):
    from pt_chat import pt_send_message
    ok, reason, notify = pt_send_message(match_id, user["id"], text)
    if not ok:
        raise HTTPException(status_code=400, detail=reason)
    if notify:
        from notify import notify_user
        from texts import t
        try:
            await notify_user(notify["recipient_telegram_id"], "notify_chat_message", notify["language"],
                              open_button_key="btn_open_app", mode=t("mode_name_pt", notify["language"]),
                              preview=notify["text_preview"])
        except Exception as exc:
            logger.warning("PT chat xabari yuborilmadi: %s", exc)
    return {"status": "ok", "profanity": contains_profanity(text)}


@router.post("/pt/matches/{match_id}/typing")
def pt_chat_typing(match_id: int, user: dict = Depends(get_authenticated_user)):
    from pt_chat import pt_set_typing
    if not pt_set_typing(match_id, user["id"]):
        raise HTTPException(status_code=403, detail="chat_no_access")
    return {"status": "ok"}


@router.get("/pt/matches/{match_id}/state")
def pt_chat_state_ep(match_id: int, user: dict = Depends(get_authenticated_user)):
    from pt_chat import pt_chat_state
    s = pt_chat_state(match_id, user["id"])
    if s is None:
        raise HTTPException(status_code=403, detail="chat_no_access")
    return s


# ============ Tashkilotchi: natijani tuzatish ============

@router.get("/pt/owner/match/{match_id}")
def pt_owner_info(match_id: int, user: dict = Depends(get_authenticated_user)):
    from pt_owner_fix import pt_owner_match_info
    ok, r = pt_owner_match_info(match_id, user["id"])
    if not ok:
        raise HTTPException(status_code=400, detail=r)
    return r


@router.post("/pt/owner/match/{match_id}/set")
async def pt_owner_set(match_id: int, score1: int = Body(..., embed=True), score2: int = Body(..., embed=True),
                 user: dict = Depends(get_authenticated_user)):
    validate_scores(score1, score2)
    from pt_owner_fix import pt_owner_set_result
    ok, r = pt_owner_set_result(match_id, user["id"], score1, score2)
    if not ok:
        raise HTTPException(status_code=400, detail=r)
    if r["advance"].get("event"):                     # final yaratildi/yangilandi yoki chempion
        from pt_notify import notify_advance, spawn, tournament_members
        name, members = tournament_members(r["tournament_id"])
        spawn(notify_advance(name, members, r["advance"]))
    return {"status": "ok", "event": r["advance"].get("event")}


@router.post("/pt/owner/match/{match_id}/cancel")
def pt_owner_cancel_ep(match_id: int, user: dict = Depends(get_authenticated_user)):
    from pt_owner_fix import pt_owner_cancel
    ok, r = pt_owner_cancel(match_id, user["id"])
    if not ok:
        raise HTTPException(status_code=400, detail=r)
    return {"status": "ok"}
