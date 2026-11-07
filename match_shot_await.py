"""
match_shot_await.py — RAQIB eFOOTBALL NIKNAMEINI KIRITMAGAN bo'lsa (2026-11-06, egasi: «raqib kiritmagan — bot hisobni
tasdiqlamayapti»). match_shot.apply_shot dan chaqiriladi.

  * Yuklovchining niknamesi qatorning bir tomonida aniq bo'lishi shart; ikkinchi tomondagi nikname — RAQIBNIKI DEB
    TAKLIF qilinadi (boshqa ro'yxatdagi ishtirokchiga tegishli bo'lsa — rad: nick_mismatch).
  * Natija rejimning o'z oqimida KIRITILADI (submit), lekin avtomatik tasdiqlanmaydi: raqibga bot xabari va ilovada
    kartochka — «Skrinshotdagi niknameingiz: X» (tahrirlash mumkin, skrinshotdagiga mos bo'lishi shart):
      «Tasdiqlash» → niknamesi saqlanadi (ef_nick) va natija raqib nomidan tasdiqlanadi;
      «Rad etish»  → natija rad etiladi (rejimning o'z rad etishi) va skrinshot adminga e'tiroz sifatida tushadi.
  * Raqib javob bermasa — rejimning odatdagi deadline qoidasi (masalan ligada kiritilgan natija tasdiqlanadi).
match_shots: status 'await_opp', opp_nick ustuni (migratsiya, qoida #31).
"""

import logging
import time

from models import get_connection

logger = logging.getLogger(__name__)

AWAIT_MAX_AGE_H = 72
ST_AWAIT = "await_opp"


def migrate_shot_await(cur) -> None:
    cols = {r["name"] for r in cur.execute("PRAGMA table_info(match_shots)")}
    if "opp_nick" not in cols:
        cur.execute("ALTER TABLE match_shots ADD COLUMN opp_nick TEXT")


def check_await(mode: str, match: dict, user_id: int, row: dict, my_nick: str) -> tuple[str | None, dict]:
    """Raqibda nikname yo'q: (xato | None, {s1, s2, opponent_id, played, opp_nick})."""
    from match_modes import MODES
    from match_shot import NICK_MATCH_MIN, _opened, _played_at, nick_sim
    p1, p2 = match["player1_id"], match["player2_id"]
    opp = p2 if user_id == p1 else p1
    sl, sr = nick_sim(row["left"], my_nick), nick_sim(row["right"], my_nick)
    if max(sl, sr) < NICK_MATCH_MIN:
        return "nick_mismatch", {"detail": my_nick}      # skrinshotda sizning niknameingiz topilmadi
    me_left = sl >= sr
    opp_nick = " ".join((row["right"] if me_left else row["left"]).split())
    if not opp_nick:
        return "nick_mismatch", {"detail": my_nick}
    conn = get_connection()
    try:                                                 # skrinshotdagi raqib — boshqa ro'yxatdagi ishtirokchi emasmi
        for r in conn.execute("SELECT user_id, nick FROM ef_nicknames WHERE user_id NOT IN (?, ?)", (user_id, opp)):
            if nick_sim(opp_nick, r["nick"]) >= NICK_MATCH_MIN:
                return "nick_mismatch", {"detail": f"{my_nick} / {r['nick']}"}   # o'yin boshqa ishtirokchi bilan
    finally:
        conn.close()
    my_goals, opp_goals = (row["s_left"], row["s_right"]) if me_left else (row["s_right"], row["s_left"])
    s1, s2 = (my_goals, opp_goals) if user_id == p1 else (opp_goals, my_goals)
    played = _played_at(row, _opened(match))
    if played is None:
        return "bad_date", {}
    if MODES[mode]["playoff"] and s1 == s2:
        return "playoff_draw", {}
    return None, {"s1": s1, "s2": s2, "opponent_id": opp, "played": played, "opp_nick": opp_nick}


def _big(s1, s2) -> bool:
    from config import MAX_NORMAL_SCORE
    return max(int(s1 or 0), int(s2 or 0)) > MAX_NORMAL_SCORE


