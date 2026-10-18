"""
tb_ucl_view.py — "TEAMLAR JANGI": UCL pley-off ko'rinishi va liga admini qarori (2026-10-18).

  tb_ko_view(season_id)            — bosqichlar: juftliklar, har oyoq natijasi, yig'indi, g'olib
  tb_ko_decide(league_id, tie_id, winner_team_id)
                                   — teng juftlikda liga admini g'olibni belgilaydi; mavsum qaror
                                     kutayotgan bo'lsa — keyingi bosqich darhol ochiladi.
Mantiq: tb_ucl.py. Tranzaksiya — tb_rounds._tx (BEGIN IMMEDIATE, qoida #38).
"""

import logging

from models import get_connection
from tb_ucl import _tie_score, ko_schedule

logger = logging.getLogger(__name__)


def _team_map(cur, ids: set[int]) -> dict:
    if not ids:
        return {}
    marks = ",".join("?" * len(ids))
    cur.execute(f"SELECT id, name, emoji, logo_ver FROM tb_teams WHERE id IN ({marks})", list(ids))
    return {r["id"]: dict(r) for r in cur.fetchall()}


def tb_ko_view(season_id: int) -> dict:
    conn = get_connection()
    try:
        cur = conn.cursor()
        s = cur.execute("SELECT format, ucl_rounds, ucl_qualify, ko_legs, final_legs, waiting_admin "
                        "FROM tb_seasons WHERE id = ?", (season_id,)).fetchone()
        if not s or s["format"] != "ucl":
            return {"stages": []}
        cur.execute("SELECT * FROM tb_ko_ties WHERE season_id = ? ORDER BY stage_size DESC, tie_no", (season_id,))
        ties = [dict(r) for r in cur.fetchall()]
        teams = _team_map(cur, {t["team_a"] for t in ties} | {t["team_b"] for t in ties})
        by_stage: dict[int, list] = {}
        for t in ties:
            sc = _tie_score(cur, t)
            cur.execute("SELECT round, home_team_id, status, home_wins, away_wins, technical FROM tb_fixtures "
                        "WHERE tie_id = ? ORDER BY round", (t["id"],))
            legs = []
            for f in cur.fetchall():
                a_home = f["home_team_id"] == t["team_a"]
                legs.append({"round": f["round"], "status": f["status"], "technical": f["technical"],
                             "a": f["home_wins"] if a_home else f["away_wins"],
                             "b": f["away_wins"] if a_home else f["home_wins"]})
            by_stage.setdefault(t["stage_size"], []).append({
                "id": t["id"], "tie_no": t["tie_no"], "a": teams.get(t["team_a"]), "b": teams.get(t["team_b"]),
                "legs": legs, "agg_a": sc["a"]["wins"], "agg_b": sc["b"]["wins"],
                "goals_a": sc["a"]["goals"], "goals_b": sc["b"]["goals"],
                "winner_team_id": t["winner_team_id"], "needs_admin": bool(t["needs_admin"])})
        sizes = []
        for size, _leg in ko_schedule(s["ucl_qualify"], s["ko_legs"], s["final_legs"]):
            if size not in sizes:
                sizes.append(size)
        stages = [{"size": z, "ties": by_stage.get(z, [])} for z in sizes]
        return {"stages": stages, "qualify": s["ucl_qualify"], "league_rounds": s["ucl_rounds"],
                "waiting_admin": bool(s["waiting_admin"])}
    finally:
        conn.close()


def tb_ko_decide(league_id: int, tie_id: int, winner_team_id: int) -> tuple[bool, str | dict]:
    """
    Sabablar: tie_not_found, bad_winner, already_decided, not_tied.
    Qaytaradi: {tie_id, opened_round (ochilgan bo'lsa), season_id}.
    """
    from tb_rounds import _now_local, _tx, open_round
    from tb_season import tb_active_season
    from tb_ucl import prepare_round

    def run(cur):
        s = tb_active_season(league_id, cur)
        tie = cur.execute("SELECT * FROM tb_ko_ties WHERE id = ?", (tie_id,)).fetchone()
        if not s or not tie or tie["season_id"] != s["id"]:
            return False, "tie_not_found"
        if winner_team_id not in (tie["team_a"], tie["team_b"]):
            return False, "bad_winner"
        if tie["winner_team_id"]:
            return False, "already_decided"
        if not tie["needs_admin"]:
            return False, "not_tied"
        cur.execute("UPDATE tb_ko_ties SET winner_team_id = ?, needs_admin = 0 WHERE id = ?", (winner_team_id, tie_id))
        opened = None
        if s["waiting_admin"] and prepare_round(cur, s, s["current_round"]) == "ok":
            open_round(cur, s["id"], s["current_round"])
            cur.execute("UPDATE tb_seasons SET waiting_admin = 0, last_advance_date = ? WHERE id = ?",
                        (_now_local().date().isoformat(), s["id"]))
            opened = s["current_round"]
        logger.info("TB UCL: juftlik %s g'olibi — team %s (admin qarori)", tie_id, winner_team_id)
        return True, {"tie_id": tie_id, "season_id": s["id"], "opened_round": opened}
    return _tx(run)
