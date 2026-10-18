"""
club_priority.py — liga klubini tanlashda NAVBAT (2026-10-18).

Egasi so'rovi: klub tanlaganlar mavsum o'rtasida kanalni tark etmasligi, oxirigacha o'ynashi uchun.
Qoida: yangi liga mavsumi ochilgach (season_state.last_finalized_at = t0) klub tanlash navbat bilan:
  1) o'tgan mavsumni OXIRIGACHA o'ynaganlar ('finished') — darhol (t0);
  2) yangi / o'tgan mavsumda qatnashmaganlar — t0 + CLUB_PRIORITY_HOURS;
  3) o'tgan mavsumda TASHLAB KETGANLAR ('abandoned') — yana CLUB_ABANDON_EXTRA_HOURS keyin.
O'tgan mavsum bo'yicha yozuv yo'q bo'lsa (funksiya ishga tushgandan keyingi birinchi mavsum) —
navbat qo'llanmaydi.

Yozuvlar (club_reliability, telegram_id bo'yicha — akkount o'chsa ham saqlanadi, sovrinlar kabi):
  * 'abandoned' — admin mavsum o'rtasida ishtirokchini yangi akkountga o'tkazganda ("tashlab ketdi"
    belgisi bilan) yoki o'yinlari bor ishtirokchini butunlay chiqarganda (mark_abandoned_cur);
  * 'finished'  — liga mavsumi yakunlanganda, o'sha paytdagi barcha ishtirokchilar
    (record_finishers_cur — season_prizes.finalize tranzaksiyasi ichida, reset'dan OLDIN).
"""

import logging
from datetime import datetime, timedelta, timezone

from config import CLUB_ABANDON_EXTRA_HOURS, CLUB_PRIORITY_HOURS
from models import get_connection

logger = logging.getLogger(__name__)

ST_FINISHED, ST_ABANDONED = "finished", "abandoned"
TIER_FINISHED, TIER_NEW, TIER_ABANDONED = "finished", "new", "abandoned"


def init_club_priority_table(cursor) -> None:
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS club_reliability (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            season_number INTEGER NOT NULL,
            status TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (telegram_id, season_number)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_club_rel_season ON club_reliability(season_number)")


def _current_season(cur) -> int:
    r = cur.execute("SELECT current_season FROM season_state WHERE id = 1").fetchone()
    return r["current_season"] if r else 1


def mark_abandoned_cur(cur, telegram_id: int) -> None:
    """Joriy liga mavsumida tashlab ketdi (abandoned 'finished'dan ustun — REPLACE)."""
    cur.execute("INSERT INTO club_reliability (telegram_id, season_number, status) VALUES (?, ?, ?) "
                "ON CONFLICT(telegram_id, season_number) DO UPDATE SET status = excluded.status",
                (telegram_id, _current_season(cur), ST_ABANDONED))
    logger.info("Klub navbati: tg %s — tashlab ketdi deb belgilandi", telegram_id)


def mark_if_league_player_cur(cur, user_id: int) -> None:
    """Butunlay chiqarishda: ligada ro'yxatda VA o'yinlari bo'lsa (qur'a o'tgan) — tashlab ketgan."""
    r = cur.execute(
        "SELECT u.telegram_id FROM users u JOIN registrations r ON r.user_id = u.id WHERE u.id = ? "
        "AND EXISTS (SELECT 1 FROM matches m WHERE m.player1_id = u.id OR m.player2_id = u.id)",
        (user_id,)).fetchone()
    if r:
        mark_abandoned_cur(cur, r["telegram_id"])


def record_finishers_cur(cur, season: int) -> int:
    """Mavsum yakunida ro'yxatdagi hamma — 'finished' (tashlab ketganlar yozuvi o'zgarmaydi)."""
    cur.execute("INSERT OR IGNORE INTO club_reliability (telegram_id, season_number, status) "
                "SELECT u.telegram_id, ?, ? FROM registrations r JOIN users u ON u.id = r.user_id",
                (season, ST_FINISHED))
    return cur.rowcount


def _parse_utc(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.strptime(str(s)[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def club_priority_for(telegram_id: int, now: datetime | None = None) -> dict:
    """
    {active, tier, open, opens_at (ISO UTC | None), prev_season, finished_count}.
    active=False — navbat qo'llanmaydi (hamma darhol tanlaydi).
    """
    now = now or datetime.now(timezone.utc)
    conn = get_connection()
    try:
        cur = conn.cursor()
        st = cur.execute("SELECT current_season, last_finalized_at FROM season_state WHERE id = 1").fetchone()
        prev = (st["current_season"] if st else 1) - 1
        t0 = _parse_utc(st["last_finalized_at"] if st else None)
        n = cur.execute("SELECT COUNT(*) AS c FROM club_reliability WHERE season_number = ?",
                        (prev,)).fetchone()["c"] if prev >= 1 else 0
        base = {"active": False, "tier": None, "open": True, "opens_at": None, "prev_season": prev,
                "finished_count": n}
        if not t0 or not n:
            return base
        r = cur.execute("SELECT status FROM club_reliability WHERE telegram_id = ? AND season_number = ?",
                        (telegram_id, prev)).fetchone()
        tier = TIER_FINISHED if r and r["status"] == ST_FINISHED else (
            TIER_ABANDONED if r and r["status"] == ST_ABANDONED else TIER_NEW)
        delay = {TIER_FINISHED: 0, TIER_NEW: CLUB_PRIORITY_HOURS,
                 TIER_ABANDONED: CLUB_PRIORITY_HOURS + CLUB_ABANDON_EXTRA_HOURS}[tier]
        opens = t0 + timedelta(hours=delay)
        last_open = t0 + timedelta(hours=CLUB_PRIORITY_HOURS + CLUB_ABANDON_EXTRA_HOURS)
        return {**base, "active": now < last_open, "tier": tier, "open": now >= opens,
                "opens_at": opens.isoformat()}
    finally:
        conn.close()
