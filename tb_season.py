"""
tb_season.py — "TEAMLAR JANGI": mavsum, divizionlar, jadval (2026-10-16, 2-bosqich).

Egasi qarorlari: teamlar divizionlarga bo'linadi (TB_DIV_SIZE ta), har divizion
o'z ichida bir martalik aylanma liga; bahsda o'yinchilar 1v1 (tasodifiy juftlash,
tb_rounds.py), ko'p g'alaba olgan team yutadi. Ochko: g'alaba 3, durang 1.
Jadval saralash: ochko -> 1v1 g'alabalar farqi -> gol farqi -> 1v1 g'alabalar.

  tb_active_season()              — faol (tugamagan) mavsum yoki None
  tb_season_preview()             — qatnasha oladigan teamlar soni (admin uchun)
  tb_create_season(div_size)      — qur'a: divizionlar + barcha turlar jadvali
  tb_standings(season_id, div)    — divizion jadvali
  tb_team_division(season_id, team_id)
"""

import logging
import random

from models import get_connection
from schedule import _generate_round_robin_pairs
from tb_core import STATUS_APPROVED, TB_LINEUP_MIN

logger = logging.getLogger(__name__)

TB_DIV_SIZE = 10        # divizion hajmi (standart)
TB_DIV_SIZE_MIN = 4     # admin kiritishi mumkin bo'lgan eng kichik hajm
TB_DIV_SIZE_MAX = 20
TB_DIV_TAIL_MIN = 6     # oxirgi divizion bundan kichik bo'lsa — oldingisiga qo'shiladi
TB_PTS_WIN, TB_PTS_DRAW = 3, 1
TB_PROMO = 2            # har divizion juftida ko'tariladigan/tushadigan teamlar soni (3-bosqich)

_SEASON_COLS = ("id, number, status, division_size, total_rounds, current_round, "
                "last_advance_date, created_at, started_at, finished_at")


def tb_active_season(cursor=None) -> dict | None:
    own = cursor is None
    conn = get_connection() if own else None
    cur = conn.cursor() if own else cursor
    try:
        cur.execute(f"SELECT {_SEASON_COLS} FROM tb_seasons WHERE status != 'finished' "
                    "ORDER BY id DESC LIMIT 1")
        r = cur.fetchone()
        return dict(r) if r else None
    finally:
        if own:
            conn.close()


def tb_last_season() -> dict | None:
    """Faol mavsum, bo'lmasa oxirgi tugagani (jadvalni ko'rsatish uchun)."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        s = tb_active_season(cur)
        if s:
            return s
        cur.execute(f"SELECT {_SEASON_COLS} FROM tb_seasons ORDER BY id DESC LIMIT 1")
        r = cur.fetchone()
        return dict(r) if r else None
    finally:
        conn.close()


def _eligible_teams(cur) -> list[int]:
    """Tasdiqlangan va asosiy tarkibi kamida TB_LINEUP_MIN bo'lgan teamlar."""
    cur.execute(
        "SELECT t.id FROM tb_teams t WHERE t.status = ? AND "
        "(SELECT COUNT(*) FROM tb_members m WHERE m.team_id = t.id AND m.in_lineup = 1) >= ?",
        (STATUS_APPROVED, TB_LINEUP_MIN),
    )
    return [r["id"] for r in cur.fetchall()]


def tb_season_preview() -> dict:
    conn = get_connection()
    try:
        cur = conn.cursor()
        eligible = _eligible_teams(cur)
        cur.execute("SELECT COUNT(*) AS c FROM tb_teams WHERE status = ?", (STATUS_APPROVED,))
        approved = cur.fetchone()["c"]
        return {"eligible": len(eligible), "approved": approved, "lineup_min": TB_LINEUP_MIN,
                "division_size": TB_DIV_SIZE, "active": tb_active_season(cur)}
    finally:
        conn.close()


def split_divisions(team_ids: list[int], size: int) -> list[list[int]]:
    """Tartiblangan ro'yxatni divizionlarga bo'ladi; kichik qoldiq oldingisiga qo'shiladi."""
    chunks = [team_ids[i:i + size] for i in range(0, len(team_ids), size)]
    if len(chunks) > 1 and len(chunks[-1]) < min(TB_DIV_TAIL_MIN, size):
        chunks[-2].extend(chunks.pop())
    return chunks


