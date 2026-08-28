"""
prize_award.py — bosh admin QO'LDA kubok berish (2026-08).

Muammo (qoida #52): ChL 2-mavsum finali o'ynalgan, lekin admin "ChL mavsumini
yakunlash" ni bosmasdan yangi mavsum boshlanib ketgan. Natijada g'olibning
season_prizes'da cl_cup yozuvi yo'q — profil sahifasida kubok ham, useri
oldida ★ yulduzcha ham ko'rinmaydi. finalize_cl_season() endi yordam bermaydi,
chunki eski setka (cl_po_bracket) tozalangan — chempionni hisoblab bo'lmaydi.

Yechim: bosh admin Telegram ID kiritib, ChL 2-mavsum kubogini qo'lda beradi.

YULDUZCHA (★): qo'shimcha kod KERAK EMAS — prize_stars.CUP_PRIZE_TYPES da
'cl_cup' bor va get_cup_star_counts() season_prizes.telegram_id bo'yicha
hisoblaydi. Biz yozuvga user_id VA telegram_id ikkovini yozamiz (qoida #11:
o'qiydigan/yozadigan joylar mos).

MUHIM: season_state.cl_season BU YERDA O'ZGARTIRILMAYDI (admin qarori) —
faqat season_prizes'ga bitta qator qo'shiladi.

Bu modul faqat SOF mantiq (DB o'qish/yozish) — API handler (api.py) uni
chaqiradi (qoida #27: biznes-mantiq handlerda emas, alohida).
"""

import logging

from models import get_connection

logger = logging.getLogger(__name__)

# ChL 2-mavsum kubogi — QAT'IY qiymat, admin tanlay olmaydi (qoida #17:
# magic number emas, nomlangan konstanta).
CL_CUP_SEASON = 2
CL_CUP_SEASON_KIND = "cl"
CL_CUP_PRIZE_TYPE = "cl_cup"


def award_cl_cup_season2(telegram_id: int) -> tuple[bool, str, dict]:
    """
    ChL 2-mavsum kubogini Telegram ID egasiga beradi.

    Xavfsizlik va idempotentlik:
      - BEGIN IMMEDIATE (parallel so'rovlar to'qnashmasin)
      - telegram_id users'da bormi tekshiriladi (yo'q bo'lsa yozilmaydi —
        aks holda kubok "egasiz" qolib, profilda ko'rinmaydi)
      - 2-mavsumda cl_cup ALLAQACHON bo'lsa — yozilmaydi (qoida #38:
        tugma ikki marta bosilsa ikkita kubok/ikkita ★ chiqmasin)

    Qaytaradi: (ok, reason, info)
      reason: ok | invalid_telegram_id | user_not_found |
              season_already_has_cup | award_failed
      info (ok bo'lsa): {prize_id, prize_type, season_number, season_kind,
                         user_id, telegram_id, nickname, username}
      info (season_already_has_cup bo'lsa): {telegram_id, nickname, username}
        — kubok hozir kimda ekani (admin ko'rsin)
    """
    try:
        tg = int(telegram_id)
    except (TypeError, ValueError):
        return False, "invalid_telegram_id", {}

    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")

        cursor.execute(
            "SELECT id, telegram_id, nickname, username FROM users WHERE telegram_id = ?",
            (tg,),
        )
        owner = cursor.fetchone()
        if owner is None:
            cursor.execute("ROLLBACK")
            return False, "user_not_found", {}

        # Shu mavsumda kubok bormi? (idempotentlik — takror bosishga himoya)
        cursor.execute(
            """
            SELECT sp.telegram_id, u.nickname, u.username
            FROM season_prizes sp
            LEFT JOIN users u ON u.telegram_id = sp.telegram_id
            WHERE sp.prize_type = ? AND sp.season_kind = ? AND sp.season_number = ?
            LIMIT 1
            """,
            (CL_CUP_PRIZE_TYPE, CL_CUP_SEASON_KIND, CL_CUP_SEASON),
        )
        existing = cursor.fetchone()
        if existing is not None:
            cursor.execute("ROLLBACK")
            return False, "season_already_has_cup", {
                "telegram_id": existing["telegram_id"],
                "nickname": existing["nickname"],
                "username": existing["username"],
            }

        cursor.execute(
            "INSERT INTO season_prizes "
            "(user_id, telegram_id, prize_type, league_id, season_number, season_kind) "
            "VALUES (?, ?, ?, NULL, ?, ?)",
            (owner["id"], owner["telegram_id"], CL_CUP_PRIZE_TYPE,
             CL_CUP_SEASON, CL_CUP_SEASON_KIND),
        )
        prize_id = cursor.lastrowid
        cursor.execute("COMMIT")

        logger.info(
            "ChL %s-mavsum kubogi qo'lda berildi: prize_id=%s user_id=%s tg=%s (@%s)",
            CL_CUP_SEASON, prize_id, owner["id"], owner["telegram_id"], owner["username"],
        )
        return True, "ok", {
            "prize_id": prize_id,
            "prize_type": CL_CUP_PRIZE_TYPE,
            "season_number": CL_CUP_SEASON,
            "season_kind": CL_CUP_SEASON_KIND,
            "user_id": owner["id"],
            "telegram_id": owner["telegram_id"],
            "nickname": owner["nickname"],
            "username": owner["username"],
        }
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            logger.exception("award_cl_cup_season2: ROLLBACK xatosi")
        logger.exception("award_cl_cup_season2 xatosi (telegram_id=%s)", tg)
        return False, "award_failed", {}
    finally:
        conn.close()
