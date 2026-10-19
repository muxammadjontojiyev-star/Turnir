"""
qm_view.py — TEZKOR O'YIN: holat (oyna har 2–3 soniyada so'raydi) va reyting (2026-10-19).
Mantiq: qm_core.py. Holat so'rovi navbatdagi "ping"ni ham yangilaydi va muddatlarni tekshiradi.
"""

from models import get_connection
from qm_core import (ACTIVE, QM_BASE_RATING, QM_CONFIRM_MINUTES, QM_ONLINE_S, QM_QUEUE_STALE_S, ST_AWAITING,
                     _expire_cur, _rating_row, _tx)

QM_RATING_TOP = 50
QM_RECENT = 5


def _secs_left(cur, ts: str | None, plus_minutes: int = 0) -> int | None:
    if not ts:
        return None
    r = cur.execute("SELECT CAST((julianday(?, ?) - julianday('now')) * 86400 AS INTEGER) AS s",
                    (ts, f"+{plus_minutes} minutes")).fetchone()
    return max(0, r["s"])


def _user(cur, uid: int) -> dict:
    u = cur.execute("SELECT id, nickname, username FROM users WHERE id = ?", (uid,)).fetchone()
    d = dict(u) if u else {"id": uid, "nickname": None, "username": None}
    d["rating"] = _rating_row(cur, uid)["rating"]
    return d


def _match_view(cur, m, me: int) -> dict:
    i_am_1 = m["player1_id"] == me
    opp = m["player2_id"] if i_am_1 else m["player1_id"]
    st = m["status"]
    return {
        "id": m["id"], "status": st, "opponent": _user(cur, opp),
        "my_score": m["score1"] if i_am_1 else m["score2"],
        "opp_score": m["score2"] if i_am_1 else m["score1"],
        "submitted_by_me": m["submitted_by"] == me if m["submitted_by"] else None,
        "room_code": m["room_code"],
        "room_left": _secs_left(cur, m["room_deadline"]) if st == "room" else None,
        "play_left": _secs_left(cur, m["play_deadline"]) if st == "playing" else None,
        "confirm_left": _secs_left(cur, m["submitted_at"], QM_CONFIRM_MINUTES) if st == ST_AWAITING else None,
        "my_delta": m["delta1"] if i_am_1 else m["delta2"], "rated": bool(m["rated"]),
        "cancel_reason": m["cancel_reason"],
    }


def qm_state(user_id: int) -> dict:
    def run(cur):
        _expire_cur(cur)
        cur.execute("UPDATE qm_queue SET last_ping = datetime('now') WHERE user_id = ?", (user_id,))
        searching = cur.rowcount > 0
        m = cur.execute(
            f"SELECT * FROM qm_matches WHERE (player1_id = ? OR player2_id = ?) AND status IN "
            f"({','.join('?' * len(ACTIVE))}) ORDER BY id DESC LIMIT 1", (user_id, user_id, *ACTIVE)).fetchone()
        last = None
        if not m:
            # yaqinda tugagan o'yin (natija/bekor qilinganini ko'rsatish uchun, 10 daqiqa)
            last = cur.execute("SELECT * FROM qm_matches WHERE (player1_id = ? OR player2_id = ?) "
                               "AND finished_at >= datetime('now', '-10 minutes') ORDER BY id DESC LIMIT 1",
                               (user_id, user_id)).fetchone()
        waiting = cur.execute("SELECT COUNT(*) AS c FROM qm_queue WHERE last_ping >= datetime('now', ?)",
                              (f"-{QM_QUEUE_STALE_S} seconds",)).fetchone()["c"]
        online = cur.execute("SELECT COUNT(*) AS c FROM users WHERE last_seen >= datetime('now', ?)",
                             (f"-{QM_ONLINE_S} seconds",)).fetchone()["c"]
        me = _user(cur, user_id)
        return {"me": {"user_id": user_id, "username": me["username"], "nickname": me["nickname"],
                       **_rating_row(cur, user_id)}, "searching": searching and not m,
                "match": _match_view(cur, m, user_id) if m else None,
                "last": _match_view(cur, last, user_id) if last else None,
                "waiting": waiting, "online": online}
    return _tx(run)


def qm_rating(user_id: int) -> dict:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT r.user_id, r.rating, r.played, r.wins, r.draws, r.losses, u.nickname, u.username "
                    "FROM qm_ratings r JOIN users u ON u.id = r.user_id WHERE r.played > 0 "
                    "ORDER BY r.rating DESC, r.wins DESC, r.played ASC LIMIT ?", (QM_RATING_TOP,))
        top = [dict(r) for r in cur.fetchall()]
        me = _rating_row(cur, user_id)
        pos = None
        if me["played"]:
            pos = cur.execute("SELECT COUNT(*) + 1 AS p FROM qm_ratings WHERE played > 0 AND rating > ?",
                              (me["rating"],)).fetchone()["p"]
        cur.execute("SELECT * FROM qm_matches WHERE (player1_id = ? OR player2_id = ?) AND status = 'confirmed' "
                    "ORDER BY id DESC LIMIT ?", (user_id, user_id, QM_RECENT))
        recent = [_match_view(cur, m, user_id) for m in cur.fetchall()]
        return {"top": top, "me": {**me, "position": pos, "base": QM_BASE_RATING}, "recent": recent}
    finally:
        conn.close()
