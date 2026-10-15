"""
tb_api_season.py — "TEAMLAR JANGI": mavsum, jadval, 1v1 natijalar (APIRouter, 2026-10-16, 2-bosqich).
Mantiq: tb_season.py, tb_rounds.py, tb_games.py. api.py oxirida include_router.
"""

import logging

from fastapi import APIRouter, Body, Depends, HTTPException

from api import get_authenticated_super_admin, get_authenticated_user

logger = logging.getLogger(__name__)
router = APIRouter()


def _ok(res: tuple):
    ok, data = res
    if not ok:
        raise HTTPException(status_code=400, detail=data)
    return {"status": "ok", **data}


@router.get("/tb/season")
def tb_season_info(user: dict = Depends(get_authenticated_user)):
    from tb_core import tb_my_team_id
    from tb_season import tb_divisions, tb_last_season, tb_team_division
    s = tb_last_season()
    if not s:
        return {"season": None}
    team_id = tb_my_team_id(user["id"])
    from tb_season import TB_PROMO
    return {"season": s, "divisions": tb_divisions(s["id"]), "promo": TB_PROMO,
            "my_team_id": team_id, "my_division": tb_team_division(s["id"], team_id)}


@router.get("/tb/season/table")
def tb_season_table(division: int, user: dict = Depends(get_authenticated_user)):
    from tb_season import tb_last_season, tb_standings
    s = tb_last_season()
    if not s:
        raise HTTPException(status_code=404, detail="no_season")
    return {"division": division, "table": tb_standings(s["id"], division)}


@router.get("/tb/season/fixtures")
def tb_season_fixtures(division: int, round: int, user: dict = Depends(get_authenticated_user)):
    from tb_games import tb_round_fixtures
    from tb_season import tb_last_season
    s = tb_last_season()
    if not s:
        raise HTTPException(status_code=404, detail="no_season")
    return {"division": division, "round": round, "fixtures": tb_round_fixtures(s["id"], division, round)}


@router.get("/tb/my-games")
def tb_my_games_ep(user: dict = Depends(get_authenticated_user)):
    from tb_games import tb_my_games
    return {"user_id": user["id"], "games": tb_my_games(user["id"])}


async def _notify(user_id: int, key: str, **fmt) -> None:
    """Raqibga bot xabari (xato bo'lsa — log, natija saqlanib qoladi; qoida #37)."""
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
        logger.warning("TB: xabar yuborilmadi (user=%s, %s): %s", user_id, key, exc)


@router.post("/tb/game/submit")
async def tb_game_submit(game_id: int = Body(..., embed=True), my_score: int = Body(..., embed=True),
                         opp_score: int = Body(..., embed=True), user: dict = Depends(get_authenticated_user)):
    from tb_games import tb_submit
    res = _ok(tb_submit(user["id"], game_id, my_score, opp_score))
    await _notify(res["opponent_user_id"], "tb_notify_result", score=f"{opp_score}:{my_score}")
    return res


@router.post("/tb/game/confirm")
async def tb_game_confirm(game_id: int = Body(..., embed=True), accept: bool = Body(..., embed=True),
                          user: dict = Depends(get_authenticated_user)):
    from tb_games import tb_confirm
    res = _ok(tb_confirm(user["id"], game_id, accept))
    if not accept and res.get("submitter_user_id"):
        await _notify(res["submitter_user_id"], "tb_notify_rejected_result")
    return res


# ---------------------------------------------------------------- bosh admin

@router.get("/tb/admin/season/preview")
def tb_admin_preview(admin: dict = Depends(get_authenticated_super_admin)):
    from tb_season import tb_season_preview
    return tb_season_preview()


@router.post("/tb/admin/season/create")
def tb_admin_create(division_size: int | None = Body(None, embed=True),
                    admin: dict = Depends(get_authenticated_super_admin)):
    from tb_season import tb_create_season
    return _ok(tb_create_season(division_size))


@router.post("/tb/admin/season/start")
async def tb_admin_start(admin: dict = Depends(get_authenticated_super_admin)):
    from tb_notify import tb_spawn_round_notify
    from tb_rounds import tb_start_rounds
    res = _ok(tb_start_rounds())
    tb_spawn_round_notify(res["season_id"], res["round"])      # 2026-10-16: raqib haqida xabar (fonda)
    return res


@router.post("/tb/admin/season/advance")
async def tb_admin_advance(admin: dict = Depends(get_authenticated_super_admin)):
    from tb_notify import tb_spawn_round_notify
    from tb_rounds import tb_force_advance
    res = _ok(tb_force_advance())
    tb_spawn_round_notify(res["season_id"], res["opened_round"])
    return res


@router.post("/tb/admin/season/finish")
def tb_admin_finish(admin: dict = Depends(get_authenticated_super_admin)):
    from tb_rounds import tb_finish_season
    return _ok(tb_finish_season())


@router.post("/tb/admin/game/set")
def tb_admin_game_set(game_id: int = Body(..., embed=True), score1: int = Body(..., embed=True),
                      score2: int = Body(..., embed=True), admin: dict = Depends(get_authenticated_super_admin)):
    from tb_games import tb_admin_set
    return _ok(tb_admin_set(game_id, score1, score2))
