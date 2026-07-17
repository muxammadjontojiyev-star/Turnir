"""
participant_admin.py — Ishtirokchini yangi akkountga almashtirish (2026-07-16).

ChL'dagi cl_participant_admin.py naqshi BARCHA rejimlarga kengaytirildi:
Liga, World Cup va Divizion. FAQAT BOSH ADMIN ishlatadi (api.py'da
get_authenticated_super_admin bilan himoyalangan).

MUHIM: qur'a natijasiga ta'sir qilmaydi — o'yin jadvali (juftliklar,
turlar, hisoblar) o'z joyida qoladi, faqat player_id ko'rsatkichlari
eski user_id'dan yangi akkount user_id'siga ko'chiriladi. Qur'a qilib
bo'lingan taqdirda ham almashtirishdan keyin kalendar o'zgarmaydi.

Har rejim uchun:
  *_list_participants() — admin dropdown'i uchun ro'yxat (orphan bayrog'i bilan)
  *_reassign_participant(old_user_id, new_telegram_id) — almashtirish

Sabablar: new_user_not_found, nothing_to_reassign, new_already_participant.
"""

import logging

from models import get_connection

logger = logging.getLogger(__name__)


# ============================================================
#  UMUMIY YADRO (DRY, qoida #26)
# ============================================================

def _get_new_user(cursor, new_telegram_id: int):
    """Yangi akkount users'da bormi (avval botga /start bosgan bo'lishi kerak)."""
    cursor.execute(
        "SELECT id, telegram_id, nickname FROM users WHERE telegram_id = ?",
        (new_telegram_id,),
    )
    return cursor.fetchone()


def _swap_user_columns(cursor, table: str, columns: list[str],
                       old_user_id: int, new_user_id: int) -> int:
    """
    Jadvalning berilgan ustunlarida old_user_id -> new_user_id.
    Qaytaradi: yangilangan qatorlar soni (jami).
    """
    total = 0
    for col in columns:
        cursor.execute(
            f"UPDATE {table} SET {col} = ? WHERE {col} = ?",  # nosec — ustun/jadval nomlari kod ichida qat'iy
            (new_user_id, old_user_id),
        )
        total += cursor.rowcount or 0
    return total


# ============================================================
#  LIGA
# ============================================================

