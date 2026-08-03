"""
cl_schedule_fix.py — ChL liga bosqichi kalendarini QAYTA QURISH (Swiss, 8 tur).

Yangi format (2026-08): guruh yo'q — barcha ishtirokchi CL_LEAGUE_GROUP(1) da,
Swiss juftlash bilan 8 tur (bir doira, mehmon o'yinisiz). Bu funksiya qur'a
tarkibini (ishtirokchilar) SAQLAB, kalendarni qaytadan yozadi.

XAVFSIZLIK: force=False bo'lsa faqat HECH QANDAY natija kiritilmagan holatda
ishlaydi (barcha 'pending'). force=True: mavjud natijalar juftlik bo'yicha yangi
kalendarga ko'chiriladi. Aks holda -> results_exist (400).
"""

import logging

from models import get_connection
from config import MATCH_STATUS_PENDING
from schedule import _generate_round_robin_pairs
from cl_core import CL_LEAGUE_GROUP, CL_ROUNDS

logger = logging.getLogger(__name__)


def cl_rebuild_schedule(season: int | None = None, force: bool = False
                        ) -> tuple[bool, str | dict]:
    """
    Liga bosqichi o'yinlarini Swiss (8 tur, bir doira, mehmon o'yinisiz) kalendar
    qilib qaytadan yozadi. Ishtirokchilar tarkibi (qur'a) O'ZGARMAYDI.

    force=False: natija kiritilgan bo'lsa ishlamaydi (results_exist).
    force=True : mavjud natijalar (juftlik bo'yicha) YANGI kalendarga KO'CHIRILADI,
                 qolganlari pending. Buzuq kalendarni tuzatish uchun.

    ⚠️ OGOHLANTIRISH (Swiss cheklovi): guruh formatidan farqli, Swiss'da har juftlik
    kafolatlangan holda uchramaydi. force=True da agar o'ynalgan juftlik yangi 8 turga
    tushmasa, o'sha natija YO'QOLADI. Shuning uchun bu funksiya asosan qur'adan keyin
    NATIJASIZ holatda ishlatilishi kerak.

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

        # Natija kiritilgan o'yin bormi?
        cursor.execute(
            "SELECT COUNT(*) AS c FROM cl_matches "
            "WHERE season = ? AND (status != ? OR score1 IS NOT NULL)",
            (season, MATCH_STATUS_PENDING),
        )
        has_results = cursor.fetchone()["c"] > 0
        if has_results and not force:
            cursor.execute("ROLLBACK")
            return False, "results_exist"

        # force rejimida: mavjud natijalarni juftlik bo'yicha eslab qolamiz.
        # Swiss'da har juftlik faqat 1 marta uchraydi — kalit tartibsiz (frozenset),
        # qiymatda esa ASL yo'nalish (home_id) saqlanadi (qayta yozishda tiklanadi).
        saved = {}   # frozenset({a,b}) -> (home_id, score_home, score_away, status, submitted_by)
        if has_results:
            cursor.execute(
                "SELECT player1_id, player2_id, score1, score2, "
                "status, submitted_by FROM cl_matches "
                "WHERE season = ? AND (status != ? OR score1 IS NOT NULL)",
                (season, MATCH_STATUS_PENDING),
            )
            for r in cursor.fetchall():
                key = frozenset((r["player1_id"], r["player2_id"]))
                saved[key] = (r["player1_id"], r["score1"], r["score2"],
                              r["status"], r["submitted_by"])

        # Yangi format: guruh yo'q — barcha ishtirokchi bitta ro'yxatda (Swiss)
        cursor.execute(
            "SELECT p.user_id FROM cl_participants p "
            "JOIN users u ON u.id = p.user_id "
            "WHERE p.season = ? AND p.group_number IS NOT NULL "
            "ORDER BY p.id",
            (season,),
        )
        players_all: list[int] = []
        for r in cursor.fetchall():
            if r["user_id"] is None:
                continue
            if r["user_id"] not in players_all:   # dublikatlarni oldini olamiz
                players_all.append(r["user_id"])
        if len(players_all) < 2:
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

        # Swiss juftlash: bitta ro'yxatdan circle method, dastlabki CL_ROUNDS(8) tur
        # (qoida #26 DRY — cl_core.cl_draw bilan bir xil mantiq).
        created = 0
        all_rounds = _generate_round_robin_pairs(players_all)
        rounds = all_rounds[:CL_ROUNDS]
        for matchday, pairs in enumerate(rounds, start=1):
            for (p1, p2) in pairs:
                if p1 is None or p2 is None:  # toq son "bye" — yozmaymiz
                    continue
                # force: shu juftlik uchun saqlangan natija bo'lsa — ASL yo'nalishda tiklaymiz
                rec = saved.get(frozenset((p1, p2))) if has_results else None
                if rec:
                    home_id, sc_home, sc_away, st, sub = rec
                    # Saqlangan uy egasini (home_id) player1 sifatida yozamiz —
                    # natija yo'nalishi o'zgarmasin
                    if home_id == p1:
                        w1, w2, s1, s2 = p1, p2, sc_home, sc_away
                    else:
                        w1, w2, s1, s2 = home_id, p1, sc_home, sc_away
                    cursor.execute(
                        "INSERT INTO cl_matches "
                        "(season, group_number, matchday, player1_id, player2_id, "
                        " score1, score2, status, submitted_by) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (season, CL_LEAGUE_GROUP, matchday, w1, w2, s1, s2, st, sub),
                    )
                else:
                    cursor.execute(
                        "INSERT INTO cl_matches "
                        "(season, group_number, matchday, player1_id, player2_id, status) "
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        (season, CL_LEAGUE_GROUP, matchday, p1, p2, MATCH_STATUS_PENDING),
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
        logger.info("ChL kalendar qayta qurildi (Swiss): %s o'yin, %s ishtirokchi (mavsum %s)",
                    created, len(players_all), season)
        return True, {"season": season, "matches": created,
                      "groups": 1, "players": len(players_all)}
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        conn.close()
