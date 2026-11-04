"""
player_card.py — ISHTIROKCHINING SHAXSIY O'YINCHI KARTASI (2026-11-04, egasi so'rovi).

eFootball kartasi uslubida: fonda karta ramkasi, futbolchi o'rnida — ISHTIROKCHINING Telegram rasmi,
chap tepada katta reyting (OVR), ostida pozitsiya va bayroq, pastda nik va yulduzlar.
  * OVR — Divizion JORIY MAVSUM statistikasidan avtomatik (div_rating): o'ynagan sari o'sadi, yangi —
    OVR_BASE. Formula — card_ovr (hamma koeffitsient shu yerda nomlangan).
  * Pozitsiya va davlat — ishtirokchi o'zi tanlaydi (Profil → «Kartani sozlash»); tanlamasa ko'rsatilmaydi.
  * Ramka — do'kondagi «karta foni» bezagi (cosmetics_cards.py, user_cosmetic_equip.card); bo'lmasa —
    standart (bepul, CSS) ramka.
  * Ko'rinadi: Divizion qur'a kartasi, Profil sahifasi, reytingdan ochilgan profil (static/player_card.js).
Jadval — player_card_info (migratsiya, qoida #31).
"""

import logging

from models import get_connection

logger = logging.getLogger(__name__)

POSITIONS = ("CF", "SS", "LWF", "RWF", "AMF", "LMF", "RMF", "CMF", "DMF", "LB", "RB", "CB", "GK")
# Davlatlar (ISO 3166-1 alpha-2); nomi va bayrog'i frontendda koddan (Intl.DisplayNames, emoji)
COUNTRIES = (
    "UZ", "KZ", "KG", "TJ", "TM", "AF", "RU", "UA", "BY", "AZ", "GE", "AM", "TR", "IR", "IQ", "SA",
    "AE", "QA", "EG", "MA", "DZ", "TN", "IN", "PK", "BD", "ID", "MY", "CN", "KR", "JP", "US", "CA",
    "MX", "BR", "AR", "CO", "GB", "DE", "FR", "ES", "IT", "PT", "NL", "BE", "PL", "CH", "SE", "NO",
    "DK", "HR", "RS", "NG", "SN", "CM", "GH",
)

# OVR formulasi (Divizion joriy mavsumi)
OVR_BASE = 60            # hali o'ynamagan (va 50% g'alabali o'rtacha o'yinchi, tajribasiz)
OVR_MIN, OVR_MAX = 50, 99
OVR_WINRATE_K = 0.4      # (g'alaba foizi − 50) × K: 100% → +20, 0% → −20 (yutqazgan pasayadi)
OVR_CONF_GAMES = 10      # g'alaba foizi shuncha o'yindan keyin to'liq hisoblanadi (1 ta tasodifiy g'alaba ≠ 85)
OVR_EXP_K = 0.25         # har o'yin uchun tajriba ...
OVR_EXP_CAP = 40         # ... shu o'yingacha (+10)
OVR_GD_K = 1.5           # o'rtacha gol farqi × K ...
OVR_GD_CAP = 3           # ... ±shu gacha (±4.5)


def card_ovr(played: int, wins: int, gf: int, ga: int) -> int:
    if not played:
        return OVR_BASE
    win_rate = wins / played * 100
    conf = min(played, OVR_CONF_GAMES) / OVR_CONF_GAMES
    gd = max(-OVR_GD_CAP, min(OVR_GD_CAP, (gf - ga) / played))
    v = OVR_BASE + (win_rate - 50) * OVR_WINRATE_K * conf + min(played, OVR_EXP_CAP) * OVR_EXP_K + gd * OVR_GD_K
    return int(max(OVR_MIN, min(OVR_MAX, round(v))))


def migrate_player_card(cur) -> None:
    cur.execute("CREATE TABLE IF NOT EXISTS player_card_info ("
                "user_id INTEGER PRIMARY KEY, position TEXT, country TEXT, updated_at TEXT DEFAULT CURRENT_TIMESTAMP)")


def set_card_info(user_id: int, position: str | None, country: str | None) -> tuple[bool, str | dict]:
    pos = (position or "").strip().upper() or None
    cc = (country or "").strip().upper() or None
    if pos is not None and pos not in POSITIONS:
        return False, "bad_position"
    if cc is not None and cc not in COUNTRIES:
        return False, "bad_country"
    conn = get_connection()
    try:
        conn.execute("INSERT INTO player_card_info (user_id, position, country) VALUES (?, ?, ?) "
                     "ON CONFLICT(user_id) DO UPDATE SET position = excluded.position, country = excluded.country, "
                     "updated_at = CURRENT_TIMESTAMP", (user_id, pos, cc))
        conn.commit()
    finally:
        conn.close()
    return True, {"position": pos, "country": cc}


def pcards_for_users(user_ids) -> dict[int, dict]:
    """{user_id: {user_id, nickname, ovr, position, country, bg, played, wins}} — xato bo'lsa ham bo'sh emas."""
    ids = sorted({int(u) for u in user_ids if u})
    if not ids:
        return {}
    stats: dict[int, dict] = {}
    try:
        from division import div_rating
        stats = {r["user_id"]: r for r in div_rating() if r["user_id"] in ids}
    except Exception:
        logger.exception("Karta: Divizion statistikasi o'qilmadi")
    from cosmetics_cards import cards_for_users
    bgs = cards_for_users(ids)
    conn = get_connection()
    try:
        q = ",".join("?" * len(ids))
        names = {r["id"]: r["nickname"] for r in conn.execute(f"SELECT id, nickname FROM users WHERE id IN ({q})", ids)}
        try:
            info = {r["user_id"]: r for r in conn.execute(
                f"SELECT user_id, position, country FROM player_card_info WHERE user_id IN ({q})", ids)}
        except Exception:          # migratsiyadan oldin
            info = {}
    finally:
        conn.close()
    out = {}
    for uid in ids:
        if uid not in names:
            continue
        st, inf = stats.get(uid) or {}, info.get(uid)
        played, wins = st.get("wins", 0) + st.get("draws", 0) + st.get("losses", 0), st.get("wins", 0)
        out[uid] = {
            "user_id": uid, "nickname": names[uid],
            "ovr": card_ovr(played, wins, st.get("goals_for", 0), st.get("goals_against", 0)),
            "position": inf["position"] if inf else None, "country": inf["country"] if inf else None,
            "bg": bgs.get(uid), "played": played, "wins": wins,
        }
    return out
