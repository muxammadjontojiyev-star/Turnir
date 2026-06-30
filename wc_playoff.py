"""
World Cup play-off (chiqib ketish bosqichi) mantig'i.

32 jamoa: 12 guruh g'olibi + 12 ikkinchi o'rin + 8 ta eng yaxshi 3-o'rin.
Bracket: 1/16 -> 1/8 -> 1/4 -> 1/2 -> final + bronza.

Bu fayl FAQAT saralash (seeding) va bracket tuzilmasini hisoblaydi.
Match yaratish/oqim DB qismi queries.py'da (wc_playoff_*).
"""

from wc_data import WC_GROUP_LETTERS
from wc_rating import calculate_wc_group_rating


def wc_get_qualified_teams() -> dict:
    """
    Guruh bosqichi natijalari asosida play-off'ga chiqadigan 32 jamoani aniqlaydi.

    Qaytaradi:
      {
        "winners":     [12 ta 1-o'rin, guruh tartibida A..L],
        "runners_up":  [12 ta 2-o'rin, guruh tartibida A..L],
        "best_thirds": [8 ta eng yaxshi 3-o'rin],
        "ready": bool,          # 32 jamoa to'liq aniqlanganmi
        "reason": str,          # ready=False bo'lsa sabab
      }

    Har jamoa dict: calculate_wc_group_rating formatidagi + "group_letter".
    Eng yaxshi 3-o'rinlar: points -> goal_difference -> goals_for bo'yicha.
    """
    winners = []
    runners_up = []
    thirds = []

    for letter in WC_GROUP_LETTERS:
        rating = calculate_wc_group_rating(letter)
        # Guruhda 4 jamoa bo'lishi kerak (1,2,3,4-o'rin)
        if len(rating) < 4:
            return {
                "winners": [], "runners_up": [], "best_thirds": [],
                "ready": False,
                "reason": f"group_{letter}_incomplete",
            }
        # rating allaqachon points -> goal_diff -> ... bo'yicha saralangan
        for pos, team in enumerate(rating):
            team = dict(team)
            team["group_letter"] = letter
            if pos == 0:
                winners.append(team)
            elif pos == 1:
                runners_up.append(team)
            elif pos == 2:
                thirds.append(team)

    # Eng yaxshi 8 ta 3-o'rin: ochko -> gol farqi -> urilgan gol
    thirds.sort(
        key=lambda t: (t["points"], t["goal_difference"], t["goals_for"]),
        reverse=True,
    )
    best_thirds = thirds[:8]

    ready = len(winners) == 12 and len(runners_up) == 12 and len(best_thirds) == 8
    return {
        "winners": winners,
        "runners_up": runners_up,
        "best_thirds": best_thirds,
        "ready": ready,
        "reason": "ok" if ready else "not_enough_teams",
    }


def wc_build_r32_pairings(qualified: dict) -> list[dict]:
    """
    32 jamoani 1/16 (r32) bracketiga joylashtiradi (16 ta juftlik).

    Qoidalar:
    - 1-o'rinlar asosan 3-o'rinlarga qarshi tushadi.
    - Qolganlari aralash.
    - MUHIM: bir guruhdan chiqqan jamoalar 1/16'da uchrashmaydi.

    Qaytaradi: 16 ta juftlik ro'yxati, har biri:
      {"position": int, "team1": dict, "team2": dict}
    position 0..15 — bracketdagi tartib.

    Strategiya:
    - 8 ta 1-o'rin (eng yaxshi) 8 ta best-third bilan o'ynaydi (1-vs-3).
    - Qolgan 4 ta 1-o'rin + 12 ta 2-o'rin = 16 jamoa -> 8 juftlik (aralash).
    - Har juftlikda guruh mosligi tekshiriladi, kerak bo'lsa almashtiriladi.
    """
    winners = list(qualified["winners"])        # 12
    runners = list(qualified["runners_up"])     # 12
    thirds = list(qualified["best_thirds"])     # 8

    # 1-o'rinlarni kuch bo'yicha tartiblaymiz (ochko -> gol farqi -> gol)
    winners.sort(key=lambda t: (t["points"], t["goal_difference"], t["goals_for"]), reverse=True)

    pairs = []

    # 1-bo'lim: eng yaxshi 8 ta g'olib vs 8 ta best-third (1 vs 3)
    top_winners = winners[:8]
    rest_winners = winners[8:]   # qolgan 4 ta g'olib

    used_thirds = list(thirds)
    for w in top_winners:
        # Bu g'olib bilan boshqa guruhdan bo'lgan third topamiz
        opponent = _pick_non_same_group(w, used_thirds)
        if opponent is None:
            # Hammasi bir guruh bo'lsa (kam ehtimol) — birinchisini olamiz
            opponent = used_thirds[0]
        used_thirds.remove(opponent)
        pairs.append({"team1": w, "team2": opponent})

    # 2-bo'lim: qolgan 4 g'olib + 12 ikkinchi = 16 jamoa -> 8 juftlik
    pool = rest_winners + runners  # 16 jamoa
    # Kuch bo'yicha: yuqori yarmi pastki yarmi bilan
    pool.sort(key=lambda t: (t["points"], t["goal_difference"], t["goals_for"]), reverse=True)
    half = len(pool) // 2
    high = pool[:half]   # 8
    low = pool[half:]    # 8

    used_low = list(low)
    for h in high:
        opponent = _pick_non_same_group(h, used_low)
        if opponent is None:
            opponent = used_low[0]
        used_low.remove(opponent)
        pairs.append({"team1": h, "team2": opponent})

    # Pozitsiya raqamlari (0..15)
    result = []
    for i, p in enumerate(pairs):
        result.append({"position": i, "team1": p["team1"], "team2": p["team2"]})
    return result


def _pick_non_same_group(team: dict, candidates: list[dict]) -> dict | None:
    """
    candidates ichidan team bilan BOSHQA guruhdan bo'lgan birinchi jamoani qaytaradi.
    Topilmasa None.
    """
    for c in candidates:
        if c["group_letter"] != team["group_letter"]:
            return c
    return None


# Bracket bosqichlari tartibi va har bosqichdagi o'yinlar soni
PLAYOFF_ROUNDS = [
    ("r32", 16),   # 1/16 final — 16 o'yin
    ("r16", 8),    # 1/8 final — 8 o'yin
    ("r8", 4),     # 1/4 final — 4 o'yin
    ("r4", 2),     # 1/2 final — 2 o'yin
    ("final", 1),  # final — 1 o'yin
    ("bronze", 1), # bronza (3-o'rin) — 1 o'yin
]


def wc_playoff_start() -> dict:
    """
    Play-off'ni boshlaydi (admin tugmasi chaqiradi):
    1. Barcha 12 guruh tugaganini tekshiradi (32 jamoa ready).
    2. 32 jamoani saralaydi va 1/16 juftliklarni tuzadi.
    3. Bracketni DB'ga yozadi (barcha bosqich matchlari + bog'lanishlar).

    Qaytaradi: (success, reason, data)
      Sabablar: ok / already_started / not_ready / <group>_incomplete
    """
    import queries

    if queries.wc_playoff_is_started() or queries.wc_playoff_has_matches():
        return {"success": False, "reason": "already_started"}

    qualified = wc_get_qualified_teams()
    if not qualified["ready"]:
        return {"success": False, "reason": qualified["reason"]}

    pairings = wc_build_r32_pairings(qualified)
    result = queries.wc_playoff_build_bracket(pairings)

    return {
        "success": True,
        "reason": "ok",
        "created": result["created"],
    }
