"""
pt_notify.py — shaxsiy turnir tur xabarlari (API va scheduler uchun umumiy — qoida #26).
MUHIM: bu modul api.py ni IMPORT QILMAYDI — scheduler alohida thread'da ishlaydi,
api'ni u yerdan import qilish ikki thread'da bir vaqtda modul yuklanishiga olib kelardi.
"""

import logging

from models import get_connection
from notify import notify_members, notify_user

logger = logging.getLogger(__name__)


def _label(uid: int | None) -> str:
    """O'yinchi nomi xabar uchun: @username yoki nickname."""
    if not uid:
        return "—"
    conn = get_connection()
    try:
        r = conn.execute("SELECT nickname, username FROM users WHERE id = ?", (uid,)).fetchone()
    finally:
        conn.close()
    if not r:
        return "—"
    return "@" + r["username"] if r["username"] else (r["nickname"] or "—")


async def notify_advance(name: str, members: list[dict], adv: dict | None) -> None:
    """pt_advance hodisasi: final yaratildi/yangilandi yoki chempion aniqlandi."""
    if not adv or not adv.get("event"):
        return
    try:
        if adv["event"] in ("final_created", "final_updated"):
            p1, p2 = adv["players"]
            await notify_members(members, "pt_notify_final", name=name, p1=_label(p1), p2=_label(p2))
        elif adv["event"] == "finished":
            await notify_members(members, "pt_notify_champion", name=name, champion=_label(adv["champion_id"]))
    except Exception as exc:
        logger.warning("PT pley-off xabari yuborilmadi: %s", exc)


def tournament_members(tid: int) -> tuple[str, list[dict]]:
    """(turnir nomi, [{telegram_id, language}]) — API tomonidagi xabarlar uchun."""
    conn = get_connection()
    try:
        name = conn.execute("SELECT name FROM pt_tournaments WHERE id = ?", (tid,)).fetchone()["name"]
        rows = conn.execute("SELECT m.telegram_id, u.language FROM pt_members m JOIN users u ON u.id = m.user_id "
                            "WHERE m.tournament_id = ? AND m.status = 'approved'", (tid,)).fetchall()
    finally:
        conn.close()
    return name, [dict(r) for r in rows]


async def notify_round_result(res: dict) -> None:
    """Tur yopilgach a'zolarga xabar: keyingi tur ochildi / guruh bosqichi tugadi /
    pley-off muddati o'tdi (tashkilotchiga hal qilinmaganlar soni)."""
    try:
        if res.get("knockout"):
            if res["pending"]:
                o = res["owner"]
                await notify_user(o["owner_telegram_id"], "pt_notify_ko_pending", o["language"],
                                  open_button_key="btn_open_app", name=res["name"], count=res["pending"])
            await notify_advance(res["name"], res["members"], res.get("advance"))
            return
        if res["groups_finished"]:
            await notify_members(res["members"], "pt_notify_groups_done", name=res["name"])
        else:
            await notify_members(res["members"], "pt_notify_round_closed", name=res["name"],
                                 round=res["closed_round"], next=res["next_round"])
    except Exception as exc:
        logger.warning("PT #%s: tur xabari yuborilmadi: %s", res.get("id"), exc)
