"""
ac_api_playoff.py — Osiyo Chempionlar ligasi PLAY-OFF endpointlari (APIRouter).
ac_api.py 300 qatorga yetgani uchun alohida fayl (qoida #21). api.py OXIRIDA
include_router qilinadi (ac_api.py bilan bir xil import tartibi).
Javob shakllari /cl/playoff/* bilan bir xil (frontend naqshi qayta ishlatiladi).
"""

from fastapi import APIRouter, Body, Depends, HTTPException

from api import get_authenticated_super_admin, get_authenticated_user, validate_scores
from ac_api import notify_ac_chat
from profanity import contains_profanity

router = APIRouter()


@router.get("/ac/playoff/status")
def ac_playoff_status(user: dict = Depends(get_authenticated_user)):
    from ac_playoff import ac_po_is_started
    return {"started": ac_po_is_started()}


@router.post("/ac/admin/playoff/start")
def ac_admin_playoff_start(admin: dict = Depends(get_authenticated_super_admin)):
    """
    Pley-in (9-24 o'rin, 8 juftlik) — bosh admin.
    Xato: already_started, not_drawn, groups_not_finished, not_enough_players -> 400
    """
    from ac_playoff import ac_po_start
    ok, result = ac_po_start()
    if not ok:
        raise HTTPException(status_code=400, detail=result)
    return {"status": "ok", **result}


@router.post("/ac/admin/playoff/start-bracket")
def ac_admin_playoff_start_bracket(admin: dict = Depends(get_authenticated_super_admin)):
    """
    Asosiy setka (r16) — bosh admin. Xato: playin_not_started, playin_not_finished,
    bracket_already_started, not_enough_players, bracket_failed -> 400
    """
    from ac_playoff import ac_po_start_bracket
    ok, result = ac_po_start_bracket()
    if not ok:
        raise HTTPException(status_code=400, detail=result)
    return {"status": "ok", **result}


@router.get("/ac/playoff/bracket")
def ac_playoff_bracket(user: dict = Depends(get_authenticated_user)):
    from ac_playoff_view import ac_po_bracket
    return ac_po_bracket()


@router.get("/ac/playoff/my-matches")
def ac_playoff_my_matches(user: dict = Depends(get_authenticated_user)):
    from ac_playoff_view import ac_po_my_matches
    return ac_po_my_matches(user["id"])


@router.get("/ac/playoff/user/{target_id}/matches")
def ac_playoff_user_matches(target_id: int, user: dict = Depends(get_authenticated_user)):
    """Boshqa ishtirokchining play-off o'yinlari — faqat o'qish."""
    from ac_playoff_view import ac_po_user_matches
    return ac_po_user_matches(target_id)


@router.post("/ac/playoff/submit-result")
def ac_playoff_submit(match_id: int, score1: int, score2: int,
                      user: dict = Depends(get_authenticated_user)):
    """Xato: not_found, not_participant, wrong_status, draw_not_allowed, aggregate_draw_not_allowed -> 400"""
    validate_scores(score1, score2)
    from ac_playoff_results import ac_po_submit_result
    ok, reason = ac_po_submit_result(match_id, score1, score2, user["id"])
    if not ok:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": reason, "match_id": match_id}


@router.post("/ac/playoff/confirm-result")
def ac_playoff_confirm(match_id: int, accept: bool = True,
                       user: dict = Depends(get_authenticated_user)):
    """Ikkala o'yin tasdiqlangach agregat g'olibi keyingi bosqichga o'tadi."""
    from ac_playoff_results import ac_po_confirm_result
    ok, reason = ac_po_confirm_result(match_id, user["id"], accept)
    if not ok:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": reason, "match_id": match_id}


# ============ Play-off chati (ac_chat kind="po"; guruh chati bilan bir xil format) ============

@router.get("/ac/playoff/matches/{match_id}/messages")
def ac_po_chat_get(match_id: int, user: dict = Depends(get_authenticated_user)):
    from ac_chat import ac_get_messages
    msgs = ac_get_messages(match_id, user["id"], kind="po")
    if msgs is None:
        raise HTTPException(status_code=403, detail="chat_no_access")
    return {"messages": msgs}


@router.post("/ac/playoff/matches/{match_id}/messages")
async def ac_po_chat_send(match_id: int, text: str = Body(..., embed=True),
                          user: dict = Depends(get_authenticated_user)):
    from ac_chat import ac_send_message
    ok, reason, notify = ac_send_message(match_id, user["id"], text, kind="po")
    if not ok:
        raise HTTPException(status_code=400, detail=reason)
    await notify_ac_chat(notify)
    return {"status": "ok", "profanity": contains_profanity(text)}


@router.post("/ac/playoff/matches/{match_id}/typing")
def ac_po_chat_typing(match_id: int, user: dict = Depends(get_authenticated_user)):
    from ac_chat import ac_set_typing
    if not ac_set_typing(match_id, user["id"], kind="po"):
        raise HTTPException(status_code=403, detail="chat_no_access")
    return {"status": "ok"}


@router.get("/ac/playoff/matches/{match_id}/state")
def ac_po_chat_state(match_id: int, user: dict = Depends(get_authenticated_user)):
    from ac_chat import ac_get_chat_state
    state = ac_get_chat_state(match_id, user["id"], kind="po")
    if state is None:
        raise HTTPException(status_code=403, detail="chat_no_access")
    return state
