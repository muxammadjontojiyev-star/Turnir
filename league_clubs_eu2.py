"""
league_clubs_eu2.py — 6 ta YANGI YEVROPA LIGASI klublari (2026-11-01, 2026/27 tarkibi).
Nomlar static/league_clubs_eu2.js bilan AYNAN bir xil (qoida #11). pt_formats.LEAGUE_CLUBS ga qo'shiladi
(auksion klub tekshiruvi, shaxsiy turnirlar). Liga sozlamalari — leagues_region.py, kvotalar — cl_qualification.
"""

NEW_EU_CLUBS: dict[str, tuple[str, ...]] = {
    "RPL": (
        "Akhmat", "Akron", "Baltika", "CSKA", "Dinamo Makhachkala", "Dinamo Moskva", "Fakel", "Krasnodar",
        "Krylia Sovetov", "Lokomotiv Moskva", "Orenburg", "Rodina", "Rostov", "Rubin", "Spartak", "Zenit",
    ),
    "Eredivisie": (
        "ADO Den Haag", "Ajax", "AZ", "Cambuur", "Excelsior", "Feyenoord", "Fortuna Sittard", "Go Ahead Eagles",
        "Groningen", "Heerenveen", "NEC", "PEC Zwolle", "PSV", "Sparta Rotterdam", "Telstar", "Twente",
        "Utrecht", "Willem II",
    ),
    "Jupiler Pro League": (
        "Anderlecht", "Antwerp", "Beveren", "Cercle Brugge", "Charleroi", "Club Brugge", "Genk", "Gent",
        "Kortrijk", "La Louvière", "Lommel", "Mechelen", "OH Leuven", "Sint-Truiden", "Standard Liège",
        "Union SG", "Westerlo", "Zulte Waregem",
    ),
    "Chance Liga": (
        "Baník Ostrava", "Bohemians 1905", "Hradec Králové", "Jablonec", "Líšeň", "Mladá Boleslav", "Pardubice",
        "Sigma Olomouc", "Slavia Praha", "Slovácko", "Slovan Liberec", "Sparta Praha", "Teplice",
        "Viktoria Plzeň", "Zbrojovka Brno", "Zlín",
    ),
    "Eliteserien": (
        "Aalesund", "Bodø/Glimt", "Brann", "Fredrikstad", "HamKam", "IK Start", "KFUM Oslo", "Kristiansund",
        "Lillestrøm", "Molde", "Rosenborg", "Sandefjord", "Sarpsborg 08", "Tromsø", "Viking", "Vålerenga",
    ),
    "Greek Super League": (
        "AEK Athens", "Aris", "Asteras Tripolis", "Atromitos", "Iraklis", "Kalamata", "Kifisia", "Levadiakos",
        "OFI", "Olympiacos", "Panathinaikos", "Panetolikos", "PAOK", "Volos",
    ),
    # 2026-11-02: Janubiy Amerika — Braziliya Seriya A (2026 mavsumi)
    "Brasileirão": (
        "Athletico Paranaense", "Atlético Mineiro", "Bahia", "Botafogo", "Chapecoense", "Corinthians", "Coritiba", "Cruzeiro", "Flamengo", "Fluminense", "Grêmio", "Internacional", "Mirassol", "Palmeiras", "RB Bragantino", "Remo", "Santos", "São Paulo", "Vasco da Gama", "Vitória",
    ),
}
