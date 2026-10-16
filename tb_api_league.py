"""
tb_api_league.py — "TEAMLAR JANGI": ligalar endpointlari (APIRouter, 2026-10-16).
Mantiq: tb_leagues.py. Bosh admin — liga ochish/admin tayinlash/o'chirish;
liga admini (yoki bosh admin) — sozlamalar va liga taklif havolasi. api.py oxirida include_router.
"""

import logging

from fastapi import APIRouter, Body, Depends, HTTPException

from api import get_authenticated_super_admin, get_authenticated_user
from config import BOT_USERNAME
from tb_api import _fail, _ok, require_manage

logger = logging.getLogger(__name__)
router = APIRouter()


def _league_link(code: str) -> str:
    if not BOT_USERNAME:
        _fail("bot_username_missing", 500)
    return f"https://t.me/{BOT_USERNAME}?start=tbl_{code}"


async def _notify_new_admin(league_id: int) -> None:
    """Yangi liga adminiga bot xabari (xato bo'lsa — log, qaror saqlanadi; qoida #37)."""
    try:
        from notify import notify_user
        from tb_leagues import tb_league, tb_league_admin_contact
        adm = tb_league_admin_contact(league_id)
        if adm:
            await notify_user(adm["telegram_id"], "tb_notify_league_admin", adm["language"],
                              open_button_key="btn_open_app", league=tb_league(league_id)["name"])
    except Exception as exc:
        logger.warning("TB: liga adminiga xabar yuborilmadi (liga=%s): %s", league_id, exc)


@router.get("/tb/league/by-code/{code}")
def tb_league_preview(code: str, user: dict = Depends(get_authenticated_user)):
    """Liga taklif havolasi ochilganda: liga ma'lumoti + mening teamim bormi."""
    from tb_core import tb_my_team_id
    from tb_leagues import tb_league_by_code
    lg = tb_league_by_code(code)
    if not lg:
        _fail("league_not_found", 404)
    lg.pop("admin_user_id", None)
    lg["my_team_id"] = tb_my_team_id(user["id"])
    return lg


@router.get("/tb/admin/leagues")
def tb_admin_leagues(user: dict = Depends(get_authenticated_user)):
    from tb_leagues import tb_managed_leagues
    return {"leagues": tb_managed_leagues(user)}


@router.post("/tb/admin/leagues")
async def tb_admin_league_create(name: str = Body(..., embed=True), emoji: str | None = Body(None, embed=True),
                                 admin_who: str | None = Body(None, embed=True),
                                 admin: dict = Depends(get_authenticated_super_admin)):
    from tb_leagues import tb_league_create
    res = _ok(tb_league_create(name, emoji, admin_who))
    if res.get("admin_user_id"):
        await _notify_new_admin(res["league_id"])
    return res


@router.post("/tb/admin/leagues/admin")
async def tb_admin_league_set_admin(league_id: int = Body(..., embed=True),
                                    admin_who: str | None = Body(None, embed=True),
                                    admin: dict = Depends(get_authenticated_super_admin)):
    from tb_leagues import tb_league_set_admin
    res = _ok(tb_league_set_admin(league_id, admin_who))
    if res.get("admin_user_id"):
        await _notify_new_admin(league_id)
    return res


@router.post("/tb/admin/leagues/delete")
def tb_admin_league_delete(league_id: int = Body(..., embed=True),
                           admin: dict = Depends(get_authenticated_super_admin)):
    from tb_leagues import tb_league_delete
    return _ok(tb_league_delete(league_id))


@router.post("/tb/admin/league/settings")
def tb_admin_league_settings(league_id: int = Body(..., embed=True), name: str | None = Body(None, embed=True),
                             emoji: str | None = Body(None, embed=True),
                             lineup_min: int | None = Body(None, embed=True),
                             lineup_max: int | None = Body(None, embed=True),
                             division_size: int | None = Body(None, embed=True),
                             user: dict = Depends(get_authenticated_user)):
    from tb_leagues import tb_league_update
    require_manage(user, league_id)
    return _ok(tb_league_update(league_id, {"name": name, "emoji": emoji, "lineup_min": lineup_min,
                                            "lineup_max": lineup_max, "division_size": division_size}))


@router.get("/tb/admin/league/link")
def tb_admin_league_link(league_id: int, user: dict = Depends(get_authenticated_user)):
    from tb_leagues import tb_league
    require_manage(user, league_id)
    lg = tb_league(league_id, with_code=True)
    if not lg:
        raise HTTPException(status_code=404, detail="league_not_found")
    return {"link": _league_link(lg["invite_code"]), "league": {k: lg[k] for k in ("id", "name", "emoji")}}


@router.post("/tb/admin/league/link/regen")
def tb_admin_league_link_regen(league_id: int = Body(..., embed=True), user: dict = Depends(get_authenticated_user)):
    from tb_leagues import tb_league_regen_code
    require_manage(user, league_id)
    res = _ok(tb_league_regen_code(league_id))
    return {"link": _league_link(res["invite_code"])}
