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


def cl_list_all_participants() -> list[dict]:
    """
    Joriy mavsumdagi BARCHA ChL ishtirokchilari (o'chirilgan/tirik farqi yo'q).
    Admin ularni yangi akkountga almashtirish uchun ro'yxatdan tanlaydi.
    orphan=True — user_id users'da yo'q (o'chirilgan akkount).
    [{user_id, nickname, club_name, group_number, orphan}, ...]
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT current_season FROM season_state WHERE id = 1")
        row = cursor.fetchone()
        season = row["current_season"] if row else 1

        cursor.execute(
            "SELECT p.user_id, p.nickname, p.club_name, p.group_number, "
            "CASE WHEN u.id IS NULL THEN 1 ELSE 0 END AS orphan "
            "FROM cl_participants p "
            "LEFT JOIN users u ON u.id = p.user_id "
            "WHERE p.season = ? "
            "ORDER BY p.group_number, p.nickname",
            (season,),
        )
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()


def cl_list_orphan_participants() -> list[dict]:
    """
    O'chirilgan akkountlar: cl_participants YOKI cl_matches'da ishlatilgan user_id
    users jadvalida yo'q bo'lsa. Har biri uchun participant ma'lumoti (bo'lsa) yoki
    faqat user_id qaytadi.
    [{participant_id|null, season, user_id, nickname, club_name, group_number}, ...]
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # 1) cl_participants'dagi orphan'lar
        cursor.execute(
            "SELECT p.id AS participant_id, p.season, p.user_id, p.nickname, "
            "p.club_name, p.group_number "
            "FROM cl_participants p "
            "LEFT JOIN users u ON u.id = p.user_id "
            "WHERE u.id IS NULL"
        )
        found = {r["user_id"]: dict(r) for r in cursor.fetchall()}

        # 2) cl_matches'da ishlatilgan, lekin users'da yo'q player_id'lar
        cursor.execute(
            "SELECT DISTINCT pid AS user_id, m.season, m.group_number FROM ("
            "  SELECT player1_id AS pid, season, group_number FROM cl_matches "
            "  UNION SELECT player2_id AS pid, season, group_number FROM cl_matches"
            ") AS m "
            "LEFT JOIN users u ON u.id = m.pid "
            "WHERE u.id IS NULL"
        )
        for r in cursor.fetchall():
            uid = r["user_id"]
            if uid is None or uid in found:
                continue
            # Shu user_id uchun participant qatorini topishga urinamiz (nickname uchun)
            cursor.execute(
                "SELECT id, nickname, club_name, group_number FROM cl_participants "
                "WHERE user_id = ? LIMIT 1", (uid,))
            p = cursor.fetchone()
            found[uid] = {
                "participant_id": p["id"] if p else None,
                "season": r["season"],
                "user_id": uid,
                "nickname": (p["nickname"] if p else None) or f"(id {uid})",
                "club_name": p["club_name"] if p else None,
                "group_number": (p["group_number"] if p else None) or r["group_number"],
            }

        return sorted(found.values(),
                      key=lambda x: (x["group_number"] or 99, x["user_id"]))
    finally:
        conn.close()


def cl_reassign_participant(old_user_id: int, new_telegram_id: int
                            ) -> tuple[bool, str | dict]:
    """
    O'chirilgan akkount (old_user_id) o'rniga yangi akkountni bog'laydi.
    old_user_id — orphan ro'yxatidagi eski user_id (participant bo'lmasa ham ishlaydi,
    chunki cl_matches'da player_id bo'lishi mumkin). Eski Telegram ID kerak emas.

    Sabablar: new_user_not_found, nothing_to_reassign, new_already_participant
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

        # Eski user_id qaysi mavsum(lar)da uchraydi? (participants yoki matches)
        cursor.execute(
            "SELECT DISTINCT season FROM cl_participants WHERE user_id = ? "
            "UNION SELECT DISTINCT season FROM cl_matches "
            "WHERE player1_id = ? OR player2_id = ?",
            (old_user_id, old_user_id, old_user_id),
        )
        seasons = [r["season"] for r in cursor.fetchall()]
        if not seasons:
            cursor.execute("ROLLBACK")
            return False, "nothing_to_reassign"

        # Yangi akkount shu mavsumlarda allaqachon ishtirokchi bo'lmasin
        ph = ",".join("?" * len(seasons))
        cursor.execute(
            f"SELECT COUNT(*) AS c FROM cl_participants "
            f"WHERE user_id = ? AND season IN ({ph})",
            (new_user_id, *seasons),
        )
        if cursor.fetchone()["c"] > 0:
            cursor.execute("ROLLBACK")
            return False, "new_already_participant"

        # 1) cl_participants (bo'lsa)
        cursor.execute(
            "UPDATE cl_participants SET user_id = ?, telegram_id = ?, nickname = ? "
            "WHERE user_id = ?",
            (new_user_id, new_telegram_id, new_user["nickname"], old_user_id),
        )
        parts = cursor.rowcount or 0

        # 2) cl_matches player_id / submitted_by
        cursor.execute("UPDATE cl_matches SET player1_id = ? WHERE player1_id = ?",
                       (new_user_id, old_user_id))
        m1 = cursor.rowcount or 0
        cursor.execute("UPDATE cl_matches SET player2_id = ? WHERE player2_id = ?",
                       (new_user_id, old_user_id))
        m2 = cursor.rowcount or 0
        cursor.execute("UPDATE cl_matches SET submitted_by = ? WHERE submitted_by = ?",
                       (new_user_id, old_user_id))

        cursor.execute("COMMIT")
        logger.info("ChL akkount ko'chirildi: user %s -> %s (tg %s), %s participant, %s o'yin",
                    old_user_id, new_user_id, new_telegram_id, parts, m1 + m2)
        return True, {"participants_updated": parts, "matches_updated": m1 + m2,
                      "new_user_id": new_user_id}
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        conn.close()
