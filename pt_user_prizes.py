"""
pt_user_prizes.py — SHAXSIY turnirlarda qo'lga kiritilgan kuboklar (2026-10-14).

Admin qarori: shaxsiy turnir sovrinlari rasmiy ★ va rasmiy "Sovrinlarim" bilan
ARALASHMAYDI — faqat profil sahifasida ALOHIDA bo'limda ko'rsatiladi (reyting
jadvallarida belgi yo'q). Minimal ishtirokchi soni cheklovi QO'YILMAGAN.

Manba — alohida jadval emas, YAKUNLANGAN turnirlarning o'zi (faqat o'qish):
  * liga formati — har tanlangan liga jadvalining 1-o'rni (pt_rounds._finish_league
    bilan bir xil: pt_results.pt_group_standings);
  * boshqa formatlar — pt_tournaments.champion_user_id (pley-off finali g'olibi).
Shu sababli eski yakunlangan turnirlar ham avtomatik ko'rinadi, turnir o'chirilsa
kubok ham yo'qoladi, ishtirokchi almashtirilsa (pt_replace) yangi egasiga o'tadi.
"""

from models import get_connection

PT_PRIZES_LIMIT = 50   # bitta profilda ko'pi bilan (eng yangilari)


def pt_user_prizes(user_id: int) -> list[dict]:
    """[{tournament_id, tournament_name, format, league, owner_username, owner_nickname, finished_at}]"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cols = ("t.id, t.name, COALESCE(t.format, 'classic') AS format, t.league_name, t.finished_at, "
                "u.username AS owner_username, u.nickname AS owner_nickname")
        cursor.execute(
            f"SELECT {cols} FROM pt_tournaments t JOIN users u ON u.id = t.owner_user_id "
            "WHERE t.status = 'finished' AND COALESCE(t.format, 'classic') != 'league' "
            "AND t.champion_user_id = ? ORDER BY t.id DESC LIMIT ?", (user_id, PT_PRIZES_LIMIT))
        prizes = [_item(r, None) for r in cursor.fetchall()]

        cursor.execute(
            f"SELECT {cols} FROM pt_tournaments t JOIN users u ON u.id = t.owner_user_id "
            "JOIN pt_members pm ON pm.tournament_id = t.id AND pm.user_id = ? AND pm.status = 'approved' "
            "WHERE t.status = 'finished' AND t.format = 'league' ORDER BY t.id DESC LIMIT ?",
            (user_id, PT_PRIZES_LIMIT))
        league_rows = cursor.fetchall()
        if league_rows:
            from pt_results import pt_group_standings
            for r in league_rows:
                for league, rows in pt_group_standings(cursor, r["id"]).items():
                    if rows and rows[0]["user_id"] == user_id:
                        prizes.append(_item(r, league))
    finally:
        conn.close()
    prizes.sort(key=lambda p: p["tournament_id"], reverse=True)
    return prizes[:PT_PRIZES_LIMIT]


def _item(r, league: str | None) -> dict:
    return {
        "tournament_id": r["id"], "tournament_name": r["name"], "format": r["format"],
        "league": league, "owner_username": r["owner_username"], "owner_nickname": r["owner_nickname"],
        "finished_at": str(r["finished_at"] or "")[:10],
    }
