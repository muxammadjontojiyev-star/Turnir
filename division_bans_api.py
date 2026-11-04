"""
division_bans_api.py — DIVIZION: BANNI OLIB TASHLASH API (2026-11-04). api.py OXIRIDA include_router.

  GET  /div/admin/bans           -> {bans: [{telegram_id, nickname, username, start_day, until_day}]}
  POST /div/admin/unban {query}  -> {status, telegram_id}  (Telegram ID yoki @username)
Faqat bosh admin (ban berish bilan bir xil — /div/admin/ban). Ishtirokchiga bot xabari boradi
(yuborilmasa ham ban olib tashlangan bo'ladi). Xatolar: user_not_found, not_banned.
"""

import logging

from fastapi import APIRouter, Body, Depends, HTTPException

from api import get_authenticated_super_admin
from notify import notify_user

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/div/admin/bans")
def div_admin_bans(admin: dict = Depends(get_authenticated_super_admin)):
    from division_bans import div_active_bans
    return {"bans": div_active_bans()}


@router.post("/div/admin/unban")
async def div_admin_unban(query: str = Body(..., embed=True),
                          admin: dict = Depends(get_authenticated_super_admin)):
    from division_bans import div_unban_by_query
    ok, res = div_unban_by_query(query)
    if not ok:
        raise HTTPException(status_code=400, detail=res)
    try:
        await notify_user(res["telegram_id"], "notify_div_unban", res.get("language"))
    except Exception as exc:   # xabar ketmasa ham ban olib tashlangan (qoida #44)
        logger.warning("Divizion unban xabari yuborilmadi (tg=%s): %s", res["telegram_id"], exc)
    logger.info("Divizion: bosh admin %s banni olib tashladi (tg %s)", admin.get("telegram_id"), res["telegram_id"])
    return {"status": "ok", "telegram_id": res["telegram_id"]}
