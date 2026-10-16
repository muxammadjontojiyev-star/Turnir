"""
tb_games.py — "TEAMLAR JANGI": 1v1 o'yin natijalari va bahslar ko'rinishi (2026-10-16, 2-bosqich).

  tb_my_games(user_id)                — mening joriy (ochiq) o'yinim(lar) + bahs ma'lumoti
  tb_submit(user_id, game_id, mine, opp) — natija kiritish (o'z nuqtai nazaridan) -> awaiting
  tb_confirm(user_id, game_id, accept)   — raqib tasdiqlaydi (confirmed) yoki rad etadi (pending)
  tb_admin_set(game_id, s1, s2)          — liga admini / bosh admin natijani qo'yadi (confirmed)
  tb_game_league(game_id)                — o'yin ligasi (ruxsat tekshiruvi)
  tb_round_fixtures(season_id, division, round) — tur bahslari + 1v1 juftliklar
Faqat OCHIQ bahsda (status='open') natija kiritiladi. Bahsdagi barcha o'yinlar
tasdiqlansa — bahs darhol yakunlanadi (tb_rounds.aggregate_fixture).
"""

import logging

from models import get_connection
from tb_rounds import G_AWAITING, G_CONFIRMED, G_PENDING, aggregate_fixture

logger = logging.getLogger(__name__)

TB_SCORE_MAX = 30

_GAME_SQL = (
    "SELECT g.id, g.fixture_id, g.slot, g.home_user_id, g.away_user_id, g.score1, g.score2, "
    "g.submitted_by, g.status, f.round, f.division, f.status AS fixture_status, "
    "f.home_team_id, f.away_team_id, ht.name AS home_team, ht.emoji AS home_emoji, "
    "at.name AS away_team, at.emoji AS away_emoji, "
    "hu.nickname AS home_nick, hu.username AS home_username, "
    "au.nickname AS away_nick, au.username AS away_username "
    "FROM tb_games g JOIN tb_fixtures f ON f.id = g.fixture_id "
    "JOIN tb_teams ht ON ht.id = f.home_team_id JOIN tb_teams at ON at.id = f.away_team_id "
    "JOIN users hu ON hu.id = g.home_user_id JOIN users au ON au.id = g.away_user_id "
)


def _tx(fn):
    conn = get_connection()
    conn.isolation_level = None
    cur = conn.cursor()
    try:
        cur.execute("BEGIN IMMEDIATE")
        res = fn(cur)
        cur.execute("COMMIT" if res[0] else "ROLLBACK")
        return res
    except Exception:
        try:
            cur.execute("ROLLBACK")
        except Exception:
            logger.exception("tb_games: ROLLBACK xatosi")
        raise
    finally:
        conn.close()


def _valid_score(x) -> int | None:
    try:
        v = int(x)
    except (TypeError, ValueError):
        return None
    return v if 0 <= v <= TB_SCORE_MAX else None


def _maybe_finish_fixture(cur, fixture_id: int) -> bool:
    cur.execute("SELECT COUNT(*) AS n, SUM(status = ?) AS c FROM tb_games WHERE fixture_id = ?",
                (G_CONFIRMED, fixture_id))
    r = cur.fetchone()
    done = r["n"] > 0 and r["c"] == r["n"]
    aggregate_fixture(cur, fixture_id, finish=done)
    return done


def tb_my_games(user_id: int) -> list[dict]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(_GAME_SQL + "WHERE (g.home_user_id = ? OR g.away_user_id = ?) AND f.status = 'open' "
                    "ORDER BY f.round", (user_id, user_id))
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def tb_submit(user_id: int, game_id: int, my_score, opp_score) -> tuple[bool, str | dict]:
    """Sabablar: bad_score, game_not_found, not_your_game, round_closed, already_confirmed."""
    mine, opp = _valid_score(my_score), _valid_score(opp_score)
    if mine is None or opp is None:
        return False, "bad_score"

    def run(cur):
        cur.execute("SELECT g.id, g.fixture_id, g.home_user_id, g.away_user_id, g.status, f.status AS fst "
                    "FROM tb_games g JOIN tb_fixtures f ON f.id = g.fixture_id WHERE g.id = ?", (game_id,))
        g = cur.fetchone()
        if not g:
            return False, "game_not_found"
        if user_id not in (g["home_user_id"], g["away_user_id"]):
            return False, "not_your_game"
        if g["fst"] != "open":
            return False, "round_closed"
        if g["status"] == G_CONFIRMED:
            return False, "already_confirmed"
        s1, s2 = (mine, opp) if user_id == g["home_user_id"] else (opp, mine)
        cur.execute("UPDATE tb_games SET score1 = ?, score2 = ?, submitted_by = ?, status = ?, "
                    "updated_at = CURRENT_TIMESTAMP WHERE id = ?", (s1, s2, user_id, G_AWAITING, game_id))
        opp_id = g["away_user_id"] if user_id == g["home_user_id"] else g["home_user_id"]
        return True, {"game_id": game_id, "opponent_user_id": opp_id}
    return _tx(run)


