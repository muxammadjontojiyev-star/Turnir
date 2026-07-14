"""
Chempionlar ligasi (ChL) yadrosi: a'zolik sinxroni, 8 guruh qur'asi, reyting.

Oqim:
  1. Liga mavsumi yakunlanadi -> cl_qualifiers'da 32 telegram_id (cl_qualification).
  2. Yangi mavsumda kvalifikant liga ro'yxatidan o'tadi (istalgan YANGI klub bilan)
     -> cl_sync_participants() uni cl_participants'ga qo'shadi (asosiy e'tibor
     odamda: telegram_id; klub — faqat ko'rsatish uchun snapshot).
  3. Admin qur'a o'tkazadi (cl_draw) -> 8 guruh × 4, har guruhga round-robin
     kalendar (3 tur × 2 o'yin = 6) cl_matches'ga yoziladi.
  4. Guruh reytingi: g'alaba=3, durang=1 (real ChL standarti), saralash
     ball > gol farqi > urilgan gol.
"""

import logging
import random

from models import get_connection
from config import MATCH_STATUS_PENDING, MATCH_STATUS_CONFIRMED
from schedule import _generate_round_robin_pairs

logger = logging.getLogger(__name__)

CL_GROUPS = 8
CL_GROUP_SIZE = 4


def _current_league_season(cursor) -> int:
    cursor.execute("SELECT current_season FROM season_state WHERE id = 1")
    row = cursor.fetchone()
    return row["current_season"] if row else 1


