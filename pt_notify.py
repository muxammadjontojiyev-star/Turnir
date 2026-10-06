"""
pt_notify.py — shaxsiy turnir tur xabarlari (API va scheduler uchun umumiy — qoida #26).
MUHIM: bu modul api.py ni IMPORT QILMAYDI — scheduler alohida thread'da ishlaydi,
api'ni u yerdan import qilish ikki thread'da bir vaqtda modul yuklanishiga olib kelardi.
"""

import logging

from notify import notify_members

logger = logging.getLogger(__name__)


async def notify_round_result(res: dict) -> None:
    """Tur yopilgach a'zolarga xabar: keyingi tur ochildi yoki guruh bosqichi tugadi."""
    try:
        if res["groups_finished"]:
            await notify_members(res["members"], "pt_notify_groups_done", name=res["name"])
        else:
            await notify_members(res["members"], "pt_notify_round_closed", name=res["name"],
                                 round=res["closed_round"], next=res["next_round"])
    except Exception as exc:
        logger.warning("PT #%s: tur xabari yuborilmadi: %s", res.get("id"), exc)
