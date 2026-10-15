"""
tb_api_chat.py — "TEAMLAR JANGI": 1v1 o'yin chati (APIRouter, 2026-10-16, 3-bosqich).
Endpointlar api.js openWebChat kutgan shaklda (prefiks /tb/matches). Mantiq: tb_chat.py.
MUHIM: /tb/matches/unread — /tb/matches/{id}/... dan OLDIN e'lon qilingan (aniq yo'l).
"""

import logging

from fastapi import APIRouter, Body, Depends, HTTPException

from api import get_authenticated_user
from profanity import contains_profanity

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/tb/matches/unread")
def tb_unread(user: dict = Depends(get_authenticated_user)):
    from tb_chat import tb_count_unread
    return tb_count_unread(user["id"])


@router.get("/tb/matches/{match_id}/messages")
def tb_chat_get(match_id: int, user: dict = Depends(get_authenticated_user)):
    from tb_chat import tb_get_messages
    msgs = tb_get_messages(match_id, user["id"])
    if msgs is None:
        raise HTTPException(status_code=403, detail="chat_no_access")
    return {"messages": msgs}


@router.post("/tb/matches/{match_id}/messages")
async def tb_chat_send(match_id: int, text: str = Body(..., embed=True),
                       user: dict = Depends(get_authenticated_user)):
    from tb_chat import tb_send_message
    ok, reason, notify = tb_send_message(match_id, user["id"], text)
    if not ok:
        raise HTTPException(status_code=400, detail=reason)
    if notify:
        from notify import notify_user
        from texts import t
        try:
            await notify_user(notify["recipient_telegram_id"], "notify_chat_message", notify["language"],
                              open_button_key="btn_open_app", mode=t("mode_name_tb", notify["language"]),
                              preview=notify["text_preview"])
        except Exception as exc:
            logger.warning("TB chat xabari yuborilmadi: %s", exc)
    return {"status": "ok", "profanity": contains_profanity(text)}


@router.post("/tb/matches/{match_id}/typing")
def tb_chat_typing(match_id: int, user: dict = Depends(get_authenticated_user)):
    from tb_chat import tb_set_typing
    if not tb_set_typing(match_id, user["id"]):
        raise HTTPException(status_code=403, detail="chat_no_access")
    return {"status": "ok"}


@router.get("/tb/matches/{match_id}/state")
def tb_chat_state_ep(match_id: int, user: dict = Depends(get_authenticated_user)):
    from tb_chat import tb_chat_state
    s = tb_chat_state(match_id, user["id"])
    if s is None:
        raise HTTPException(status_code=403, detail="chat_no_access")
    return s
