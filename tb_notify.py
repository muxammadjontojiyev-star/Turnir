"""
tb_notify.py — "TEAMLAR JANGI": tur ochilganda har o'yinchiga raqibi haqida bot xabari
(2026-10-16, 3-bosqich). ~1200 kishiga yuborish ~1 daqiqa — FONDA (pt_notify.spawn),
xabarlar orasida TB_NOTIFY_DELAY (Telegram ~30 xabar/s chegarasi, qoida #39).
"""

import asyncio
import logging

from models import get_connection

logger = logging.getLogger(__name__)

TB_NOTIFY_DELAY = 0.05


def tb_round_targets(season_id: int, rnd: int) -> list[dict]:
    """Shu tur o'yinlaridagi har o'yinchi: {telegram_id, language, opp, opp_team, my_team}."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT hu.telegram_id AS h_tg, hu.language AS h_lang, "
            "COALESCE('@' || hu.username, hu.nickname) AS h_name, "
            "au.telegram_id AS a_tg, au.language AS a_lang, "
            "COALESCE('@' || au.username, au.nickname) AS a_name, "
            "ht.name AS h_team, at.name AS a_team "
            "FROM tb_games g JOIN tb_fixtures f ON f.id = g.fixture_id "
            "JOIN users hu ON hu.id = g.home_user_id JOIN users au ON au.id = g.away_user_id "
            "JOIN tb_teams ht ON ht.id = f.home_team_id JOIN tb_teams at ON at.id = f.away_team_id "
            "WHERE f.season_id = ? AND f.round = ?", (season_id, rnd))
        out = []
        for r in cur.fetchall():
            out.append({"telegram_id": r["h_tg"], "language": r["h_lang"], "opp": r["a_name"],
                        "opp_team": r["a_team"], "my_team": r["h_team"]})
            out.append({"telegram_id": r["a_tg"], "language": r["a_lang"], "opp": r["h_name"],
                        "opp_team": r["h_team"], "my_team": r["a_team"]})
        return out
    finally:
        conn.close()


async def tb_notify_round(season_id: int, rnd: int) -> int:
    from notify import notify_user
    sent = 0
    for t in tb_round_targets(season_id, rnd):
        try:
            if await notify_user(t["telegram_id"], "tb_notify_round", t["language"],
                                 open_button_key="btn_open_app", round=rnd, opp=t["opp"],
                                 opp_team=t["opp_team"], my_team=t["my_team"]):
                sent += 1
        except Exception as exc:
            logger.warning("TB: tur xabari yuborilmadi (tg=%s): %s", t["telegram_id"], exc)
        await asyncio.sleep(TB_NOTIFY_DELAY)
    logger.info("TB: %s-tur xabari %s kishiga yuborildi", rnd, sent)
    return sent


def tb_spawn_round_notify(season_id: int, rnd: int | None) -> None:
    """Tur ochilgan bo'lsa — xabarlarni fonda yuboradi (endpoint/scheduler kutib qolmaydi)."""
    if not rnd:
        return
    from pt_notify import spawn
    spawn(tb_notify_round(season_id, rnd))
