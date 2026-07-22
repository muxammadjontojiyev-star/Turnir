"""
queries_wc_playoff_results.py — WC play-off: natija kiritish/tasdiqlash, foydalanuvchi o'yinlari, chempion.

queries.py'dan ajratildi (2026-07-03, audit C1 — fayl hajmi qoidasi #21).
Barcha funksiyalar VERBATIM ko'chirilgan, mantiq o'zgartirilmagan.
"""

from models import get_connection
from queries_wc_playoff import (
    WC_PLAYOFF_ROUND_ORDER,  # 2026-07-03 hotfix: round tartibi core modulda qolgan edi
    wc_playoff_advance_winner, wc_playoff_get_match_by_id,
    wc_playoff_get_open_round_index, wc_playoff_round_is_open,
)


def wc_playoff_get_user_matches(user_id: int) -> list[dict]:
    """
    O'yinchining play-off matchlari (ochiq bosqichlargacha). Har bosqichdan
    o'yinchi qatnashayotgan match. is_open: shu bosqich kun bo'yicha ochiqmi.

    Faqat o'yinchi ishtirok etayotgan (player1 yoki player2) va ikkala o'yinchi
    ham aniq (NULL emas) matchlar qaytadi.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT p.*,
               u1.nickname AS p1_nick, u1.username AS p1_user, r1.team_name AS p1_team,
               u2.nickname AS p2_nick, u2.username AS p2_user, r2.team_name AS p2_team
        FROM wc_playoff_matches p
        LEFT JOIN users u1 ON u1.id = p.player1_id
        LEFT JOIN users u2 ON u2.id = p.player2_id
        LEFT JOIN wc_registrations r1 ON r1.user_id = p.player1_id
        LEFT JOIN wc_registrations r2 ON r2.user_id = p.player2_id
        WHERE (p.player1_id = ? OR p.player2_id = ?)
        ORDER BY
            CASE p.round
                WHEN 'r32' THEN 0 WHEN 'r16' THEN 1 WHEN 'r8' THEN 2
                WHEN 'r4' THEN 3 WHEN 'final' THEN 4 WHEN 'bronze' THEN 4
            END
        """,
        (user_id, user_id),
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    open_idx = wc_playoff_get_open_round_index()
    result = []
    for m in rows:
        rname = "final" if m["round"] == "bronze" else m["round"]
        try:
            ridx = WC_PLAYOFF_ROUND_ORDER.index(rname)
        except ValueError:
            ridx = 99
        m["is_open"] = (open_idx >= 0 and ridx <= open_idx)
        result.append(m)
    return result


# ---- WC PLAY-OFF: natija kiritish/tasdiqlash ----

def wc_playoff_submit_result(match_id: int, score1: int, score2: int, submitted_by: int) -> tuple[bool, str]:
    """
    Play-off match natijasini kiritadi (awaiting_confirmation holatiga o'tkazadi).
    Durang QABUL QILINMAYDI — g'olib aniq bo'lishi shart (eFootballda penalti/
    extra-time bilan o'ynaladi).

    Sabablar: ok / match_not_found / not_open / not_participant / both_filled_needed /
              draw_not_allowed / already_done / score_negative
    """
    if score1 < 0 or score2 < 0:
        return False, "score_negative"
    if score1 == score2:
        return False, "draw_not_allowed"

    match = wc_playoff_get_match_by_id(match_id)
    if match is None:
        return False, "match_not_found"
    if match["player1_id"] is None or match["player2_id"] is None:
        return False, "both_filled_needed"
    if submitted_by not in (match["player1_id"], match["player2_id"]):
        return False, "not_participant"
    if match["status"] == "confirmed":
        return False, "already_done"
    if not wc_playoff_round_is_open(match["round"]):
        return False, "not_open"

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE wc_playoff_matches SET score1 = ?, score2 = ?, submitted_by = ?, status = 'awaiting_confirmation' WHERE id = ?",
        (score1, score2, submitted_by, match_id),
    )
    conn.commit()
    conn.close()
    return True, "ok"


