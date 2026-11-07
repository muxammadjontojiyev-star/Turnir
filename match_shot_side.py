"""
match_shot_side.py — O'YIN YAKUNI EKRANI (match_shot_result.read_result) BILAN YIRIK HISOBNI TEKSHIRISH (2026-11-07).

Ekranda sana va eFootball niknamei yo'q (team nomlari bor), shuning uchun:
  * faqat YIRIK hisob (MAX_NORMAL_SCORE dan ko'p) va faqat qo'lda kiritilgan hisob bilan solishtirib (expect majburiy):
    skrinshotdagi ikki son = kiritilgan ikki son;
  * tomon: team nomi ↔ eFootball niknamei (ef_nick) yoki o'yinchi avval ishlatgan team nomi (ef_team_names — har
    tasdiqlangan skrinshotdan o'rganiladi). Tomon aniq bo'lsa va hisob teskari chiqsa — rad (shot_score_mismatch);
  * qayta ishlatish: o'xshash team nomlari + shu hisob RESULT_REUSE_DAYS ichida ikkinchi marta qabul qilinmaydi;
  * raqib baribir xabar oladi va DISPUTE_HOURS ichida «E'tiroz» bosa oladi (e'tirozda o'rganilgan nomlar o'chadi).
"""

import time
from difflib import SequenceMatcher

from models import get_connection

RESULT_REUSE_DAYS = 30
SIDE_SIM_MIN = 0.80              # team nomi ↔ nikname / o'rganilgan nom o'xshashligi
REUSE_SIM_MIN = 0.80             # boshqa skrinshotdagi team nomlari shunchalik o'xshash bo'lsa — o'sha o'yin
NAME_KEY_MIN = 3
FP_PREFIX = "res|"


def migrate_side(cur) -> None:
    cur.execute("CREATE TABLE IF NOT EXISTS ef_team_names (user_id INTEGER NOT NULL, name_key TEXT NOT NULL, "
                "seen_at REAL, PRIMARY KEY (user_id, name_key))")


def _sim(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio() if a and b else 0.0


def result_fp(row: dict) -> str:
    """res|nom1|nom2|kichik-katta|vaqt — vaqt bilan noyob (match_shots.fp UNIQUE)."""
    from match_shot import _key
    n1, n2 = sorted([_key(row["left"]), _key(row["right"])])
    a, b = sorted([int(row["s_left"]), int(row["s_right"])])
    return f"{FP_PREFIX}{n1}|{n2}|{a}-{b}|{time.time():.3f}"


def _reused(conn, row: dict) -> bool:
    from match_shot import _key
    n1, n2 = sorted([_key(row["left"]), _key(row["right"])])
    a, b = sorted([int(row["s_left"]), int(row["s_right"])])
    since = time.time() - RESULT_REUSE_DAYS * 86400
    for r in conn.execute("SELECT fp FROM match_shots WHERE fp LIKE ? AND created_at >= ?", (FP_PREFIX + "%", since)):
        p = (r["fp"] or "").split("|")
        if len(p) >= 4 and p[3] == f"{a}-{b}" and _sim(p[1], n1) >= REUSE_SIM_MIN and _sim(p[2], n2) >= REUSE_SIM_MIN:
            return True
    return False


def _side_score(name: str, nick: str | None, learned: list[str]) -> float:
    from match_shot import _key, nick_sim
    k = _key(name)
    return max([nick_sim(name, nick) if nick else 0.0] + [_sim(k, x) for x in learned])


def check_result(match: dict, user_id: int, row: dict, expect: tuple[int, int] | None) -> tuple[str | None, dict]:
    """(xato | None, {s1, s2, opponent_id}). expect — qo'lda kiritilgan yirik hisob (player1, player2)."""
    from config import MAX_NORMAL_SCORE
    from ef_nick import nicks_for_users
    p1, p2 = match["player1_id"], match["player2_id"]
    if user_id not in (p1, p2) or not p2:
        return "not_participant", {}
    if expect is None or max(expect) <= MAX_NORMAL_SCORE:
        return "result_big_only", {}                     # bu ekran — faqat yirik hisob uchun (Match History — har doim)
    a, b = int(row["s_left"]), int(row["s_right"])
    if sorted((a, b)) != sorted(expect):
        return f"res_score_mismatch|{a}:{b}", {}         # tomon noma'lum — skrinshotdagi tartibda ko'rsatiladi
    nicks = nicks_for_users([p1, p2])
    conn = get_connection()
    try:
        migrate_side(conn.cursor())
        if _reused(conn, row):
            return "shot_used", {}
        learned = {u: [r["name_key"] for r in conn.execute("SELECT name_key FROM ef_team_names WHERE user_id = ?", (u,))]
                   for u in (p1, p2)}
    finally:
        conn.close()
    if a != b:
        straight = min(_side_score(row["left"], nicks.get(p1), learned[p1]),
                       _side_score(row["right"], nicks.get(p2), learned[p2]))
        swapped = min(_side_score(row["left"], nicks.get(p2), learned[p2]),
                      _side_score(row["right"], nicks.get(p1), learned[p1]))
        if max(straight, swapped) >= SIDE_SIM_MIN:          # tomon ma'lum — hisob shu tomonga mos bo'lsin
            s1, s2 = (a, b) if straight >= swapped else (b, a)
            if (s1, s2) != tuple(expect):
                me1 = user_id == p1
                return f"shot_score_mismatch|{s1 if me1 else s2}:{s2 if me1 else s1}", {}
    return None, {"s1": int(expect[0]), "s2": int(expect[1]), "opponent_id": p2 if user_id == p1 else p1}


def learn_names(match: dict, row: dict, s1: int, s2: int) -> None:
    """Tasdiqlangan skrinshotdan: qaysi team nomi qaysi o'yinchiniki (hisob teng bo'lmasa)."""
    from match_shot import _key
    a, b = int(row["s_left"]), int(row["s_right"])
    if a == b:
        return
    left_p1 = (a, b) == (s1, s2)
    pairs = ((match["player1_id"], row["left"] if left_p1 else row["right"]),
             (match["player2_id"], row["right"] if left_p1 else row["left"]))
    conn = get_connection()
    try:
        migrate_side(conn.cursor())
        for uid, name in pairs:
            k = _key(name)
            if len(k) >= NAME_KEY_MIN:
                conn.execute("INSERT OR REPLACE INTO ef_team_names (user_id, name_key, seen_at) VALUES (?, ?, ?)",
                             (uid, k, time.time()))
        conn.commit()
    finally:
        conn.close()


def forget_names(shot: dict) -> None:
    """E'tiroz — shu skrinshotdan o'rganilgan nomlar o'chiriladi."""
    p = (shot.get("fp") or "").split("|")
    if not (shot.get("fp") or "").startswith(FP_PREFIX) or len(p) < 3:
        return
    conn = get_connection()
    try:
        migrate_side(conn.cursor())
        conn.execute("DELETE FROM ef_team_names WHERE name_key IN (?, ?) AND user_id IN (?, ?)",
                     (p[1], p[2], shot["uploader_id"], shot["opponent_id"]))
        conn.commit()
    finally:
        conn.close()
