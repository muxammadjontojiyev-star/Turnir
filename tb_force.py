"""
tb_force.py — "TEAMLAR JANGI": BOSH ADMIN — ISTALGAN HOLATDA O'CHIRISH (2026-11-07, egasi: «Bosh adminga har qanday
holatda ham ligani yoki teamni o'chira olish huquqini bering»).

Liga admini uchun eski cheklovlar qoladi (tb_manage.tb_admin_delete — mavsumda qatnashgan team o'chirilmaydi;
tb_leagues.tb_league_delete — faqat bo'sh liga). Bosh admin uchun — bog'liq yozuvlar bilan birga (kaskad) o'chiriladi:
  team:  uning bahslari (tb_fixtures) → 1v1 o'yinlar (tb_games) → chat (tb_messages), shikoyatlar (tb_reports);
         pley-off juftliklari (tb_ko_ties), chempionliklar (tb_titles), mavsum ro'yxati (tb_season_teams),
         a'zolar (tb_members), logo, team.
  liga:  barcha mavsumlari (yuqoridagi zanjir bilan), barcha teamlari, logo, liga.
Hammasi bitta tranzaksiyada (xato bo'lsa hech narsa o'chmaydi). Raqib teamlarning o'chgan teamga qarshi bahslari ham
o'chadi — jadval qolgan bahslar bo'yicha hisoblanadi (ogohlantirish UI da).
"""

import logging

from models import get_connection
from tb_core import _begin, _finish

logger = logging.getLogger(__name__)


def _ids(cur, sql: str, args: tuple) -> list[int]:
    return [int(r[0]) for r in cur.execute(sql, args).fetchall()]


def _marks(ids: list[int]) -> str:
    return ",".join("?" * len(ids))


def _drop_fixtures(cur, fixture_ids: list[int]) -> int:
    if not fixture_ids:
        return 0
    games = _ids(cur, f"SELECT id FROM tb_games WHERE fixture_id IN ({_marks(fixture_ids)})", tuple(fixture_ids))
    if games:
        g = _marks(games)
        cur.execute(f"DELETE FROM tb_messages WHERE match_id IN ({g})", tuple(games))
        cur.execute(f"DELETE FROM tb_reports WHERE game_id IN ({g})", tuple(games))
        cur.execute(f"DELETE FROM tb_games WHERE id IN ({g})", tuple(games))
    cur.execute(f"DELETE FROM tb_fixtures WHERE id IN ({_marks(fixture_ids)})", tuple(fixture_ids))
    return len(fixture_ids)


def _drop_team(cur, team_id: int) -> None:
    from tb_logos import delete_logo_cur
    fx = _ids(cur, "SELECT id FROM tb_fixtures WHERE home_team_id = ? OR away_team_id = ?", (team_id, team_id))
    ties = _ids(cur, "SELECT id FROM tb_ko_ties WHERE team_a = ? OR team_b = ?", (team_id, team_id))
    if ties:
        fx += _ids(cur, f"SELECT id FROM tb_fixtures WHERE tie_id IN ({_marks(ties)})", tuple(ties))
    _drop_fixtures(cur, sorted(set(fx)))
    if ties:
        cur.execute(f"DELETE FROM tb_ko_ties WHERE id IN ({_marks(ties)})", tuple(ties))
    cur.execute("UPDATE tb_ko_ties SET winner_team_id = NULL WHERE winner_team_id = ?", (team_id,))
    cur.execute("DELETE FROM tb_titles WHERE team_id = ?", (team_id,))
    cur.execute("DELETE FROM tb_season_teams WHERE team_id = ?", (team_id,))
    cur.execute("DELETE FROM tb_members WHERE team_id = ?", (team_id,))
    delete_logo_cur(cur, "team", team_id)
    cur.execute("DELETE FROM tb_teams WHERE id = ?", (team_id,))


def force_delete_team(team_id: int) -> tuple[bool, str | dict]:
    conn = get_connection()
    cur = _begin(conn)
    try:
        r = cur.execute("SELECT name FROM tb_teams WHERE id = ?", (team_id,)).fetchone()
        if not r:
            _finish(cur, False)
            return False, "not_found"
        _drop_team(cur, team_id)
        _finish(cur, True)
        logger.warning("TB: BOSH ADMIN team #%s (%s) ni to'liq o'chirdi", team_id, r["name"])
        return True, {"team_id": team_id}
    except Exception:
        _finish(cur, False)
        raise
    finally:
        conn.close()


def force_delete_league(league_id: int) -> tuple[bool, str | dict]:
    from tb_logos import delete_logo_cur
    conn = get_connection()
    cur = _begin(conn)
    try:
        r = cur.execute("SELECT name FROM tb_leagues WHERE id = ?", (league_id,)).fetchone()
        if not r:
            _finish(cur, False)
            return False, "league_not_found"
        teams = _ids(cur, "SELECT id FROM tb_teams WHERE league_id = ?", (league_id,))
        for t in teams:
            _drop_team(cur, t)
        seasons = _ids(cur, "SELECT id FROM tb_seasons WHERE league_id = ?", (league_id,))
        if seasons:
            s = _marks(seasons)
            _drop_fixtures(cur, _ids(cur, f"SELECT id FROM tb_fixtures WHERE season_id IN ({s})", tuple(seasons)))
            for tbl in ("tb_ko_ties", "tb_season_teams", "tb_titles"):
                cur.execute(f"DELETE FROM {tbl} WHERE season_id IN ({s})", tuple(seasons))
            cur.execute(f"DELETE FROM tb_seasons WHERE id IN ({s})", tuple(seasons))
        delete_logo_cur(cur, "league", league_id)
        cur.execute("DELETE FROM tb_leagues WHERE id = ?", (league_id,))
        _finish(cur, True)
        logger.warning("TB: BOSH ADMIN liga #%s (%s) ni to'liq o'chirdi: %s team, %s mavsum",
                       league_id, r["name"], len(teams), len(seasons))
        return True, {"league_id": league_id, "teams": len(teams), "seasons": len(seasons)}
    except Exception:
        _finish(cur, False)
        raise
    finally:
        conn.close()
