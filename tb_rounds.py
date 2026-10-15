"""
tb_rounds.py — "TEAMLAR JANGI": turlar oqimi va 1v1 juftlash (2026-10-16, 2-bosqich).

Qoida (rasmiy rejimlar bilan bir xil ritm):
  • Kuniga BITTA tur, deadline — 23:30 (Toshkent). Admin "Turlarni boshlash" -> 1-tur ochiladi.
  • Tur OCHILGANDA har bahs uchun ikkala teamning shu paytdagi ASOSIY TARKIBI olinadi,
    n = min(tarkib A, tarkib B) ta 1v1 juftlik TASODIFIY tuziladi (katta tarkibdan n kishi
    tasodifiy tanlanadi). Tarkibi TB_LINEUP_MIN dan kam team — texnik mag'lubiyat
    (raqib TB_LINEUP_MIN:0 bilan yutadi; ikkalasi ham kam bo'lsa 0:0).
  • 23:30 da joriy tur YOPILADI: awaiting -> confirmed (kiritilgan hisob), pending -> 0:0;
    har bahs natijasi hisoblanadi (1v1 g'alabalar soni), keyingi tur ochiladi.
  • Bahsdagi barcha o'yinlar tasdiqlansa — bahs darhol yakunlanadi (tb_games.py).
Idempotent: kuniga bir marta (last_advance_date), BEGIN IMMEDIATE (qoida #38).
"""

import logging
import random
from datetime import datetime, timedelta, timezone

from config import MATCHDAY_UNLOCK_HOUR, TOURNAMENT_TIMEZONE_OFFSET
from models import get_connection
from tb_core import TB_LINEUP_MIN
from tb_season import tb_active_season

logger = logging.getLogger(__name__)

TB_DEADLINE_MINUTE = 30     # 23:30 (Toshkent)
G_PENDING, G_AWAITING, G_CONFIRMED = "pending", "awaiting_confirmation", "confirmed"


def _now_local() -> datetime:
    return datetime.now(timezone(timedelta(hours=TOURNAMENT_TIMEZONE_OFFSET)))


def _lineup(cur, team_id: int) -> list[int]:
    cur.execute("SELECT user_id FROM tb_members WHERE team_id = ? AND in_lineup = 1 ORDER BY lineup_pos",
                (team_id,))
    return [r["user_id"] for r in cur.fetchall()]


def _open_fixture(cur, f) -> int:
    """Bahs uchun 1v1 juftliklar (yoki texnik natija). Qaytaradi: yaratilgan o'yinlar soni."""
    home, away = _lineup(cur, f["home_team_id"]), _lineup(cur, f["away_team_id"])
    h_ok, a_ok = len(home) >= TB_LINEUP_MIN, len(away) >= TB_LINEUP_MIN
    if not (h_ok and a_ok):
        tech = "both" if not (h_ok or a_ok) else ("home" if not h_ok else "away")
        hw = TB_LINEUP_MIN if tech == "away" else 0
        aw = TB_LINEUP_MIN if tech == "home" else 0
        cur.execute("UPDATE tb_fixtures SET status = 'finished', technical = ?, home_wins = ?, away_wins = ?, "
                    "draws = 0, home_goals = 0, away_goals = 0 WHERE id = ?", (tech, hw, aw, f["id"]))
        return 0
    n = min(len(home), len(away))
    hs, as_ = random.sample(home, n), random.sample(away, n)
    for slot, (hu, au) in enumerate(zip(hs, as_), start=1):
        cur.execute("INSERT INTO tb_games (fixture_id, slot, home_user_id, away_user_id, status) "
                    "VALUES (?, ?, ?, ?, ?)", (f["id"], slot, hu, au, G_PENDING))
    cur.execute("UPDATE tb_fixtures SET status = 'open' WHERE id = ?", (f["id"],))
    return n


def open_round(cur, season_id: int, rnd: int) -> dict:
    cur.execute("SELECT id, home_team_id, away_team_id FROM tb_fixtures "
                "WHERE season_id = ? AND round = ? AND status = 'scheduled'", (season_id, rnd))
    fixtures = cur.fetchall()
    games = sum(_open_fixture(cur, f) for f in fixtures)
    return {"fixtures": len(fixtures), "games": games}


def aggregate_fixture(cur, fixture_id: int, finish: bool) -> None:
    """Bahs natijasini 1v1 o'yinlardan hisoblaydi (faqat confirmed). finish=True — yakunlaydi."""
    cur.execute("SELECT score1, score2 FROM tb_games WHERE fixture_id = ? AND status = ?",
                (fixture_id, G_CONFIRMED))
    hw = aw = dr = hg = ag = 0
    for g in cur.fetchall():
        hg += g["score1"]
        ag += g["score2"]
        if g["score1"] > g["score2"]:
            hw += 1
        elif g["score1"] < g["score2"]:
            aw += 1
        else:
            dr += 1
    cur.execute("UPDATE tb_fixtures SET home_wins = ?, away_wins = ?, draws = ?, home_goals = ?, away_goals = ?"
                + (", status = 'finished'" if finish else "") + " WHERE id = ?",
                (hw, aw, dr, hg, ag, fixture_id))


