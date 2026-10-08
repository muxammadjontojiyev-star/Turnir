"""
pt_api_support.py — SHAXSIY turnir: ishtirokchi <-> tashkilotchi chati (2026-10-08, APIRouter).
/pt/support/{thread_id}/messages|typing|state — api.js openWebChat kutgan shaklda (o'yin chati kabi).
api.py'da /pt/{id}/... routerlaridan OLDIN ulanadi (aniq yo'llar).
"""

import logging

from fastapi import APIRouter, Body, Depends, HTTPException

from api import get_authenticated_user
from profanity import contains_profanity

logger = logging.getLogger("pt_api_support")
router = APIRouter()


@router.post("/pt/{tournament_id}/support/open")
def pt_support_open_ep(tournament_id: int, user: dict = Depends(get_authenticated_user)):
    """Ishtirokchi o'z suhbatini ochadi. Xato: not_found -> 404; not_member, is_manager -> 400."""
    from pt_support import pt_support_open
    ok, r = pt_support_open(tournament_id, user["id"])
    if not ok:
        raise HTTPException(status_code=404 if r == "not_found" else 400, detail=r)
    return r


@router.get("/pt/{tournament_id}/support/threads")
def pt_support_threads_ep(tournament_id: int, user: dict = Depends(get_authenticated_user)):
    """Boshqaruvchiga suhbatlar ro'yxati (tashkilotchi, turnir admini, bosh admin)."""
    from pt_support import pt_support_threads
    rows = pt_support_threads(tournament_id, user["id"])
    if rows is None:
        raise HTTPException(status_code=403, detail="not_manager")
    return {"threads": rows}


@router.get("/pt/support/{thread_id}/messages")
def pt_support_get(thread_id: int, user: dict = Depends(get_authenticated_user)):
    from pt_support import pt_support_messages
    msgs = pt_support_messages(thread_id, user["id"])
    if msgs is None:
        raise HTTPException(status_code=403, detail="chat_no_access")
    return {"messages": msgs}


@router.post("/pt/support/{thread_id}/messages")
async def pt_support_send_ep(thread_id: int, text: str = Body(..., embed=True),
                             user: dict = Depends(get_authenticated_user)):
    from pt_support import pt_support_send
    ok, reason, n = pt_support_send(thread_id, user["id"], text)
    if not ok:
        raise HTTPException(status_code=403 if reason == "chat_no_access" else 400, detail=reason)
    from notify import notify_user
    key = "pt_notify_support_msg" if n["role"] == "member" else "pt_notify_support_reply"
    for r in n["recipients"]:
        try:
            await notify_user(r["telegram_id"], key, r.get("language"), open_button_key="btn_open_app",
                              who=n["who"], name=n["name"], preview=n["preview"])
        except Exception as exc:                       # bitta xato qolganlarini to'xtatmaydi (qoida #44)
            logger.warning("PT support xabari yuborilmadi (%s): %s", r.get("telegram_id"), exc)
    return {"status": "ok", "profanity": contains_profanity(text)}


@router.post("/pt/support/{thread_id}/typing")
def pt_support_typing_ep(thread_id: int, user: dict = Depends(get_authenticated_user)):
    from pt_support import pt_support_typing
    if not pt_support_typing(thread_id, user["id"]):
        raise HTTPException(status_code=403, detail="chat_no_access")
    return {"status": "ok"}


@router.get("/pt/support/{thread_id}/state")
def pt_support_state_ep(thread_id: int, user: dict = Depends(get_authenticated_user)):
    from pt_support import pt_support_state
    s = pt_support_state(thread_id, user["id"])
    if s is None:
        raise HTTPException(status_code=403, detail="chat_no_access")
    return s
