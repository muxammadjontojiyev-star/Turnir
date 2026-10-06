"""
pt_api.py — SHAXSIY turnirlar endpointlari (APIRouter; api.py OXIRIDA include_router).
el_api.py bilan bir xil import tartibi (auth dependency'lar api.py'da yuqorida e'lon qilingan).
"""

import logging

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import Response

from api import get_authenticated_super_admin, get_authenticated_user
from config import ADMIN_TELEGRAM_IDS, PT_CARD_HOLDER, PT_CARD_NUMBER, PT_PRICE_UZS
from queries import get_user_by_telegram_id

logger = logging.getLogger("pt_api")
router = APIRouter()


def _is_super(user: dict) -> bool:
    from admin_roles import is_super_admin
    return is_super_admin(user["telegram_id"])


@router.get("/pt/config")
def pt_config(user: dict = Depends(get_authenticated_user)):
    """To'lov ma'lumotlari (.env'dan) va cheklovlar — yaratish ekrani uchun."""
    from pt_core import (PT_DEFAULT_PLAYERS, PT_GROUP_SIZE, PT_MAX_PLAYERS, PT_MIN_PLAYERS,
                         PT_NAME_MAX, PT_NAME_MIN)
    return {"price_uzs": PT_PRICE_UZS, "card_number": PT_CARD_NUMBER,
            "card_holder": PT_CARD_HOLDER, "price_set": PT_PRICE_UZS > 0,
            "is_super": _is_super(user),
            "min_players": PT_MIN_PLAYERS, "max_players": PT_MAX_PLAYERS,
            "default_players": PT_DEFAULT_PLAYERS, "group_size": PT_GROUP_SIZE,
            "name_min": PT_NAME_MIN, "name_max": PT_NAME_MAX}


@router.get("/pt/my")
def pt_my(user: dict = Depends(get_authenticated_user)):
    from pt_core import pt_list_my_tournaments
    return {"tournaments": pt_list_my_tournaments(user["id"])}


@router.post("/pt/create")
def pt_create(name: str = Body(..., embed=True), max_players: int = Body(8, embed=True),
              user: dict = Depends(get_authenticated_user)):
    """Xato: price_not_set, bad_size, name_too_short, name_too_long, too_many_unpaid -> 400"""
    from pt_core import pt_create_tournament
    ok, result = pt_create_tournament(user, name, PT_PRICE_UZS, max_players)
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


# ============ To'lov (2-bosqich) ============

@router.post("/pt/{tournament_id}/receipt")
async def pt_receipt_submit(tournament_id: int, image_base64: str = Body(..., embed=True),
                            user: dict = Depends(get_authenticated_user)):
    """
    Tashkilotchi chek rasmini yuboradi (base64, JPEG/PNG/WEBP, <= 2.5 MB).
    Xato: empty_image, bad_image, image_too_large, not_found, not_owner, wrong_status -> 400
    Bosh adminlarga chek rasmi bot orqali yuboriladi (xato bo'lsa log, so'rov baribir ok).
    """
    from pt_payment import decode_receipt, pt_submit_receipt
    data, mime = decode_receipt(image_base64)
    if data is None:
        raise HTTPException(status_code=400, detail=mime)
    ok, result = pt_submit_receipt(tournament_id, user["id"], data, mime)
    if not ok:
        raise HTTPException(status_code=400, detail=result)

    from notify import notify_user_photo
    owner = "@" + result["owner_username"] if result.get("owner_username") else (result.get("owner_nickname") or "")
    price = f"{result['price_uzs']:,}".replace(",", " ")
    for admin_tg in ADMIN_TELEGRAM_IDS:
        try:
            admin = get_user_by_telegram_id(admin_tg)
            sent = await notify_user_photo(
                admin_tg, data, mime, "pt_notify_receipt_admin",
                admin.get("language") if admin else None, open_button_key="btn_open_app",
                name=result["name"], id=result["id"], owner=owner, price=price)
            if not sent:
                logger.warning("PT #%s: chek adminga (%s) yetmadi", tournament_id, admin_tg)
        except Exception as exc:
            logger.warning("PT #%s: admin xabari xatosi (%s): %s", tournament_id, admin_tg, exc)
    return {"status": "ok"}


@router.get("/pt/admin/payments")
def pt_admin_payments(admin: dict = Depends(get_authenticated_super_admin)):
    """Bosh admin: tekshiruvdagi to'lovlar navbati."""
    from pt_payment import pt_list_payments
    return {"payments": pt_list_payments()}


@router.get("/pt/admin/{tournament_id}/receipt")
def pt_admin_receipt(tournament_id: int, admin: dict = Depends(get_authenticated_super_admin)):
    """Chek rasmi — FAQAT bosh admin (bank ma'lumoti; ochiq <img> havolasi emas)."""
    from pt_payment import pt_get_receipt
    r = pt_get_receipt(tournament_id)
    if r is None:
        raise HTTPException(status_code=404, detail="not_found")
    data, mime = r
    return Response(content=data, media_type=mime, headers={"Cache-Control": "no-store"})


async def _notify_owner(info: dict, text_key: str, **fmt) -> None:
    from notify import notify_user
    try:
        await notify_user(info["owner_telegram_id"], text_key, info.get("language"),
                          open_button_key="btn_open_app", name=info["name"], **fmt)
    except Exception as exc:
        logger.warning("PT: tashkilotchiga xabar yuborilmadi: %s", exc)


@router.post("/pt/admin/{tournament_id}/approve")
async def pt_admin_approve(tournament_id: int, admin: dict = Depends(get_authenticated_super_admin)):
    """payment_review -> recruiting. Xato: not_found, wrong_status -> 400"""
    from pt_payment import pt_approve_payment
    ok, info = pt_approve_payment(tournament_id, admin["telegram_id"])
    if not ok:
        raise HTTPException(status_code=400, detail=info)
    await _notify_owner(info, "pt_notify_approved")
    return {"status": "ok"}


@router.post("/pt/admin/{tournament_id}/reject")
async def pt_admin_reject(tournament_id: int, reason: str = Body("", embed=True),
                          admin: dict = Depends(get_authenticated_super_admin)):
    """payment_review -> rejected (sabab ixtiyoriy, 200 belgigacha). Xato: not_found, wrong_status -> 400"""
    from pt_payment import clean_reject_reason, pt_reject_payment
    reason = clean_reject_reason(reason)          # bazaga va xabarga BIR XIL matn
    ok, info = pt_reject_payment(tournament_id, admin["telegram_id"], reason)
    if not ok:
        raise HTTPException(status_code=400, detail=info)
    await _notify_owner(info, "pt_notify_rejected", reason=reason or "—")
    return {"status": "ok"}


@router.post("/pt/{tournament_id}/capacity")
def pt_capacity(tournament_id: int, max_players: int = Body(..., embed=True),
                user: dict = Depends(get_authenticated_user)):
    """Sig'imni o'zgartirish (qur'agacha). Xato: bad_size, not_owner, already_started, below_members -> 400"""
    from pt_core import pt_set_capacity
    ok, r = pt_set_capacity(tournament_id, user["id"], max_players)
    if not ok:
        raise HTTPException(status_code=400, detail=r)
    return {"status": "ok", "max_players": max_players}

