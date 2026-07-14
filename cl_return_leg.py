"""
cl_return_leg.py — mavjud ChL qur'asiga QAYTISH DOIRASINI qo'shish.

Nega kerak (qoida 19): qur'a bir doira (har juftlik 1 marta) bilan o'tkazilgan
edi. Guruh bosqichi uy/mehmon tartibida bo'lishi kerak — har juftlik 2 marta.
Yangi qur'a (cl_core.cl_draw) endi darhol ikki doira yaratadi; bu modul esa
ALLAQACHON o'tkazilgan qur'a uchun yetishmayotgan qaytish o'yinlarini qo'shadi.

Idempotent (qoida #38): mavjud juftlik-yo'nalishlari tekshiriladi, faqat
yo'qlari qo'shiladi. Tugagan/kiritilgan natijalarga TEGMAYDI.
"""

import logging

from models import get_connection
from config import MATCH_STATUS_PENDING

logger = logging.getLogger(__name__)


def cl_add_return_leg(season: int | None = None) -> tuple[bool, str | dict]:
    """
    Har guruhdagi har juftlik uchun teskari yo'nalishdagi o'yin (mehmon) yo'q
    bo'lsa — qo'shadi. Yangi turlar mavjud eng katta matchday'dan keyin boshlanadi.

    Qaytaradi: (True, {"season", "added", "groups"}) yoki (False, sabab).
    Sabablar: not_drawn (qur'a yo'q), nothing_to_add (hammasi bor).
    """
    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        if season is None:
            cursor.execute("SELECT current_season FROM season_state WHERE id = 1")
            row = cursor.fetchone()
            season = row["current_season"] if row else 1

        cursor.execute(
            "SELECT group_number, matchday, player1_id, player2_id "
            "FROM cl_matches WHERE season = ?",
            (season,),
        )
        rows = [dict(r) for r in cursor.fetchall()]
        if not rows:
            cursor.execute("ROLLBACK")
            return False, "not_drawn"

        # Mavjud yo'nalishlar: (guruh, uy, mehmon) — takror yozmaslik uchun (set → O(1))
        existing = {(r["group_number"], r["player1_id"], r["player2_id"]) for r in rows}
        max_md = {}
        for r in rows:
            g = r["group_number"]
            max_md[g] = max(max_md.get(g, 0), r["matchday"])

        added = 0
        groups = set()
        for (g, p1, p2) in sorted(existing):
            if (g, p2, p1) in existing:
                continue                      # qaytish o'yini allaqachon bor
            max_md[g] += 1
            cursor.execute(
                "INSERT INTO cl_matches "
                "(season, group_number, matchday, player1_id, player2_id, status) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (season, g, max_md[g], p2, p1, MATCH_STATUS_PENDING),
            )
            added += 1
            groups.add(g)

        if added == 0:
            cursor.execute("ROLLBACK")
            return False, "nothing_to_add"

        cursor.execute("COMMIT")
        logger.info("ChL qaytish doirasi: %s o'yin qo'shildi (%s guruh, mavsum %s)",
                    added, len(groups), season)
        return True, {"season": season, "added": added, "groups": len(groups)}
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        conn.close()
