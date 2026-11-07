"""
tb_api_public.py — "TEAMLAR JANGI" (2026-11-07): ochiq ligalar teamlari (teamsizlar uchun) va bosh admin sozlamasi.
  GET  /tb/public-teams                    — teami yo'q foydalanuvchiga: ochiq ligalar teamlari + sardor kontakti
  POST /tb/admin/league/public {league_id, on} — faqat bosh admin: liga teamlarini teamsizlarga ko'rsatish
Mantiq: tb_public.py. Bosh adminning istalgan holatda o'chirishi — tb_force.py (tb_api.py / tb_api_league.py ulaydi).
"""

from fastapi import APIRouter, Body, Depends, HTTPException

from api import get_authenticated_super_admin, get_authenticated_user

router = APIRouter()


@router.get("/tb/public-teams")
def tb_public_teams(user: dict = Depends(get_authenticated_user)):
    from tb_core import tb_my_team_id
    from tb_public import public_teams
    if tb_my_team_id(user["id"]):
        return {"leagues": []}                         # teami bor — kerak emas (sardorlar kontakti ochilmaydi)
    return {"leagues": public_teams()}


@router.post("/tb/admin/league/public")
def tb_admin_league_public(league_id: int = Body(..., embed=True), on: bool = Body(..., embed=True),
                           admin: dict = Depends(get_authenticated_super_admin)):
    from tb_public import set_public
    ok, r = set_public(league_id, on)
    if not ok:
        raise HTTPException(status_code=400, detail=r)
    return r
