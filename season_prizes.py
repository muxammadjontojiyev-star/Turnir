"""
Mavsum sovrinlari — hisoblash va tarixga saqlash.

Sovrin turlari:
- golden_ball: 5 liga bo'ylab eng ko'p OCHKO yig'gan (umumiy 1 kishi)   [LIGA]
- golden_boot: 5 liga bo'ylab eng ko'p GOL urgan (umumiy 1 kishi)      [LIGA]
- league_cup:  har liga 1-o'rni — o'sha liga kubogi (league_id bilan)  [LIGA]
- wc_cup:      play-off chempioni                                       [WC]

MUHIM: Liga va WC mavsumi ALOHIDA yakunlanadi (loyiha egasining qarori):
  - "Liga mavsumini yakunlash"  → golden_ball/golden_boot/league_cup, season_kind='league',
                                  season_state.current_season oshadi.
  - "WC mavsumini yakunlash"    → wc_cup, season_kind='wc',
                                  season_state.wc_season oshadi.
Har biri o'z cooldowni + idempotentligi bilan (audit A3 naqshi).
"""

from config import SEASON_FINALIZE_COOLDOWN_SECONDS
from models import get_connection


# ============================================================
#  Joriy mavsum raqamlari
# ============================================================

def get_league_season() -> int:
    """Joriy LIGA mavsum raqami (season_state.current_season)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT current_season FROM season_state WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    return row["current_season"] if row else 1


def get_wc_season() -> int:
    """Joriy WC mavsum raqami (season_state.wc_season)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT wc_season FROM season_state WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    return row["wc_season"] if row else 1


def get_current_season() -> int:
    """
    Orqaga moslik uchun — LIGA mavsumini qaytaradi (eski nom).
    Yangi kodda get_league_season()/get_wc_season() ishlatilsin.
    """
    return get_league_season()


# ============================================================
#  Sovrin egalarini hisoblash (SAQLAMAYDI — faqat hisob)
# ============================================================

def calculate_league_prizes() -> dict:
    """
    LIGA sovrinlari (golden_ball, golden_boot, league_cups) — joriy holatga ko'ra.

    Qaytaradi:
      {
        "golden_ball": {user_id, nickname, username, points} | None,
        "golden_boot": {user_id, nickname, username, goals_for} | None,
        "league_cups": [{league_id, league_name, user_id, nickname, username}, ...],
      }
    """
    from rating import calculate_league_rating
    from queries import get_all_leagues

    leagues = get_all_leagues()

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
        # Umumiy ochko/gol yig'indisi (barcha liga bo'ylab)
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

    golden_ball = None
    if players_list:
        golden_ball = max(players_list, key=lambda p: p["points"])
        if golden_ball["points"] <= 0:
            golden_ball = None

    golden_boot = None
    if players_list:
        golden_boot = max(players_list, key=lambda p: p["goals_for"])
        if golden_boot["goals_for"] <= 0:
            golden_boot = None

    return {
        "golden_ball": golden_ball,
        "golden_boot": golden_boot,
        "league_cups": league_cups,
    }


def calculate_wc_prizes() -> dict:
    """
    WC sovrinlari (wc_cup) — joriy holatga ko'ra.

    Qaytaradi: {"wc_cup": {user_id, nickname, username, team_name} | None}
    """
    from queries import wc_playoff_get_champion
    return {"wc_cup": wc_playoff_get_champion()}


def calculate_season_prizes() -> dict:
    """
    Barcha sovrinlar (liga + WC) — preview uchun. Orqaga moslik: eski
    kalitlar (golden_ball/golden_boot/league_cups/wc_cup) saqlanadi.
    """
    lg = calculate_league_prizes()
    wc = calculate_wc_prizes()
    return {
        "golden_ball": lg["golden_ball"],
        "golden_boot": lg["golden_boot"],
        "league_cups": lg["league_cups"],
        "wc_cup": wc["wc_cup"],
    }


# ============================================================
#  Cooldown yordamchisi (liga/WC uchun umumiy — DRY, qoida #26)
# ============================================================

def _cooldown_active(cursor, last_at_col: str) -> bool:
    """
    Berilgan ustundagi (last_finalized_at / wc_last_finalized_at) oxirgi
    yakunlash vaqtidan beri cooldown o'tmagan bo'lsa True (takror bosish).
    """
    cursor.execute(f"SELECT {last_at_col} AS last_at FROM season_state WHERE id = 1")
    row = cursor.fetchone()
    last_at = row["last_at"] if row else None
    if last_at is None:
        return False
    cursor.execute(
        "SELECT (julianday('now') - julianday(?)) * 86400 AS diff", (last_at,)
    )
    diff = cursor.fetchone()["diff"]
    return diff is not None and diff < SEASON_FINALIZE_COOLDOWN_SECONDS


# ============================================================
#  LIGA mavsumini yakunlash
# ============================================================

def finalize_league_season() -> dict:
    """
    LIGA mavsumini yakunlaydi: golden_ball/golden_boot/league_cup hisoblanadi,
    season_kind='league' bilan saqlanadi, current_season oshadi.

    IDEMPOTENTLIK (A3): BEGIN IMMEDIATE + cooldown (last_finalized_at) +
    "shu liga mavsumida yozuv bormi" tekshiruvi. Takror bosishda {"already": True}.

    Qaytaradi: {season, already, counts: {...}, prizes: {...}}
    """
    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        return _finalize_league_locked(conn, cursor)
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            pass
        conn.close()
        raise


