"""
pt_formats.py — SHAXSIY turnir formatlari (2026-10-07).

Admin qarorlari:
  - classic : erkin — 4 kishilik guruhlar + pley-off, 8..128 (4 ga karrali), jamoa tanlanmaydi
              (2026-10-07 gacha yaratilgan barcha turnirlar shu format).
  - league  : rasmiy ligalar kabi — BIR YOKI BIR NECHTA liga tanlanadi (LaLiga, Premier Liga, ...;
              league_name = "Premier Liga|LaLiga"), ishtirokchilar soni DOIM tanlangan ligalardagi klublar
              yig'indisi, har kim bitta klub tanlaydi va o'sha liga jadvalida o'ynaydi (har liga — alohida
              jadval va chempion). Har kim har kim bilan 1 yoki 2 doira (tashkilotchi tanlaydi).
              Oxirgi tur yopilgach — har liga jadvali birinchisi chempion (pley-off yo'q).
              Narx: 1 liga narxi + har qo'shimcha liga uchun PT_PRICE_EXTRA_LEAGUE_UZS (bir martalikda).
  - classic : 2026-10-07 — 1 yoki 2 doira: 2 doirada guruh uy+mehmon, pley-off ikki o'yin yig'indisi
              (final — 1 o'yin).
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
SINGLE_TABLE = (FMT_LEAGUE, FMT_CL, FMT_EL)      # guruhsiz jadval (liga: har liga — o'z jadvali)
TABLE_LABEL = "L"                                # yagona jadval "guruh" nomi (pt_members.group_label)
SWISS_ROUNDS = 8                                 # ChL/YeL: rasmiy kabi 8 tur (kam kishida n-1)
LEGS_ALLOWED = (1, 2)
LEGS_FORMATS = ("league", "classic")             # 2 doira (javob o'yini) mumkin bo'lgan formatlar

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
    # 2026-10-09: rasmiy ligalarga qo'shilgan 3 liga (api.js LEAGUE_CLUBS bilan sinxron)
    "Liga Portugal": (
        "Académico Viseu", "Alverca", "Arouca", "Benfica",
        "Braga", "Casa Pia", "Estoril", "Estrela Amadora",
        "Famalicão", "Gil Vicente", "Marítimo", "Moreirense",
        "Nacional", "Porto", "Rio Ave", "Santa Clara",
        "Sporting CP", "Vitória SC",
    ),
    "Süper Lig": (
        "Alanyaspor", "Amedspor", "Başakşehir", "Beşiktaş",
        "Çorum", "Erzurumspor", "Eyüpspor", "Fenerbahçe",
        "Galatasaray", "Gaziantep", "Gençlerbirliği", "Göztepe",
        "Kasımpaşa", "Kocaelispor", "Konyaspor", "Rizespor",
        "Samsunspor", "Trabzonspor",
    ),
    "Superliga": (
        "Andijon", "Bunyodkor", "Buxoro", "Dinamo Samarqand",
        "Lokomotiv", "Mash'al", "Nasaf", "Navbahor",
        "Neftchi", "OKMK", "Paxtakor", "Qizilqum",
        "Qo'qon-1912", "So'g'diyona", "Surxon", "Xorazm",
    ),
    "Saudi Pro Liga": (
        "Abha", "Al-Ahli", "Al-Diriyah", "Al-Ettifaq",
        "Al-Faisaly", "Al-Fateh", "Al-Fayha", "Al-Hazem",
        "Al-Hilal", "Al-Ittihad", "Al-Khaleej", "Al-Kholood",
        "Al-Nassr", "Al-Qadsiah", "Al-Riyadh", "Al-Shabab",
        "Al-Taawoun", "Neom",
    ),
    "UAE Pro Liga": (
        "Ajman", "Al-Ain", "Al-Dhafra", "Al-Jazira",
        "Al-Nasr", "Al-Wahda", "Al-Wasl", "Baniyas",
        "Hatta", "Kalba", "Khor Fakkan", "Shabab Al-Ahli",
        "Sharjah", "United FC",
    ),
    "J1 Liga": (
        "Avispa Fukuoka", "Cerezo Osaka", "FC Tokyo", "Fagiano Okayama",
        "Gamba Osaka", "JEF United Chiba", "Kashima Antlers", "Kashiwa Reysol",
        "Kawasaki Frontale", "Kyoto Sanga", "Machida Zelvia", "Mito HollyHock",
        "Nagoya Grampus", "Sanfrecce Hiroshima", "Shimizu S-Pulse", "Tokyo Verdy",
        "Urawa Reds", "V-Varen Nagasaki", "Vissel Kobe", "Yokohama F. Marinos",
    ),
    "LaLiga 2": (
        "Albacete", "Andorra", "Burgos", "Castellón",
        "Celta Fortuna", "Ceuta", "Córdoba", "Cultural Leonesa",
        "Deportivo", "Eibar", "Eldense", "Huesca",
        "Leganés", "Málaga", "Mirandés", "Oviedo",
        "Racing Santander", "Real Sociedad B", "Sabadell", "Sporting Gijón",
        "Tenerife", "Zaragoza",
    ),
    "Championship": (
        "Birmingham", "Blackburn", "Bolton", "Bristol City",
        "Cardiff", "Charlton", "Coventry", "Derby",
        "Hull City", "Ipswich", "Leicester", "Lincoln City",
        "Middlesbrough", "Millwall", "Norwich", "Portsmouth",
        "Preston", "QPR", "Southampton", "Stoke City",
        "Swansea", "Watford", "West Brom", "Wrexham",
    ),
}

WC_TEAMS: tuple[str, ...] = tuple(team for teams in WC_GROUPS.values() for team in teams)
ALL_CLUBS: tuple[str, ...] = tuple(c for cl in LEAGUE_CLUBS.values() for c in cl)


LEAGUE_SEP = "|"                                 # ko'p liga: league_name = "Premier Liga|LaLiga"


def split_leagues(value) -> list[str]:
    """league_name (yoki ro'yxat) -> takrorsiz ligalar ro'yxati (tanlash tartibida)."""
    items = value if isinstance(value, (list, tuple)) else str(value or "").split(LEAGUE_SEP)
    out = []
    for x in items:
        x = str(x or "").strip()
        if x and x not in out:
            out.append(x)
    return out


def join_leagues(leagues) -> str | None:
    lst = split_leagues(leagues)
    return LEAGUE_SEP.join(lst) if lst else None


def valid_leagues(value) -> bool:
    lst = split_leagues(value)
    return bool(lst) and all(lg in LEAGUE_CLUBS for lg in lst)


def club_league(team: str, league: str | None) -> str | None:
    """Klub qaysi (tanlangan) ligaga tegishli."""
    return next((lg for lg in split_leagues(league) if team in LEAGUE_CLUBS.get(lg, ())), None)


def valid_format(fmt) -> bool:
    return fmt in FORMATS


def uses_teams(fmt: str) -> bool:
    return fmt != FMT_CLASSIC


def is_single_table(fmt: str) -> bool:
    return fmt in SINGLE_TABLE


def size_rule(fmt: str, league: str | None = None) -> tuple[int, int, int]:
    if fmt == FMT_LEAGUE:                         # ko'p liga — klublar yig'indisi (har liga to'liq)
        n = sum(len(LEAGUE_CLUBS.get(lg, ())) for lg in split_leagues(league))
        return n, n, 1
    return _SIZE_RULES.get(fmt, _SIZE_RULES[FMT_CLASSIC])


def valid_size_for(fmt: str, n, league: str | None = None) -> bool:
    if isinstance(n, bool) or not isinstance(n, int):
        return False
    lo, hi, step = size_rule(fmt, league)
    return lo > 0 and lo <= n <= hi and (n - lo) % step == 0


def teams_for(fmt: str, league: str | None = None) -> tuple[str, ...]:
    if fmt == FMT_LEAGUE:
        return tuple(c for lg in split_leagues(league) for c in LEAGUE_CLUBS.get(lg, ()))
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
            "legs": list(LEGS_ALLOWED), "legs_formats": list(LEGS_FORMATS)}
