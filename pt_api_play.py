"""
pt_api_play.py — SHAXSIY turnir o'yinlari endpointlari (4-bosqich, APIRouter).
Mantiq pt_draw / pt_rounds / pt_results'da; bu yerda chaqiruv + bildirishnoma (qoida #27).
"""

import logging

from fastapi import APIRouter, Body, Depends, HTTPException

from api import get_authenticated_user, validate_scores
from pt_notify import _label, notify_advance, notify_round_result, tournament_members

logger = logging.getLogger("pt_api_play")
router = APIRouter()


def _is_super(user: dict) -> bool:
    from admin_roles import is_super_admin
    return is_super_admin(user["telegram_id"])


@router.post("/pt/{tournament_id}/start")
async def pt_start(tournament_id: int, user: dict = Depends(get_authenticated_user)):
    """Tashkilotchi: qur'a + guruh o'yinlari. Xato: not_owner, not_recruiting, not_enough_players, ... -> 400"""
    from pt_draw import pt_start_tournament
    ok, r = pt_start_tournament(tournament_id, user["id"])
    if not ok:
        raise HTTPException(status_code=400, detail=r)
    from models import get_connection
    from notify import notify_user
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT m.telegram_id, m.group_label, u.language FROM pt_members m JOIN users u ON u.id = m.user_id "
            "WHERE m.tournament_id = ? AND m.status = 'approved'", (tournament_id,)).fetchall()
    finally:
        conn.close()
    for row in rows:
        try:
            await notify_user(row["telegram_id"], "pt_notify_started", row["language"],
                              open_button_key="btn_open_app", name=r["name"], group=row["group_label"])
        except Exception as exc:
            logger.warning("PT #%s: boshlanish xabari yuborilmadi: %s", tournament_id, exc)
    return {"status": "ok", **{k: v for k, v in r.items() if k != "name"}}


@router.get("/pt/{tournament_id}/play")
def pt_play(tournament_id: int, user: dict = Depends(get_authenticated_user)):
    """Tur, muddat, guruh jadvallari, o'yinlar — faqat a'zo/tashkilotchi/bosh admin."""
    from pt_results import pt_get_play
    d = pt_get_play(tournament_id, user["id"], is_super=_is_super(user))
    if d is None:
        raise HTTPException(status_code=404, detail="not_found")
    return d


@router.post("/pt/{tournament_id}/deadline")
async def pt_deadline(tournament_id: int, deadline: str = Body(..., embed=True),
                      user: dict = Depends(get_authenticated_user)):
    """Joriy tur muddati (Toshkent 'YYYY-MM-DDTHH:MM'). Xato: bad_deadline, deadline_in_past, ... -> 400"""
    from notify import notify_members, notify_user
    from pt_rounds import pt_set_deadline
    from texts import t as tr
    ok, r = pt_set_deadline(tournament_id, user["id"], deadline)
    if not ok:
        raise HTTPException(status_code=400, detail=r)
    try:
        if r.get("phase") in ("semi", "final"):        # pley-off: bosqich nomi har kimga o'z tilida
            for m in r["members"]:
                await notify_user(m["telegram_id"], "pt_notify_ko_deadline", m.get("language"),
                                  open_button_key="btn_open_app", name=r["name"],
                                  stage=tr(f"pt_stage_{r['phase']}", m.get("language")),
                                  deadline=r["deadline_local"])
        else:
            await notify_members(r["members"], "pt_notify_round_open", name=r["name"],
                                 round=r["round"], deadline=r["deadline_local"])
    except Exception as exc:
        logger.warning("PT #%s: muddat xabari yuborilmadi: %s", tournament_id, exc)
    return {"status": "ok", "deadline_local": r["deadline_local"]}


@router.post("/pt/{tournament_id}/close-round")
async def pt_close_round(tournament_id: int, user: dict = Depends(get_authenticated_user)):
    """Tashkilotchi joriy turni hozir yopadi. Xato: not_owner, not_running, groups_finished -> 400"""
    from pt_rounds import pt_close_round_now
    ok, r = pt_close_round_now(tournament_id, user["id"])
    if not ok:
        raise HTTPException(status_code=400, detail=r)
    await notify_round_result(r)
    return {"status": "ok", "next_round": r["next_round"], "groups_finished": r["groups_finished"]}


@router.post("/pt/match/{match_id}/result")
async def pt_match_result(match_id: int, score1: int = Body(..., embed=True),
                          score2: int = Body(..., embed=True), user: dict = Depends(get_authenticated_user)):
    """Xato: match_not_found, not_participant, not_running, round_closed, already_submitted -> 400"""
    validate_scores(score1, score2)
    from pt_results import pt_submit_result
    ok, r = pt_submit_result(match_id, user["id"], score1, score2)
    if not ok:
        raise HTTPException(status_code=400, detail=r)
    opp = r.get("opponent")
    if opp:
        from notify import notify_user
        try:
            await notify_user(opp["telegram_id"], "notify_result_submitted", opp["language"],
                              open_button_key="btn_open_app")
        except Exception as exc:
            logger.warning("PT match %s: raqibga xabar yuborilmadi: %s", match_id, exc)
    return {"status": "ok"}


@router.post("/pt/match/{match_id}/confirm")
async def pt_match_confirm(match_id: int, accept: bool = Body(True, embed=True),
                     user: dict = Depends(get_authenticated_user)):
    """Xato: match_not_found, not_opponent, wrong_status -> 400"""
    from pt_results import pt_confirm_result
    ok, r = pt_confirm_result(match_id, user["id"], accept)
    if not ok:
        raise HTTPException(status_code=400, detail=r)
    if r["advance"].get("event"):
        name, members = tournament_members(r["tournament_id"])
        await notify_advance(name, members, r["advance"])
    return {"status": r["status"], "event": r["advance"].get("event")}


@router.post("/pt/{tournament_id}/semis/start")
async def pt_semis_start(tournament_id: int, user: dict = Depends(get_authenticated_user)):
    """Tashkilotchi: guruhlar tugagach yarim final. Xato: not_owner, not_running, not_ready -> 400"""
    from notify import notify_members
    from pt_knockout import pt_owner_start_semis
    ok, pairs = pt_owner_start_semis(tournament_id, user["id"])
    if not ok:
        raise HTTPException(status_code=400, detail=pairs)
    name, members = tournament_members(tournament_id)
    text = "\n".join(f"{_label(a)} — {_label(b)}" for a, b in pairs)
    try:
        await notify_members(members, "pt_notify_semis", name=name, pairs=text)
    except Exception as exc:
        logger.warning("PT #%s: yarim final xabari yuborilmadi: %s", tournament_id, exc)
    return {"status": "ok", "pairs": pairs}

