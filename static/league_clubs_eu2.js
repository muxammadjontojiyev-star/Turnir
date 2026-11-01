// =============================================================
//  league_clubs_eu2.js — 6 ta YANGI YEVROPA LIGASI klublari (2026-11-01)
//  Rossiya (RPL), Niderlandiya (Eredivisie), Belgiya (Jupiler Pro League), Chexiya (Chance Liga),
//  Norvegiya (Eliteserien), Gretsiya (Greek Super League) — 2026/27 mavsumi tarkibi.
//  Nomlar backend league_clubs_eu2.py bilan AYNAN bir xil (qoida #11).
//  Logo: rasmiy rasm o'rniga klub ranglarida qisqartmali qalqon (SVG, data: URI) — tashqi
//  so'rovsiz, hamma joyda (ro'yxat, reyting, profil, ChL/YeL) ishlaydi; rasmiy logo qo'shilsa
//  logo maydoni almashtiriladi. Liga logolari — FotMob CDN.
//  api.js dagi LEAGUE_CLUBS / LEAGUE_LOGOS ga qo'shiladi — index.html da api.js dan KEYIN ulanadi.
// =============================================================

(function () {
  // [nom, qisqartma, asosiy rang, ikkinchi rang]
  const CLUBS = {
    "RPL": [
      ["Akhmat", "AKH", "#00843D", "#ffffff"], ["Akron", "AKR", "#1A3C8F", "#ffffff"],
      ["Baltika", "BAL", "#004B8D", "#ffffff"], ["CSKA", "CSKA", "#C8102E", "#003DA5"],
      ["Dinamo Makhachkala", "DMK", "#0033A0", "#ffffff"], ["Dinamo Moskva", "DIN", "#0033A0", "#ffffff"],
      ["Fakel", "FAK", "#0057B8", "#ffffff"], ["Krasnodar", "KRA", "#111111", "#00843D"],
      ["Krylia Sovetov", "KS", "#0050A0", "#ffffff"], ["Lokomotiv Moskva", "LOK", "#D2122E", "#00843D"],
      ["Orenburg", "ORE", "#1E3F8F", "#ffffff"], ["Rodina", "ROD", "#C8102E", "#ffffff"],
      ["Rostov", "ROS", "#FFD100", "#002D72"], ["Rubin", "RUB", "#7A0019", "#00843D"],
      ["Spartak", "SPA", "#D50032", "#ffffff"], ["Zenit", "ZEN", "#0072CE", "#ffffff"],
    ],
    "Eredivisie": [
      ["ADO Den Haag", "ADO", "#00843D", "#FFD100"], ["Ajax", "AJX", "#D2122E", "#ffffff"],
      ["AZ", "AZ", "#E30613", "#ffffff"], ["Cambuur", "CAM", "#FFD100", "#0057B8"],
      ["Excelsior", "EXC", "#E30613", "#111111"], ["Feyenoord", "FEY", "#E30613", "#ffffff"],
      ["Fortuna Sittard", "FOR", "#FFD100", "#00843D"], ["Go Ahead Eagles", "GAE", "#E30613", "#FFD100"],
      ["Groningen", "GRO", "#00843D", "#ffffff"], ["Heerenveen", "HEE", "#0057B8", "#ffffff"],
      ["NEC", "NEC", "#E30613", "#00843D"], ["PEC Zwolle", "PEC", "#0057B8", "#ffffff"],
      ["PSV", "PSV", "#E30613", "#ffffff"], ["Sparta Rotterdam", "SPR", "#E30613", "#ffffff"],
      ["Telstar", "TEL", "#ffffff", "#111111"], ["Twente", "TWE", "#E30613", "#ffffff"],
      ["Utrecht", "UTR", "#E30613", "#ffffff"], ["Willem II", "WII", "#E30613", "#0057B8"],
    ],
    "Jupiler Pro League": [
      ["Anderlecht", "AND", "#4B2683", "#ffffff"], ["Antwerp", "ANT", "#E30613", "#ffffff"],
      ["Beveren", "BEV", "#FFD100", "#0057B8"], ["Cercle Brugge", "CER", "#00843D", "#111111"],
      ["Charleroi", "CHA", "#111111", "#ffffff"], ["Club Brugge", "CLB", "#0057B8", "#111111"],
      ["Genk", "GNK", "#0057B8", "#ffffff"], ["Gent", "GNT", "#0057B8", "#ffffff"],
      ["Kortrijk", "KOR", "#E30613", "#ffffff"], ["La Louvière", "RAAL", "#00843D", "#ffffff"],
      ["Lommel", "LOM", "#00843D", "#111111"], ["Mechelen", "KVM", "#E30613", "#FFD100"],
      ["OH Leuven", "OHL", "#00843D", "#ffffff"], ["Sint-Truiden", "STV", "#FFD100", "#0057B8"],
      ["Standard Liège", "STA", "#E30613", "#ffffff"], ["Union SG", "USG", "#FFD100", "#0057B8"],
      ["Westerlo", "WES", "#FFD100", "#0057B8"], ["Zulte Waregem", "ZWA", "#E30613", "#00843D"],
    ],
    "Chance Liga": [
      ["Baník Ostrava", "BAN", "#0057B8", "#ffffff"], ["Bohemians 1905", "BOH", "#00843D", "#ffffff"],
      ["Hradec Králové", "HRK", "#111111", "#ffffff"], ["Jablonec", "JAB", "#00843D", "#111111"],
      ["Líšeň", "LIS", "#111111", "#ffffff"], ["Mladá Boleslav", "MBO", "#0057B8", "#ffffff"],
      ["Pardubice", "PAR", "#E30613", "#ffffff"], ["Sigma Olomouc", "SIG", "#0057B8", "#ffffff"],
      ["Slavia Praha", "SLA", "#E30613", "#ffffff"], ["Slovácko", "SLO", "#0057B8", "#ffffff"],
      ["Slovan Liberec", "LIB", "#0057B8", "#ffffff"], ["Sparta Praha", "SPP", "#7A0019", "#FFD100"],
      ["Teplice", "TEP", "#FFD100", "#0057B8"], ["Viktoria Plzeň", "VPL", "#E30613", "#0057B8"],
      ["Zbrojovka Brno", "ZBR", "#E30613", "#ffffff"], ["Zlín", "ZLN", "#FFD100", "#0057B8"],
    ],
    "Eliteserien": [
      ["Aalesund", "AFK", "#F28C00", "#0057B8"], ["Bodø/Glimt", "B/G", "#FFD100", "#111111"],
      ["Brann", "BRA", "#E30613", "#ffffff"], ["Fredrikstad", "FFK", "#E30613", "#ffffff"],
      ["HamKam", "HAM", "#00843D", "#ffffff"], ["IK Start", "IKS", "#FFD100", "#111111"],
      ["KFUM Oslo", "KFUM", "#0057B8", "#ffffff"], ["Kristiansund", "KBK", "#0057B8", "#ffffff"],
      ["Lillestrøm", "LSK", "#FFD100", "#111111"], ["Molde", "MOL", "#0057B8", "#ffffff"],
      ["Rosenborg", "RBK", "#111111", "#ffffff"], ["Sandefjord", "SAN", "#0057B8", "#ffffff"],
      ["Sarpsborg 08", "S08", "#0057B8", "#ffffff"], ["Tromsø", "TIL", "#E30613", "#ffffff"],
      ["Viking", "VIK", "#0057B8", "#ffffff"], ["Vålerenga", "VIF", "#0057B8", "#E30613"],
    ],
    "Greek Super League": [
      ["AEK Athens", "AEK", "#FFD100", "#111111"], ["Aris", "ARI", "#FFD100", "#111111"],
      ["Asteras Tripolis", "AST", "#FFD100", "#0057B8"], ["Atromitos", "ATR", "#0057B8", "#ffffff"],
      ["Iraklis", "IRA", "#0057B8", "#ffffff"], ["Kalamata", "KAL", "#111111", "#ffffff"],
      ["Kifisia", "KIF", "#0057B8", "#ffffff"], ["Levadiakos", "LEV", "#00843D", "#ffffff"],
      ["OFI", "OFI", "#111111", "#ffffff"], ["Olympiacos", "OLY", "#E30613", "#ffffff"],
      ["Panathinaikos", "PAO", "#00843D", "#ffffff"], ["Panetolikos", "PNE", "#FFD100", "#0057B8"],
      ["PAOK", "PAOK", "#111111", "#ffffff"], ["Volos", "VOL", "#0057B8", "#E30613"],
    ],
  };
  const LOGOS = {   // FotMob liga ID'lari
    "RPL": 63, "Eredivisie": 57, "Jupiler Pro League": 40, "Chance Liga": 122, "Eliteserien": 59,
    "Greek Super League": 135,
  };
  const LIGHT = new Set(["#ffffff", "#FFD100", "#F28C00"]);

  function badge(abbr, main, second) {
    const ink = LIGHT.has(main) ? "#111111" : "#ffffff";
    const size = abbr.length > 3 ? 15 : 19;
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">`
      + `<path d="M32 3 L57 11 V30 C57 46 46 56 32 61 C18 56 7 46 7 30 V11 Z" fill="${main}" stroke="${second}" stroke-width="3"/>`
      + `<path d="M12 44 H52" stroke="${second}" stroke-width="4" opacity=".85"/>`
      + `<text x="32" y="35" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-weight="800" `
      + `font-size="${size}" fill="${ink}">${abbr}</text></svg>`;
    return "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
  }

  if (typeof LEAGUE_CLUBS === "undefined") return;
  Object.entries(CLUBS).forEach(([league, list]) => {
    LEAGUE_CLUBS[league] = list.map(([name, abbr, main, second]) => ({ name, logo: badge(abbr, main, second) }));
  });
  if (typeof LEAGUE_LOGOS !== "undefined") {
    Object.entries(LOGOS).forEach(([league, id]) => {
      LEAGUE_LOGOS[league] = `https://images.fotmob.com/image_resources/logo/leaguelogo/${id}.png`;
    });
  }
})();
