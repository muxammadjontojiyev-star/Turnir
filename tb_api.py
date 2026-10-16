"""
tb_api.py — "TEAMLAR JANGI" endpointlari (APIRouter, 2026-10-15, 1-bosqich).
Mantiq: tb_core.py (o'qish, yaratish, qo'shilish), tb_manage.py (sardor va liga admini amallari).
2026-10-16: ligalar — admin amallari bosh admin YOKI shu liga admini uchun (tb_leagues.tb_can_manage).
Liga endpointlari — tb_api_league.py. api.py oxirida include_router qilinadi.
"""

import logging

from fastapi import APIRouter, Body, Depends, HTTPException

from admin_roles import is_super_admin
from api import get_authenticated_user
from config import BOT_USERNAME

logger = logging.getLogger(__name__)
router = APIRouter()


def _fail(reason: str, code: int = 400):
    raise HTTPException(status_code=code, detail=reason)


def _ok(res: tuple):
    ok, data = res
    if not ok:
        _fail(data)
    return {"status": "ok", **data}


def require_manage(user: dict, league_id: int | None) -> int:
    """Bosh admin yoki shu liga admini — aks holda 403 (qoida #34)."""
    from tb_leagues import tb_can_manage
    if not league_id or not tb_can_manage(user, league_id):
        _fail("not_league_admin", 403)
    return league_id


def league_or_mine(user: dict, league_id: int | None) -> int | None:
    """So'ralgan liga yoki foydalanuvchi teamining ligasi."""
    if league_id:
        return league_id
    from tb_core import tb_my_team_id, tb_team_league_id
    return tb_team_league_id(tb_my_team_id(user["id"]))


@router.get("/tb/me")
def tb_me(user: dict = Depends(get_authenticated_user)):
    from tb_core import (TB_EMOJIS, TB_LINEUP_MAX, TB_LINEUP_MIN, TB_NAME_MAX, TB_NAME_MIN,
                         tb_my_team_id, tb_team_detail)
    from tb_leagues import tb_can_manage, tb_league, tb_managed_leagues
    is_super = is_super_admin(user["telegram_id"])
    managed = [{"id": x["id"], "name": x["name"], "emoji": x["emoji"], "pending": x["pending"]}
               for x in tb_managed_leagues(user)]
    team_id = tb_my_team_id(user["id"])
    team = tb_team_detail(team_id, user["id"], False) if team_id else None
    if team and tb_can_manage(user, team.get("league_id")):
        team = tb_team_detail(team_id, user["id"], True)
    league = tb_league(team["league_id"]) if team else None
    return {
        "user_id": user["id"],
        "is_admin": is_super or bool(managed),           # Admin tabi ko'rinadimi
        "is_super": is_super,
        "managed_leagues": managed,
        "team": team,
        "league": league,
        "emojis": list(TB_EMOJIS),
        "lineup_min": league["lineup_min"] if league else TB_LINEUP_MIN,
        "lineup_max": league["lineup_max"] if league else TB_LINEUP_MAX,
        "name_min": TB_NAME_MIN, "name_max": TB_NAME_MAX,
    }


@router.get("/tb/teams")
def tb_teams(league_id: int | None = None, user: dict = Depends(get_authenticated_user)):
    from tb_core import tb_list_teams
    lid = league_or_mine(user, league_id)
    return {"league_id": lid, "teams": tb_list_teams(league_id=lid) if lid else []}


@router.get("/tb/teams/{team_id}")
def tb_team(team_id: int, user: dict = Depends(get_authenticated_user)):
    from tb_core import tb_team_detail, tb_team_league_id
    from tb_leagues import tb_can_manage
    d = tb_team_detail(team_id, user["id"], tb_can_manage(user, tb_team_league_id(team_id)))
    if not d:
        _fail("not_found", 404)
    return d


@router.post("/tb/teams")
async def tb_create(name: str = Body(..., embed=True), emoji: str | None = Body(None, embed=True),
                    league_code: str | None = Body(None, embed=True),
                    user: dict = Depends(get_authenticated_user)):
    """2026-10-16: team faqat liga havolasi (league_code) bilan ochiladi; liga adminiga xabar."""
    from tb_core import tb_create_team
    res = _ok(tb_create_team(user["id"], name, emoji, league_code))
    try:
        from notify import notify_user
        from tb_leagues import tb_league, tb_league_admin_contact
        adm = tb_league_admin_contact(res["league_id"])
        if adm:
            await notify_user(adm["telegram_id"], "tb_notify_league_new_team", adm["language"],
                              open_button_key="btn_open_app", name=res["name"],
                              league=tb_league(res["league_id"])["name"])
    except Exception as exc:   # xabar ketmasa ham team saqlanadi (qoida #37)
        logger.warning("TB: liga adminiga xabar yuborilmadi (team=%s): %s", res.get("team_id"), exc)
    return res