def apply_promotion(tables: list[list[int]], n: int = None) -> list[list[int]]:
    """
    3-bosqich (2026-10-16): ko'tarilish/tushish. Har qo'shni divizion juftida yuqori
    divizionning oxirgi n tasi pastga, pastkisining birinchi n tasi yuqoriga almashadi
    (asl jadvallar bo'yicha — bir vaqtda). Kichik divizionda (< 2n) almashinuv yo'q.
    """
    n = TB_PROMO if n is None else n
    out = [list(t) for t in tables]
    for d in range(len(tables) - 1):
        up, low = tables[d], tables[d + 1]
        if len(up) < 2 * n or len(low) < 2 * n:
            continue
        down_ids, up_ids = up[-n:], low[:n]
        out[d] = [t for t in out[d] if t not in down_ids] + up_ids
        out[d + 1] = down_ids + [t for t in out[d + 1] if t not in up_ids]
    return out


def _ordered_for_draw(cur, team_ids: list[int]) -> list[int]:
    """
    Oldingi mavsum yakuniy o'rinlari bo'yicha (divizion, o'rin) tartib — ko'tarilish/tushish
    (apply_promotion) bilan; yangi teamlar oxirida tasodifiy. Oldingi mavsum bo'lmasa — tasodifiy.
    """
    cur.execute("SELECT id FROM tb_seasons WHERE status = 'finished' ORDER BY id DESC LIMIT 1")
    prev = cur.fetchone()
    rank = {}
    if prev:
        cur.execute("SELECT DISTINCT division FROM tb_season_teams WHERE season_id = ? ORDER BY division",
                    (prev["id"],))
        tables = [[row["team_id"] for row in _standings_cur(cur, prev["id"], r["division"])]
                  for r in cur.fetchall()]
        order = 0
        for tbl in apply_promotion(tables):
            for tid in tbl:
                rank[tid] = order
                order += 1
    known = sorted([t for t in team_ids if t in rank], key=lambda t: rank[t])
    new = [t for t in team_ids if t not in rank]
    random.shuffle(new)
    if not known:
        return new
    return known + new


def tb_create_season(division_size: int | None = None) -> tuple[bool, str | dict]:
    """
    Qur'a. Sabablar: active_exists, bad_division_size, not_enough_teams.
    Qaytaradi: {season_id, number, divisions, teams, fixtures, total_rounds}
    """
    size = int(division_size or TB_DIV_SIZE)
    if size < TB_DIV_SIZE_MIN or size > TB_DIV_SIZE_MAX:
        return False, "bad_division_size"
    conn = get_connection()
    conn.isolation_level = None
    cur = conn.cursor()
    try:
        cur.execute("BEGIN IMMEDIATE")
        if tb_active_season(cur):
            cur.execute("ROLLBACK")
            return False, "active_exists"
        teams = _eligible_teams(cur)
        if len(teams) < 2:
            cur.execute("ROLLBACK")
            return False, "not_enough_teams"
        divisions = split_divisions(_ordered_for_draw(cur, teams), size)
        cur.execute("SELECT COALESCE(MAX(number), 0) + 1 AS n FROM tb_seasons")
        number = cur.fetchone()["n"]
        cur.execute("INSERT INTO tb_seasons (number, status, division_size) VALUES (?, 'drawn', ?)",
                    (number, size))
        sid = cur.lastrowid
        fixtures = 0
        total_rounds = 0
        for d, ids in enumerate(divisions, start=1):
            ids = ids[:]
            random.shuffle(ids)                      # divizion ichida juftlash tartibi tasodifiy
            for tid in ids:
                cur.execute("INSERT INTO tb_season_teams (season_id, team_id, division) VALUES (?, ?, ?)",
                            (sid, tid, d))
            rounds = _generate_round_robin_pairs(ids)
            total_rounds = max(total_rounds, len(rounds))
            for rnd, pairs in enumerate(rounds, start=1):
                for home, away in pairs:
                    cur.execute("INSERT INTO tb_fixtures (season_id, division, round, home_team_id, away_team_id) "
                                "VALUES (?, ?, ?, ?, ?)", (sid, d, rnd, home, away))
                    fixtures += 1
        cur.execute("UPDATE tb_seasons SET total_rounds = ? WHERE id = ?", (total_rounds, sid))
        cur.execute("COMMIT")
        logger.info("TB: %s-mavsum qur'asi — %s team, %s divizion, %s bahs, %s tur",
                    number, len(teams), len(divisions), fixtures, total_rounds)
        return True, {"season_id": sid, "number": number, "divisions": len(divisions),
                      "teams": len(teams), "fixtures": fixtures, "total_rounds": total_rounds}
    except Exception:
        try:
            cur.execute("ROLLBACK")
        except Exception:
            logger.exception("tb_create_season: ROLLBACK xatosi")
        raise
    finally:
        conn.close()