def league_list_participants() -> list[dict]:
    """
    Barcha liga ishtirokchilari (admin dropdown uchun).
    orphan=1 — user_id users'da yo'q (o'chirilgan akkount).
    [{user_id, nickname, username, club_name, league_name, orphan}, ...]
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT r.user_id, u.nickname, u.username, r.club_name, l.name AS league_name, "
            "CASE WHEN u.id IS NULL THEN 1 ELSE 0 END AS orphan "
            "FROM registrations r "
            "LEFT JOIN users u ON u.id = r.user_id "
            "LEFT JOIN leagues l ON l.id = r.league_id "
            "ORDER BY l.name, u.nickname"
        )
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()


def league_reassign_participant(old_user_id: int, new_telegram_id: int
                                ) -> tuple[bool, str | dict]:
    """
    Liga ishtirokchisini (old_user_id) yangi akkountga bog'laydi:
    registrations.user_id, matches.player1/2_id + submitted_by,
    messages.sender_id yangilanadi. Qur'a (jadval) o'zgarmaydi.
    """
    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")

        new_user = _get_new_user(cursor, new_telegram_id)
        if not new_user:
            cursor.execute("ROLLBACK")
            return False, "new_user_not_found"
        new_user_id = new_user["id"]

        # Eski id biror joyda bormi?
        cursor.execute(
            "SELECT (SELECT COUNT(*) FROM registrations WHERE user_id = ?) + "
            "(SELECT COUNT(*) FROM matches WHERE player1_id = ? OR player2_id = ?) AS c",
            (old_user_id, old_user_id, old_user_id),
        )
        if cursor.fetchone()["c"] == 0:
            cursor.execute("ROLLBACK")
            return False, "nothing_to_reassign"

        # Yangi akkount allaqachon biror ligada ro'yxatdan o'tgan bo'lmasin
        # (registrations.user_id UNIQUE — aks holda UPDATE UNIQUE'ga uriladi)
        cursor.execute(
            "SELECT COUNT(*) AS c FROM registrations WHERE user_id = ?",
            (new_user_id,),
        )
        if cursor.fetchone()["c"] > 0:
            cursor.execute("ROLLBACK")
            return False, "new_already_participant"

        regs = _swap_user_columns(cursor, "registrations", ["user_id"],
                                  old_user_id, new_user_id)
        matches = _swap_user_columns(
            cursor, "matches", ["player1_id", "player2_id", "submitted_by"],
            old_user_id, new_user_id)
        _swap_user_columns(cursor, "messages", ["sender_id"],
                           old_user_id, new_user_id)

        cursor.execute("COMMIT")
        logger.info("Liga akkount almashtirildi: user %s -> %s (tg %s), %s reg, %s o'yin",
                    old_user_id, new_user_id, new_telegram_id, regs, matches)
        return True, {"registrations_updated": regs, "matches_updated": matches,
                      "new_user_id": new_user_id}
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        conn.close()


# ============================================================
#  LIGALARARO O'ZARO ALMASHTIRISH (SWAP) — 2026-07-16
# ============================================================

def league_swap_participants(user_id_a: int, user_id_b: int
                             ) -> tuple[bool, str | dict]:
    """
    Ikki liga ishtirokchisini O'ZARO almashtiradi (masalan, LaLiga <-> Bundesliga).
    O'RIN (liga, klub, jadval, kiritilgan natijalar) joyida qoladi — faqat
    o'rin ortidagi ODAM almashadi: A endi B'ning ligasida B'ning klubi bilan
    o'ynaydi va aksincha. QUR'AGA TA'SIR QILMAYDI.

    Texnik: registrations.user_id UNIQUE + FK ON bo'lgani uchun almashtirish
    sentinel (-1) orqali, FK shu ulanishda vaqtincha OFF (season_reset naqshi;
    yakuniy holat baribir to'g'ri id'lar). matches/messages'da UNIQUE yo'q —
    bitta CASE UPDATE bilan almashtiriladi.

    Sabablar: same_user, participant_not_found.
    """
    if user_id_a == user_id_b:
        return False, "same_user"

    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        # PRAGMA tranzaksiya ichida o'zgarmaydi — BEGIN'dan OLDIN o'chiriladi
        cursor.execute("PRAGMA foreign_keys = OFF")
        cursor.execute("BEGIN IMMEDIATE")

        # Ikkala ishtirokchi ham ro'yxatda bo'lishi shart
        cursor.execute(
            "SELECT user_id FROM registrations WHERE user_id IN (?, ?)",
            (user_id_a, user_id_b),
        )
        found = {r["user_id"] for r in cursor.fetchall()}
        if user_id_a not in found or user_id_b not in found:
            cursor.execute("ROLLBACK")
            return False, "participant_not_found"

        # 1) registrations: sentinel orqali user_id almashtiriladi
        #    (league_id + club_name o'z qatorida qoladi — o'rin saqlanadi)
        cursor.execute("UPDATE registrations SET user_id = -1 WHERE user_id = ?",
                       (user_id_a,))
        cursor.execute("UPDATE registrations SET user_id = ? WHERE user_id = ?",
                       (user_id_a, user_id_b))
        cursor.execute("UPDATE registrations SET user_id = ? WHERE user_id = -1",
                       (user_id_b,))

        # 2) matches: har ikkala liganing jadvalida id'lar o'zaro almashadi
        #    (matchday, hisoblar, status — TEGILMAYDI)
        swapped = 0
        for col in ("player1_id", "player2_id", "submitted_by"):
            cursor.execute(
                f"UPDATE matches SET {col} = CASE {col} WHEN ? THEN ? WHEN ? THEN ? END "  # nosec — ustun nomi kod ichida qat'iy
                f"WHERE {col} IN (?, ?)",
                (user_id_a, user_id_b, user_id_b, user_id_a, user_id_a, user_id_b),
            )
            swapped += cursor.rowcount or 0

        # 3) liga chat xabarlari — o'rin tarixi o'rin bilan qoladi
        cursor.execute(
            "UPDATE messages SET sender_id = CASE sender_id WHEN ? THEN ? WHEN ? THEN ? END "
            "WHERE sender_id IN (?, ?)",
            (user_id_a, user_id_b, user_id_b, user_id_a, user_id_a, user_id_b),
        )

        cursor.execute("COMMIT")
        logger.info("Liga SWAP: user %s <-> %s, %s o'yin ustuni yangilandi",
                    user_id_a, user_id_b, swapped)
        return True, {"matches_updated": swapped}
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        try:
            cursor.execute("PRAGMA foreign_keys = ON")
        except Exception:
            pass
        conn.close()


# ============================================================
#  WORLD CUP (guruh + play-off)
# ============================================================

def wc_list_participants() -> list[dict]:
    """
    Barcha WC ishtirokchilari (admin dropdown uchun), orphan bayrog'i bilan.
    [{user_id, nickname, username, team_name, group_letter, orphan}, ...]
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT w.user_id, u.nickname, u.username, w.team_name, w.group_letter, "
            "CASE WHEN u.id IS NULL THEN 1 ELSE 0 END AS orphan "
            "FROM wc_registrations w "
            "LEFT JOIN users u ON u.id = w.user_id "
            "ORDER BY w.group_letter, w.team_name"
        )
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()