@router.get("/tb/invite/{code}")
def tb_invite(code: str, user: dict = Depends(get_authenticated_user)):
    from tb_core import tb_invite_preview
    p = tb_invite_preview(code, user["id"])
    if not p:
        _fail("not_found", 404)
    return p


@router.post("/tb/join")
def tb_join_ep(code: str = Body(..., embed=True), user: dict = Depends(get_authenticated_user)):
    from tb_core import tb_join
    return _ok(tb_join(user["id"], code))


@router.get("/tb/invite-link")
def tb_invite_link(user: dict = Depends(get_authenticated_user)):
    from tb_core import tb_my_team_id, tb_team_detail
    team_id = tb_my_team_id(user["id"])
    d = tb_team_detail(team_id, user["id"]) if team_id else None
    if not d or not d["is_captain"]:
        _fail("not_captain", 403)
    if not BOT_USERNAME:
        _fail("bot_username_missing", 500)
    return {"link": f"https://t.me/{BOT_USERNAME}?start=tb_{d['invite_code']}"}


@router.post("/tb/invite/regen")
def tb_invite_regen(user: dict = Depends(get_authenticated_user)):
    from tb_manage import tb_regen_invite
    _ok(tb_regen_invite(user["id"]))
    return tb_invite_link(user)


@router.post("/tb/leave")
def tb_leave_ep(user: dict = Depends(get_authenticated_user)):
    from tb_manage import tb_leave
    return _ok(tb_leave(user["id"]))


@router.post("/tb/members/remove")
def tb_remove(user_id: int = Body(..., embed=True), user: dict = Depends(get_authenticated_user)):
    from tb_manage import tb_remove_member
    return _ok(tb_remove_member(user["id"], user_id))


@router.post("/tb/captain/transfer")
def tb_transfer(user_id: int = Body(..., embed=True), user: dict = Depends(get_authenticated_user)):
    from tb_manage import tb_transfer_captain
    return _ok(tb_transfer_captain(user["id"], user_id))


@router.post("/tb/lineup")
def tb_lineup(user_ids: list[int] = Body(..., embed=True), user: dict = Depends(get_authenticated_user)):
    from tb_manage import tb_set_lineup
    return _ok(tb_set_lineup(user["id"], user_ids))


@router.post("/tb/dissolve")
def tb_dissolve_ep(user: dict = Depends(get_authenticated_user)):
    from tb_manage import tb_dissolve
    return _ok(tb_dissolve(user["id"]))


# ---------------------------------------------------------------- liga admini / bosh admin

@router.get("/tb/admin/teams")
def tb_admin_teams(league_id: int, admin: dict = Depends(get_authenticated_user)):
    from tb_core import tb_list_teams
    require_manage(admin, league_id)
    return {"teams": tb_list_teams(status=None, league_id=league_id)}


@router.post("/tb/admin/review")
async def tb_admin_review_ep(team_id: int = Body(..., embed=True), approve: bool = Body(..., embed=True),
                             reason: str | None = Body(None, embed=True),
                             admin: dict = Depends(get_authenticated_user)):
    from tb_manage import tb_admin_review, tb_team_league
    require_manage(admin, tb_team_league(team_id))
    ok, data = tb_admin_review(team_id, admin["telegram_id"], approve, reason)
    if not ok:
        _fail(data)
    try:
        from notify import notify_user
        await notify_user(data["captain_telegram_id"],
                          "tb_notify_approved" if approve else "tb_notify_rejected",
                          data["language"], open_button_key="btn_open_app",
                          name=data["name"], reason=(reason or "—"))
    except Exception as exc:   # xabar ketmasa ham qaror saqlanadi (qoida #37)
        logger.warning("TB: sardorga xabar yuborilmadi (team=%s): %s", team_id, exc)
    return {"status": "ok"}


@router.post("/tb/admin/delete")
def tb_admin_delete_ep(team_id: int = Body(..., embed=True),
                       admin: dict = Depends(get_authenticated_user)):
    from tb_manage import tb_admin_delete, tb_team_league
    require_manage(admin, tb_team_league(team_id))
    return _ok(tb_admin_delete(team_id))
