"""
Mavsum sovrinlari — hisoblash va tarixga saqlash.

Sovrin turlari:
- golden_ball: 5 liga bo'ylab eng ko'p OCHKO yig'gan (umumiy 1 kishi)
- golden_boot: 5 liga bo'ylab eng ko'p GOL urgan (umumiy 1 kishi)
- league_cup:  har liga 1-o'rni — o'sha liga kubogi (league_id bilan)
- wc_cup:      play-off chempioni

Mavsum "Mavsumni yakunlash" admin tugmasi bilan yakunlanadi: sovrinlar
hisoblanadi, season_prizes'ga saqlanadi, mavsum raqami oshadi.
"""

from models import get_connection


def get_current_season() -> int:
    """Joriy mavsum raqami."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT current_season FROM season_state WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    return row["current_season"] if row else 1


def calculate_season_prizes() -> dict:
    """
    Joriy holatga ko'ra sovrin egalarini hisoblaydi (SAQLAMAYDI — faqat hisob).

    Qaytaradi:
      {
        "golden_ball": {user_id, nickname, username, points} | None,
        "golden_boot": {user_id, nickname, username, goals_for} | None,
        "league_cups": [{league_id, league_name, user_id, nickname, username}, ...],
        "wc_cup": {user_id, nickname, username, team_name} | None,
      }
    """
    from rating import calculate_league_rating
    from queries import get_all_leagues, wc_playoff_get_champion

    leagues = get_all_leagues()

    # Barcha ligalardagi o'yinchilarni yig'amiz (ochko/gol umumiy hisob)
    all_players = {}   # user_id -> {points, goals_for, nickname, username}
    league_cups = []

    for lg in leagues:
        rating = calculate_league_rating(lg["id"])
        if not rating:
            continue
        # Liga 1-o'rni — liga kubogi
        champ = rating[0]
        league_cups.append({
            "league_id": lg["id"],
            "league_name": lg["name"],
            "user_id": champ["user_id"],
            "nickname": champ.get("nickname"),
            "username": champ.get("username"),
        })
        # Umumiy ochko/gol yig'indisi (5 liga bo'ylab)
        for p in rating:
            uid = p["user_id"]
            if uid not in all_players:
                all_players[uid] = {
                    "user_id": uid,
                    "nickname": p.get("nickname"),
                    "username": p.get("username"),
                    "points": 0,
                    "goals_for": 0,
                }
            all_players[uid]["points"] += p.get("points", 0)
            all_players[uid]["goals_for"] += p.get("goals_for", 0)

    players_list = list(all_players.values())

    # Oltin to'p — eng ko'p ochko
    golden_ball = None
    if players_list:
        golden_ball = max(players_list, key=lambda p: p["points"])
        if golden_ball["points"] <= 0:
            golden_ball = None

    # Oltin butsa — eng ko'p gol
    golden_boot = None
    if players_list:
        golden_boot = max(players_list, key=lambda p: p["goals_for"])
        if golden_boot["goals_for"] <= 0:
            golden_boot = None

    # WC kubogi — play-off chempioni
    wc_cup = wc_playoff_get_champion()

    return {
        "golden_ball": golden_ball,
        "golden_boot": golden_boot,
        "league_cups": league_cups,
        "wc_cup": wc_cup,
    }


def finalize_season() -> dict:
    """
    Mavsumni yakunlaydi: sovrinlarni hisoblaydi, season_prizes'ga saqlaydi,
    mavsum raqamini oshiradi.

    Qaytaradi: {season, saved: {golden_ball, golden_boot, league_cups, wc_cup},
                counts: {...}}
    """
    season = get_current_season()
    prizes = calculate_season_prizes()

    conn = get_connection()
    cursor = conn.cursor()

    def save(user_id, prize_type, league_id=None):
        cursor.execute(
            """
            INSERT INTO season_prizes (user_id, prize_type, league_id, season_number)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, prize_type, league_id, season),
        )

    counts = {"golden_ball": 0, "golden_boot": 0, "league_cups": 0, "wc_cup": 0}

    if prizes["golden_ball"]:
        save(prizes["golden_ball"]["user_id"], "golden_ball")
        counts["golden_ball"] = 1
    if prizes["golden_boot"]:
        save(prizes["golden_boot"]["user_id"], "golden_boot")
        counts["golden_boot"] = 1
    for cup in prizes["league_cups"]:
        save(cup["user_id"], "league_cup", cup["league_id"])
        counts["league_cups"] += 1
    if prizes["wc_cup"]:
        save(prizes["wc_cup"]["user_id"], "wc_cup")
        counts["wc_cup"] = 1

    # Mavsum raqamini oshiramiz
    cursor.execute("UPDATE season_state SET current_season = current_season + 1 WHERE id = 1")

    conn.commit()
    conn.close()

    return {"season": season, "counts": counts, "prizes": prizes}


def get_user_prizes(user_id: int) -> list[dict]:
    """
    Foydalanuvchining barcha sovrinlari (tarix, mavsum bo'yicha).

    Qaytaradi: [{prize_type, league_id, league_name, season_number, awarded_at}, ...]
    Eng yangi mavsum birinchi.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT sp.prize_type, sp.league_id, sp.season_number, sp.awarded_at,
               l.name AS league_name
        FROM season_prizes sp
        LEFT JOIN leagues l ON l.id = sp.league_id
        WHERE sp.user_id = ?
        ORDER BY sp.season_number DESC, sp.id ASC
        """,
        (user_id,),
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows
