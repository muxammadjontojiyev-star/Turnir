"""
tb_draw.py — "TEAMLAR JANGI": mavsum qur'asi (tb_season.py dan ajratildi, 2026-10-18).

Liga admini qur'ada tanlaydi:
  fmt          — 'league' (divizionlar, bir martalik aylanma) yoki 'ucl' (tb_ucl.py)
  match_size   — bahsda necha kishi o'ynaydi (11 vs 11, 10 vs 10 ...). Berilmasa — eski qoida:
                 ikki tarkibning kichigi (kamida liga lineup_min). Asosiy tarkibi match_size dan
                 kam team qur'aga kirmaydi; tur ochilganda ham kam bo'lsa — texnik mag'lubiyat.
  division_size — faqat liga formati; UCL: ucl_rounds, ucl_qualify, ko_legs, final_legs.
"""

import logging
import random

from models import get_connection
from schedule import _generate_round_robin_pairs
from tb_season import (TB_DIV_SIZE_MAX, TB_DIV_SIZE_MIN, _eligible_teams, _league_settings,
                       _ordered_for_draw, split_divisions, tb_active_season)
from tb_ucl import (FMT_LEAGUE, FMT_UCL, TB_MATCH_SIZE_MAX, TB_MATCH_SIZE_MIN, create_ucl_fixtures,
                    ko_schedule, validate_ucl)

logger = logging.getLogger(__name__)


def _league_fixtures(cur, sid: int, divisions: list[list[int]]) -> tuple[int, int]:
    fixtures = total_rounds = 0
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
    return fixtures, total_rounds


def tb_create_season(league_id: int, division_size: int | None = None, fmt: str | None = None,
                     match_size: int | None = None, ucl_rounds: int | None = None,
                     ucl_qualify: int | None = None, ko_legs: int | None = None,
                     final_legs: int | None = None, ucl_playin: bool = False) -> tuple[bool, str | dict]:
    """
    Ligada qur'a. Sabablar: bad_format, bad_match_size, bad_division_size, active_exists,
    not_enough_teams, bad_qualify, bad_playin, bad_legs, bad_ucl_rounds, bad_ucl_params.
    2026-10-26: ucl_playin — rasmiy ChL kabi pley-off raundi (tb_ucl.py).
    Qaytaradi: {season_id, number, format, divisions, teams, fixtures, total_rounds}
    """
    fmt = fmt or FMT_LEAGUE
    if fmt not in (FMT_LEAGUE, FMT_UCL):
        return False, "bad_format"
    if match_size not in (None, ""):
        try:
            match_size = int(match_size)
        except (TypeError, ValueError):
            return False, "bad_match_size"
        if not TB_MATCH_SIZE_MIN <= match_size <= TB_MATCH_SIZE_MAX:
            return False, "bad_match_size"
    else:
        match_size = None
    conn = get_connection()
    conn.isolation_level = None
    cur = conn.cursor()
    try:
        size = int(division_size or _league_settings(cur, league_id)["division_size"])
        if fmt == FMT_LEAGUE and (size < TB_DIV_SIZE_MIN or size > TB_DIV_SIZE_MAX):
            return False, "bad_division_size"
        cur.execute("BEGIN IMMEDIATE")
        if tb_active_season(league_id, cur):
            cur.execute("ROLLBACK")
            return False, "active_exists"
        teams = _eligible_teams(cur, league_id, match_size)
        if len(teams) < 2:
            cur.execute("ROLLBACK")
            return False, "not_enough_teams"
        ucl = {}
        if fmt == FMT_UCL:
            why, ucl = validate_ucl(len(teams), ucl_rounds, ucl_qualify, ko_legs, final_legs, ucl_playin)
            if why:
                cur.execute("ROLLBACK")
                return False, why
        cur.execute("SELECT COALESCE(MAX(number), 0) + 1 AS n FROM tb_seasons WHERE league_id = ?", (league_id,))
        number = cur.fetchone()["n"]
        cur.execute("INSERT INTO tb_seasons (league_id, number, status, division_size, format, match_size, "
                    "ucl_rounds, ucl_qualify, ko_legs, final_legs, ucl_playin) "
                    "VALUES (?, ?, 'drawn', ?, ?, ?, ?, ?, ?, ?, ?)",
                    (league_id, number, size, fmt, match_size, ucl.get("ucl_rounds"), ucl.get("ucl_qualify"),
                     ucl.get("ko_legs"), ucl.get("final_legs"), ucl.get("ucl_playin", 0)))
        sid = cur.lastrowid
        if fmt == FMT_UCL:
            fixtures = create_ucl_fixtures(cur, sid, teams, ucl["ucl_rounds"])
            total_rounds = ucl["ucl_rounds"] + len(ko_schedule(ucl["ucl_qualify"], ucl["ko_legs"], ucl["final_legs"],
                                                               bool(ucl["ucl_playin"])))
            n_div = 1
        else:
            divisions = split_divisions(_ordered_for_draw(cur, teams, league_id), size)
            fixtures, total_rounds = _league_fixtures(cur, sid, divisions)
            n_div = len(divisions)
        cur.execute("UPDATE tb_seasons SET total_rounds = ? WHERE id = ?", (total_rounds, sid))
        cur.execute("COMMIT")
        logger.info("TB: liga %s, %s-mavsum qur'asi (%s, %s vs %s) — %s team, %s bahs, %s tur",
                    league_id, number, fmt, match_size, match_size, len(teams), fixtures, total_rounds)
        return True, {"season_id": sid, "number": number, "format": fmt, "divisions": n_div,
                      "teams": len(teams), "fixtures": fixtures, "total_rounds": total_rounds}
    except Exception:
        try:
            cur.execute("ROLLBACK")
        except Exception:
            logger.exception("tb_create_season: ROLLBACK xatosi")
        raise
    finally:
        conn.close()
