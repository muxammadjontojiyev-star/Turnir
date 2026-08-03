"""
prize_admin.py — bosh admin uchun sovrin boshqaruvi (2026-08).

Muammo: mavsum yakunlangach sovrin (masalan Oltin to'p) noto'g'ri egaga
berilib qolishi mumkin (tenglik xatosi tuzatildi, lekin allaqachon yozilganlar
qoladi). Bosh admin panelidan sovrinni to'g'ri egaga KO'CHIRISH kerak.

Bu modul faqat SOF mantiq (DB o'qish/yozish) — API handler (api.py) uni chaqiradi
(qoida #27: biznes-mantiq handlerda emas, alohida). Faqat golden_ball/golden_boot
(liga individual sovrinlari) ko'chiriladi — bular tenglik xatosiga uchraydi.
Kubok/ChL sovrinlari bu funksiyada QAMRALMAGAN (kerak bo'lsa keyin qo'shiladi).
"""

import logging

from models import get_connection

logger = logging.getLogger(__name__)

# Ko'chirishga RUXSAT etilgan sovrin turlari (faqat liga individual sovrinlari)
TRANSFERABLE_PRIZE_TYPES = ("golden_ball", "golden_boot")


def list_transferable_prizes() -> list[dict]:
    """
    Ko'chirish mumkin bo'lgan sovrinlar ro'yxati (golden_ball/golden_boot),
    hozirgi egasi bilan. Eng yangi mavsum birinchi.

    Qaytaradi: [{
      prize_id, prize_type, season_number, season_kind,
      user_id, telegram_id, nickname, username
    }, ...]
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        placeholders = ",".join("?" * len(TRANSFERABLE_PRIZE_TYPES))
        cursor.execute(
            f"""
            SELECT sp.id AS prize_id, sp.prize_type, sp.season_number,
                   sp.season_kind, sp.user_id, sp.telegram_id,
                   u.nickname, u.username
            FROM season_prizes sp
            LEFT JOIN users u
              ON u.telegram_id = sp.telegram_id
              OR (sp.telegram_id IS NULL AND u.id = sp.user_id)
            WHERE sp.prize_type IN ({placeholders})
            ORDER BY sp.season_number DESC, sp.prize_type ASC
            """,
            TRANSFERABLE_PRIZE_TYPES,
        )
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()


def transfer_prize(prize_id: int, new_owner_user_id: int) -> tuple[bool, str, dict]:
    """
    Sovrinni (prize_id) yangi egaga (new_owner_user_id) ko'chiradi.
    Sovrin telegram_id ga bog'langani uchun HAM user_id, HAM telegram_id
    yangilanadi (qoida #11 — o'qiydigan joylar telegram_id bo'yicha ishlaydi).

    Xavfsizlik (qoida #38 idempotent, #34 to'g'ri odam):
      - prize_id mavjud va TRANSFERABLE turdami tekshiriladi
      - new_owner_user_id users'da bormi tekshiriladi
      - yangi ega allaqachon shu sovrin egasi bo'lsa — no-op (already_owner)

    Qaytaradi: (ok, reason, info)
      reason: ok | prize_not_found | not_transferable | user_not_found | already_owner
      info (ok bo'lsa): {prize_id, prize_type, season_number,
                         old_user_id, new_user_id, new_telegram_id,
                         new_nickname, new_username}
    """
    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")

        cursor.execute(
            "SELECT id, prize_type, season_number, user_id, telegram_id "
            "FROM season_prizes WHERE id = ?",
            (prize_id,),
        )
        prize = cursor.fetchone()
        if prize is None:
            cursor.execute("ROLLBACK")
            return False, "prize_not_found", {}
        if prize["prize_type"] not in TRANSFERABLE_PRIZE_TYPES:
            cursor.execute("ROLLBACK")
            return False, "not_transferable", {}

        cursor.execute(
            "SELECT id, telegram_id, nickname, username FROM users WHERE id = ?",
            (new_owner_user_id,),
        )
        owner = cursor.fetchone()
        if owner is None:
            cursor.execute("ROLLBACK")
            return False, "user_not_found", {}

        # Allaqachon shu odamniki bo'lsa — o'zgartirishga hojat yo'q
        if prize["telegram_id"] == owner["telegram_id"] and prize["telegram_id"] is not None:
            cursor.execute("ROLLBACK")
            return False, "already_owner", {}

        cursor.execute(
            "UPDATE season_prizes SET user_id = ?, telegram_id = ? WHERE id = ?",
            (owner["id"], owner["telegram_id"], prize_id),
        )
        cursor.execute("COMMIT")
        logger.info(
            "Sovrin ko'chirildi: prize_id=%s (%s, %s-mavsum) user_id %s -> %s (@%s)",
            prize_id, prize["prize_type"], prize["season_number"],
            prize["user_id"], owner["id"], owner["username"],
        )
        return True, "ok", {
            "prize_id": prize_id,
            "prize_type": prize["prize_type"],
            "season_number": prize["season_number"],
            "old_user_id": prize["user_id"],
            "new_user_id": owner["id"],
            "new_telegram_id": owner["telegram_id"],
            "new_nickname": owner["nickname"],
            "new_username": owner["username"],
        }
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            pass
        logger.exception("transfer_prize xatosi (prize_id=%s)", prize_id)
        return False, "transfer_failed", {}
    finally:
        conn.close()
