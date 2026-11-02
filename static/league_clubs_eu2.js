// =============================================================
//  league_clubs_eu2.js — 6 ta YANGI YEVROPA LIGASI klublari (2026-11-01)
//  Rossiya (RPL), Niderlandiya (Eredivisie), Belgiya (Jupiler Pro League), Chexiya (Chance Liga),
//  Norvegiya (Eliteserien), Gretsiya (Greek Super League) — 2026/27 mavsumi tarkibi.
//  Nomlar backend league_clubs_eu2.py bilan AYNAN bir xil (qoida #11).
//  Logolar — RASMIY klub logolari, FotMob CDN (team ID — FotMob liga jadvallaridan, 2026/27), liga logolari ham
//  FotMob (Liga Portugal, Süper Lig va boshqalar bilan bir xil manba). (2026-11-01 birinchi versiyada —
//  vaqtinchalik qisqartmali qalqonlar edi.)
//  api.js dagi LEAGUE_CLUBS / LEAGUE_LOGOS / LEAGUE_TROPHIES ga qo'shiladi — index.html da api.js dan KEYIN ulanadi.
// =============================================================

(function () {
  const TEAM_LOGO = "https://images.fotmob.com/image_resources/logo/teamlogo/";
  const LEAGUE_LOGO = "https://images.fotmob.com/image_resources/logo/leaguelogo/";
  // [nom, FotMob team ID]
  const CLUBS = {
    "RPL": [["Akhmat", 8708], ["Akron", 1068364], ["Baltika", 49694], ["CSKA", 9760], ["Dinamo Makhachkala", 1068353], ["Dinamo Moskva", 9763], ["Fakel", 1692], ["Krasnodar", 168719], ["Krylia Sovetov", 8709], ["Lokomotiv Moskva", 8710], ["Orenburg", 132286], ["Rodina", 1066681], ["Rostov", 8705], ["Rubin", 8683], ["Spartak", 8643], ["Zenit", 8698]],
    "Eredivisie": [["ADO Den Haag", 10217], ["Ajax", 8593], ["AZ", 10229], ["Cambuur", 7788], ["Excelsior", 10218], ["Feyenoord", 10235], ["Fortuna Sittard", 6422], ["Go Ahead Eagles", 6433], ["Groningen", 8674], ["Heerenveen", 10228], ["NEC", 8464], ["PEC Zwolle", 6413], ["PSV", 8640], ["Sparta Rotterdam", 8614], ["Telstar", 6414], ["Twente", 8611], ["Utrecht", 9908], ["Willem II", 8525]],
    "Jupiler Pro League": [["Anderlecht", 8635], ["Antwerp", 9988], ["Beveren", 8475], ["Cercle Brugge", 9984], ["Charleroi", 9986], ["Club Brugge", 8342], ["Genk", 9987], ["Gent", 9991], ["Kortrijk", 8571], ["La Louvière", 1218969], ["Lommel", 6702], ["Mechelen", 8203], ["OH Leuven", 1773], ["Sint-Truiden", 9997], ["Standard Liège", 9985], ["Union SG", 7978], ["Westerlo", 10001], ["Zulte Waregem", 10000]],
    "Chance Liga": [["Baník Ostrava", 6362], ["Bohemians 1905", 1670], ["Hradec Králové", 1712], ["Jablonec", 7758], ["Líšeň", 106189], ["Mladá Boleslav", 10180], ["Pardubice", 2406], ["Sigma Olomouc", 6461], ["Slavia Praha", 7787], ["Slovácko", 2021], ["Slovan Liberec", 10245], ["Sparta Praha", 10247], ["Teplice", 4721], ["Viktoria Plzeň", 6033], ["Zbrojovka Brno", 1673], ["Zlín", 1860]],
    "Eliteserien": [["Aalesund", 8404], ["Bodø/Glimt", 8402], ["Brann", 8468], ["Fredrikstad", 8417], ["HamKam", 8448], ["IK Start", 9919], ["KFUM Oslo", 2305], ["Kristiansund", 8605], ["Lillestrøm", 8476], ["Molde", 9917], ["Rosenborg", 8422], ["Sandefjord", 8609], ["Sarpsborg 08", 8509], ["Tromsø", 8608], ["Viking", 8478], ["Vålerenga", 8007]],
    "Greek Super League": [["AEK Athens", 8563], ["Aris", 8239], ["Asteras Tripolis", 80654], ["Atromitos", 10187], ["Iraklis", 8675], ["Kalamata", 1585], ["Kifisia", 488099], ["Levadiakos", 4493], ["OFI", 7753], ["Olympiacos", 8638], ["Panathinaikos", 10200], ["Panetolikos", 162386], ["PAOK", 8619], ["Volos", 885256]],
    // 2026-11-02: Janubiy Amerika — Braziliya Seriya A (2026 mavsumi, FotMob jadvalidan)
    "Brasileirão": [["Athletico Paranaense", 10273], ["Atlético Mineiro", 10272], ["Bahia", 7877], ["Botafogo", 8517], ["Chapecoense", 197693], ["Corinthians", 9808], ["Coritiba", 9767], ["Cruzeiro", 9781], ["Flamengo", 9770], ["Fluminense", 9863], ["Grêmio", 9769], ["Internacional", 8702], ["Mirassol", 163782], ["Palmeiras", 10283], ["RB Bragantino", 109705], ["Remo", 1626], ["Santos", 8514], ["São Paulo", 10277], ["Vasco da Gama", 10276], ["Vitória", 7733]],
    // 2026-11-02: Kolumbiya Primera A (2026 mavsumi, FotMob jadvalidan)
    "Primera A": [["Águilas Doradas", 193025], ["Alianza", 193029], ["América de Cali", 10280], ["Atlético Nacional", 6368], ["Boyacá Chicó", 6255], ["Bucaramanga", 4401], ["Cúcuta Deportivo", 6254], ["Deportivo Cali", 6387], ["Deportivo Pasto", 4405], ["Deportivo Pereira", 4404], ["Fortaleza", 244167], ["Independiente Medellín", 2528], ["Internacional de Bogotá", 47240], ["Jaguares de Córdoba", 424270], ["Junior", 2254], ["Llaneros", 348397], ["Millonarios", 4403], ["Once Caldas", 6024], ["Santa Fe", 7818], ["Tolima", 1894]],
    // 2026-11-02: Shimoliy Amerika — MLS (2026 mavsumi, 30 klub, FotMob jadvalidan)
    "MLS": [["Atlanta United", 773958], ["Austin FC", 1218886], ["CF Montréal", 161195], ["Charlotte FC", 1323940], ["Chicago Fire", 6397], ["Colorado Rapids", 8314], ["Columbus Crew", 6001], ["DC United", 6602], ["FC Cincinnati", 722265], ["FC Dallas", 6399], ["Houston Dynamo", 8259], ["Inter Miami", 960720], ["LA Galaxy", 6637], ["Los Angeles FC", 867280], ["Minnesota United", 207242], ["Nashville SC", 915807], ["New England Revolution", 6580], ["New York City FC", 546238], ["New York Red Bulls", 6514], ["Orlando City", 267810], ["Philadelphia Union", 191716], ["Portland Timbers", 307690], ["Real Salt Lake", 6606], ["San Diego FC", 1701119], ["San Jose Earthquakes", 6603], ["Seattle Sounders", 130394], ["Sporting Kansas City", 6604], ["St. Louis City", 1427963], ["Toronto FC", 56453], ["Vancouver Whitecaps", 307691]],
  };
  const LOGOS = {   // FotMob liga ID'lari
    "RPL": 63, "Eredivisie": 57, "Jupiler Pro League": 40, "Chance Liga": 122, "Eliteserien": 59,
    "Greek Super League": 135, "Brasileirão": 268, "Primera A": 274, "MLS": 130,
  };

  if (typeof LEAGUE_CLUBS === "undefined") return;
  Object.entries(CLUBS).forEach(([league, list]) => {
    LEAGUE_CLUBS[league] = list.map(([name, id]) => ({ name, logo: `${TEAM_LOGO}${id}.png` }));
  });
  // 2026-11-01: liga kuboklari (egasi yuborgan rasmlar, shaffof fonli PNG — static/images/)
  const TROPHIES = {
    "RPL": "images/rpl-trophy.png", "Eredivisie": "images/eredivisie-trophy.png",
    "Jupiler Pro League": "images/jupiler-trophy.png", "Chance Liga": "images/chance-trophy.png",
    "Eliteserien": "images/eliteserien-trophy.png", "Greek Super League": "images/greek-trophy.png",
  };
  if (typeof LEAGUE_TROPHIES !== "undefined") Object.assign(LEAGUE_TROPHIES, TROPHIES);
  if (typeof LEAGUE_LOGOS !== "undefined") {
    Object.entries(LOGOS).forEach(([league, id]) => { LEAGUE_LOGOS[league] = `${LEAGUE_LOGO}${id}.png`; });
  }
})();
