"""
pt_api_play.py — SHAXSIY turnir o'yinlari endpointlari (4-bosqich, APIRouter).
Mantiq pt_draw / pt_rounds / pt_results'da; bu yerda chaqiruv + bildirishnoma (qoida #27).
"""

import logging

from fastapi import APIRouter, Body, Depends, HTTPException

from api import get_authenticated_user, validate_scores
from pt_notify import notify_advance, notify_members_stage, notify_round_result, spawn, tournament_members

logger = logging.getLogger("pt_api_play")
router = APIRouter()


def _is_super(user: dict) -> bool:
    from admin_roles import is_super_admin
    return is_super_admin(user["telegram_id"])


@router.post("/pt/{tournament_id}/start")
async def pt_start(tournament_id: int, user: dict = Depends(get_authenticated_user)):
    """Tashkilotchi: qur'a + guruh o'yinlari. Xato: not_owner, not_recruiting, not_enough_players, not_multiple, ... -> 400"""
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
    async def _send_started():
        for row in rows:
            try:
                single = r.get("format") in ("league", "cl", "el")
                await notify_user(row["telegram_id"], "pt_notify_started_table" if single else "pt_notify_started",
                                  row["language"], open_button_key="btn_open_app", name=r["name"],
                                  group=row["group_label"], rounds=r["total_rounds"])
            except Exception as exc:
                logger.warning("PT #%s: boshlanish xabari yuborilmadi: %s", tournament_id, exc)
    spawn(_send_started())                       # 128 kishigacha — fonda
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
    from notify import notify_members
    from pt_rounds import pt_set_deadline
    ok, r = pt_set_deadline(tournament_id, user["id"], deadline)
    if not ok:
        raise HTTPException(status_code=400, detail=r)
    if r.get("phase"):                              # pley-off: bosqich nomi har kimga o'z tilida
        spawn(notify_members_stage(r["members"], "pt_notify_ko_deadline", r["phase"],
                                   name=r["name"], deadline=r["deadline_local"]))
    else:
        spawn(notify_members(r["members"], "pt_notify_round_open", name=r["name"],
                             round=r["round"], deadline=r["deadline_local"]))
    return {"status": "ok", "deadline_local": r["deadline_local"]}


@router.post("/pt/{tournament_id}/rounds-per-day")
async def pt_rounds_per_day(tournament_id: int, n: int = Body(..., embed=True),
                            user: dict = Depends(get_authenticated_user)):
    """
    2026-10-10: kuniga nechta tur ochilishi (0 = qo'lda; 1..4 — har kuni rasmiy ligalar vaqtida
    avtomatik yopiladi/ochiladi). Xato: bad_value, not_found, not_owner, finished, groups_finished -> 400
    """
    from notify import notify_members
    from pt_daily import pt_set_rounds_per_day
    ok, r = pt_set_rounds_per_day(tournament_id, user["id"], n)
    if not ok:
        raise HTTPException(status_code=400, detail=r)
    if r["members"] and r["round"]:                  # yangi muddat / ko'p tur ochildi — a'zolarga xabar
        spawn(notify_members(r["members"], "pt_notify_round_open", name=r["name"],
                             round=r["round"], deadline=r["deadline_local"] or "—"))
    return {"status": "ok", "rounds_per_day": r["rounds_per_day"], "deadline_local": r["deadline_local"]}


@router.post("/pt/{tournament_id}/close-round")
async def pt_close_round(tournament_id: int, user: dict = Depends(get_authenticated_user)):
    """Tashkilotchi joriy turni hozir yopadi. Xato: not_owner, not_running, groups_finished -> 400"""
    from pt_rounds import pt_close_round_now
    ok, r = pt_close_round_now(tournament_id, user["id"])
    if not ok:
        raise HTTPException(status_code=400, detail=r)
    spawn(notify_round_result(r))
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
    if r.get("admin_pending"):                         # 2026-10-07: katta hisob — qaror qiluvchilarga xabar
        from notify import notify_members
        spawn(notify_members(r["deciders"], "pt_notify_big_score", name=r["name"], match=match_id, score=r["score"]))
        return {"status": "admin_pending"}
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
        spawn(notify_advance(name, members, r["advance"]))
    return {"status": r["status"], "event": r["advance"].get("event")}


@router.post("/pt/{tournament_id}/playoff/start")
async def pt_playoff_start(tournament_id: int, user: dict = Depends(get_authenticated_user)):
    """
    Tashkilotchi: guruhlar tugagach pley-off (setka 4..64; g'oliblar + eng yaxshi 2-o'rinlar).
    Xato: not_owner, not_running, not_ready -> 400. Xabarlar FONDA (128 kishigacha).
    """
    from pt_knockout import pt_owner_start_knockout
    ok, r = pt_owner_start_knockout(tournament_id, user["id"])
    if not ok:
        raise HTTPException(status_code=400, detail=r)
    name, members = tournament_members(tournament_id)
    spawn(notify_members_stage(members, "pt_notify_ko_start", r["stage"], name=name))
    return {"status": "ok", "stage": r["stage"], "pairs": len(r["pairs"])}


@router.get("/pt/{tournament_id}/player/{user_id}")
def pt_player(tournament_id: int, user_id: int, user: dict = Depends(get_authenticated_user)):
    """Ishtirokchi profili (Reytingdan). Faqat a'zo/tashkilotchi/admin. Xato: not_found, player_not_found -> 404"""
    from pt_results import pt_get_player
    ok, r = pt_get_player(tournament_id, user["id"], user_id, is_super=_is_super(user))
    if not ok:
        raise HTTPException(status_code=404, detail=r)
    return r



@router.post("/pt/match/{match_id}/big-decide")
async def pt_big_decide(match_id: int, accept: bool = Body(..., embed=True), user: dict = Depends(get_authenticated_user)):
    """2026-10-07: katta hisob (admin_pending) — tashkilotchi/turnir admini (o'yinda o'ynamayotgan) yoki bosh admin.
    Xato: match_not_found, not_allowed, wrong_status -> 400"""
    from pt_bigscore import pt_decide_big
    ok, r = pt_decide_big(match_id, user["id"], accept, is_super=_is_super(user))
    if not ok:
        raise HTTPException(status_code=400, detail=r)
    from notify import notify_members
    key = {"confirmed": "pt_notify_big_ok", "rejected": "pt_notify_big_rejected", "zeroed": "pt_notify_big_zeroed"}[r["status"]]
    spawn(notify_members(r["players"], key, match=match_id))
    if r["advance"].get("event"):
        name, members = tournament_members(r["tournament_id"])
        spawn(notify_advance(name, members, r["advance"]))
    return {"status": r["status"], "event": r["advance"].get("event")}
