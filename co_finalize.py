"""
co_finalize.py — Konferensiya ligasi mavsumini yakunlash va kubok (season_prizes.finalize_cl_season
naqshi, ALOHIDA). season_prizes.py 560+ qator bo'lgani uchun alohida fayl (qoida #21) —
division_finalize.py bilan bir xil yondashuv.

  calculate_co_prizes()  — joriy setka chempioni (co_po_bracket).
  finalize_co_season()   — co_cup (season_kind='co') saqlanadi, co_season oshadi,
                           cooldown belgilanadi, so'ng reset_co_data().
  get_co_cup_holder()    — Sovrinlar sahifasi: saqlangan oxirgi co_cup, bo'lmasa jonli chempion.

Kubok season_prizes'da DOIMIY qoladi: profil sahifasida va ★ yulduzchada ko'rinadi
(prize_stars.CUP_PRIZE_TYPES'da co_cup).
"""

import logging

from models import get_connection
from season_prizes import _cooldown_active, _telegram_id_for

logger = logging.getLogger(__name__)

CO_PRIZE_CUP = "co_cup"
CO_SEASON_KIND = "co"


def calculate_co_prizes() -> dict:
    """{"co_cup": {user_id, nickname, username, club_name} | None} — final g'olibi."""
    from co_playoff_view import co_po_bracket
    try:
        bracket = co_po_bracket()
    except Exception:
        logger.exception("calculate_co_prizes: setkani o'qishda xato")
        return {CO_PRIZE_CUP: None}
    champ = bracket.get("champion") if bracket.get("started") else None
    if champ and not champ.get("user_id"):
        champ = None
    return {CO_PRIZE_CUP: champ}


def finalize_co_season() -> dict:
    """
    Qaytaradi: {season, already, counts, prizes, reset[, reason]}
    already=True — takror bosish (cooldown yoki shu mavsum allaqachon yozilgan).
    reason='no_champion' — final o'ynalmagan, hech narsa o'zgarmaydi.
    """
    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute("SELECT co_season FROM season_state WHERE id = 1")
        row = cursor.fetchone()
        season = row["co_season"] if row else 1

        if _cooldown_active(cursor, "co_last_finalized_at"):
            cursor.execute("ROLLBACK")
            return {"season": season, "already": True, "counts": {}, "prizes": None}
        cursor.execute(
            "SELECT 1 FROM season_prizes WHERE season_kind = ? AND season_number = ? LIMIT 1",
            (CO_SEASON_KIND, season),
        )
        if cursor.fetchone() is not None:
            cursor.execute("ROLLBACK")
            return {"season": season, "already": True, "counts": {}, "prizes": None}

        prizes = calculate_co_prizes()
        champ = prizes.get(CO_PRIZE_CUP)
        if not champ:
            cursor.execute("ROLLBACK")
            return {"season": season, "already": False, "counts": {CO_PRIZE_CUP: 0},
                    "prizes": prizes, "reason": "no_champion"}

        cursor.execute(
            "INSERT INTO season_prizes "
            "(user_id, telegram_id, prize_type, league_id, season_number, season_kind) "
            "VALUES (?, ?, ?, NULL, ?, ?)",
            (champ["user_id"], _telegram_id_for(cursor, champ["user_id"]),
             CO_PRIZE_CUP, season, CO_SEASON_KIND),
        )
        # 2026-11-01: mavsum mukofoti — bosqich bo'yicha eF Token (season_rewards.py, reset'dan OLDIN)
        from season_rewards import grant_cup_rewards
        rewards = grant_cup_rewards(cursor, "co", season, champ["user_id"])
        cursor.execute(
            "UPDATE season_state SET co_season = co_season + 1, "
            "co_last_finalized_at = datetime('now') WHERE id = 1"
        )
        cursor.execute("COMMIT")
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            logger.exception("finalize_co_season: ROLLBACK xatosi")
        raise
    finally:
        conn.close()

    logger.info("KL %s-mavsum yakunlandi: kubok user %s", season, champ["user_id"])
    # Kubok saqlandi — KL ma'lumoti tozalanadi (users/season_prizes tegilmaydi).
    # Xato bo'lsa kubok baribir saqlangan qoladi; admin qayta yakunlay olmaydi (cooldown),
    # shuning uchun xato logga yoziladi va javobda reset=None qaytadi.
    reset_info = None
    try:
        from season_reset import reset_co_data
        reset_info = reset_co_data()
    except Exception:
        logger.exception("KL reset xatosi (kubok saqlangan)")
    return {"season": season, "already": False, "counts": {CO_PRIZE_CUP: 1, "rewards": rewards},
            "prizes": prizes, "reset": reset_info}


def get_co_cup_holder() -> dict:
    """
    {"holder": {user_id, nickname, username, club_name, season} | None, "finalized": bool}
    1) season_prizes'dagi oxirgi co_cup (doimiy); 2) jonli setka chempioni.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT sp.season_number, sp.user_id, u.id AS cur_user_id, u.nickname, u.username
            FROM season_prizes sp
            LEFT JOIN users u ON u.telegram_id = sp.telegram_id
            WHERE sp.prize_type = ?
            ORDER BY sp.season_number DESC, sp.id DESC
            LIMIT 1
            """,
            (CO_PRIZE_CUP,),
        )
        row = cursor.fetchone()
    finally:
        conn.close()
    if row:
        return {"finalized": True, "holder": {
            "user_id": row["cur_user_id"] or row["user_id"], "nickname": row["nickname"],
            "username": row["username"], "club_name": None, "season": row["season_number"]}}
    champ = calculate_co_prizes().get(CO_PRIZE_CUP)
    if champ:
        return {"finalized": False, "holder": {**champ, "season": None}}
    return {"finalized": False, "holder": None}
