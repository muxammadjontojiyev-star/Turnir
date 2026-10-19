"""
qm_api.py — TEZKOR O'YIN endpointlari (APIRouter, 2026-10-19). Mantiq: qm_core.py, qm_view.py, qm_chat.py.
api.py oxirida include_router. Chat endpointlari api.js openWebChat kutgan shaklda (prefiks /qm/matches).
"""

import logging

from fastapi import APIRouter, Body, Depends, HTTPException

from api import get_authenticated_user
from profanity import contains_profanity

logger = logging.getLogger(__name__)
router = APIRouter()


async def _notify(user_id: int, key: str, **fmt) -> None:
    """Bot xabari (xato bo'lsa — log; o'yin holati saqlanadi, qoida #37)."""
    try:
        from models import get_connection
        from notify import notify_user
        conn = get_connection()
        try:
            r = conn.cursor().execute("SELECT telegram_id, language FROM users WHERE id = ?", (user_id,)).fetchone()
        finally:
            conn.close()
        if r:
            await notify_user(r["telegram_id"], key, r["language"], open_button_key="btn_open_app", **fmt)
    except Exception as exc:
        logger.warning("Tezkor o'yin: xabar yuborilmadi (user=%s, %s): %s", user_id, key, exc)


def _who(user: dict) -> str:
    return "@" + user["username"] if user.get("username") else (user.get("nickname") or "")


def _fail(res: tuple):
    ok, data = res
    if not ok:
        raise HTTPException(status_code=400, detail=data)
    return data


@router.get("/qm/state")
def qm_state_ep(user: dict = Depends(get_authenticated_user)):
    from qm_chat import qm_count_unread
    from qm_view import qm_state
    st = qm_state(user["id"])
    st["unread"] = qm_count_unread(user["id"], st["match"]["id"] if st["match"] else None)
    return st


@router.post("/qm/search")
async def qm_search_ep(user: dict = Depends(get_authenticated_user)):
    from qm_core import QM_ROOM_MINUTES, qm_search
    res = qm_search(user["id"])
    if res.get("opponent_id"):                      # navbatda kutayotgan raqibga — "raqib topildi"
        await _notify(res["opponent_id"], "qm_notify_found", opp=_who(user), minutes=QM_ROOM_MINUTES)
    return res


@router.post("/qm/cancel")
def qm_cancel_ep(user: dict = Depends(get_authenticated_user)):
    from qm_core import qm_cancel
    return qm_cancel(user["id"])


@router.post("/qm/room")
async def qm_room_ep(match_id: int = Body(..., embed=True), code: str = Body(..., embed=True),
                     user: dict = Depends(get_authenticated_user)):
    """Xona ID: chatga yoziladi (room_code — dalil izi) va raqibga bot xabari; o'yin 'playing' ga o'tadi."""
    from qm_core import qm_room_allowed, qm_set_room
    from room_code import send_room_code
    _fail(qm_room_allowed(user["id"], match_id))
    ok, reason, info = send_room_code(match_id, user["id"], code, "qm")
    if not ok:
        raise HTTPException(status_code=400, detail=reason)
    _fail(qm_set_room(user["id"], match_id, info["code"]))
    try:
        from notify import notify_user
        from queries_users import get_user_by_telegram_id
        from texts import t
        rec = get_user_by_telegram_id(info["recipient_telegram_id"])
        lang = rec.get("language") if rec else None
        await notify_user(info["recipient_telegram_id"], "notify_room_code", lang, open_button_key="btn_open_app",
                          mode=t("mode_name_qm", lang), code=info["code"])
    except Exception as exc:
        logger.warning("Tezkor o'yin: xona ID xabari yuborilmadi: %s", exc)
    return {"status": "ok", "code": info["code"]}


@router.post("/qm/submit")
async def qm_submit_ep(my_score: int = Body(..., embed=True), opp_score: int = Body(..., embed=True),
                       user: dict = Depends(get_authenticated_user)):
    from qm_core import QM_CONFIRM_MINUTES, qm_submit
    data = _fail(qm_submit(user["id"], my_score, opp_score))
    await _notify(data["opponent_id"], "qm_notify_result", opp=_who(user), score=f"{opp_score}:{my_score}",
                  minutes=QM_CONFIRM_MINUTES)
    return {"status": "ok", **data}


@router.post("/qm/confirm")
async def qm_confirm_ep(accept: bool = Body(..., embed=True), user: dict = Depends(get_authenticated_user)):
    from qm_core import qm_confirm
    data = _fail(qm_confirm(user["id"], accept))
    if not accept and data.get("submitter_id"):
        await _notify(data["submitter_id"], "qm_notify_rejected")
    return {"status": "ok", **data}


@router.get("/qm/rating")
def qm_rating_ep(user: dict = Depends(get_authenticated_user)):
    from qm_view import qm_rating
    return qm_rating(user["id"])


# ---------------------------------------------------------------- chat (openWebChat, prefiks /qm/matches)

@router.get("/qm/matches/{match_id}/messages")
def qm_chat_get(match_id: int, user: dict = Depends(get_authenticated_user)):
    from qm_chat import qm_get_messages
    msgs = qm_get_messages(match_id, user["id"])
    if msgs is None:
        raise HTTPException(status_code=403, detail="chat_no_access")
    return {"messages": msgs}


@router.post("/qm/matches/{match_id}/messages")
async def qm_chat_send(match_id: int, text: str = Body(..., embed=True), user: dict = Depends(get_authenticated_user)):
    from qm_chat import qm_send_message
    ok, reason, notify = qm_send_message(match_id, user["id"], text)
    if not ok:
        raise HTTPException(status_code=400, detail=reason)
    if notify:
        try:
            from notify import notify_user
            from texts import t
            await notify_user(notify["recipient_telegram_id"], "notify_chat_message", notify["language"],
                              open_button_key="btn_open_app", mode=t("mode_name_qm", notify["language"]),
                              preview=notify["text_preview"])
        except Exception as exc:
            logger.warning("Tezkor o'yin chat xabari yuborilmadi: %s", exc)
    return {"status": "ok", "profanity": contains_profanity(text)}


@router.post("/qm/matches/{match_id}/typing")
def qm_chat_typing(match_id: int, user: dict = Depends(get_authenticated_user)):
    from qm_chat import qm_set_typing
    if not qm_set_typing(match_id, user["id"]):
        raise HTTPException(status_code=403, detail="chat_no_access")
    return {"status": "ok"}


@router.get("/qm/matches/{match_id}/state")
def qm_chat_state_ep(match_id: int, user: dict = Depends(get_authenticated_user)):
    from qm_chat import qm_chat_state
    s = qm_chat_state(match_id, user["id"])
    if s is None:
        raise HTTPException(status_code=403, detail="chat_no_access")
    return s
