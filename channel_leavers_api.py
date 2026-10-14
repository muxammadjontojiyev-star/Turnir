"""
channel_leavers_api.py — "KANALNI TARK ETGANLAR" (APIRouter, 2026-10-14).
Mantiq: channel_leavers.py.

  GET /admin/channel-leavers — bosh admin: barcha ligalar; liga admini: faqat o'z ligalari.
"""

import time

from fastapi import APIRouter, Depends, HTTPException

from admin_roles import get_admin_league_ids, is_super_admin
from api import get_authenticated_league_admin

router = APIRouter()

SCAN_COOLDOWN_S = 20          # bir admin tez-tez bossa Telegram limitiga urilmaslik uchun
_last_scan: dict[int, float] = {}


@router.get("/admin/channel-leavers")
async def admin_channel_leavers(user: dict = Depends(get_authenticated_league_admin)):
    from channel_leavers import scan_channel_leavers
    tg = user["telegram_id"]
    now = time.monotonic()
    if now - _last_scan.get(tg, 0) < SCAN_COOLDOWN_S:
        raise HTTPException(status_code=429, detail="too_many_requests")
    _last_scan[tg] = now
    league_ids = None if is_super_admin(tg) else get_admin_league_ids(tg)
    result = await scan_channel_leavers(league_ids)
    result["can_manage"] = is_super_admin(tg)      # o'tkazish/chiqarish faqat bosh adminda
    return result
