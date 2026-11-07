"""
match_shot_user.py — skrinshotli natija: ishtirokchi tomoni (match_shot.py dan ajratildi 2026-11-07, fayl ≤300 qator).
  incoming — men haqimda yozilgan, e'tiroz muddati o'tmagan natijalar; dispute — e'tiroz; shot_image — rasm.
"""

import time

from match_shot import DISPUTE_HOURS
from models import get_connection


def incoming(user_id: int) -> list[dict]:
    """Men haqimda skrinshot bilan yozilgan, hali e'tiroz muddati o'tmagan natijalar."""
    since = time.time() - DISPUTE_HOURS * 3600
    conn = get_connection()
    try:
        rows = conn.execute("SELECT s.id, s.mode, s.match_id, s.score1, s.score2, s.played_at, s.created_at, "
                            "s.uploader_id, u.nickname FROM match_shots s JOIN users u ON u.id = s.uploader_id "
                            "WHERE s.opponent_id = ? AND s.status = 'applied' AND s.created_at > ? ORDER BY s.id DESC",
                            (user_id, since)).fetchall()
    finally:
        conn.close()
    from match_modes import get_match
    out = []
    for r in rows:
        m = get_match(r["mode"], r["match_id"]) or {}
        p1_me = m.get("player1_id") == user_id
        out.append({"id": r["id"], "mode": r["mode"], "match_id": r["match_id"], "nickname": r["nickname"],
                    "my_goals": r["score1"] if p1_me else r["score2"], "their_goals": r["score2"] if p1_me else r["score1"],
                    "left_s": int(r["created_at"] + DISPUTE_HOURS * 3600 - time.time())})
    from match_shot_await import incoming_await
    return incoming_await(user_id) + out


def dispute(user_id: int, shot_id: int) -> tuple[bool, str | dict]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        r = cur.execute("SELECT * FROM match_shots WHERE id = ?", (shot_id,)).fetchone()
        if not r or r["opponent_id"] != user_id:
            return False, "not_found"
        if r["status"] != "applied":
            return False, "wrong_status"
        if time.time() - r["created_at"] > DISPUTE_HOURS * 3600:
            return False, "too_late"
        cur.execute("UPDATE match_shots SET status = 'disputed', disputed_at = ? WHERE id = ? AND status = 'applied'",
                    (time.time(), shot_id))
        conn.commit()
    finally:
        conn.close()
    from match_shot_side import forget_names            # 2026-11-07: o'yin yakuni ekranidan o'rganilgan team nomlari
    forget_names(dict(r))
    return True, dict(r)


def shot_image(shot_id: int) -> bytes | None:
    conn = get_connection()
    try:
        r = conn.execute("SELECT img FROM match_shots WHERE id = ?", (shot_id,)).fetchone()
        return r["img"] if r else None
    finally:
        conn.close()
