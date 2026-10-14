"""
Osiyo Chempionlar ligasi (OChL) yadrosi — cl_core.py naqshi, ALOHIDA nusxa (ChL'ga tegilmaydi).

Format (ChL bilan bir xil): guruh YO'Q, 32 klub yagona liga bosqichida —
har biri 8 ta TURLI raqib bilan mehmon o'yinisiz (1 martadan) o'ynaydi.

Oqim:
  1. Liga mavsumi yakunlanadi -> ac_qualifiers'da 32 telegram_id (ac_qualification).
  2. Yangi mavsumda kvalifikant liga ro'yxatidan o'tadi (istalgan YANGI klub bilan)
     -> ac_sync_participants() uni ac_participants'ga qo'shadi. Huquq ODAMDA
     (telegram_id), klub — faqat ko'rsatish uchun snapshot.
  3. Qur'ada _ac_seed_participants_from_qualifiers() — yangi mavsum ligasiga
     yozilmagan kvalifikant ham qatnashadi (ChL bilan bir xil qaror).
"""

import logging
import random

from config import MATCH_STATUS_CONFIRMED, MATCH_STATUS_PENDING
from models import get_connection
from schedule import _generate_round_robin_pairs

logger = logging.getLogger(__name__)

AC_LEAGUE_GROUP = 1   # barcha ishtirokchining group_number qiymati (yagona reyting)
AC_ROUNDS = 8         # liga bosqichida har ishtirokchi o'ynaydigan o'yinlar soni