async def apply_await(user: dict, mode: str, match: dict, r: dict, fp: str, img: bytes) -> tuple[bool, str | dict]:
    from match_modes import submit_as
    if match.get("submitted_by"):
        return False, "opp_other_score" if match["submitted_by"] != user["id"] else "my_other_score"
    if _big(r["s1"], r["s2"]):                          # 2026-11-07: yirik hisob — rejimga yozilmaydi (adminga xabar yo'q),
        pending = False                                 # raqib tasdiqlaganda darhol force_set (accept_await)
    else:
        ok, res = await submit_as(mode, match["id"], r["s1"], r["s2"], user)
        if not ok:
            return False, str(res)
        pending = "admin_pending" in str(res)
    conn = get_connection()
    try:
        conn.execute("INSERT INTO match_shots (mode, match_id, uploader_id, opponent_id, score1, score2, played_at, fp, "
                     "img, status, created_at, opp_nick) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                     (mode, match["id"], user["id"], r["opponent_id"], r["s1"], r["s2"], r["played"].isoformat(), fp, img,
                      "admin_pending" if pending else ST_AWAIT, time.time(), r["opp_nick"]))
        conn.commit()
    finally:
        conn.close()
    logger.info("MATCH SHOT: %s #%s — %s:%s, raqib niknamesi yo'q → tasdig'i kutiladi (%r)",
                mode, match["id"], r["s1"], r["s2"], r["opp_nick"])
    return True, {"await_opp": not pending, "admin_pending": pending}


def incoming_await(user_id: int) -> list[dict]:
    since = time.time() - AWAIT_MAX_AGE_H * 3600
    conn = get_connection()
    try:
        rows = conn.execute("SELECT s.id, s.mode, s.match_id, s.score1, s.score2, s.opp_nick, u.nickname FROM match_shots s "
                            "JOIN users u ON u.id = s.uploader_id WHERE s.opponent_id = ? AND s.status = ? AND s.created_at > ? "
                            "ORDER BY s.id DESC", (user_id, ST_AWAIT, since)).fetchall()
    finally:
        conn.close()
    from match_modes import get_match
    out = []
    for r in rows:
        m = get_match(r["mode"], r["match_id"]) or {}
        if m.get("status") == "confirmed":
            continue
        p1_me = m.get("player1_id") == user_id
        out.append({"id": r["id"], "mode": r["mode"], "match_id": r["match_id"], "nickname": r["nickname"], "await": True,
                    "opp_nick": r["opp_nick"], "my_goals": r["score1"] if p1_me else r["score2"],
                    "their_goals": r["score2"] if p1_me else r["score1"]})
    return out


def _load(user_id: int, shot_id: int):
    conn = get_connection()
    try:
        r = conn.execute("SELECT * FROM match_shots WHERE id = ?", (shot_id,)).fetchone()
    finally:
        conn.close()
    if not r or r["opponent_id"] != user_id:
        return None, "not_found"
    if r["status"] != ST_AWAIT:
        return None, "wrong_status"
    return r, None


def _set_status(shot_id: int, status: str) -> None:
    conn = get_connection()
    try:
        conn.execute("UPDATE match_shots SET status = ?, disputed_at = CASE WHEN ? = 'disputed' THEN ? ELSE disputed_at END "
                     "WHERE id = ?", (status, status, time.time(), shot_id))
        conn.commit()
    finally:
        conn.close()


async def accept_await(user: dict, shot_id: int, nick: str) -> tuple[bool, str | dict]:
    """Raqib: «bu mening niknamem» — niknamesi saqlanadi va natija tasdiqlanadi."""
    from ef_nick import set_nick
    from match_modes import confirm_as
    from match_shot import NICK_MATCH_MIN, nick_sim
    r, why = _load(user["id"], shot_id)
    if why:
        return False, why
    if nick_sim(nick, r["opp_nick"] or "") < NICK_MATCH_MIN:
        return False, "nick_not_in_shot"                # skrinshotdagi niknamedan boshqa nom kiritildi
    ok, res = set_nick(user["id"], nick)
    if not ok and res != "same_nick":
        return False, res
    if isinstance(res, dict) and res.get("pending"):
        return False, "nick_taken"
    if _big(r["score1"], r["score2"]):
        from match_modes import force_set
        ok, res = force_set(r["mode"], r["match_id"], r["score1"], r["score2"])
    else:
        ok, res = await confirm_as(r["mode"], r["match_id"], user)
    if not ok:
        return False, str(res)
    _set_status(shot_id, "applied")
    return True, dict(r)


async def reject_await(user: dict, shot_id: int) -> tuple[bool, str | dict]:
    """Raqib: «natija noto'g'ri» — rejimda rad etiladi, skrinshot adminga e'tiroz sifatida."""
    from match_modes import reject_as
    r, why = _load(user["id"], shot_id)
    if why:
        return False, why
    ok, res = await reject_as(r["mode"], r["match_id"], user)
    if not ok:
        logger.warning("MATCH SHOT: await rad etilmadi (%s #%s): %s", r["mode"], r["match_id"], res)
    _set_status(shot_id, "disputed")
    return True, dict(r)
