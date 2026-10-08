"""
stats_api.py — bot statistikasi endpointi (2026-10-08, APIRouter; api.py OXIRIDA include_router).
Mantiq stats.py'da (qoida #27). Faqat bosh admin (config.ADMIN_TELEGRAM_IDS).
"""

from fastapi import APIRouter, Depends

from api import get_authenticated_super_admin

router = APIRouter()


@router.get("/admin/stats")
def admin_stats(admin: dict = Depends(get_authenticated_super_admin)):
    """Foydalanuvchilar, faollik, rejimlar, shaxsiy turnirlar, tillar, 14 kunlik o'sish."""
    from stats import get_bot_stats
    return get_bot_stats()
