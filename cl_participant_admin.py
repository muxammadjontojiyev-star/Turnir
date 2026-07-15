"""
cl_participant_admin.py — ChL ishtirokchisini yangi akkountga ko'chirish.

Muammo (qoida #19): qur'a paytida ishtirokchining Telegram akkounti keyinchalik
o'chirilgan. Bot uning eski user_id'sini cl_participants va cl_matches'ga yozgan.
Endi o'sha odam yangi akkountda — uni eski o'rniga bog'lash kerak, aks holda
FOREIGN KEY xatosi (eski user_id users'da yo'q) va u o'ynay olmaydi.

Yechim: eski telegram_id bo'yicha cl_participants qatorini topib, uning
user_id/telegram_id/nickname'ini yangi akkount ma'lumotiga yangilaymiz.
cl_matches'dagi player1_id/player2_id ham yangi user_id'ga ko'chiriladi.
"""

import logging

from models import get_connection

logger = logging.getLogger(__name__)


def cl_reassign_participant(old_telegram_id: int, new_telegram_id: int
                            ) -> tuple[bool, str | dict]:
    """
    Eski akkount (o'chirilgan) o'rniga yangi akkountni ChL ishtirokchisi qiladi.

    Sabablar:
      new_user_not_found     — yangi telegram_id users'da yo'q
      old_not_participant    — eski telegram_id ChL ishtirokchisi emas
      new_already_participant — yangi akkount allaqachon shu mavsumda ishtirokchi
    """
    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")

        # Yangi akkount users'da bormi?
        cursor.execute(
            "SELECT id, nickname FROM users WHERE telegram_id = ?", (new_telegram_id,))
        new_user = cursor.fetchone()
        if not new_user:
            cursor.execute("ROLLBACK")
            return False, "new_user_not_found"
        new_user_id = new_user["id"]

        # Eski ishtirokchi qatori (barcha mavsumlar bo'yicha — odatda joriy)
        cursor.execute(
            "SELECT id, season, user_id, group_number FROM cl_participants "
            "WHERE telegram_id = ?", (old_telegram_id,))
        old_rows = [dict(r) for r in cursor.fetchall()]
        if not old_rows:
            cursor.execute("ROLLBACK")
            return False, "old_not_participant"

        old_user_id = old_rows[0]["user_id"]

        # Yangi akkount allaqachon shu mavsumlarda ishtirokchi emasligi (dublikat oldini olish)
        seasons = tuple({r["season"] for r in old_rows})
        placeholders = ",".join("?" * len(seasons))
        cursor.execute(
            f"SELECT COUNT(*) AS c FROM cl_participants "
            f"WHERE telegram_id = ? AND season IN ({placeholders})",
            (new_telegram_id, *seasons),
        )
        if cursor.fetchone()["c"] > 0:
            cursor.execute("ROLLBACK")
            return False, "new_already_participant"

        # 1) cl_participants: eski qatorlarni yangi akkountga ko'chiramiz
        cursor.execute(
            "UPDATE cl_participants SET user_id = ?, telegram_id = ?, nickname = ? "
            "WHERE telegram_id = ?",
            (new_user_id, new_telegram_id, new_user["nickname"], old_telegram_id),
        )
        participants_updated = cursor.rowcount or 0

        # 2) cl_matches: player1_id/player2_id eski user_id -> yangi user_id
        cursor.execute(
            "UPDATE cl_matches SET player1_id = ? WHERE player1_id = ?",
            (new_user_id, old_user_id))
        m1 = cursor.rowcount or 0
        cursor.execute(
            "UPDATE cl_matches SET player2_id = ? WHERE player2_id = ?",
            (new_user_id, old_user_id))
        m2 = cursor.rowcount or 0

        # 3) submitted_by ham (agar eski id bilan yozilgan bo'lsa)
        cursor.execute(
            "UPDATE cl_matches SET submitted_by = ? WHERE submitted_by = ?",
            (new_user_id, old_user_id))

        cursor.execute("COMMIT")
        logger.info("ChL ishtirokchi ko'chirildi: tg %s -> %s (user %s -> %s), "
                    "%s qator, %s+%s o'yin",
                    old_telegram_id, new_telegram_id, old_user_id, new_user_id,
                    participants_updated, m1, m2)
        return True, {"participants_updated": participants_updated,
                      "matches_updated": m1 + m2,
                      "new_user_id": new_user_id}
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        conn.close()
