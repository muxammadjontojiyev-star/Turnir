"""
tb_api.py — "TEAMLAR JANGI" endpointlari (APIRouter, 2026-10-15, 1-bosqich).
Mantiq: tb_core.py (o'qish, yaratish, qo'shilish), tb_manage.py (sardor va bosh admin amallari).
api.py oxirida include_router qilinadi.
"""

import logging

from fastapi import APIRouter, Body, Depends, HTTPException

from admin_roles import is_super_admin
from api import get_authenticated_super_admin, get_authenticated_user
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


@router.get("/tb/me")
def tb_me(user: dict = Depends(get_authenticated_user)):
    from tb_core import (TB_EMOJIS, TB_LINEUP_MAX, TB_LINEUP_MIN, TB_NAME_MAX, TB_NAME_MIN,
                         tb_my_team_id, tb_team_detail)
    admin = is_super_admin(user["telegram_id"])
    team_id = tb_my_team_id(user["id"])
    return {
        "user_id": user["id"],
        "is_admin": admin,
        "team": tb_team_detail(team_id, user["id"], admin) if team_id else None,
        "emojis": list(TB_EMOJIS),
        "lineup_min": TB_LINEUP_MIN, "lineup_max": TB_LINEUP_MAX,
        "name_min": TB_NAME_MIN, "name_max": TB_NAME_MAX,
    }


@router.get("/tb/teams")
def tb_teams(user: dict = Depends(get_authenticated_user)):
    from tb_core import tb_list_teams
    return {"teams": tb_list_teams()}


@router.get("/tb/teams/{team_id}")
def tb_team(team_id: int, user: dict = Depends(get_authenticated_user)):
    from tb_core import tb_team_detail
    d = tb_team_detail(team_id, user["id"], is_super_admin(user["telegram_id"]))
    if not d:
        _fail("not_found", 404)
    return d


@router.post("/tb/teams")
def tb_create(name: str = Body(..., embed=True), emoji: str | None = Body(None, embed=True),
              user: dict = Depends(get_authenticated_user)):
    from tb_core import tb_create_team
    return _ok(tb_create_team(user["id"], name, emoji))


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


# ---------------------------------------------------------------- bosh admin

@router.get("/tb/admin/teams")
def tb_admin_teams(admin: dict = Depends(get_authenticated_super_admin)):
    from tb_core import tb_list_teams
    return {"teams": tb_list_teams(status=None)}


@router.post("/tb/admin/review")
async def tb_admin_review_ep(team_id: int = Body(..., embed=True), approve: bool = Body(..., embed=True),
                             reason: str | None = Body(None, embed=True),
                             admin: dict = Depends(get_authenticated_super_admin)):
    from tb_manage import tb_admin_review
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
                       admin: dict = Depends(get_authenticated_super_admin)):
    from tb_manage import tb_admin_delete
    return _ok(tb_admin_delete(team_id))
