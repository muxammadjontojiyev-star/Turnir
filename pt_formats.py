"""
pt_formats.py — SHAXSIY turnir formatlari (2026-10-07).

Admin qarorlari:
  - classic : erkin — 4 kishilik guruhlar + pley-off, 8..128 (4 ga karrali), jamoa tanlanmaydi
              (2026-10-07 gacha yaratilgan barcha turnirlar shu format).
  - league  : rasmiy ligalar kabi — liga tanlanadi (LaLiga, Premier Liga, ...), ishtirokchilar soni
              DOIM ligadagi klublar soniga teng (20 yoki 18), har kim shu ligadan bitta klub tanlaydi.
              Yagona jadval, har kim har kim bilan 1 yoki 2 doira (tashkilotchi tanlaydi).
              Oxirgi tur yopilgach — jadval birinchisi chempion (pley-off yo'q).
  - cl / el : Chempionlar / Yevropa ligasi kabi — 8..36 (juft son), klub 5 ligadan tanlanadi.
              Yagona jadval, Swiss: har tur hamma o'ynaydi, raqib takrorlanmaydi, min(8, n-1) tur.
              Keyin pley-off: top-Q to'g'ridan setkaga, Q+1..3Q pley-off raundi (rasmiy 9–24 pley-in
              kabi), setka 2Q. Q = 8 (n>=24) | 4 (n>=12) | 2.
  - wc      : Jahon chempionati kabi — 4 kishilik guruhlar + pley-off (classic mexanizmi), 8..48,
              har kim rasmiy JCh'dagi 48 terma jamoadan birini tanlaydi.
Klub nomlari static/api.js LEAGUE_CLUBS bilan AYNAN mos (qoida #11) — logolar frontendda.
"""

from wc_data import WC_GROUPS

FMT_CLASSIC, FMT_LEAGUE, FMT_CL, FMT_EL, FMT_WC = "classic", "league", "cl", "el", "wc"
FORMATS = (FMT_CLASSIC, FMT_LEAGUE, FMT_CL, FMT_EL, FMT_WC)
SINGLE_TABLE = (FMT_LEAGUE, FMT_CL, FMT_EL)      # guruhsiz yagona jadval
TABLE_LABEL = "L"                                # yagona jadval "guruh" nomi (pt_members.group_label)
SWISS_ROUNDS = 8                                 # ChL/YeL: rasmiy kabi 8 tur (kam kishida n-1)
LEGS_ALLOWED = (1, 2)

# (min, max, qadam) — liga uchun sig'im ligadagi klublar soni (alohida)
_SIZE_RULES = {FMT_CLASSIC: (8, 128, 4), FMT_WC: (8, 48, 4), FMT_CL: (8, 36, 2), FMT_EL: (8, 36, 2)}

LEAGUE_CLUBS: dict[str, tuple[str, ...]] = {
    "LaLiga": (
        "Almería", "Athletic Club", "Atlético Madrid", "Barcelona",
        "Betis", "Cádiz", "Celta Vigo", "Getafe",
        "Girona", "Granada", "Las Palmas", "Mallorca",
        "Osasuna", "Rayo Vallecano", "Real Madrid", "Real Sociedad",
        "Sevilla", "Valencia", "Valladolid", "Villarreal",
    ),
    "Premier Liga": (
        "Arsenal", "Aston Villa", "Bournemouth", "Brentford",
        "Brighton", "Burnley", "Chelsea", "Crystal Palace",
        "Everton", "Fulham", "Liverpool", "Luton Town",
        "Man City", "Man United", "Newcastle", "Nottm Forest",
        "Sheffield Utd", "Tottenham", "West Ham", "Wolves",
    ),
    "Bundesliga": (
        "Augsburg", "Bayer Leverkusen", "Bayern München", "Bochum",
        "Borussia Dortmund", "Darmstadt", "Eintracht Frankfurt", "Freiburg",
        "Gladbach", "Heidenheim", "Hoffenheim", "Köln",
        "Mainz 05", "RB Leipzig", "Stuttgart", "Union Berlin",
        "Werder Bremen", "Wolfsburg",
    ),
    "Serie A": (
        "Atalanta", "Bologna", "Cagliari", "Empoli",
        "Fiorentina", "Frosinone", "Genoa", "Inter",
        "Juventus", "Lazio", "Lecce", "Milan",
        "Monza", "Napoli", "Roma", "Salernitana",
        "Sassuolo", "Torino", "Udinese", "Verona",
    ),
    "Ligue 1": (
        "Angers", "Auxerre", "Brest", "Le Havre",
        "Lens", "Lille", "Lorient", "Lyon",
        "Marseille", "Metz", "Monaco", "Nantes",
        "Nice", "Paris FC", "Paris SG", "Rennes",
        "Strasbourg", "Toulouse",
    ),
}

WC_TEAMS: tuple[str, ...] = tuple(team for teams in WC_GROUPS.values() for team in teams)
ALL_CLUBS: tuple[str, ...] = tuple(c for cl in LEAGUE_CLUBS.values() for c in cl)


def valid_format(fmt) -> bool:
    return fmt in FORMATS


def uses_teams(fmt: str) -> bool:
    return fmt != FMT_CLASSIC


def is_single_table(fmt: str) -> bool:
    return fmt in SINGLE_TABLE


def size_rule(fmt: str, league: str | None = None) -> tuple[int, int, int]:
    if fmt == FMT_LEAGUE:
        n = len(LEAGUE_CLUBS.get(league or "", ()))
        return n, n, 1
    return _SIZE_RULES.get(fmt, _SIZE_RULES[FMT_CLASSIC])


def valid_size_for(fmt: str, n, league: str | None = None) -> bool:
    if isinstance(n, bool) or not isinstance(n, int):
        return False
    lo, hi, step = size_rule(fmt, league)
    return lo > 0 and lo <= n <= hi and (n - lo) % step == 0


def teams_for(fmt: str, league: str | None = None) -> tuple[str, ...]:
    if fmt == FMT_LEAGUE:
        return LEAGUE_CLUBS.get(league or "", ())
    if fmt in (FMT_CL, FMT_EL):
        return ALL_CLUBS
    if fmt == FMT_WC:
        return WC_TEAMS
    return ()


def can_start_fmt(fmt: str, n: int, max_players: int) -> str | None:
    """Boshlash to'sig'i (jamoa tekshiruvi alohida): None — mumkin."""
    if fmt == FMT_LEAGUE:
        return None if n == max_players else "league_not_full"
    lo = size_rule(fmt)[0]
    if n < lo:
        return "not_enough_players"
    if fmt in (FMT_CL, FMT_EL):
        return None if n % 2 == 0 else "not_even"
    return None if n % 4 == 0 else "not_multiple"


def swiss_rounds(n: int) -> int:
    return min(SWISS_ROUNDS, n - 1)


def cl_direct_count(n: int) -> int:
    """ChL/YeL: to'g'ridan setkaga chiqadiganlar (Q). Pley-off raundi Q+1..3Q, setka 2Q."""
    for q in (8, 4, 2):
        if 3 * q <= n:
            return q
    return 2


def public_formats() -> dict:
    """/pt/config uchun: formatlar sig'im qoidalari va ligalar (klublar soni)."""
    return {"formats": {f: dict(zip(("min", "max", "step"), size_rule(f))) for f in FORMATS if f != FMT_LEAGUE},
            "leagues": {name: len(c) for name, c in LEAGUE_CLUBS.items()},
            "legs": list(LEGS_ALLOWED)}
