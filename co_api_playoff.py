"""
co_api_playoff.py — Konferensiya ligasi PLAY-OFF endpointlari (APIRouter).
co_api.py 300 qatorga yetgani uchun alohida fayl (qoida #21). api.py OXIRIDA
include_router qilinadi (co_api.py bilan bir xil import tartibi).
Javob shakllari /cl/playoff/* bilan bir xil (frontend naqshi qayta ishlatiladi).
"""

from fastapi import APIRouter, Body, Depends, HTTPException

from api import get_authenticated_super_admin, get_authenticated_user, validate_scores
from co_api import notify_co_chat
from profanity import contains_profanity

router = APIRouter()


@router.get("/co/playoff/status")
def co_playoff_status(user: dict = Depends(get_authenticated_user)):
    from co_playoff import co_po_is_started
    return {"started": co_po_is_started()}


@router.post("/co/admin/playoff/start")
def co_admin_playoff_start(admin: dict = Depends(get_authenticated_super_admin)):
    """
    Pley-in (9-24 o'rin, 8 juftlik) — bosh admin.
    Xato: already_started, not_drawn, groups_not_finished, not_enough_players -> 400
    """
    from co_playoff import co_po_start
    ok, result = co_po_start()
    if not ok:
        raise HTTPException(status_code=400, detail=result)
    return {"status": "ok", **result}


@router.post("/co/admin/playoff/start-bracket")
def co_admin_playoff_start_bracket(admin: dict = Depends(get_authenticated_super_admin)):
    """
    Asosiy setka (r16) — bosh admin. Xato: playin_not_started, playin_not_finished,
    bracket_already_started, not_enough_players, bracket_failed -> 400
    """
    from co_playoff import co_po_start_bracket
    ok, result = co_po_start_bracket()
    if not ok:
        raise HTTPException(status_code=400, detail=result)
    return {"status": "ok", **result}


@router.get("/co/playoff/bracket")
def co_playoff_bracket(user: dict = Depends(get_authenticated_user)):
    from co_playoff_view import co_po_bracket
    return co_po_bracket()


@router.get("/co/playoff/my-matches")
def co_playoff_my_matches(user: dict = Depends(get_authenticated_user)):
    from co_playoff_view import co_po_my_matches
    return co_po_my_matches(user["id"])


@router.get("/co/playoff/user/{target_id}/matches")
def co_playoff_user_matches(target_id: int, user: dict = Depends(get_authenticated_user)):
    """Boshqa ishtirokchining play-off o'yinlari — faqat o'qish."""
    from co_playoff_view import co_po_user_matches
    return co_po_user_matches(target_id)


@router.post("/co/playoff/submit-result")
def co_playoff_submit(match_id: int, score1: int, score2: int,
                      user: dict = Depends(get_authenticated_user)):
    """Xato: not_found, not_participant, wrong_status, draw_not_allowed, aggregate_draw_not_allowed -> 400"""
    validate_scores(score1, score2)
    from co_playoff_results import co_po_submit_result
    ok, reason = co_po_submit_result(match_id, score1, score2, user["id"])
    if not ok:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": reason, "match_id": match_id}


@router.post("/co/playoff/confirm-result")
def co_playoff_confirm(match_id: int, accept: bool = True,
                       user: dict = Depends(get_authenticated_user)):
    """Ikkala o'yin tasdiqlangach agregat g'olibi keyingi bosqichga o'tadi."""
    from co_playoff_results import co_po_confirm_result
    ok, reason = co_po_confirm_result(match_id, user["id"], accept)
    if not ok:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": reason, "match_id": match_id}


# ============ Play-off chati (co_chat kind="po"; guruh chati bilan bir xil format) ============

@router.get("/co/playoff/matches/{match_id}/messages")
def co_po_chat_get(match_id: int, user: dict = Depends(get_authenticated_user)):
    from co_chat import co_get_messages
    msgs = co_get_messages(match_id, user["id"], kind="po")
    if msgs is None:
        raise HTTPException(status_code=403, detail="chat_no_access")
    return {"messages": msgs}


@router.post("/co/playoff/matches/{match_id}/messages")
async def co_po_chat_send(match_id: int, text: str = Body(..., embed=True),
                          user: dict = Depends(get_authenticated_user)):
    from co_chat import co_send_message
    ok, reason, notify = co_send_message(match_id, user["id"], text, kind="po")
    if not ok:
        raise HTTPException(status_code=400, detail=reason)
    await notify_co_chat(notify)
    return {"status": "ok", "profanity": contains_profanity(text)}


@router.post("/co/playoff/matches/{match_id}/typing")
def co_po_chat_typing(match_id: int, user: dict = Depends(get_authenticated_user)):
    from co_chat import co_set_typing
    if not co_set_typing(match_id, user["id"], kind="po"):
        raise HTTPException(status_code=403, detail="chat_no_access")
    return {"status": "ok"}


@router.get("/co/playoff/matches/{match_id}/state")
def co_po_chat_state(match_id: int, user: dict = Depends(get_authenticated_user)):
    from co_chat import co_get_chat_state
    state = co_get_chat_state(match_id, user["id"], kind="po")
    if state is None:
        raise HTTPException(status_code=403, detail="chat_no_access")
    return state
