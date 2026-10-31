"""
auction_api.py — AUKSION endpointlari (2026-10-30, APIRouter). Mantiq — auction_core.py / auction_admin.py.

Ishtirokchi:
  GET  /shop/auction              — faol lotlar, oxirgi yakunlanganlar, balans, cheklov (block)
  POST /shop/auction/{id}/bid     — {amount}; oshirilgan ishtirokchiga bot xabari (fonda emas — bitta xabar)
Bosh admin:
  GET  /shop/admin/auction        — faol va oxirgi lotlar
  POST /shop/admin/auction        — {league_id, club_name, start_price, min_step, hours}
  POST /shop/admin/auction/{id}/cancel — yetakchiga pul qaytadi + xabar
"""

import logging

from fastapi import APIRouter, Body, Depends, HTTPException

from api import get_authenticated_super_admin, get_authenticated_user

logger = logging.getLogger("auction_api")
router = APIRouter()


@router.get("/shop/auction")
def auction_get(user: dict = Depends(get_authenticated_user)):
    from auction_core import auction_state
    return auction_state(user["id"])


@router.post("/shop/auction/{lot_id}/bid")
async def auction_bid_post(lot_id: int, amount: int = Body(..., embed=True), user: dict = Depends(get_authenticated_user)):
    """Xato (400): lot_not_found, ended, already_leader, leading_other, already_won, bid_too_low, bad_amount, insufficient."""
    from auction_core import auction_bid
    ok, r = auction_bid(user["id"], lot_id, amount)
    if not ok:
        raise HTTPException(status_code=400, detail=r)
    prev = r.pop("prev", None)
    if prev and prev.get("telegram_id"):
        from auction_notify import _safe, money
        from auction_notify import left_text
        await _safe(prev["telegram_id"], "auction_notify_outbid", prev.get("language"), club=r["club_name"],
                    league=r["league_name"], amount=money(r["amount"]), refund=money(prev["amount"]),
                    next_min=money(r["next_min"]), left=left_text(r["left_s"], prev.get("language")))
    return {"status": "ok", **r}


@router.get("/shop/admin/auction")
def auction_admin_get(admin: dict = Depends(get_authenticated_super_admin)):
    from auction_admin import auction_admin_list
    from queries import get_all_leagues
    return {**auction_admin_list(), "leagues": [{"id": lg["id"], "name": lg["name"]} for lg in get_all_leagues()]}


@router.post("/shop/admin/auction")
def auction_admin_create(league_id: int = Body(...), club_name: str = Body(...), start_price: int = Body(...),
                         min_step: int = Body(...), hours: int = Body(...),
                         admin: dict = Depends(get_authenticated_super_admin)):
    """Xato (400): league_not_found, bad_club, bad_price, bad_step, bad_hours, club_on_auction."""
    from auction_admin import auction_create
    ok, r = auction_create(admin["telegram_id"], league_id, club_name, start_price, min_step, hours)
    if not ok:
        raise HTTPException(status_code=400, detail=r)
    return {"status": "ok", **r}


@router.post("/shop/admin/auction/{lot_id}/cancel")
async def auction_admin_cancel(lot_id: int, admin: dict = Depends(get_authenticated_super_admin)):
    """Xato (400): not_found, wrong_status."""
    from auction_admin import auction_cancel
    ok, r = auction_cancel(lot_id)
    if not ok:
        raise HTTPException(status_code=400, detail=r)
    if r["leader"] and r["leader"].get("telegram_id"):
        from auction_notify import _safe, money
        await _safe(r["leader"]["telegram_id"], "auction_notify_cancelled", r["leader"].get("language"),
                    club=r["club_name"], amount=money(r["leader"]["amount"]))
    return {"status": "ok"}