def close_round(cur, season_id: int, rnd: int) -> dict:
    cur.execute("SELECT id FROM tb_fixtures WHERE season_id = ? AND round <= ? AND status = 'open'",
                (season_id, rnd))
    fx = [r["id"] for r in cur.fetchall()]
    awaiting = pending = 0
    for fid in fx:
        cur.execute("UPDATE tb_games SET status = ?, updated_at = CURRENT_TIMESTAMP "
                    "WHERE fixture_id = ? AND status = ?", (G_CONFIRMED, fid, G_AWAITING))
        awaiting += cur.rowcount
        cur.execute("UPDATE tb_games SET status = ?, score1 = 0, score2 = 0, updated_at = CURRENT_TIMESTAMP "
                    "WHERE fixture_id = ? AND status = ?", (G_CONFIRMED, fid, G_PENDING))
        pending += cur.rowcount
        aggregate_fixture(cur, fid, finish=True)
    return {"fixtures_closed": len(fx), "awaiting_resolved": awaiting, "pending_resolved": pending}


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
            logger.exception("tb_rounds: ROLLBACK xatosi")
        raise
    finally:
        conn.close()


def tb_start_rounds() -> tuple[bool, str | dict]:
    """Admin: 1-turni ochadi. Sabablar: no_season, already_started."""
    def run(cur):
        s = tb_active_season(cur)
        if not s:
            return False, "no_season"
        if s["status"] != "drawn":
            return False, "already_started"
        info = open_round(cur, s["id"], 1)
        cur.execute("UPDATE tb_seasons SET status = 'running', current_round = 1, started_at = datetime('now'), "
                    "last_advance_date = ? WHERE id = ?", (_now_local().date().isoformat(), s["id"]))
        return True, {"round": 1, **info}
    return _tx(run)


def _advance(cur, s: dict, today: str) -> dict:
    cur_round = s["current_round"]
    closed = close_round(cur, s["id"], cur_round)
    nxt = cur_round + 1
    opened = open_round(cur, s["id"], nxt) if nxt <= s["total_rounds"] else {"fixtures": 0, "games": 0}
    cur.execute("UPDATE tb_seasons SET current_round = ?, last_advance_date = ? WHERE id = ?",
                (nxt, today, s["id"]))
    return {"closed_round": cur_round, "opened_round": nxt if nxt <= s["total_rounds"] else None,
            **closed, "games_created": opened["games"]}


def tb_force_advance() -> tuple[bool, str | dict]:
    """Admin: joriy turni hozir yopib, keyingisini ochadi. Sabablar: no_season, not_running, all_rounds_done."""
    def run(cur):
        s = tb_active_season(cur)
        if not s:
            return False, "no_season"
        if s["status"] != "running":
            return False, "not_running"
        if s["current_round"] > s["total_rounds"]:
            return False, "all_rounds_done"
        return True, _advance(cur, s, _now_local().date().isoformat())
    return _tx(run)


def tb_tick() -> dict | None:
    """Scheduler (daqiqada bir): 23:30 dan keyin, bugun hali siljimagan bo'lsa — tur almashadi."""
    now = _now_local()
    if now < now.replace(hour=MATCHDAY_UNLOCK_HOUR, minute=TB_DEADLINE_MINUTE, second=0, microsecond=0):
        return None
    today = now.date().isoformat()

    def run(cur):
        s = tb_active_season(cur)
        if (not s or s["status"] != "running" or s["last_advance_date"] == today
                or s["current_round"] > s["total_rounds"]):
            return False, None
        return True, _advance(cur, s, today)
    ok, res = _tx(run)
    return res if ok else None


def tb_finish_season() -> tuple[bool, str | dict]:
    """Admin: mavsumni yakunlaydi (ochiq bahslar yopiladi). Sabab: no_season."""
    def run(cur):
        s = tb_active_season(cur)
        if not s:
            return False, "no_season"
        closed = close_round(cur, s["id"], s["total_rounds"])
        # o'ynalmagan (scheduled) bahslar shundayligicha qoladi — jadvalga kirmaydi
        cur.execute("UPDATE tb_seasons SET status = 'finished', finished_at = datetime('now') WHERE id = ?",
                    (s["id"],))
        return True, {"season": s["number"], **closed}
    return _tx(run)