def _finalize_league_locked(conn, cursor) -> dict:
    cursor.execute("BEGIN IMMEDIATE")

    cursor.execute("SELECT current_season FROM season_state WHERE id = 1")
    row = cursor.fetchone()
    season = row["current_season"] if row else 1

    if _cooldown_active(cursor, "last_finalized_at"):
        cursor.execute("ROLLBACK")
        conn.close()
        return {"season": season, "already": True, "counts": {}, "prizes": None}

    # Shu liga mavsumida allaqachon yozuv bormi? (qo'shimcha himoya)
    cursor.execute(
        "SELECT 1 FROM season_prizes WHERE season_kind = 'league' AND season_number = ? LIMIT 1",
        (season,),
    )
    if cursor.fetchone() is not None:
        cursor.execute("ROLLBACK")
        conn.close()
        return {"season": season, "already": True, "counts": {}, "prizes": None}

    prizes = calculate_league_prizes()

    def save(user_id, prize_type, league_id=None):
        cursor.execute(
            "INSERT INTO season_prizes (user_id, prize_type, league_id, season_number, season_kind) "
            "VALUES (?, ?, ?, ?, 'league')",
            (user_id, prize_type, league_id, season),
        )

    counts = {"golden_ball": 0, "golden_boot": 0, "league_cups": 0}
    if prizes["golden_ball"]:
        save(prizes["golden_ball"]["user_id"], "golden_ball")
        counts["golden_ball"] = 1
    if prizes["golden_boot"]:
        save(prizes["golden_boot"]["user_id"], "golden_boot")
        counts["golden_boot"] = 1
    for cup in prizes["league_cups"]:
        save(cup["user_id"], "league_cup", cup["league_id"])
        counts["league_cups"] += 1

    cursor.execute(
        "UPDATE season_state SET current_season = current_season + 1, "
        "last_finalized_at = datetime('now') WHERE id = 1"
    )
    cursor.execute("COMMIT")
    conn.close()
    return {"season": season, "already": False, "counts": counts, "prizes": prizes}


# ============================================================
#  WC mavsumini yakunlash
# ============================================================

def finalize_wc_season() -> dict:
    """
    WC mavsumini yakunlaydi: wc_cup (play-off chempioni) hisoblanadi,
    season_kind='wc' bilan saqlanadi, wc_season oshadi.

    IDEMPOTENTLIK (A3): BEGIN IMMEDIATE + cooldown (wc_last_finalized_at) +
    "shu WC mavsumida yozuv bormi" tekshiruvi. Takror bosishda {"already": True}.

    Qaytaradi: {season, already, counts: {...}, prizes: {...}}
    """
    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        return _finalize_wc_locked(conn, cursor)
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            pass
        conn.close()
        raise


def _finalize_wc_locked(conn, cursor) -> dict:
    cursor.execute("BEGIN IMMEDIATE")

    cursor.execute("SELECT wc_season FROM season_state WHERE id = 1")
    row = cursor.fetchone()
    season = row["wc_season"] if row else 1

    if _cooldown_active(cursor, "wc_last_finalized_at"):
        cursor.execute("ROLLBACK")
        conn.close()
        return {"season": season, "already": True, "counts": {}, "prizes": None}

    # Shu WC mavsumida allaqachon yozuv bormi? (qo'shimcha himoya)
    cursor.execute(
        "SELECT 1 FROM season_prizes WHERE season_kind = 'wc' AND season_number = ? LIMIT 1",
        (season,),
    )
    if cursor.fetchone() is not None:
        cursor.execute("ROLLBACK")
        conn.close()
        return {"season": season, "already": True, "counts": {}, "prizes": None}

    prizes = calculate_wc_prizes()

    counts = {"wc_cup": 0}
    if prizes["wc_cup"]:
        cursor.execute(
            "INSERT INTO season_prizes (user_id, prize_type, league_id, season_number, season_kind) "
            "VALUES (?, 'wc_cup', NULL, ?, 'wc')",
            (prizes["wc_cup"]["user_id"], season),
        )
        counts["wc_cup"] = 1

    cursor.execute(
        "UPDATE season_state SET wc_season = wc_season + 1, "
        "wc_last_finalized_at = datetime('now') WHERE id = 1"
    )
    cursor.execute("COMMIT")
    conn.close()
    return {"season": season, "already": False, "counts": counts, "prizes": prizes}


# ============================================================
#  Foydalanuvchi sovrinlari (profil uchun)
# ============================================================

def get_user_prizes(user_id: int) -> list[dict]:
    """
    Foydalanuvchining barcha sovrinlari (liga + WC, tarix bo'yicha).

    Qaytaradi: [{prize_type, league_id, league_name, season_number,
                 season_kind, awarded_at}, ...]
    Eng yangi birinchi.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT sp.prize_type, sp.league_id, sp.season_number, sp.season_kind,
               sp.awarded_at, l.name AS league_name
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