def wc_playoff_confirm_result(match_id: int, user_id: int, accept: bool) -> tuple[bool, str]:
    """
    Raqib play-off natijasini tasdiqlaydi (accept=True) yoki rad etadi (False).
    Tasdiqlansa: status=confirmed va g'olib keyingi bosqichga o'tadi.
    Rad etilsa: pending holatiga qaytadi.

    Sabablar: ok / match_not_found / not_awaiting / not_opponent / cannot_confirm_own
    """
    match = wc_playoff_get_match_by_id(match_id)
    if match is None:
        return False, "match_not_found"
    if match["status"] != "awaiting_confirmation":
        return False, "not_awaiting"
    if user_id not in (match["player1_id"], match["player2_id"]):
        return False, "not_opponent"
    if user_id == match["submitted_by"]:
        return False, "cannot_confirm_own"

    conn = get_connection()
    cursor = conn.cursor()
    if accept:
        cursor.execute("UPDATE wc_playoff_matches SET status = 'confirmed' WHERE id = ?", (match_id,))
        conn.commit()
        conn.close()
        # G'olibni keyingi bosqichga joylash
        wc_playoff_advance_winner(match_id)
        return True, "ok"
    else:
        cursor.execute(
            "UPDATE wc_playoff_matches SET score1 = NULL, score2 = NULL, submitted_by = NULL, status = 'pending' WHERE id = ?",
            (match_id,),
        )
        conn.commit()
        conn.close()
        return True, "ok"


def wc_playoff_get_champion() -> dict | None:
    """
    Play-off chempioni (final g'olibi). Final 'confirmed' bo'lmasa None.

    Qaytaradi: {user_id, nickname, username, team_name} yoki None.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT p.player1_id, p.player2_id, p.score1, p.score2, p.status,
               u1.nickname AS n1, u1.username AS us1, r1.team_name AS t1,
               u2.nickname AS n2, u2.username AS us2, r2.team_name AS t2
        FROM wc_playoff_matches p
        LEFT JOIN users u1 ON u1.id = p.player1_id
        LEFT JOIN users u2 ON u2.id = p.player2_id
        LEFT JOIN wc_registrations r1 ON r1.user_id = p.player1_id
        LEFT JOIN wc_registrations r2 ON r2.user_id = p.player2_id
        WHERE p.round = 'final'
        LIMIT 1
        """
    )
    row = cursor.fetchone()
    conn.close()
    if row is None or row["status"] != "confirmed":
        return None
    if row["score1"] is None or row["score2"] is None:
        return None
    if row["score1"] > row["score2"]:
        return {"user_id": row["player1_id"], "nickname": row["n1"], "username": row["us1"], "team_name": row["t1"]}
    elif row["score2"] > row["score1"]:
        return {"user_id": row["player2_id"], "nickname": row["n2"], "username": row["us2"], "team_name": row["t2"]}
    return None


def wc_playoff_auto_confirm_awaiting() -> dict:
    """
    2026-07-22 (talab 2): deadline (23:30) da WC play-off o'yinlarini avtomatik
    yopish. FAQAT awaiting_confirmation (hisob kiritilgan) → confirmed. PENDING
    (hisob kiritilmagan) TEGILMAYDI — play-off'da durang yo'q, admin qo'lda
    tasdiqlaydi. Har yopilgan o'yindan keyin g'olib keyingi bosqichga o'tadi
    (wc_playoff_advance_winner qayta ishlatiladi — DRY; idempotent).

    Scheduler chaqiradi. Idempotent — awaiting qolmagach 0 qaytaradi.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM wc_playoff_matches WHERE status = 'awaiting_confirmation'"
    )
    ids = [r["id"] for r in cursor.fetchall()]
    if not ids:
        conn.close()
        return {"confirmed": 0, "advanced": 0}

    cursor.execute(
        "UPDATE wc_playoff_matches SET status = 'confirmed' "
        "WHERE status = 'awaiting_confirmation'"
    )
    conn.commit()
    conn.close()

    # G'oliblarni keyingi bosqichga (advance idempotent — bir xil slotni qayta yozadi)
    advanced = 0
    for mid in ids:
        try:
            wc_playoff_advance_winner(mid)
            advanced += 1
        except Exception:
            pass  # bitta o'yin xatosi qolganlarini to'xtatmasin (scheduler log qiladi)
    return {"confirmed": len(ids), "advanced": advanced}
