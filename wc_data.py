"""
wc_data.py — Jahon Chempionati (World Cup) guruh va jamoa ma'lumoti.

48 terma jamoa, 12 guruh (A–L), har guruhda 4 jamoa.
Frontend (static/worldcup.js) dagi WC_GROUPS bilan AYNAN mos bo'lishi shart
(jamoa nomlari band qilish va tekshirishda kalit sifatida ishlatiladi).

Bu fayl faqat statik ma'lumot — DB emas. Markazlashtirilgan (qoida #17),
shuning uchun jamoa/guruh ro'yxati faqat shu yerda va worldcup.js da turadi.
"""

# Guruh harfi -> shu guruhdagi 4 jamoa nomi (alifbo emas, rasmdagi tartib)
WC_GROUPS = {
    "A": ["Mexico", "South Africa", "South Korea", "Czech Republic"],
    "B": ["Canada", "Bosnia", "Qatar", "Switzerland"],
    "C": ["Brazil", "Morocco", "Haiti", "Scotland"],
    "D": ["USA", "Paraguay", "Australia", "Turkey"],
    "E": ["Germany", "Curacao", "Ivory Coast", "Ecuador"],
    "F": ["Netherlands", "Japan", "Sweden", "Tunisia"],
    "G": ["Belgium", "Egypt", "Iran", "New Zealand"],
    "H": ["Spain", "Cape Verde", "Saudi Arabia", "Uruguay"],
    "I": ["France", "Senegal", "Iraq", "Norway"],
    "J": ["Argentina", "Algeria", "Austria", "Jordan"],
    "K": ["Portugal", "DR Congo", "Uzbekistan", "Colombia"],
    "L": ["England", "Croatia", "Ghana", "Panama"],
}

# Guruh harflari ro'yxati (tartibda)
WC_GROUP_LETTERS = list(WC_GROUPS.keys())

# Har guruhda nechta jamoa (= ishtirokchi) bo'lishi mumkin
WC_TEAMS_PER_GROUP = 4


def wc_is_valid_group(letter: str) -> bool:
    """Berilgan harf haqiqiy guruhmi (A–L)."""
    return letter in WC_GROUPS


def wc_group_teams(letter: str) -> list[str]:
    """Guruhdagi 4 jamoa nomini qaytaradi (yoki bo'sh ro'yxat)."""
    return WC_GROUPS.get(letter, [])


def wc_team_in_group(letter: str, team_name: str) -> bool:
    """team_name shu guruhga tegishlimi (band qilishni tekshirish uchun)."""
    return team_name in WC_GROUPS.get(letter, [])