def tb_confirm(user_id: int, game_id: int, accept: bool) -> tuple[bool, str | dict]:
    """Sabablar: game_not_found, not_your_game, round_closed, nothing_to_confirm, own_submission."""
    def run(cur):
        cur.execute("SELECT g.id, g.fixture_id, g.home_user_id, g.away_user_id, g.status, g.submitted_by, "
                    "f.status AS fst FROM tb_games g JOIN tb_fixtures f ON f.id = g.fixture_id WHERE g.id = ?",
                    (game_id,))
        g = cur.fetchone()
        if not g:
            return False, "game_not_found"
        if user_id not in (g["home_user_id"], g["away_user_id"]):
            return False, "not_your_game"
        if g["fst"] != "open":
            return False, "round_closed"
        if g["status"] != G_AWAITING:
            return False, "nothing_to_confirm"
        if g["submitted_by"] == user_id:
            return False, "own_submission"
        if accept:
            cur.execute("UPDATE tb_games SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (G_CONFIRMED, game_id))
            finished = _maybe_finish_fixture(cur, g["fixture_id"])
        else:
            cur.execute("UPDATE tb_games SET status = ?, score1 = NULL, score2 = NULL, submitted_by = NULL, "
                        "updated_at = CURRENT_TIMESTAMP WHERE id = ?", (G_PENDING, game_id))
            finished = False
        return True, {"game_id": game_id, "accepted": bool(accept), "fixture_finished": finished,
                      "submitter_user_id": g["submitted_by"]}
    return _tx(run)


def tb_admin_set(game_id: int, s1, s2) -> tuple[bool, str | dict]:
    """Bosh admin: natijani qo'yadi (yopilgan turda ham — bahs qayta hisoblanadi). Sabablar: bad_score, game_not_found."""
    a, b = _valid_score(s1), _valid_score(s2)
    if a is None or b is None:
        return False, "bad_score"

    def run(cur):
        cur.execute("SELECT fixture_id FROM tb_games WHERE id = ?", (game_id,))
        g = cur.fetchone()
        if not g:
            return False, "game_not_found"
        cur.execute("UPDATE tb_games SET score1 = ?, score2 = ?, status = ?, updated_at = CURRENT_TIMESTAMP "
                    "WHERE id = ?", (a, b, G_CONFIRMED, game_id))
        cur.execute("SELECT status FROM tb_fixtures WHERE id = ?", (g["fixture_id"],))
        if cur.fetchone()["status"] == "finished":
            aggregate_fixture(cur, g["fixture_id"], finish=True)
        else:
            _maybe_finish_fixture(cur, g["fixture_id"])
        return True, {"game_id": game_id}
    return _tx(run)


def tb_round_fixtures(season_id: int, division: int, rnd: int) -> list[dict]:
    """Tur bahslari (divizion ichida) + har biridagi 1v1 o'yinlar."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT f.id, f.round, f.status, f.technical, f.home_wins, f.away_wins, f.draws, "
            "f.home_team_id, f.away_team_id, ht.name AS home_team, ht.emoji AS home_emoji, "
            "at.name AS away_team, at.emoji AS away_emoji "
            "FROM tb_fixtures f JOIN tb_teams ht ON ht.id = f.home_team_id JOIN tb_teams at ON at.id = f.away_team_id "
            "WHERE f.season_id = ? AND f.division = ? AND f.round = ? ORDER BY f.id",
            (season_id, division, rnd))
        fixtures = [dict(r) for r in cur.fetchall()]
        if fixtures:
            marks = ",".join("?" * len(fixtures))
            cur.execute(_GAME_SQL + f"WHERE g.fixture_id IN ({marks}) ORDER BY g.fixture_id, g.slot",
                        [f["id"] for f in fixtures])
            by_fx = {}
            for g in cur.fetchall():
                by_fx.setdefault(g["fixture_id"], []).append({
                    "id": g["id"], "slot": g["slot"], "status": g["status"],
                    "score1": g["score1"], "score2": g["score2"],
                    "home": g["home_username"] and "@" + g["home_username"] or g["home_nick"],
                    "away": g["away_username"] and "@" + g["away_username"] or g["away_nick"],
                })
            for f in fixtures:
                f["games"] = by_fx.get(f["id"], [])
        return fixtures
    finally:
        conn.close()


def tb_game_league(game_id: int) -> int | None:
    """2026-10-16: o'yin qaysi ligada (admin ruxsatini tekshirish uchun)."""
    conn = get_connection()
    try:
        r = conn.cursor().execute(
            "SELECT s.league_id FROM tb_games g JOIN tb_fixtures f ON f.id = g.fixture_id "
            "JOIN tb_seasons s ON s.id = f.season_id WHERE g.id = ?", (game_id,)).fetchone()
        return r["league_id"] if r else None
    finally:
        conn.close()
