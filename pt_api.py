"""
pt_api.py — SHAXSIY turnirlar endpointlari (APIRouter; api.py OXIRIDA include_router).
el_api.py bilan bir xil import tartibi (auth dependency'lar api.py'da yuqorida e'lon qilingan).
"""

from fastapi import APIRouter, Body, Depends, HTTPException

from api import get_authenticated_user
from config import PT_CARD_HOLDER, PT_CARD_NUMBER, PT_PRICE_UZS

router = APIRouter()


def _is_super(user: dict) -> bool:
    from admin_roles import is_super_admin
    return is_super_admin(user["telegram_id"])


@router.get("/pt/config")
def pt_config(user: dict = Depends(get_authenticated_user)):
    """To'lov ma'lumotlari (.env'dan) va cheklovlar — yaratish ekrani uchun."""
    from pt_core import PT_MAX_PLAYERS, PT_MIN_PLAYERS, PT_NAME_MAX, PT_NAME_MIN
    return {"price_uzs": PT_PRICE_UZS, "card_number": PT_CARD_NUMBER,
            "card_holder": PT_CARD_HOLDER, "price_set": PT_PRICE_UZS > 0,
            "min_players": PT_MIN_PLAYERS, "max_players": PT_MAX_PLAYERS,
            "name_min": PT_NAME_MIN, "name_max": PT_NAME_MAX}


@router.get("/pt/my")
def pt_my(user: dict = Depends(get_authenticated_user)):
    from pt_core import pt_list_my_tournaments
    return {"tournaments": pt_list_my_tournaments(user["id"])}


@router.post("/pt/create")
def pt_create(name: str = Body(..., embed=True), user: dict = Depends(get_authenticated_user)):
    """Xato: price_not_set, name_too_short, name_too_long, too_many_unpaid -> 400"""
    from pt_core import pt_create_tournament
    ok, result = pt_create_tournament(user, name, PT_PRICE_UZS)
    if not ok:
        raise HTTPException(status_code=400, detail=result)
    return {"status": "ok", **result}


@router.get("/pt/{tournament_id}")
def pt_detail(tournament_id: int, user: dict = Depends(get_authenticated_user)):
    """Turnir tafsiloti — faqat tashkilotchi, a'zo yoki bosh admin (aks holda 404)."""
    from pt_core import pt_get_tournament
    t = pt_get_tournament(tournament_id, user["id"], is_super=_is_super(user))
    if t is None:
        raise HTTPException(status_code=404, detail="not_found")
    return t
