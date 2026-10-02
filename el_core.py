"""
Yevropa ligasi (YeL) yadrosi — cl_core.py naqshi, ALOHIDA nusxa (ChL'ga tegilmaydi).

Hozircha (2-bosqich boshi): kirish huquqi — a'zolik sinxroni.
Qur'a / reyting keyingi qadamda shu faylga qo'shiladi.

Oqim:
  1. Liga mavsumi yakunlanadi -> el_qualifiers'da 36 telegram_id (el_qualification).
  2. Yangi mavsumda kvalifikant liga ro'yxatidan o'tadi (istalgan YANGI klub bilan)
     -> el_sync_participants() uni el_participants'ga qo'shadi. Huquq ODAMDA
     (telegram_id), klub — faqat ko'rsatish uchun snapshot.
  3. Qur'ada _el_seed_participants_from_qualifiers() — yangi mavsum ligasiga
     yozilmagan kvalifikant ham qatnashadi (ChL bilan bir xil qaror).
"""

import logging

from models import get_connection

logger = logging.getLogger(__name__)


def _current_league_season(cursor) -> int:
    cursor.execute("SELECT current_season FROM season_state WHERE id = 1")
    row = cursor.fetchone()
    return row["current_season"] if row else 1


def _latest_el_from_season(cursor) -> int | None:
    cursor.execute("SELECT MAX(from_season) AS s FROM el_qualifiers")
    row = cursor.fetchone()
    return row["s"] if row and row["s"] else None


def _insert_participant(cursor, season: int, r) -> bool:
    """INSERT OR IGNORE + UNIQUE(telegram_id, season) — idempotent (qoida #38)."""
    cursor.execute(
        "INSERT OR IGNORE INTO el_participants "
        "(season, telegram_id, user_id, nickname, club_name) "
        "VALUES (?, ?, ?, ?, ?)",
        (season, r["telegram_id"], r["user_id"], r["nickname"], r["club_name"]),
    )
    return cursor.rowcount > 0


def el_sync_participants(season: int | None = None) -> dict:
    """
    Kvalifikantlarni (oxirgi el_qualifiers) joriy mavsum liga ro'yxatlari bilan
    telegram_id orqali solishtirib, ro'yxatdan o'tganlarini el_participants'ga
    qo'shadi (YANGI klubi bilan).

    Qaytaradi: {"season", "qualified_total", "registered", "added"}
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if season is None:
            season = _current_league_season(cursor)

        from_season = _latest_el_from_season(cursor)
        if not from_season:
            return {"season": season, "qualified_total": 0, "registered": 0, "added": 0}

        cursor.execute(
            """
            SELECT q.telegram_id, u.id AS user_id, u.nickname, r.club_name
            FROM el_qualifiers q
            JOIN users u ON u.telegram_id = q.telegram_id
            JOIN registrations r ON r.user_id = u.id
            WHERE q.from_season = ?
            """,
            (from_season,),
        )
        rows = cursor.fetchall()
        added = sum(1 for r in rows if _insert_participant(cursor, season, r))

        cursor.execute(
            "SELECT COUNT(*) AS c FROM el_qualifiers WHERE from_season = ?",
            (from_season,),
        )
        total = cursor.fetchone()["c"]
        conn.commit()
        return {"season": season, "qualified_total": total,
                "registered": len(rows), "added": added}
    finally:
        conn.close()


def _el_seed_participants_from_qualifiers(cursor, season: int) -> int:
    """
    Qur'a uchun ishtirokchilarni TO'G'RIDAN-TO'G'RI el_qualifiers'dan oladi
    (ochiq tranzaksiya cursor'i bilan). Kvalifikant yangi mavsum ligasiga
    yozilmagan bo'lsa ham qatnashadi — huquq telegram_id'ga tegishli.
    club_name: joriy mavsumdagi yangi klubi, bo'lmasa NULL.
    Qaytaradi: qo'shilganlar soni.
    """
    from_season = _latest_el_from_season(cursor)
    if not from_season:
        return 0

    cursor.execute(
        """
        SELECT q.telegram_id, u.id AS user_id, q.nickname, r.club_name
        FROM el_qualifiers q
        JOIN users u ON u.telegram_id = q.telegram_id
        LEFT JOIN registrations r ON r.user_id = u.id
        WHERE q.from_season = ?
        """,
        (from_season,),
    )
    return sum(1 for r in cursor.fetchall() if _insert_participant(cursor, season, r))
