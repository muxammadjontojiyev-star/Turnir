"""
pt_owner_fix.py — tashkilotchi o'z turnirida natijani tuzatadi (2026-10-02, 4b).
Shaxsiy turnir admini — TASHKILOTCHI (bosh admin aralashmaydi). Match ID bo'yicha.

  pt_owner_set_result  — istalgan holatdagi guruh o'yini -> confirmed (yopilgan tur ham).
  pt_owner_cancel      — natijani bekor qiladi -> pending; FAQAT joriy turda (yopilgan
                         turdagi o'yinni hech kim qayta kirita olmaydi — u yerda faqat tuzatish).
Pley-off (5-bosqich): durang yo'q; set -> pt_advance (final yangilanadi / chempion);
cancel faqat tasdiqlanmagan (awaiting) pley-off o'yinida.
Sabablar: match_not_found, not_owner, not_running, round_closed, draw_not_allowed, wrong_status.
"""

import logging

from models import get_connection

logger = logging.getLogger(__name__)


def _load(cursor, match_id: int):
    cursor.execute(
        "SELECT m.id, m.stage, m.round, m.player1_id, m.player2_id, m.score1, m.score2, m.status, "
        "m.group_label, t.owner_user_id, t.status AS t_status, t.current_round, t.id AS tid "
        "FROM pt_matches m JOIN pt_tournaments t ON t.id = m.tournament_id WHERE m.id = ?", (match_id,))
    r = cursor.fetchone()
    return dict(r) if r else None


def _check(m: dict | None, owner_id: int) -> str | None:
    if not m:
        return "match_not_found"
    if m["owner_user_id"] != owner_id:
        return "not_owner"
    if m["t_status"] != "running":
        return "not_running"
    return None


def _tx(fn):
    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        ok, result = fn(cursor)
        cursor.execute("COMMIT" if ok else "ROLLBACK")
        return ok, result
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            logger.exception("pt_owner_fix: ROLLBACK xatosi")
        raise
    finally:
        conn.close()


def pt_owner_match_info(match_id: int, owner_id: int) -> tuple[bool, str | dict]:
    """Tuzatishdan oldin ko'rish: o'yinchilar, hisob, holat, tur."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        m = _load(cursor, match_id)
        if not m:
            return False, "match_not_found"
        if m["owner_user_id"] != owner_id:
            return False, "not_owner"
        cursor.execute("SELECT id, nickname, username FROM users WHERE id IN (?, ?)",
                       (m["player1_id"], m["player2_id"]))
        names = {r["id"]: (("@" + r["username"]) if r["username"] else r["nickname"]) for r in cursor.fetchall()}
    finally:
        conn.close()
    return True, {"id": m["id"], "round": m["round"], "group_label": m["group_label"], "status": m["status"],
                  "score1": m["score1"], "score2": m["score2"],
                  "player1": names.get(m["player1_id"]), "player2": names.get(m["player2_id"]),
                  "stage": m["stage"],
                  "can_cancel": (m["round"] == m["current_round"]) if m["stage"] == "group"
                                else m["status"] == "awaiting_confirmation"}


def pt_owner_set_result(match_id: int, owner_id: int, score1: int, score2: int) -> tuple[bool, str | dict]:
    """Pley-offda durang taqiqlanadi (draw_not_allowed); keyin pt_advance (final/chempion)."""
    def run(cursor):
        m = _load(cursor, match_id)
        why = _check(m, owner_id)
        if why:
            return False, why
        if m["stage"] != "group" and score1 == score2:
            return False, "draw_not_allowed"
        cursor.execute("UPDATE pt_matches SET score1 = ?, score2 = ?, status = 'confirmed' WHERE id = ?",
                       (score1, score2, match_id))
        logger.info("PT #%s: tashkilotchi o'yin %s natijasini %s:%s qildi", m["tid"], match_id, score1, score2)
        advance = {"event": None}
        if m["stage"] != "group":
            from pt_knockout import pt_advance
            advance = pt_advance(cursor, m["tid"])
        return True, {"advance": advance, "tournament_id": m["tid"]}
    return _tx(run)


def pt_owner_cancel(match_id: int, owner_id: int) -> tuple[bool, str]:
    def run(cursor):
        m = _load(cursor, match_id)
        why = _check(m, owner_id)
        if why:
            return False, why
        if m["stage"] == "group" and m["round"] != m["current_round"]:
            return False, "round_closed"
        if m["stage"] != "group" and m["status"] != "awaiting_confirmation":
            return False, "wrong_status"     # tasdiqlangan pley-off — faqat tuzatish (set)
        cursor.execute("UPDATE pt_matches SET score1 = NULL, score2 = NULL, submitted_by = NULL, "
                       "status = 'pending' WHERE id = ?", (match_id,))
        return True, "ok"
    return _tx(run)
