"""
channel_leavers.py — Majburiy kanalni TARK ETGAN liga ishtirokchilari (2026-10-14).

Muammo: ishtirokchi kanaldan chiqib ketadi, lekin klubi ligada unda qolib ketadi.
Yechim (bosh admin tanlovi — "ikkalasi ham", klubni admin o'zi hal qiladi):
  1) Bot kanaldan chiqish hodisasini (chat_member) ushlaydi → bosh adminlarga va
     o'sha liga adminlariga darhol xabar: kim, qaysi liga, qaysi klub
     (channel_leave_bot.py → notify_admins_about_leaver);
  2) Admin panelda "KANALNI TARK ETGANLAR" — barcha liga ishtirokchilari kanalda
     bormi tekshiriladi (getChatMember), chiqib ketganlar ro'yxati
     (channel_leavers_api.py → scan_channel_leavers).
Klub AVTOMATIK bo'shatilmaydi — admin mavjud "ISHTIROKCHILAR" vositasi bilan
boshqa akkountga o'tkazadi yoki chiqaradi (natijalar saqlanadi).

⚠️ Bot kanalda ADMIN bo'lishi shart (membership.py bilan bir xil talab).
"""

import asyncio
import logging

import httpx

from config import (
    ADMIN_TELEGRAM_IDS, BOT_TOKEN, DEFAULT_LANGUAGE, REQUIRED_CHANNEL_USERNAME,
)
from models import get_connection

logger = logging.getLogger(__name__)

_API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"

LEFT_STATUSES = ("left", "kicked")      # kanalda yo'q hisoblanadigan statuslar
SCAN_CONCURRENCY = 8                    # bir vaqtda nechta getChatMember (Telegram limiti ~30/s)
SCAN_TIMEOUT_S = 8.0

_PARTICIPANT_SQL = (
    "SELECT r.user_id, u.telegram_id, u.nickname, u.username, r.club_name, "
    "r.league_id, l.name AS league_name "
    "FROM registrations r "
    "JOIN users u ON u.id = r.user_id "
    "LEFT JOIN leagues l ON l.id = r.league_id "
)


def league_participant_by_tg(telegram_id: int) -> dict | None:
    """Telegram ID bo'yicha liga ishtirokchisi (ligada bo'lmasa — None)."""
    conn = get_connection()
    try:
        row = conn.cursor().execute(
            _PARTICIPANT_SQL + "WHERE u.telegram_id = ?", (telegram_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def league_participants(league_ids: list[int] | None = None) -> list[dict]:
    """Liga ishtirokchilari (league_ids berilsa — faqat o'sha ligalar)."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        if league_ids is None:
            cur.execute(_PARTICIPANT_SQL + "ORDER BY l.id, r.club_name")
        else:
            if not league_ids:
                return []
            marks = ",".join("?" * len(league_ids))
            cur.execute(
                _PARTICIPANT_SQL + f"WHERE r.league_id IN ({marks}) ORDER BY l.id, r.club_name",
                tuple(league_ids),
            )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def leave_recipients(league_id: int) -> list[dict]:
    """Xabar oluvchilar: bosh adminlar + shu ligaga biriktirilgan liga adminlari (takrorsiz)."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT DISTINCT al.telegram_id, u.language FROM admin_leagues al "
            "LEFT JOIN users u ON u.telegram_id = al.telegram_id WHERE al.league_id = ?",
            (league_id,),
        )
        out = {r["telegram_id"]: r["language"] for r in cur.fetchall()}
        for tg in ADMIN_TELEGRAM_IDS:
            if tg not in out:
                row = cur.execute("SELECT language FROM users WHERE telegram_id = ?", (tg,)).fetchone()
                out[tg] = row["language"] if row else None
        return [{"telegram_id": tg, "language": lang or DEFAULT_LANGUAGE} for tg, lang in out.items()]
    finally:
        conn.close()


def _who(p: dict) -> str:
    return f"@{p['username']}" if p.get("username") else (p.get("nickname") or str(p["telegram_id"]))


async def notify_admins_about_leaver(telegram_id: int) -> int:
    """
    Kanaldan chiqqan foydalanuvchi liga ishtirokchisi bo'lsa — adminlarga xabar.
    Qaytaradi: yuborilgan xabarlar soni (ishtirokchi emas — 0).
    """
    p = league_participant_by_tg(telegram_id)
    if not p:
        return 0
    from notify import notify_user
    sent = 0
    for r in leave_recipients(p["league_id"]):
        ok = await notify_user(
            r["telegram_id"], "notify_channel_leave", r["language"],
            open_button_key="btn_open_app",
            who=_who(p), league=p.get("league_name") or "?",
            club=p.get("club_name") or "—", tg=p["telegram_id"],
        )
        sent += 1 if ok else 0
    logger.info("Kanalni tark etdi: tg=%s (%s · %s), %d adminga xabar",
                telegram_id, p.get("league_name"), p.get("club_name"), sent)
    return sent


async def _channel_status(client: httpx.AsyncClient, telegram_id: int) -> str | None:
    """getChatMember statusi; xato bo'lsa None (noma'lum — ro'yxatga qo'shilmaydi)."""
    try:
        r = await client.get(f"{_API_BASE}/getChatMember", params={
            "chat_id": REQUIRED_CHANNEL_USERNAME, "user_id": telegram_id,
        })
        data = r.json()
        if not data.get("ok"):
            logger.warning("getChatMember xato (tg=%s): %s", telegram_id, data.get("description"))
            return None
        return data.get("result", {}).get("status")
    except Exception as exc:
        logger.warning("getChatMember tarmoq xatosi (tg=%s): %s", telegram_id, exc)
        return None


async def scan_channel_leavers(league_ids: list[int] | None = None) -> dict:
    """
    Liga ishtirokchilarini kanalda bormi tekshiradi.
    Qaytaradi: {checked, unknown, leavers: [{user_id, telegram_id, nickname, username,
                club_name, league_id, league_name, status}, ...]}
    """
    players = league_participants(league_ids)
    if not BOT_TOKEN or not players:
        return {"checked": 0, "unknown": 0, "leavers": []}
    sem = asyncio.Semaphore(SCAN_CONCURRENCY)

    async with httpx.AsyncClient(timeout=SCAN_TIMEOUT_S) as client:
        async def one(p):
            async with sem:
                return p, await _channel_status(client, p["telegram_id"])
        results = await asyncio.gather(*(one(p) for p in players))

    leavers = [dict(p, status=st) for p, st in results if st in LEFT_STATUSES]
    unknown = sum(1 for _, st in results if st is None)
    return {"checked": len(players), "unknown": unknown, "leavers": leavers}