def wc_reassign_participant(old_user_id: int, new_telegram_id: int
                            ) -> tuple[bool, str | dict]:
    """
    WC ishtirokchisini yangi akkountga bog'laydi: wc_registrations.user_id,
    wc_matches va wc_playoff_matches player/submitted_by, wc_messages.sender_id.
    Qur'a (guruhlar, jadval, setka) o'zgarmaydi.
    """
    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")

        new_user = _get_new_user(cursor, new_telegram_id)
        if not new_user:
            cursor.execute("ROLLBACK")
            return False, "new_user_not_found"
        new_user_id = new_user["id"]

        cursor.execute(
            "SELECT (SELECT COUNT(*) FROM wc_registrations WHERE user_id = ?) + "
            "(SELECT COUNT(*) FROM wc_matches WHERE player1_id = ? OR player2_id = ?) + "
            "(SELECT COUNT(*) FROM wc_playoff_matches WHERE player1_id = ? OR player2_id = ?) AS c",
            (old_user_id, old_user_id, old_user_id, old_user_id, old_user_id),
        )
        if cursor.fetchone()["c"] == 0:
            cursor.execute("ROLLBACK")
            return False, "nothing_to_reassign"

        # wc_registrations.user_id UNIQUE — yangi akkount allaqachon WC'da bo'lmasin
        cursor.execute(
            "SELECT COUNT(*) AS c FROM wc_registrations WHERE user_id = ?",
            (new_user_id,),
        )
        if cursor.fetchone()["c"] > 0:
            cursor.execute("ROLLBACK")
            return False, "new_already_participant"

        regs = _swap_user_columns(cursor, "wc_registrations", ["user_id"],
                                  old_user_id, new_user_id)
        matches = _swap_user_columns(
            cursor, "wc_matches", ["player1_id", "player2_id", "submitted_by"],
            old_user_id, new_user_id)
        matches += _swap_user_columns(
            cursor, "wc_playoff_matches", ["player1_id", "player2_id", "submitted_by"],
            old_user_id, new_user_id)
        _swap_user_columns(cursor, "wc_messages", ["sender_id"],
                           old_user_id, new_user_id)

        cursor.execute("COMMIT")
        logger.info("WC akkount almashtirildi: user %s -> %s (tg %s), %s reg, %s o'yin",
                    old_user_id, new_user_id, new_telegram_id, regs, matches)
        return True, {"registrations_updated": regs, "matches_updated": matches,
                      "new_user_id": new_user_id}
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        conn.close()


