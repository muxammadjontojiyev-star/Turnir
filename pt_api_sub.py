"""
pt_api_sub.py — SHAXSIY turnir obunalari endpointlari (2026-10-03, APIRouter).
api.py'da pt_router'dan OLDIN ulanadi: '/pt/sub' aks holda '/pt/{tournament_id}' ga tushib 422 berardi.
Mantiq pt_subscriptions.py'da; bu yerda chaqiruv + bildirishnoma (qoida #27).
"""

import logging

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import Response

from api import get_authenticated_super_admin, get_authenticated_user
from config import ADMIN_TELEGRAM_IDS
from queries import get_user_by_telegram_id

logger = logging.getLogger("pt_api_sub")
router = APIRouter()


def _plan_label(plan: str, lang: str | None) -> str:
    from texts import t
    return t(f"pt_plan_{plan}", lang)


@router.get("/pt/sub")
def pt_sub(user: dict = Depends(get_authenticated_user)):
    """Mening obunam: faol (muddati bilan), ochiq buyurtma, obuna-turnirlar soni / limit."""
    from pt_subscriptions import pt_sub_status
    return pt_sub_status(user["id"])


@router.post("/pt/sub/order")
def pt_sub_order(plan: str = Body(..., embed=True), user: dict = Depends(get_authenticated_user)):
    """Xato: plan_unavailable, pending_exists -> 400"""
    from pt_subscriptions import pt_order_subscription
    ok, r = pt_order_subscription(user, plan)
    if not ok:
        raise HTTPException(status_code=400, detail=r)
    return {"status": "ok", **r}


@router.post("/pt/sub/{sub_id}/cancel")
def pt_sub_cancel(sub_id: int, user: dict = Depends(get_authenticated_user)):
    from pt_subscriptions import pt_sub_cancel_order
    ok, r = pt_sub_cancel_order(sub_id, user["id"])
    if not ok:
        raise HTTPException(status_code=400, detail=r)
    return {"status": "ok"}


@router.post("/pt/sub/{sub_id}/receipt")
async def pt_sub_receipt(sub_id: int, image_base64: str = Body(..., embed=True),
                         user: dict = Depends(get_authenticated_user)):
    """Xato: empty_image, bad_image, image_too_large, not_found, wrong_status -> 400"""
    from notify import notify_user_photo
    from pt_payment import decode_receipt
    from pt_subscriptions import pt_sub_submit_receipt
    data, mime = decode_receipt(image_base64)
    if data is None:
        raise HTTPException(status_code=400, detail=mime)
    ok, r = pt_sub_submit_receipt(sub_id, user["id"], data, mime)
    if not ok:
        raise HTTPException(status_code=400, detail=r)
    owner = "@" + r["owner_username"] if r.get("owner_username") else (r.get("owner_nickname") or "")
    price = f"{r['price_uzs']:,}".replace(",", " ")
    for admin_tg in ADMIN_TELEGRAM_IDS:
        try:
            admin = get_user_by_telegram_id(admin_tg)
            lang = admin.get("language") if admin else None
            await notify_user_photo(admin_tg, data, mime, "pt_notify_sub_receipt_admin", lang,
                                    open_button_key="btn_open_app", plan=_plan_label(r["plan"], lang),
                                    id=r["id"], owner=owner, price=price)
        except Exception as exc:
            logger.warning("Obuna #%s: admin xabari xatosi (%s): %s", sub_id, admin_tg, exc)
    return {"status": "ok"}


@router.get("/pt/admin/sub/{sub_id}/receipt")
def pt_admin_sub_receipt(sub_id: int, admin: dict = Depends(get_authenticated_super_admin)):
    """Obuna cheki — FAQAT bosh admin."""
    from pt_subscriptions import pt_sub_get_receipt
    r = pt_sub_get_receipt(sub_id)
    if r is None:
        raise HTTPException(status_code=404, detail="not_found")
    return Response(content=r[0], media_type=r[1], headers={"Cache-Control": "no-store"})


async def _notify(info: dict, key: str, **fmt) -> None:
    from notify import notify_user
    lang = info.get("language")
    try:
        await notify_user(info["telegram_id"], key, lang, open_button_key="btn_open_app",
                          plan=_plan_label(info["plan"], lang), **fmt)
    except Exception as exc:
        logger.warning("Obuna xabari yuborilmadi: %s", exc)


@router.post("/pt/admin/sub/{sub_id}/approve")
async def pt_admin_sub_approve(sub_id: int, admin: dict = Depends(get_authenticated_super_admin)):
    from pt_subscriptions import pt_sub_approve
    ok, info = pt_sub_approve(sub_id, admin["telegram_id"])
    if not ok:
        raise HTTPException(status_code=400, detail=info)
    await _notify(info, "pt_notify_sub_approved", until=info["expires_local"])
    return {"status": "ok", "expires_local": info["expires_local"]}


@router.post("/pt/admin/sub/{sub_id}/reject")
async def pt_admin_sub_reject(sub_id: int, reason: str = Body("", embed=True),
                              admin: dict = Depends(get_authenticated_super_admin)):
    from pt_subscriptions import pt_sub_reject
    ok, info = pt_sub_reject(sub_id, admin["telegram_id"], reason)
    if not ok:
        raise HTTPException(status_code=400, detail=info)
    await _notify(info, "pt_notify_sub_rejected", reason=info["reason"] or "—")
    return {"status": "ok"}
