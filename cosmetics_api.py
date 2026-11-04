"""
cosmetics_api.py — DO'KON → BEZAKLAR endpointlari (2026-10-30). Mantiq — cosmetics.py.
  GET  /shop/cosmetics          — katalog, menikilar, qo'llanganlar, balans
  POST /shop/cosmetics/buy      — {item_id}; sotib olinadi va darhol qo'llanadi
  POST /shop/cosmetics/equip    — {kind: frame|bg|card, item_id: id|null}
  2026-11-04: GET/POST /shop/admin/cosmetics/card-sale {on} — o'yin kartasi fonlari sotuvi (bosh admin)
"""

from fastapi import APIRouter, Body, Depends, HTTPException

from admin_roles import is_super_admin
from api import get_authenticated_super_admin, get_authenticated_user

router = APIRouter()


@router.get("/shop/cosmetics")
def cosmetics_get(user: dict = Depends(get_authenticated_user)):
    from cosmetics import cos_state
    return cos_state(user["id"], is_super_admin(user["telegram_id"]))


@router.post("/shop/cosmetics/buy")
def cosmetics_buy(item_id: str = Body(..., embed=True), user: dict = Depends(get_authenticated_user)):
    """Xato (400): not_found, already_owned, insufficient."""
    from cosmetics import cos_buy
    ok, r = cos_buy(user["id"], item_id)
    if not ok:
        raise HTTPException(status_code=400, detail=r)
    return {"status": "ok", **r}


@router.post("/shop/cosmetics/equip")
def cosmetics_equip(kind: str = Body(...), item_id: str | None = Body(None), user: dict = Depends(get_authenticated_user)):
    """Xato (400): bad_kind, not_found, not_owned."""
    from cosmetics import cos_equip
    ok, r = cos_equip(user["id"], kind, item_id, is_super_admin(user["telegram_id"]))
    if not ok:
        raise HTTPException(status_code=400, detail=r)
    return {"status": "ok", **r}


@router.get("/shop/admin/cosmetics/card-sale")
def cosmetics_card_sale_get(admin: dict = Depends(get_authenticated_super_admin)):
    from cosmetics_cards import get_card_sale
    return {"on": get_card_sale()}


@router.post("/shop/admin/cosmetics/card-sale")
def cosmetics_card_sale_set(on: bool = Body(..., embed=True), admin: dict = Depends(get_authenticated_super_admin)):
    """O'yin kartasi fonlari sotuvini yoqish/o'chirish (bosh admin). Sotib olinganlar egalarida qoladi."""
    from cosmetics_cards import set_card_sale
    return {"on": set_card_sale(on)}
