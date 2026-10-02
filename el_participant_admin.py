"""
el_participant_admin.py — YeL ishtirokchisini yangi akkountga ko'chirish
(cl_participant_admin naqshi, ALOHIDA nusxa). Faqat bosh admin.

Muammo: ishtirokchining Telegram akkounti o'chirilib, yangisi ochilgan. Eski
user_id el_participants/el_matches'da qolgan — yangi akkount o'ynay olmaydi.
Yechim: eski user_id o'rniga yangi akkount (telegram_id bo'yicha topiladi)
bog'lanadi. Qur'a o'zgarmaydi — faqat player_id ko'chadi.
"""

import logging

from models import get_connection

logger = logging.getLogger(__name__)


def _current_season(cursor) -> int:
    cursor.execute("SELECT current_season FROM season_state WHERE id = 1")
    row = cursor.fetchone()
    return row["current_season"] if row else 1


def el_list_all_participants() -> list[dict]:
    """
    Joriy mavsumdagi BARCHA YeL ishtirokchilari. orphan=1 — user_id users'da yo'q.
    [{user_id, nickname, club_name, group_number, orphan}, ...]
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT p.user_id, p.nickname, p.club_name, p.group_number, "
            "CASE WHEN u.id IS NULL THEN 1 ELSE 0 END AS orphan "
            "FROM el_participants p LEFT JOIN users u ON u.id = p.user_id "
            "WHERE p.season = ? ORDER BY p.group_number, p.nickname",
            (_current_season(cursor),),
        )
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()


def el_reassign_participant(old_user_id: int, new_telegram_id: int
                            ) -> tuple[bool, str | dict]:
    """
    Sabablar: new_user_not_found, nothing_to_reassign, new_already_participant.
    Bitta tranzaksiya: el_participants + el_matches (player1/2_id, submitted_by).
    """
    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute("SELECT id, nickname FROM users WHERE telegram_id = ?", (new_telegram_id,))
        new_user = cursor.fetchone()
        if not new_user:
            cursor.execute("ROLLBACK")
            return False, "new_user_not_found"
        new_user_id = new_user["id"]

        cursor.execute(
            "SELECT DISTINCT season FROM el_participants WHERE user_id = ? "
            "UNION SELECT DISTINCT season FROM el_matches "
            "WHERE player1_id = ? OR player2_id = ?",
            (old_user_id, old_user_id, old_user_id),
        )
        seasons = [r["season"] for r in cursor.fetchall()]
        if not seasons:
            cursor.execute("ROLLBACK")
            return False, "nothing_to_reassign"

        ph = ",".join("?" * len(seasons))
        cursor.execute(
            f"SELECT COUNT(*) AS c FROM el_participants WHERE user_id = ? AND season IN ({ph})",
            (new_user_id, *seasons),
        )
        if cursor.fetchone()["c"] > 0:
            cursor.execute("ROLLBACK")
            return False, "new_already_participant"

        cursor.execute(
            "UPDATE el_participants SET user_id = ?, telegram_id = ?, nickname = ? "
            "WHERE user_id = ?",
            (new_user_id, new_telegram_id, new_user["nickname"], old_user_id),
        )
        parts = cursor.rowcount or 0
        moved = 0
        for col in ("player1_id", "player2_id"):
            cursor.execute(f"UPDATE el_matches SET {col} = ? WHERE {col} = ?",
                           (new_user_id, old_user_id))
            moved += cursor.rowcount or 0
        cursor.execute("UPDATE el_matches SET submitted_by = ? WHERE submitted_by = ?",
                       (new_user_id, old_user_id))
        cursor.execute("COMMIT")
        logger.info("YeL akkount ko'chirildi: user %s -> %s (tg %s), %s participant, %s o'yin",
                    old_user_id, new_user_id, new_telegram_id, parts, moved)
        return True, {"participants_updated": parts, "matches_updated": moved,
                      "new_user_id": new_user_id}
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            logger.exception("el_reassign_participant: ROLLBACK xatosi")
        raise
    finally:
        conn.close()