def cl_sync_participants(season: int | None = None) -> dict:
    """
    Kvalifikantlarni (oxirgi cl_qualifiers) joriy mavsum liga ro'yxatlari bilan
    solishtirib, ro'yxatdan o'tganlarini cl_participants'ga qo'shadi.
    Idempotent (INSERT OR IGNORE + UNIQUE). Qur'a o'tkazilganidan keyin ham
    chaqirish xavfsiz — yangi qo'shilganlar group_number=NULL bo'lib qoladi
    (qur'a faqat qur'agacha qo'shilganlarni qamraydi).

    Qaytaradi: {"season", "qualified_total", "registered", "added"}
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if season is None:
            season = _current_league_season(cursor)

        cursor.execute("SELECT MAX(from_season) AS s FROM cl_qualifiers")
        row = cursor.fetchone()
        from_season = row["s"] if row else None
        if not from_season:
            return {"season": season, "qualified_total": 0, "registered": 0, "added": 0}

        # Kvalifikant + joriy mavsumda liga ro'yxatidan o'tgan (yangi klubi bilan)
        cursor.execute(
            """
            SELECT q.telegram_id, u.id AS user_id, u.nickname, r.club_name
            FROM cl_qualifiers q
            JOIN users u ON u.telegram_id = q.telegram_id
            JOIN registrations r ON r.user_id = u.id
            WHERE q.from_season = ?
            """,
            (from_season,),
        )
        rows = cursor.fetchall()

        added = 0
        for r in rows:
            cursor.execute(
                "INSERT OR IGNORE INTO cl_participants "
                "(season, telegram_id, user_id, nickname, club_name) "
                "VALUES (?, ?, ?, ?, ?)",
                (season, r["telegram_id"], r["user_id"], r["nickname"], r["club_name"]),
            )
            if cursor.rowcount > 0:
                added += 1

        cursor.execute(
            "SELECT COUNT(*) AS c FROM cl_qualifiers WHERE from_season = ?",
            (from_season,),
        )
        total = cursor.fetchone()["c"]
        conn.commit()
        return {"season": season, "qualified_total": total,
                "registered": len(rows), "added": added}
    finally:
        conn.close()


def _seed_participants_from_qualifiers(cursor, season: int) -> int:
    """
    Qur'a uchun ishtirokchilarni TO'G'RIDAN-TO'G'RI cl_qualifiers'dan oladi
    (yangi mavsum liga ro'yxatini kutmasdan) va cl_participants'ga yozadi.

    Sabab (qoida #19): kvalifikatsiya huquqi ODAMGA (telegram_id) tegishli;
    32 kvalifikant qur'ada qatnashishi kerak, ular yangi mavsum ligasiga
    yozilgan-yozilmaganidan qat'i nazar.

    club_name — agar joriy mavsumda ro'yxatdan o'tgan bo'lsa yangi klubi,
    aks holda kvalifikatsiya paytidagi snapshot (NULL bo'lishi mumkin).
    INSERT OR IGNORE — idempotent (qoida #38). Qaytaradi: qo'shilganlar soni.
    """
    cursor.execute("SELECT MAX(from_season) AS s FROM cl_qualifiers")
    row = cursor.fetchone()
    from_season = row["s"] if row else None
    if not from_season:
        return 0

    cursor.execute(
        """
        SELECT q.telegram_id, u.id AS user_id, q.nickname, r.club_name
        FROM cl_qualifiers q
        JOIN users u ON u.telegram_id = q.telegram_id
        LEFT JOIN registrations r ON r.user_id = u.id
        WHERE q.from_season = ?
        """,
        (from_season,),
    )
    added = 0
    for r in cursor.fetchall():
        cursor.execute(
            "INSERT OR IGNORE INTO cl_participants "
            "(season, telegram_id, user_id, nickname, club_name) "
            "VALUES (?, ?, ?, ?, ?)",
            (season, r["telegram_id"], r["user_id"], r["nickname"], r["club_name"]),
        )
        if cursor.rowcount > 0:
            added += 1
    return added


def cl_draw(season: int | None = None) -> tuple[bool, str | dict]:
    """
    ChL guruh qur'asi: ishtirokchilarni tasodifiy aralashtirib 8 guruhga
    (4 tadan) bo'ladi va har guruh uchun round-robin kalendar yaratadi.

    Himoyalar: allaqachon o'tkazilgan bo'lsa -> already_drawn;
    ishtirokchi yo'q bo'lsa -> no_participants. Bitta tranzaksiya.
    """
    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        if season is None:
            season = _current_league_season(cursor)

        cursor.execute(
            "SELECT 1 FROM cl_matches WHERE season = ? LIMIT 1", (season,)
        )
        if cursor.fetchone():
            cursor.execute("ROLLBACK")
            return False, "already_drawn"

        # Kvalifikantlarni (32 ta) shu tranzaksiya ichida ishtirokchiga aylantiramiz
        _seed_participants_from_qualifiers(cursor, season)

        cursor.execute(
            "SELECT id, user_id FROM cl_participants WHERE season = ?", (season,)
        )
        parts = [dict(r) for r in cursor.fetchall()]
        if not parts:
            cursor.execute("ROLLBACK")
            return False, "no_participants"

        random.shuffle(parts)

        created_matches = 0
        groups_used = 0
        for g in range(CL_GROUPS):
            chunk = parts[g * CL_GROUP_SIZE:(g + 1) * CL_GROUP_SIZE]
            if not chunk:
                break
            groups_used += 1
            group_number = g + 1
            for p in chunk:
                cursor.execute(
                    "UPDATE cl_participants SET group_number = ? WHERE id = ?",
                    (group_number, p["id"]),
                )
            # Round-robin faqat 2+ o'yinchida ma'noga ega
            player_ids = [p["user_id"] for p in chunk]
            if len(player_ids) < 2:
                continue
            # Ikki doira: birinchi doira (uy) + qaytish doirasi (juftlik teskari)
            first_leg = _generate_round_robin_pairs(player_ids)
            second_leg = [[(away, home) for (home, away) in rnd] for rnd in first_leg]
            rounds = first_leg + second_leg   # 4 o'yinchi → 6 tur, guruhda 12 o'yin
            for matchday, pairs in enumerate(rounds, start=1):
                for (p1, p2) in pairs:
                    cursor.execute(
                        "INSERT INTO cl_matches "
                        "(season, group_number, matchday, player1_id, player2_id, status) "
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        (season, group_number, matchday, p1, p2, MATCH_STATUS_PENDING),
                    )
                    created_matches += 1

        cursor.execute("COMMIT")
        logger.info("ChL qur'a: %s guruh, %s o'yin (mavsum %s)",
                    groups_used, created_matches, season)
        return True, {"season": season, "groups": groups_used,
                      "matches": created_matches, "participants": len(parts)}
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        conn.close()


def cl_get_groups(season: int | None = None) -> dict:
    """Guruhlar va a'zolari (qur'adan keyin). Qur'agacha — participants ro'yxati."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if season is None:
            season = _current_league_season(cursor)
        cursor.execute(
            "SELECT telegram_id, user_id, nickname, club_name, group_number "
            "FROM cl_participants WHERE season = ? "
            "ORDER BY group_number, nickname",
            (season,),
        )
        rows = [dict(r) for r in cursor.fetchall()]
        drawn = any(r["group_number"] for r in rows)
        return {"season": season, "drawn": drawn, "participants": rows}
    finally:
        conn.close()


def cl_group_rating(group_number: int, season: int | None = None) -> list[dict]:
    """
    Guruh reyting jadvali (faqat confirmed cl_matches):
    g'alaba=3, durang=1; saralash ball > gol farqi > urilgan gol.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if season is None:
            season = _current_league_season(cursor)
        cursor.execute(
            "SELECT p.user_id, p.nickname, p.club_name, u.username "
            "FROM cl_participants p JOIN users u ON u.id = p.user_id "
            "WHERE p.season = ? AND p.group_number = ?",
            (season, group_number),
        )
        players = {r["user_id"]: {
            "user_id": r["user_id"], "nickname": r["nickname"],
            "username": r["username"],
            "club_name": r["club_name"], "played": 0, "wins": 0, "draws": 0,
            "losses": 0, "goals_for": 0, "goals_against": 0, "points": 0,
        } for r in cursor.fetchall()}

        cursor.execute(
            "SELECT player1_id, player2_id, score1, score2 FROM cl_matches "
            "WHERE season = ? AND group_number = ? AND status = ?",
            (season, group_number, MATCH_STATUS_CONFIRMED),
        )
        for m in cursor.fetchall():
            p1, p2, s1, s2 = m["player1_id"], m["player2_id"], m["score1"], m["score2"]
            if p1 not in players or p2 not in players:
                continue
            players[p1]["played"] += 1; players[p2]["played"] += 1
            players[p1]["goals_for"] += s1; players[p1]["goals_against"] += s2
            players[p2]["goals_for"] += s2; players[p2]["goals_against"] += s1
            if s1 > s2:
                players[p1]["wins"] += 1; players[p1]["points"] += 3
                players[p2]["losses"] += 1
            elif s2 > s1:
                players[p2]["wins"] += 1; players[p2]["points"] += 3
                players[p1]["losses"] += 1
            else:
                players[p1]["draws"] += 1; players[p2]["draws"] += 1
                players[p1]["points"] += 1; players[p2]["points"] += 1

        table = list(players.values())
        for p in table:
            p["goal_difference"] = p["goals_for"] - p["goals_against"]
        table.sort(key=lambda p: (p["points"], p["goal_difference"], p["goals_for"]),
                   reverse=True)
        return table
    finally:
        conn.close()
