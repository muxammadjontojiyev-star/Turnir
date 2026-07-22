"""
wc_playoff_swap.py — World Cup play-off setkasidagi ikki pozitsiyani (ishtirokchini)
o'zaro almashtirish (faqat bosh admin). Ligadagi swap naqshiga o'xshash, lekin bu
GURUH emas, PLAY-OFF SETKA pozitsiyalarini almashtiradi.

2026-07-22: bosh admin setkada istalgan ikki bo'sh bo'lmagan pozitsiyani (1/16,
1/8, ... aralash) o'zaro almashtira oladi.

Pozitsiya = (match_id, slot). slot: 1 → player1_id, 2 → player2_id.

XAVFSIZLIK / SHARTLAR (qoida #38, #41):
  - Ikkala slot ham bo'sh bo'lmasligi (ishtirokchi mavjud).
  - Ikkala o'yin ham natija kiritilmagan (pending, hisobsiz) bo'lishi — natija
    bor bo'lsa admin AVVAL bekor qiladi (aks holda agregat/g'olib chalkashadi).
  - Bir xil pozitsiyani o'ziga almashtirib bo'lmaydi.
  - Faqat wc_playoff_matches jadvali — guruh o'yinlari (wc_matches) TEGILMAYDI.

Natijalar o'sha joyda qoladi (hisobsiz), faqat ishtirokchi (user_id) almashadi.
G'olib hali chiqmagani uchun (pending) keyingi bosqichga ta'sir yo'q.
"""

import logging

from models import get_connection
from config import MATCH_STATUS_PENDING

logger = logging.getLogger(__name__)

_SLOT_COL = {1: "player1_id", 2: "player2_id"}


def _load_slot(cursor, match_id: int, slot: int) -> tuple[dict | None, str]:
    """
    Bitta pozitsiyani (o'yin + slot) o'qiydi va tekshiradi.
    Qaytaradi: (info, reason). info = {match_id, slot, col, user_id, status}.
    reason: ok / slot_invalid / match_not_found / slot_empty / has_result.
    """
    if slot not in _SLOT_COL:
        return None, "slot_invalid"
    col = _SLOT_COL[slot]
    cursor.execute(
        "SELECT id, round, position, player1_id, player2_id, "
        "score1, score2, status FROM wc_playoff_matches WHERE id = ?",
        (match_id,),
    )
    row = cursor.fetchone()
    if not row:
        return None, "match_not_found"
    m = dict(row)
    user_id = m[col]
    if not user_id:
        return None, "slot_empty"
    # Natija kiritilmagan bo'lishi shart (pending + hisobsiz)
    has_score = m["score1"] is not None or m["score2"] is not None
    if m["status"] != MATCH_STATUS_PENDING or has_score:
        return None, "has_result"
    return {"match_id": match_id, "slot": slot, "col": col,
            "user_id": user_id, "round": m["round"], "position": m["position"]}, "ok"


def wc_playoff_swap_positions(match_a_id: int, slot_a: int,
                              match_b_id: int, slot_b: int
                              ) -> tuple[bool, str | dict]:
    """
    Play-off setkada ikki pozitsiyadagi ishtirokchini O'ZARO almashtiradi.

    Sabablar: same_position / slot_invalid / match_not_found / slot_empty /
              has_result. Muvaffaqiyatда: {"a_user_id", "b_user_id"}.
    """
    if match_a_id == match_b_id and slot_a == slot_b:
        return False, "same_position"

    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")

        info_a, reason_a = _load_slot(cursor, match_a_id, slot_a)
        if not info_a:
            cursor.execute("ROLLBACK")
            return False, reason_a
        info_b, reason_b = _load_slot(cursor, match_b_id, slot_b)
        if not info_b:
            cursor.execute("ROLLBACK")
            return False, reason_b

        # Bir xil ishtirokchini o'ziga almashtirish — hech narsa o'zgarmaydi
        if info_a["user_id"] == info_b["user_id"]:
            cursor.execute("ROLLBACK")
            return False, "same_position"

        # A slotiga B ishtirokchisini, B slotiga A ishtirokchisini yozamiz.
        # Bir o'yinda ikkala slot ham qatnashsa ham xavfsiz (alohida UPDATE).
        cursor.execute(
            f"UPDATE wc_playoff_matches SET {info_a['col']} = ? WHERE id = ?",  # nosec — ustun nomi kod ichida qat'iy
            (info_b["user_id"], match_a_id),
        )
        cursor.execute(
            f"UPDATE wc_playoff_matches SET {info_b['col']} = ? WHERE id = ?",  # nosec — ustun nomi kod ichida qat'iy
            (info_a["user_id"], match_b_id),
        )

        cursor.execute("COMMIT")
        logger.info("WC play-off SWAP: (m%s s%s user%s) <-> (m%s s%s user%s)",
                    match_a_id, slot_a, info_a["user_id"],
                    match_b_id, slot_b, info_b["user_id"])
        return True, {"a_user_id": info_b["user_id"], "b_user_id": info_a["user_id"]}
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        conn.close()
