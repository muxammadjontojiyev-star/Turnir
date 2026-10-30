"""
shop_api.py — DO'KON endpointlari (2026-10-30, APIRouter). Mantiq — shop_core.py, balans — wallet.py.

Ishtirokchi:
  GET  /shop                       — balans, faol paketlar, karta, buyurtmalarim
  POST /shop/order                 — {package_id, image_base64} chek bilan yoki {package_id, no_receipt: true}
Bosh admin:
  GET  /shop/admin/orders          — tekshiruvdagi buyurtmalar
  GET  /shop/admin/order/{id}/receipt — chek rasmi (no-store)
  POST /shop/admin/order/{id}/review  — {approve: bool, reason?}
  GET  /shop/admin/packages        — barcha paketlar (nofaollari ham)
  POST /shop/admin/package         — {id?, coins, price_uzs, active}
"""

import logging

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import Response

from api import get_authenticated_super_admin, get_authenticated_user
from config import ADMIN_TELEGRAM_IDS, SHOP_CARD_HOLDER, SHOP_CARD_NUMBER
from queries import get_user_by_telegram_id

logger = logging.getLogger("shop_api")
router = APIRouter()


def _money(n: int) -> str:
    return f"{int(n):,}".replace(",", " ")


@router.get("/shop")
def shop_get(user: dict = Depends(get_authenticated_user)):
    from shop_core import shop_state
    return {**shop_state(user["id"]), "card_number": SHOP_CARD_NUMBER, "card_holder": SHOP_CARD_HOLDER}


@router.post("/shop/order")
async def shop_order(package_id: int = Body(...), image_base64: str | None = Body(None), no_receipt: bool = Body(False),
                     user: dict = Depends(get_authenticated_user)):
    """
    Xato (400): empty_image, bad_image, image_too_large, package_not_found, too_many_pending, no_card.
    2026-10-30: no_receipt=true — chekni ilovada yubora olmadi: buyurtma chek rasmisiz ochiladi, xaridor chekni
    adminga Telegram'da yuboradi; adminga matnli xabar (shop_notify_order_admin_nochek).
    """
    if not SHOP_CARD_NUMBER:
        raise HTTPException(status_code=400, detail="no_card")
    from pt_payment import decode_receipt
    from shop_core import NO_RECEIPT, shop_create_order
    if no_receipt:
        data, mime = NO_RECEIPT
    else:
        data, mime = decode_receipt(image_base64 or "")
        if data is None:
            logger.info("SHOP: chek rad etildi (user %s): %s, %s belgi", user["id"], mime, len(image_base64 or ""))
            raise HTTPException(status_code=400, detail=mime)
    ok, r = shop_create_order(user["id"], package_id, data, mime)
    if not ok:
        raise HTTPException(status_code=400, detail=r)
    from notify import notify_user, notify_user_photo
    buyer = "@" + r["username"] if r.get("username") else (r.get("nickname") or "")
    fmt = {"id": r["id"], "buyer": buyer, "coins": _money(r["coins"]), "price": _money(r["price_uzs"])}
    for admin_tg in ADMIN_TELEGRAM_IDS:
        try:
            admin = get_user_by_telegram_id(admin_tg)
            lang = admin.get("language") if admin else None
            if no_receipt:
                await notify_user(admin_tg, "shop_notify_order_admin_nochek", lang, open_button_key="btn_open_app", **fmt)
            else:
                await notify_user_photo(admin_tg, data, mime, "shop_notify_order_admin", lang, open_button_key="btn_open_app", **fmt)
        except Exception as exc:
            logger.warning("SHOP #%s: admin xabari xatosi (%s): %s", r["id"], admin_tg, exc)
    return {"status": "ok", "id": r["id"]}


@router.get("/shop/admin/orders")
def shop_admin_orders(admin: dict = Depends(get_authenticated_super_admin)):
    from shop_core import shop_list_review
    return {"orders": shop_list_review()}


@router.get("/shop/admin/order/{order_id}/receipt")
def shop_admin_receipt(order_id: int, admin: dict = Depends(get_authenticated_super_admin)):
    """Chek rasmi — FAQAT bosh admin (bank ma'lumoti)."""
    from shop_core import shop_get_receipt
    r = shop_get_receipt(order_id)
    if r is None:
        raise HTTPException(status_code=404, detail="not_found")
    return Response(content=r[0], media_type=r[1], headers={"Cache-Control": "no-store"})


@router.post("/shop/admin/order/{order_id}/review")
async def shop_admin_review(order_id: int, approve: bool = Body(...), reason: str = Body(""),
                            admin: dict = Depends(get_authenticated_super_admin)):
    """review -> approved | rejected. Xato (400): not_found, wrong_status."""
    from pt_payment import clean_reject_reason
    from shop_core import shop_review_order
    reason = clean_reject_reason(reason)
    ok, info = shop_review_order(order_id, admin["telegram_id"], approve, reason)
    if not ok:
        raise HTTPException(status_code=400, detail=info)
    from notify import notify_user
    try:
        if approve:
            await notify_user(info["telegram_id"], "shop_notify_approved", info.get("language"),
                              open_button_key="btn_open_app", coins=_money(info["coins"]), balance=_money(info["balance"]))
        else:
            await notify_user(info["telegram_id"], "shop_notify_rejected", info.get("language"),
                              open_button_key="btn_open_app", coins=_money(info["coins"]), reason=reason or "—")
    except Exception as exc:
        logger.warning("SHOP #%s: xaridorga xabar yuborilmadi: %s", order_id, exc)
    return {"status": "ok"}


@router.get("/shop/admin/packages")
def shop_admin_packages(admin: dict = Depends(get_authenticated_super_admin)):
    from shop_core import shop_list_packages
    return {"packages": shop_list_packages()}


@router.post("/shop/admin/package")
def shop_admin_package(id: int | None = Body(None), coins: int = Body(...), price_uzs: int = Body(...),
                       active: bool = Body(True), admin: dict = Depends(get_authenticated_super_admin)):
    """Xato (400): bad_coins, bad_price, not_found, too_many_packages."""
    from shop_core import shop_save_package
    ok, r = shop_save_package(id, coins, price_uzs, active)
    if not ok:
        raise HTTPException(status_code=400, detail=r)
    return {"status": "ok", **r}
