"""
el_finalize.py — Yevropa ligasi mavsumini yakunlash va kubok (season_prizes.finalize_cl_season
naqshi, ALOHIDA). season_prizes.py 560+ qator bo'lgani uchun alohida fayl (qoida #21) —
division_finalize.py bilan bir xil yondashuv.

  calculate_el_prizes()  — joriy setka chempioni (el_po_bracket).
  finalize_el_season()   — el_cup (season_kind='el') saqlanadi, el_season oshadi,
                           cooldown belgilanadi, so'ng reset_el_data().
  get_el_cup_holder()    — Sovrinlar sahifasi: saqlangan oxirgi el_cup, bo'lmasa jonli chempion.

Kubok season_prizes'da DOIMIY qoladi: profil sahifasida va ★ yulduzchada ko'rinadi
(prize_stars.CUP_PRIZE_TYPES'da el_cup).
"""

import logging

from models import get_connection
from season_prizes import _cooldown_active, _telegram_id_for

logger = logging.getLogger(__name__)

EL_PRIZE_CUP = "el_cup"
EL_SEASON_KIND = "el"


def calculate_el_prizes() -> dict:
    """{"el_cup": {user_id, nickname, username, club_name} | None} — final g'olibi."""
    from el_playoff_view import el_po_bracket
    try:
        bracket = el_po_bracket()
    except Exception:
        logger.exception("calculate_el_prizes: setkani o'qishda xato")
        return {EL_PRIZE_CUP: None}
    champ = bracket.get("champion") if bracket.get("started") else None
    if champ and not champ.get("user_id"):
        champ = None
    return {EL_PRIZE_CUP: champ}


def finalize_el_season() -> dict:
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
        cursor.execute("SELECT el_season FROM season_state WHERE id = 1")
        row = cursor.fetchone()
        season = row["el_season"] if row else 1

        if _cooldown_active(cursor, "el_last_finalized_at"):
            cursor.execute("ROLLBACK")
            return {"season": season, "already": True, "counts": {}, "prizes": None}
        cursor.execute(
            "SELECT 1 FROM season_prizes WHERE season_kind = ? AND season_number = ? LIMIT 1",
            (EL_SEASON_KIND, season),
        )
        if cursor.fetchone() is not None:
            cursor.execute("ROLLBACK")
            return {"season": season, "already": True, "counts": {}, "prizes": None}

        prizes = calculate_el_prizes()
        champ = prizes.get(EL_PRIZE_CUP)
        if not champ:
            cursor.execute("ROLLBACK")
            return {"season": season, "already": False, "counts": {EL_PRIZE_CUP: 0},
                    "prizes": prizes, "reason": "no_champion"}

        cursor.execute(
            "INSERT INTO season_prizes "
            "(user_id, telegram_id, prize_type, league_id, season_number, season_kind) "
            "VALUES (?, ?, ?, NULL, ?, ?)",
            (champ["user_id"], _telegram_id_for(cursor, champ["user_id"]),
             EL_PRIZE_CUP, season, EL_SEASON_KIND),
        )
        cursor.execute(
            "UPDATE season_state SET el_season = el_season + 1, "
            "el_last_finalized_at = datetime('now') WHERE id = 1"
        )
        cursor.execute("COMMIT")
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            logger.exception("finalize_el_season: ROLLBACK xatosi")
        raise
    finally:
        conn.close()

    logger.info("YeL %s-mavsum yakunlandi: kubok user %s", season, champ["user_id"])
    # Kubok saqlandi — YeL ma'lumoti tozalanadi (users/season_prizes tegilmaydi).
    # Xato bo'lsa kubok baribir saqlangan qoladi; admin qayta yakunlay olmaydi (cooldown),
    # shuning uchun xato logga yoziladi va javobda reset=None qaytadi.
    reset_info = None
    try:
        from season_reset import reset_el_data
        reset_info = reset_el_data()
    except Exception:
        logger.exception("YeL reset xatosi (kubok saqlangan)")
    return {"season": season, "already": False, "counts": {EL_PRIZE_CUP: 1},
            "prizes": prizes, "reset": reset_info}


def get_el_cup_holder() -> dict:
    """
    {"holder": {user_id, nickname, username, club_name, season} | None, "finalized": bool}
    1) season_prizes'dagi oxirgi el_cup (doimiy); 2) jonli setka chempioni.
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
            (EL_PRIZE_CUP,),
        )
        row = cursor.fetchone()
    finally:
        conn.close()
    if row:
        return {"finalized": True, "holder": {
            "user_id": row["cur_user_id"] or row["user_id"], "nickname": row["nickname"],
            "username": row["username"], "club_name": None, "season": row["season_number"]}}
    champ = calculate_el_prizes().get(EL_PRIZE_CUP)
    if champ:
        return {"finalized": False, "holder": {**champ, "season": None}}
    return {"finalized": False, "holder": None}
