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


def cl_list_orphan_participants() -> list[dict]:
    """
    cl_participants'dan user_id users jadvalida yo'q bo'lganlar (o'chirilgan akkount).
    [{participant_id, season, user_id, nickname, club_name, group_number}, ...]
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT p.id AS participant_id, p.season, p.user_id, p.nickname, "
            "p.club_name, p.group_number "
            "FROM cl_participants p "
            "LEFT JOIN users u ON u.id = p.user_id "
            "WHERE u.id IS NULL "
            "ORDER BY p.group_number, p.id"
        )
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()


def cl_reassign_participant(participant_id: int, new_telegram_id: int
                            ) -> tuple[bool, str | dict]:
    """
    ChL ishtirokchi qatorini (participant_id) yangi akkountga bog'laydi.
    Eski Telegram ID kerak emas — participant_id yetarli (o'chirilgan akkountга kirib
    bo'lmaydi, shuning uchun ID'ni ro'yxatdan tanlaydi).

    Sabablar: new_user_not_found, participant_not_found, new_already_participant
    """
    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")

        cursor.execute(
            "SELECT id, nickname FROM users WHERE telegram_id = ?", (new_telegram_id,))
        new_user = cursor.fetchone()
        if not new_user:
            cursor.execute("ROLLBACK")
            return False, "new_user_not_found"
        new_user_id = new_user["id"]

        cursor.execute(
            "SELECT id, season, user_id FROM cl_participants WHERE id = ?",
            (participant_id,))
        part = cursor.fetchone()
        if not part:
            cursor.execute("ROLLBACK")
            return False, "participant_not_found"
        old_user_id = part["user_id"]
        season = part["season"]

        # Yangi akkount shu mavsumda allaqachon ishtirokchi emasligini tekshiramiz
        cursor.execute(
            "SELECT COUNT(*) AS c FROM cl_participants "
            "WHERE season = ? AND user_id = ? AND id != ?",
            (season, new_user_id, participant_id),
        )
        if cursor.fetchone()["c"] > 0:
            cursor.execute("ROLLBACK")
            return False, "new_already_participant"

        # 1) cl_participants — shu qatorni yangi akkountga ko'chiramiz
        cursor.execute(
            "UPDATE cl_participants SET user_id = ?, telegram_id = ?, nickname = ? "
            "WHERE id = ?",
            (new_user_id, new_telegram_id, new_user["nickname"], participant_id),
        )

        # 2) cl_matches — shu mavsumdagi eski user_id -> yangi user_id
        cursor.execute(
            "UPDATE cl_matches SET player1_id = ? WHERE season = ? AND player1_id = ?",
            (new_user_id, season, old_user_id))
        m1 = cursor.rowcount or 0
        cursor.execute(
            "UPDATE cl_matches SET player2_id = ? WHERE season = ? AND player2_id = ?",
            (new_user_id, season, old_user_id))
        m2 = cursor.rowcount or 0
        cursor.execute(
            "UPDATE cl_matches SET submitted_by = ? WHERE season = ? AND submitted_by = ?",
            (new_user_id, season, old_user_id))

        cursor.execute("COMMIT")
        logger.info("ChL ishtirokchi ko'chirildi: participant %s (user %s -> %s tg %s), "
                    "%s+%s o'yin",
                    participant_id, old_user_id, new_user_id, new_telegram_id, m1, m2)
        return True, {"matches_updated": m1 + m2, "new_user_id": new_user_id}
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        conn.close()