# ============================================================
#  DIVIZION (kunlik)
# ============================================================

def div_list_participants() -> list[dict]:
    """
    Divizionda qatnashgan barcha ishtirokchilar (so'nggi ro'yxat kuni bilan),
    orphan bayrog'i bilan. Admin istalganini almashtiradi — almashtirish
    BARCHA kunlardagi yozuvlarga qo'llanadi.
    [{user_id, telegram_id, nickname, username, last_day, orphan}, ...]
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT r.user_id, r.telegram_id, "
            "COALESCE(u.nickname, r.nickname) AS nickname, u.username, "
            "MAX(r.day) AS last_day, "
            "CASE WHEN u.id IS NULL THEN 1 ELSE 0 END AS orphan "
            "FROM div_registrations r "
            "LEFT JOIN users u ON u.id = r.user_id "
            "GROUP BY r.user_id "
            "ORDER BY last_day DESC, nickname"
        )
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()


def div_reassign_participant(old_user_id: int, new_telegram_id: int
                             ) -> tuple[bool, str | dict]:
    """
    Divizion ishtirokchisini yangi akkountga bog'laydi:
    div_registrations (user_id + telegram_id + nickname), div_matches
    player/submitted_by, div_messages.sender_id. Juftlash (qur'a) o'zgarmaydi.
    """
    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")

        new_user = _get_new_user(cursor, new_telegram_id)
        if not new_user:
            cursor.execute("ROLLBACK")
            return False, "new_user_not_found"
        new_user_id = new_user["id"]

        cursor.execute(
            "SELECT (SELECT COUNT(*) FROM div_registrations WHERE user_id = ?) + "
            "(SELECT COUNT(*) FROM div_matches WHERE player1_id = ? OR player2_id = ?) AS c",
            (old_user_id, old_user_id, old_user_id),
        )
        if cursor.fetchone()["c"] == 0:
            cursor.execute("ROLLBACK")
            return False, "nothing_to_reassign"

        # Yangi akkount eski ishtirokchi bilan BIR XIL KUNda ro'yxatdan o'tgan
        # bo'lmasin (UNIQUE(day, telegram_id) buziladi va reyting ikkilanadi)
        cursor.execute(
            "SELECT COUNT(*) AS c FROM div_registrations r_old "
            "JOIN div_registrations r_new ON r_new.day = r_old.day "
            "AND (r_new.user_id = ? OR r_new.telegram_id = ?) "
            "WHERE r_old.user_id = ?",
            (new_user_id, new_telegram_id, old_user_id),
        )
        if cursor.fetchone()["c"] > 0:
            cursor.execute("ROLLBACK")
            return False, "new_already_participant"

        cursor.execute(
            "UPDATE div_registrations SET user_id = ?, telegram_id = ?, nickname = ? "
            "WHERE user_id = ?",
            (new_user_id, new_telegram_id, new_user["nickname"], old_user_id),
        )
        regs = cursor.rowcount or 0
        matches = _swap_user_columns(
            cursor, "div_matches", ["player1_id", "player2_id", "submitted_by"],
            old_user_id, new_user_id)
        _swap_user_columns(cursor, "div_messages", ["sender_id"],
                           old_user_id, new_user_id)

        cursor.execute("COMMIT")
        logger.info("Divizion akkount almashtirildi: user %s -> %s (tg %s), %s reg, %s o'yin",
                    old_user_id, new_user_id, new_telegram_id, regs, matches)
        return True, {"registrations_updated": regs, "matches_updated": matches,
                      "new_user_id": new_user_id}
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        conn.close()