def get_ac_season() -> int:
    """Joriy OChL mavsum raqami (season_state.ac_season) — ko'rsatish uchun."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT ac_season FROM season_state WHERE id = 1")
        row = cursor.fetchone()
        return row["ac_season"] if row else 1
    finally:
        conn.close()


def _current_league_season(cursor) -> int:
    cursor.execute("SELECT current_season FROM season_state WHERE id = 1")
    row = cursor.fetchone()
    return row["current_season"] if row else 1


def _latest_ac_from_season(cursor) -> int | None:
    cursor.execute("SELECT MAX(from_season) AS s FROM ac_qualifiers")
    row = cursor.fetchone()
    return row["s"] if row and row["s"] else None


def _insert_participant(cursor, season: int, r) -> bool:
    """INSERT OR IGNORE + UNIQUE(telegram_id, season) — idempotent (qoida #38)."""
    cursor.execute(
        "INSERT OR IGNORE INTO ac_participants "
        "(season, telegram_id, user_id, nickname, club_name) "
        "VALUES (?, ?, ?, ?, ?)",
        (season, r["telegram_id"], r["user_id"], r["nickname"], r["club_name"]),
    )
    return cursor.rowcount > 0


def ac_sync_participants(season: int | None = None) -> dict:
    """
    Kvalifikantlarni (oxirgi ac_qualifiers) joriy mavsum liga ro'yxatlari bilan
    telegram_id orqali solishtirib, ro'yxatdan o'tganlarini ac_participants'ga
    qo'shadi (YANGI klubi bilan).

    Qaytaradi: {"season", "qualified_total", "registered", "added"}
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if season is None:
            season = _current_league_season(cursor)

        from_season = _latest_ac_from_season(cursor)
        if not from_season:
            return {"season": season, "qualified_total": 0, "registered": 0, "added": 0}

        cursor.execute(
            """
            SELECT q.telegram_id, u.id AS user_id, u.nickname, r.club_name
            FROM ac_qualifiers q
            JOIN users u ON u.telegram_id = q.telegram_id
            JOIN registrations r ON r.user_id = u.id
            WHERE q.from_season = ?
            """,
            (from_season,),
        )
        rows = cursor.fetchall()
        added = sum(1 for r in rows if _insert_participant(cursor, season, r))

        cursor.execute(
            "SELECT COUNT(*) AS c FROM ac_qualifiers WHERE from_season = ?",
            (from_season,),
        )
        total = cursor.fetchone()["c"]
        conn.commit()
        return {"season": season, "qualified_total": total,
                "registered": len(rows), "added": added}
    finally:
        conn.close()


def _ac_seed_participants_from_qualifiers(cursor, season: int) -> int:
    """
    Qur'a uchun ishtirokchilarni TO'G'RIDAN-TO'G'RI ac_qualifiers'dan oladi
    (ochiq tranzaksiya cursor'i bilan). Kvalifikant yangi mavsum ligasiga
    yozilmagan bo'lsa ham qatnashadi — huquq telegram_id'ga tegishli.
    club_name: joriy mavsumdagi yangi klubi, bo'lmasa NULL.
    Qaytaradi: qo'shilganlar soni.
    """
    from_season = _latest_ac_from_season(cursor)
    if not from_season:
        return 0

    cursor.execute(
        """
        SELECT q.telegram_id, u.id AS user_id, q.nickname, r.club_name
        FROM ac_qualifiers q
        JOIN users u ON u.telegram_id = q.telegram_id
        LEFT JOIN registrations r ON r.user_id = u.id
        WHERE q.from_season = ?
        """,
        (from_season,),
    )
    return sum(1 for r in cursor.fetchall() if _insert_participant(cursor, season, r))


def ac_draw(season: int | None = None) -> tuple[bool, str | dict]:
    """
    OChL Swiss qur'asi: kvalifikantlar ishtirokchiga aylanadi, tasodifiy
    aralashtiriladi va circle method'ning dastlabki AC_ROUNDS turi yoziladi
    (har kim 8 ta turli raqib bilan 1 martadan). Bitta tranzaksiya.
    Sabablar: already_drawn, no_participants.
    """
    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        if season is None:
            season = _current_league_season(cursor)

        cursor.execute("SELECT 1 FROM ac_matches WHERE season = ? LIMIT 1", (season,))
        if cursor.fetchone():
            cursor.execute("ROLLBACK")
            return False, "already_drawn"

        # Yangi qur'a — tur holati ham toza boshlanadi (ChL 2026-09-22 saboq'i:
        # eski holat yangi o'yinlar ustiga tushib, turlar yopiq qolmasin).
        # Xavfsiz: bu yerga faqat shu mavsumda o'yin YO'Q bo'lsa kelinadi.
        cursor.execute("DELETE FROM ac_state WHERE season = ?", (season,))

        _ac_seed_participants_from_qualifiers(cursor, season)
        cursor.execute("SELECT id, user_id FROM ac_participants WHERE season = ?", (season,))
        parts = [dict(r) for r in cursor.fetchall()]
        if not parts:
            cursor.execute("ROLLBACK")
            return False, "no_participants"

        random.shuffle(parts)
        cursor.execute(
            "UPDATE ac_participants SET group_number = ? WHERE season = ?",
            (AC_LEAGUE_GROUP, season),
        )

        player_ids = [p["user_id"] for p in parts]
        created = 0
        if len(player_ids) >= 2:
            rounds = _generate_round_robin_pairs(player_ids)[:AC_ROUNDS]
            for matchday, pairs in enumerate(rounds, start=1):
                for (p1, p2) in pairs:
                    cursor.execute(
                        "INSERT INTO ac_matches "
                        "(season, group_number, matchday, player1_id, player2_id, status) "
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        (season, AC_LEAGUE_GROUP, matchday, p1, p2, MATCH_STATUS_PENDING),
                    )
                    created += 1

        cursor.execute("COMMIT")
        logger.info("OChL qur'a: %s o'yin, %s ishtirokchi (mavsum %s)",
                    created, len(parts), season)
        return True, {"season": season, "groups": 1 if player_ids else 0,
                      "matches": created, "participants": len(parts)}
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            logger.exception("ac_draw: ROLLBACK xatosi")
        raise
    finally:
        conn.close()


def ac_get_groups(season: int | None = None) -> dict:
    """Liga bosqichi ishtirokchilari (yagona ro'yxat) + ac_season."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if season is None:
            season = _current_league_season(cursor)
        cursor.execute(
            "SELECT p.telegram_id, p.user_id, p.nickname, "
            "COALESCE(r.club_name, p.club_name) AS club_name, p.group_number "
            "FROM ac_participants p "
            "LEFT JOIN registrations r ON r.user_id = p.user_id "
            "WHERE p.season = ? ORDER BY p.group_number, p.nickname",
            (season,),
        )
        rows = [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()
    return {"season": season, "ac_season": get_ac_season(),
            "drawn": any(r["group_number"] for r in rows), "participants": rows}


def ac_group_rating(group_number: int = AC_LEAGUE_GROUP, season: int | None = None) -> list[dict]:
    """
    Yagona reyting (faqat confirmed ac_matches): g'alaba=3, durang=1;
    saralash ball > gol farqi > urilgan gol.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if season is None:
            season = _current_league_season(cursor)
        cursor.execute(
            "SELECT p.user_id, p.nickname, u.username, "
            "COALESCE(r.club_name, p.club_name) AS club_name "
            "FROM ac_participants p JOIN users u ON u.id = p.user_id "
            "LEFT JOIN registrations r ON r.user_id = p.user_id "
            "WHERE p.season = ? AND p.group_number = ?",
            (season, group_number),
        )
        players = {r["user_id"]: {
            "user_id": r["user_id"], "nickname": r["nickname"],
            "username": r["username"], "club_name": r["club_name"],
            "played": 0, "wins": 0, "draws": 0, "losses": 0,
            "goals_for": 0, "goals_against": 0, "points": 0,
        } for r in cursor.fetchall()}

        cursor.execute(
            "SELECT player1_id, player2_id, score1, score2 FROM ac_matches "
            "WHERE season = ? AND group_number = ? AND status = ?",
            (season, group_number, MATCH_STATUS_CONFIRMED),
        )
        matches = cursor.fetchall()
    finally:
        conn.close()

    for m in matches:
        a, b = players.get(m["player1_id"]), players.get(m["player2_id"])
        if a is None or b is None:
            continue
        _apply_result(a, m["score1"], m["score2"])
        _apply_result(b, m["score2"], m["score1"])

    table = list(players.values())
    for p in table:
        p["goal_difference"] = p["goals_for"] - p["goals_against"]
    table.sort(key=lambda p: (p["points"], p["goal_difference"], p["goals_for"]),
               reverse=True)
    return table


def _apply_result(p: dict, scored: int, conceded: int) -> None:
    """Bitta o'yinchining statistikasiga natijani qo'shadi (ikkala tomon uchun bitta kod)."""
    p["played"] += 1
    p["goals_for"] += scored
    p["goals_against"] += conceded
    if scored > conceded:
        p["wins"] += 1
        p["points"] += 3
    elif scored < conceded:
        p["losses"] += 1
    else:
        p["draws"] += 1
        p["points"] += 1