def _standings_cur(cur, season_id: int, division: int) -> list[dict]:
    cur.execute(
        "SELECT st.team_id, t.name, t.emoji FROM tb_season_teams st JOIN tb_teams t ON t.id = st.team_id "
        "WHERE st.season_id = ? AND st.division = ?", (season_id, division))
    rows = {r["team_id"]: {"team_id": r["team_id"], "name": r["name"], "emoji": r["emoji"],
                           "played": 0, "wins": 0, "draws": 0, "losses": 0, "points": 0,
                           "gw": 0, "gl": 0, "gf": 0, "ga": 0} for r in cur.fetchall()}
    cur.execute("SELECT home_team_id, away_team_id, home_wins, away_wins, home_goals, away_goals "
                "FROM tb_fixtures WHERE season_id = ? AND division = ? AND status = 'finished'",
                (season_id, division))
    for f in cur.fetchall():
        h, a = rows.get(f["home_team_id"]), rows.get(f["away_team_id"])
        if not h or not a:
            continue
        for me, my_w, op_w, my_g, op_g in ((h, f["home_wins"], f["away_wins"], f["home_goals"], f["away_goals"]),
                                           (a, f["away_wins"], f["home_wins"], f["away_goals"], f["home_goals"])):
            me["played"] += 1
            me["gw"] += my_w
            me["gl"] += op_w
            me["gf"] += my_g
            me["ga"] += op_g
            if my_w > op_w:
                me["wins"] += 1
                me["points"] += TB_PTS_WIN
            elif my_w < op_w:
                me["losses"] += 1
            else:
                me["draws"] += 1
                me["points"] += TB_PTS_DRAW
    table = list(rows.values())
    # teng holatda — alifbo tartibi (barqaror)
    table.sort(key=lambda r: (-r["points"], -(r["gw"] - r["gl"]), -(r["gf"] - r["ga"]), -r["gw"], r["name"].lower()))
    return table


def tb_standings(season_id: int, division: int) -> list[dict]:
    conn = get_connection()
    try:
        return _standings_cur(conn.cursor(), season_id, division)
    finally:
        conn.close()


def tb_divisions(season_id: int) -> list[dict]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT division, COUNT(*) AS teams FROM tb_season_teams WHERE season_id = ? "
                    "GROUP BY division ORDER BY division", (season_id,))
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def tb_team_division(season_id: int, team_id: int | None) -> int | None:
    if not team_id:
        return None
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT division FROM tb_season_teams WHERE season_id = ? AND team_id = ?",
                    (season_id, team_id))
        r = cur.fetchone()
        return r["division"] if r else None
    finally:
        conn.close()


def tb_team_in_active_season(team_id: int) -> bool:
    """Team faol mavsumdami (tarqatish/o'chirishni bloklash uchun)."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        s = tb_active_season(cur)
        if not s:
            return False
        cur.execute("SELECT 1 FROM tb_season_teams WHERE season_id = ? AND team_id = ?", (s["id"], team_id))
        return cur.fetchone() is not None
    finally:
        conn.close()


def tb_team_titles(team_id: int) -> list[dict]:
    """3-bosqich: teamning divizion chempionliklari (eng yangisi birinchi)."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT season_number, division FROM tb_titles WHERE team_id = ? ORDER BY season_id DESC",
                    (team_id,))
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()
