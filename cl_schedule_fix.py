"""
cl_schedule_fix.py — ChL guruh kalendarini QAYTA QURISH (ikki doira, to'g'ri turlar).

Nega kerak (qoida 19): dastlabki qur'a bir doira yaratgan, keyin qo'shilgan
qaytish o'yinlari har juftlikka alohida tur bergan (4,5,6,7,8,9). To'g'risi:
4 o'yinchi → 6 tur, har turda 2 o'yin.

XAVFSIZLIK: faqat HECH QANDAY natija kiritilmagan bo'lsa ishlaydi (barcha
o'yinlar 'pending'). Aks holda -> results_exist (400) — o'ynalgan o'yin o'chmaydi.
"""

import logging

from models import get_connection
from config import MATCH_STATUS_PENDING
from schedule import _generate_round_robin_pairs

logger = logging.getLogger(__name__)


def cl_rebuild_schedule(season: int | None = None) -> tuple[bool, str | dict]:
    """
    Guruhlardagi barcha o'yinlarni o'chirib, ikki doirali (uy + mehmon)
    kalendarni qaytadan yozadi. Guruh tarkibi (qur'a) O'ZGARMAYDI.

    Sabablar: not_drawn, results_exist.
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
            "SELECT COUNT(*) AS c FROM cl_matches WHERE season = ?", (season,))
        if cursor.fetchone()["c"] == 0:
            cursor.execute("ROLLBACK")
            return False, "not_drawn"

        # Natija kiritilgan o'yin bormi? (pending'dan boshqa yoki score yozilgan)
        cursor.execute(
            "SELECT COUNT(*) AS c FROM cl_matches "
            "WHERE season = ? AND (status != ? OR score1 IS NOT NULL)",
            (season, MATCH_STATUS_PENDING),
        )
        if cursor.fetchone()["c"] > 0:
            cursor.execute("ROLLBACK")
            return False, "results_exist"

        cursor.execute(
            "SELECT p.group_number, p.user_id FROM cl_participants p "
            "JOIN users u ON u.id = p.user_id "
            "WHERE p.season = ? AND p.group_number IS NOT NULL "
            "ORDER BY p.group_number, p.id",
            (season,),
        )
        groups: dict[int, list[int]] = {}
        for r in cursor.fetchall():
            if r["user_id"] is None:
                continue
            lst = groups.setdefault(r["group_number"], [])
            if r["user_id"] not in lst:          # dublikatlarni oldini olamiz
                lst.append(r["user_id"])
        if not groups:
            cursor.execute("ROLLBACK")
            return False, "not_drawn"

        # cl_messages cl_matches'ga FK bilan bog'langan — avval ularni tozalaymiz
        # (o'ynalmagan o'yinlar chati baribir bo'sh). Aks holda DELETE FK'ni buzadi.
        try:
            cursor.execute(
                "DELETE FROM cl_messages WHERE match_id IN "
                "(SELECT id FROM cl_matches WHERE season = ?)", (season,))
        except Exception as exc:
            logger.warning("cl_messages tozalash o'tkazilmadi: %s", exc)
        cursor.execute("DELETE FROM cl_matches WHERE season = ?", (season,))

        created = 0
        for group_number, players in sorted(groups.items()):
            if len(players) < 2:
                continue
            first_leg = _generate_round_robin_pairs(players)
            second_leg = [[(a, h) for (h, a) in rnd] for rnd in first_leg]
            for matchday, pairs in enumerate(first_leg + second_leg, start=1):
                for (p1, p2) in pairs:
                    if p1 is None or p2 is None:  # toq son "bye" — yozmaymiz
                        continue
                    cursor.execute(
                        "INSERT INTO cl_matches "
                        "(season, group_number, matchday, player1_id, player2_id, status) "
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        (season, group_number, matchday, p1, p2, MATCH_STATUS_PENDING),
                    )
                    created += 1

        # Kalendar o'zgardi — tur hisoblagichini ham reset qilamiz (started bo'lsa
        # 1-turdan boshlanadi; bo'lmasa 0). cl_state jadvali bo'lmasligi mumkin — xavfsiz.
        try:
            cursor.execute(
                "UPDATE cl_state SET current_matchday = CASE WHEN started = 1 THEN 1 ELSE 0 END, "
                "last_advance_date = NULL WHERE season = ?",
                (season,),
            )
        except Exception as exc:
            logger.warning("cl_state reset o'tkazilmadi (jadval yo'q?): %s", exc)
        cursor.execute("COMMIT")
        logger.info("ChL kalendar qayta qurildi: %s o'yin, %s guruh (mavsum %s)",
                    created, len(groups), season)
        total_players = sum(len(v) for v in groups.values())
        return True, {"season": season, "matches": created,
                      "groups": len(groups), "players": total_players}
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        conn.close()
