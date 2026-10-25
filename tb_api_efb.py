"""
tb_api_efb.py — "TEAMLAR JANGI": eFootball akkaunti endpointlari (2026-10-25).
Mantiq: tb_efb.py. Foydalanuvchi — faqat o'zini, bir marta (POST /tb/efb).
Almashtirish / o'chirish / tarix — liga admini yoki bosh admin (qoida #34):
ruxsat a'zoning teami ligasi bo'yicha (tb_api.require_manage); teami yo'q bo'lsa — faqat bosh admin.
api.py da include_router qilinadi.
"""

from fastapi import APIRouter, Body, Depends

from admin_roles import is_super_admin
from api import get_authenticated_user
from tb_api import _fail, _ok, require_manage

router = APIRouter()


def _require_target(admin: dict, target_user_id: int) -> None:
    from tb_core import tb_my_team_id, tb_team_league_id
    league_id = tb_team_league_id(tb_my_team_id(target_user_id))
    if league_id:
        require_manage(admin, league_id)
    elif not is_super_admin(admin["telegram_id"]):
        _fail("not_league_admin", 403)


@router.post("/tb/efb")
def tb_efb_set(efb_id: str = Body(..., embed=True), efb_name: str = Body(..., embed=True),
               user: dict = Depends(get_authenticated_user)):
    from tb_efb import tb_efb_set_self
    return _ok(tb_efb_set_self(user["id"], efb_id, efb_name))


@router.post("/tb/admin/efb")
def tb_admin_efb_set(user_id: int = Body(..., embed=True), efb_id: str = Body(..., embed=True),
                     efb_name: str = Body(..., embed=True), admin: dict = Depends(get_authenticated_user)):
    from tb_efb import tb_efb_admin_set
    _require_target(admin, user_id)
    return _ok(tb_efb_admin_set(user_id, efb_id, efb_name, admin["id"]))


@router.post("/tb/admin/efb/clear")
def tb_admin_efb_clear(user_id: int = Body(..., embed=True), admin: dict = Depends(get_authenticated_user)):
    from tb_efb import tb_efb_admin_clear
    _require_target(admin, user_id)
    return _ok(tb_efb_admin_clear(user_id, admin["id"]))


@router.get("/tb/admin/efb/history")
def tb_admin_efb_history(user_id: int, admin: dict = Depends(get_authenticated_user)):
    from tb_efb import tb_efb_history
    _require_target(admin, user_id)
    return {"history": tb_efb_history(user_id)}
