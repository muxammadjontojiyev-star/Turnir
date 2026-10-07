"""
pt_bigscore.py — SHAXSIY turnirda katta hisob tasdig'i (2026-10-07).

Muammo (qoida #52): rasmiy turnirlarda bir tomon MAX_NORMAL_SCORE (standart 5) dan ko'p gol
kiritsa natija 'admin_pending' ga tushadi va admin tasdiqlaydi (soxta katta hisoblar — 20:0 —
reytingni buzmasin). Shaxsiy turnirda bu himoya yo'q edi.

Yechim (rasmiy oqim bilan bir xil chegara — config.MAX_NORMAL_SCORE):
  - o'yinchi katta hisob kiritsa: pending -> admin_pending (raqib tasdig'i kerak emas);
  - QAROR: turnir tashkilotchisi yoki turnir admini — lekin shu o'yinda O'YNAMAYOTGAN bo'lsa
    (o'z o'yinini o'zi tasdiqlamasin); bunday boshqaruvchi bo'lmasa — bosh admin;
  - tasdiq -> confirmed (pley-offda pt_advance); rad -> natija o'chadi (pending) yoki,
    guruh/jadval turi allaqachon yopilgan bo'lsa, tur yopilishidagi kabi 0:0 confirmed.
"""

import logging

from config import ADMIN_TELEGRAM_IDS, MAX_NORMAL_SCORE
from models import get_connection

logger = logging.getLogger(__name__)

STATUS_ADMIN_PENDING = "admin_pending"


def is_big_score(score1: int, score2: int) -> bool:
    return max(score1, score2) > MAX_NORMAL_SCORE


def deciders(cursor, tid: int, p1: int | None, p2: int | None) -> list[dict]:
    """
    Qaror qabul qiluvchilar: shu o'yinda o'ynamayotgan tashkilotchi va turnir adminlari;
    ular bo'lmasa — bosh adminlar. [{telegram_id, language}] (xabar uchun).
    """
    cursor.execute(
        "SELECT u.id, u.telegram_id, u.language FROM pt_tournaments t JOIN users u ON u.id = t.owner_user_id "
        "WHERE t.id = ? UNION SELECT u.id, u.telegram_id, u.language FROM pt_admins a "
        "JOIN users u ON u.id = a.user_id WHERE a.tournament_id = ?", (tid, tid))
    out = [{"telegram_id": r["telegram_id"], "language": r["language"]}
           for r in cursor.fetchall() if r["id"] not in (p1, p2)]
    if out:
        return out
    return [{"telegram_id": tg, "language": None} for tg in ADMIN_TELEGRAM_IDS]


def can_decide(cursor, tid: int, user_id: int, p1: int | None, p2: int | None, is_super: bool) -> bool:
    if is_super:
        return True
    if user_id in (p1, p2):
        return False                                   # o'z o'yinini o'zi tasdiqlamaydi
    from pt_core import is_manager
    return is_manager(cursor, tid, user_id)


def pt_decide_big(match_id: int, user_id: int, accept: bool, is_super: bool = False) -> tuple[bool, str | dict]:
    """
    Katta hisob bo'yicha qaror. Sabablar: match_not_found, not_allowed, wrong_status.
    Qaytaradi (ok): {status: confirmed|rejected|zeroed, advance, tournament_id, players: [{telegram_id, language}]}.
    """
    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute(
            "SELECT m.id, m.tournament_id, m.stage, m.round, m.player1_id, m.player2_id, m.status, "
            "t.current_round, t.total_rounds FROM pt_matches m JOIN pt_tournaments t ON t.id = m.tournament_id "
            "WHERE m.id = ?", (match_id,))
        m = cursor.fetchone()
        why = None
        if not m:
            why = "match_not_found"
        elif not can_decide(cursor, m["tournament_id"], user_id, m["player1_id"], m["player2_id"], is_super):
            why = "not_allowed"
        elif m["status"] != STATUS_ADMIN_PENDING:
            why = "wrong_status"
        if why:
            cursor.execute("ROLLBACK")
            return False, why
        tid = m["tournament_id"]
        advance = {"event": None}
        if accept:
            cursor.execute("UPDATE pt_matches SET status = 'confirmed' WHERE id = ? AND status = ?",
                           (match_id, STATUS_ADMIN_PENDING))
            result = "confirmed"
            if m["stage"] != "group":
                from pt_knockout import pt_advance
                advance = pt_advance(cursor, tid)
        elif m["stage"] == "group" and m["round"] < m["current_round"]:
            # tur allaqachon yopilgan — tur yopilishi qoidasi kabi 0:0 (natija qayta kiritilmaydi)
            cursor.execute("UPDATE pt_matches SET score1 = 0, score2 = 0, status = 'confirmed' WHERE id = ?",
                           (match_id,))
            result = "zeroed"
        else:
            cursor.execute("UPDATE pt_matches SET score1 = NULL, score2 = NULL, submitted_by = NULL, "
                           "status = 'pending' WHERE id = ?", (match_id,))
            result = "rejected"
        cursor.execute("SELECT telegram_id, language FROM users WHERE id IN (?, ?)",
                       (m["player1_id"], m["player2_id"]))
        players = [dict(r) for r in cursor.fetchall()]
        cursor.execute("COMMIT")
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            logger.exception("pt_decide_big: ROLLBACK xatosi")
        raise
    finally:
        conn.close()
    logger.info("PT #%s: katta hisob (o'yin %s) — %s (user %s)", tid, match_id, result, user_id)
    return True, {"status": result, "advance": advance, "tournament_id": tid, "players": players}
