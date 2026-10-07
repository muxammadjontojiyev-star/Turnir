"""
pt_notify.py — shaxsiy turnir tur xabarlari (API va scheduler uchun umumiy — qoida #26).
MUHIM: bu modul api.py ni IMPORT QILMAYDI — scheduler alohida thread'da ishlaydi,
api'ni u yerdan import qilish ikki thread'da bir vaqtda modul yuklanishiga olib kelardi.
"""

import asyncio
import logging

from models import get_connection
from notify import notify_members, notify_user
from texts import t

logger = logging.getLogger(__name__)

# Fon vazifalari havolasi (GC yig'ib yubormasin)
_BG_TASKS: set = set()


def spawn(coro) -> None:
    """
    Bildirishnomani FONDA yuboradi — 128 kishilik turnirda ketma-ket yuborish ~13 s;
    endpoint shuncha kutib qolmasin. Xato log'ga yoziladi (qoida #44).
    """
    async def _run():
        try:
            await coro
        except Exception:
            logger.exception("PT fon bildirishnomasi xatosi")
    task = asyncio.get_running_loop().create_task(_run())
    _BG_TASKS.add(task)
    task.add_done_callback(_BG_TASKS.discard)


async def notify_members_stage(members: list[dict], key: str, stage: str, **fmt) -> None:
    """Bosqich nomi har kimga O'Z tilida (pt_stage_<stage>)."""
    for m in members:
        lang = m.get("language")
        await notify_user(m["telegram_id"], key, lang, open_button_key="btn_open_app",
                          stage=t(f"pt_stage_{stage}", lang), **fmt)


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
    """pt_advance hodisasi: keyingi bosqich yaratildi/yangilandi (final — alohida xabar) yoki chempion."""
    if not adv or not adv.get("event"):
        return
    try:
        ev, stage = adv["event"], adv.get("stage")
        if ev in ("stage_created", "stage_updated") and stage == "final":
            p1, p2 = adv["players"]
            await notify_members(members, "pt_notify_final", name=name, p1=_label(p1), p2=_label(p2))
        elif ev == "stage_created":
            await notify_members_stage(members, "pt_notify_next_stage", stage, name=name)
        elif ev == "finished":
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
                for o in res["managers"]:                # tashkilotchi + adminlar
                    await notify_user(o["telegram_id"], "pt_notify_ko_pending", o.get("language"),
                                      open_button_key="btn_open_app", name=res["name"], count=res["pending"])
            await notify_advance(res["name"], res["members"], res.get("advance"))
            return
        if res.get("champion_id"):                       # 2026-10-07: liga yakunlandi — har liga chempioni
            champs = res.get("champions") or [(None, res["champion_id"])]
            for lg, uid in champs:
                title = f"{res['name']} · {lg}" if lg and len(champs) > 1 else res["name"]
                await notify_members(res["members"], "pt_notify_champion", name=title, champion=_label(uid))
        elif res["groups_finished"]:
            key = "pt_notify_table_done" if res.get("single_table") else "pt_notify_groups_done"
            await notify_members(res["members"], key, name=res["name"])
        else:
            await notify_members(res["members"], "pt_notify_round_closed", name=res["name"],
                                 round=res["closed_round"], next=res["next_round"])
    except Exception as exc:
        logger.warning("PT #%s: tur xabari yuborilmadi: %s", res.get("id"), exc)
