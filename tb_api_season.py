"""
tb_api_season.py — "TEAMLAR JANGI": mavsum, jadval, 1v1 natijalar (APIRouter, 2026-10-16, 2-bosqich).
Mantiq: tb_season.py, tb_rounds.py, tb_games.py. api.py oxirida include_router.
2026-10-16: ligalar — ko'rish ?league_id= (berilmasa — o'z teamim ligasi); admin amallari
bosh admin yoki shu liga admini uchun (tb_api.require_manage).
"""

import logging

from fastapi import APIRouter, Body, Depends, HTTPException

from api import get_authenticated_user
from tb_api import league_or_mine, require_manage

logger = logging.getLogger(__name__)
router = APIRouter()


def _ok(res: tuple):
    ok, data = res
    if not ok:
        raise HTTPException(status_code=400, detail=data)
    return {"status": "ok", **data}


@router.get("/tb/season")
def tb_season_info(league_id: int | None = None, user: dict = Depends(get_authenticated_user)):
    from tb_core import tb_my_team_id
    from tb_season import TB_PROMO, tb_divisions, tb_last_season, tb_team_division
    lid = league_or_mine(user, league_id)
    s = tb_last_season(lid) if lid else None
    if not s:
        return {"season": None, "league_id": lid}
    team_id = tb_my_team_id(user["id"])
    return {"season": s, "league_id": lid, "divisions": tb_divisions(s["id"]), "promo": TB_PROMO,
            "my_team_id": team_id, "my_division": tb_team_division(s["id"], team_id)}


@router.get("/tb/season/table")
def tb_season_table(division: int, league_id: int | None = None, user: dict = Depends(get_authenticated_user)):
    from tb_season import tb_last_season, tb_standings
    lid = league_or_mine(user, league_id)
    s = tb_last_season(lid) if lid else None
    if not s:
        raise HTTPException(status_code=404, detail="no_season")
    return {"division": division, "table": tb_standings(s["id"], division)}


@router.get("/tb/season/fixtures")
def tb_season_fixtures(division: int, round: int, league_id: int | None = None,
                       user: dict = Depends(get_authenticated_user)):
    from tb_games import tb_round_fixtures
    from tb_season import tb_last_season
    lid = league_or_mine(user, league_id)
    s = tb_last_season(lid) if lid else None
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


# ---------------------------------------------------------------- liga admini / bosh admin

@router.get("/tb/admin/season/preview")
def tb_admin_preview(league_id: int, admin: dict = Depends(get_authenticated_user)):
    from tb_season import tb_season_preview
    return tb_season_preview(require_manage(admin, league_id))


@router.post("/tb/admin/season/create")
def tb_admin_create(league_id: int = Body(..., embed=True), division_size: int | None = Body(None, embed=True),
                    format: str | None = Body(None, embed=True), match_size: int | None = Body(None, embed=True),
                    ucl_rounds: int | None = Body(None, embed=True), ucl_qualify: int | None = Body(None, embed=True),
                    ko_legs: int | None = Body(None, embed=True), final_legs: int | None = Body(None, embed=True),
                    admin: dict = Depends(get_authenticated_user)):
    """2026-10-18: format (league | ucl), match_size (N vs N), UCL parametrlari — tb_draw.py."""
    from tb_draw import tb_create_season
    return _ok(tb_create_season(require_manage(admin, league_id), division_size, format, match_size,
                                ucl_rounds, ucl_qualify, ko_legs, final_legs))


@router.get("/tb/season/ko")
def tb_season_ko(league_id: int | None = None, user: dict = Depends(get_authenticated_user)):
    """2026-10-18: UCL pley-off (bosqichlar, juftliklar, natijalar)."""
    from tb_season import tb_last_season
    from tb_ucl_view import tb_ko_view
    lid = league_or_mine(user, league_id)
    s = tb_last_season(lid) if lid else None
    return tb_ko_view(s["id"]) if s else {"stages": []}


@router.post("/tb/admin/ko/decide")
async def tb_admin_ko_decide(league_id: int = Body(..., embed=True), tie_id: int = Body(..., embed=True),
                             winner_team_id: int = Body(..., embed=True), admin: dict = Depends(get_authenticated_user)):
    """2026-10-18: teng pley-off juftligida liga admini g'olibni belgilaydi."""
    from tb_notify import tb_spawn_round_notify
    from tb_ucl_view import tb_ko_decide
    res = _ok(tb_ko_decide(require_manage(admin, league_id), tie_id, winner_team_id))
    tb_spawn_round_notify(res["season_id"], res.get("opened_round"))
    return res


@router.post("/tb/admin/season/start")
async def tb_admin_start(league_id: int = Body(..., embed=True), admin: dict = Depends(get_authenticated_user)):
    from tb_notify import tb_spawn_round_notify
    from tb_rounds import tb_start_rounds
    res = _ok(tb_start_rounds(require_manage(admin, league_id)))
    tb_spawn_round_notify(res["season_id"], res["round"])      # 2026-10-16: raqib haqida xabar (fonda)
    return res


@router.post("/tb/admin/season/advance")
async def tb_admin_advance(league_id: int = Body(..., embed=True), admin: dict = Depends(get_authenticated_user)):
    from tb_notify import tb_spawn_round_notify
    from tb_rounds import tb_force_advance
    res = _ok(tb_force_advance(require_manage(admin, league_id)))
    tb_spawn_round_notify(res["season_id"], res["opened_round"])
    return res


@router.post("/tb/admin/season/finish")
def tb_admin_finish(league_id: int = Body(..., embed=True), admin: dict = Depends(get_authenticated_user)):
    from tb_rounds import tb_finish_season
    return _ok(tb_finish_season(require_manage(admin, league_id)))


@router.post("/tb/admin/game/set")
def tb_admin_game_set(game_id: int = Body(..., embed=True), score1: int = Body(..., embed=True),
                      score2: int = Body(..., embed=True), admin: dict = Depends(get_authenticated_user)):
    from tb_games import tb_admin_set, tb_game_league
    lid = tb_game_league(game_id)
    if not lid:
        raise HTTPException(status_code=400, detail="game_not_found")
    require_manage(admin, lid)
    return _ok(tb_admin_set(game_id, score1, score2))
