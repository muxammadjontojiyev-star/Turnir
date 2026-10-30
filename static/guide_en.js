// =============================================================
//  guide_en.js — Qo'llanma matni: INGLIZCHA (guide_uz.js tarjimasi, 2026-10-25). Ko'rsatuvchi — guide.js.
//  Tuzilma va raqamlar guide_uz.js bilan bir xil bo'lishi shart.
// =============================================================

var GUIDE_I18N = window.GUIDE_I18N || {};
window.GUIDE_I18N = GUIDE_I18N;

GUIDE_I18N.en = {
  ui: {
    title: "Guide", close: "Close", back: "Back", all_sections: "All sections",
    steps: "HOW TO DO IT", tips: "GOOD TO KNOW", admin_write: "Message the admin:",
    hub_btn: "Guide", hub_btn_sub: "How the bot works — for newcomers",
    intro: "The bot runs online eFootball tournaments: you sign up, play your opponent in eFootball and enter the result here. Tables, ratings and prizes are calculated automatically. Pick a section.",
  },
  sections: [
    {
      id: "start", icon: "🚀", title: "Getting started", sub: "Channel, language and sections",
      intro: "Getting started takes a couple of minutes.",
      steps: [
        "**Join the channel** the bot asks for — the app won't open without it. News and announcements are posted there.",
        "Tap **/start** in the bot and choose a language (Uzbek, Russian, English), then the **«Enter»** button opens the app.",
        "Pick a section: **Official tournaments** (Leagues, cups, Division, World Cup), **Private tournaments** or **Team Battle**.",
        "Sign up for a tournament and watch for bot messages: your opponent, the room ID and deadlines.",
      ],
      tips: [
        "All times are **Tashkent time**.",
        "Keep bot notifications on — that's how you learn your opponent wrote or entered a result.",
        "Set a **@username** in your Telegram profile so opponents can reach you faster.",
        "Don't want to wait? ⚡ **Quick match**: no sign-up, find an opponent right now.",
      ],
    },
    {
      id: "play", icon: "🎮", title: "How a match works", sub: "Opponent, room ID, result, confirmation",
      intro: "Every match in every tournament follows the same steps.",
      steps: [
        "Find your opponent: the match card is in **«My current matches»** or the **Profile** section, and the bot sends a message too.",
        "Agree on a time in **💬 Chat**. Keep agreements in the bot chat — if there's a dispute, the messages are your evidence.",
        "Create a friendly room in eFootball and send the **room ID** with the button on the match card — it reaches your opponent instantly.",
        "Play, and take a **screenshot of the final screen**.",
        "Enter the result: **your score goes first**. Your opponent confirms or rejects it.",
        "If it's rejected, sort it out in chat. If you can't agree, contact an admin with a screenshot or video.",
      ],
      tips_title: "MATCH RULES",
      tips: [
        "Matches are **8 minutes**.",
        "Double defending is **not allowed**.",
        "Player condition must be **«Excellent»**.",
        "**No** extra time or penalties.",
        "After the deadline: an entered but unconfirmed result is **confirmed automatically**, and an unplayed match becomes a **0:0 draw**.",
      ],
    },
    {
      id: "leagues", icon: "🏆", title: "Leagues", sub: "Picking a club, rounds, points",
      intro: "Leagues are the main mode: everyone plays with one club, all in one table, and everyone plays everyone home and away.",
      steps: [
        "**Official tournaments → Leagues**. Pick an open league: leagues open in order — the next one stays locked until the previous one is full.",
        "Pick a free club. In a new season, players who **finished the last season** choose first, newcomers a bit later, and those who quit last.",
        "When the league is full, the draw is made and rounds begin: **2** new rounds open every day at **23:30**.",
        "You can enter a result **1 hour 45 minutes** after a round opens — so nobody records a score for an unplayed match in advance.",
      ],
      tips: [
        "Win — **3** points, draw — **1**, loss — **0**. If level: goal difference, then goals scored.",
        "A league usually has **20** players (LaLiga 2 — 22).",
        "Your league position decides qualification for the Champions League, Europa League and Asian Champions League.",
        "Prizes: the league trophy, the **Golden Ball** (winner) and the **Golden Boot** (top scorer). The Golden Ball and Boot are decided among **top-tier leagues** only — second-tier leagues (LaLiga 2, Championship, 2. Bundesliga, Serie B, Ligue 2, Liga Portugal 2) play for the league trophy only.",
      ],
    },
    {
      id: "cups", icon: "⭐", title: "Cups: UCL, UEL, ACL", sub: "Who plays and the format",
      intro: "When the league season ends, the best players qualify for the cups. Qualification belongs to the person — you keep your place even if you change club next season.",
      steps_title: "WHO PLAYS",
      steps: [
        "**Champions League** — places 1–5 from each of the 7 European leagues plus the best 6th place: **36** players.",
        "**Europa League** — places 6–10 from those leagues (except the 6th place that went to the UCL) plus the 2 best 11th places: **36** players.",
        "**Asian Champions League** — places 1–8 from the Superliga, Saudi Pro League, UAE Pro League and J1 League: **32** players.",
      ],
      tips_title: "FORMAT",
      tips: [
        "League phase: everyone in one table, each player meets **8** different opponents. **1** round a day, deadline **23:30**.",
        "Places **1–8** go straight to the round of 16; places **9–24** play a play-off round (9–24, 10–23 …).",
        "Then the round of 16, quarter-finals, semi-finals and the final.",
      ],
    },
    {
      id: "division", icon: "📅", title: "Division", sub: "Daily sign-up and a random opponent",
      intro: "Division is the daily mode: you sign up each day and the bot gives you a random opponent. Points add up in the season rating.",
      steps: [
        "Sign up in the Division every day between **17:00 and 20:00** (the bot reminds you at 17:00).",
        "The draw is at **20:00**: your opponent appears in Profile and in a bot message.",
        "Play and enter the result by **16:00** the next day — your opponent confirms it.",
        "A match not played in time becomes a **0:0 draw**.",
      ],
      tips: [
        "Win **+15**, draw **+10**, loss **−10** points.",
        "Everyone starts with **1500** points.",
        "With an odd number of players, one is left without an opponent and spins a **wheel**: 5, 10 or 15 points (5 if they don't spin).",
        "At the end of the season the **TOP-48** in the rating qualify for the World Cup.",
      ],
    },
    {
      id: "wc", icon: "🌍", title: "World Cup", sub: "48 national teams, groups and play-off",
      intro: "The World Cup has 48 national teams: 12 groups of 4 players.",
      steps: [
        "The right to sign up goes to the **TOP-48 of the Division season** (refreshed every season).",
        "Pick your national team — it decides your group.",
        "Group stage: **3** rounds, **1** round a day, deadline **23:30**.",
        "**32** players reach the play-off: group winners, runners-up and the **8** best third places. Then from the round of 32 to the final.",
      ],
      tips: [
        "Best third places are ranked by points, then goal difference, then goals scored.",
      ],
    },
    {
      id: "qm", icon: "⚡", title: "Quick match", sub: "Play right now",
      intro: "Quick match — no sign-up, no deadlines, play right now. It has its own rating.",
      steps: [
        "Tap the **⚡** button on the section screen or on the Leagues home page.",
        "**«Find opponent»** — you're paired instantly with another player who is searching.",
        "Within **3 minutes** create a room in eFootball and send its ID, otherwise the match is cancelled. Your opponent can send the ID too.",
        "Enter the result within **40 minutes** of the room ID. If your opponent doesn't respond in **10 minutes**, it's confirmed automatically.",
      ],
      tips: [
        "Points depend on goal difference: win **+10** plus **+2** per goal of difference (max +20), loss **−5** and **−2** per goal (max −15), draw **+3**.",
        "Starting rating is **1000**.",
        "Only **3** matches a day against the same opponent count for the rating.",
      ],
    },
    {
      id: "pt", icon: "🎟", title: "Private tournaments", sub: "Create your own tournament",
      intro: "A private tournament is one you create yourself — for friends, a group or a team.",
      steps: [
        "**Private tournaments → «+ Create a tournament»**.",
        "Pick a format: League, Champions League, Europa League, World Cup or Free format (groups of 4 + play-off).",
        "Choose the number of players. The price (if one is set) is shown in the creation screen.",
        "Send the **invite link** to your friends — whoever opens it joins the tournament.",
        "When the places are filled, tap **«Start tournament»**. The table, play-off and champion are decided automatically.",
      ],
      tips: [
        "Only the **organizer** can change the tournament rules (on the Home page).",
        "The organizer sets round deadlines, settles disputes and can appoint a helper admin.",
      ],
    },
    {
      id: "tb", icon: "🛡", title: "Team Battle", sub: "Team matches played 1v1",
      intro: "Team Battle is playing as a team: in a match between two teams the players play 1v1, and the team with more wins takes it.",
      steps: [
        "To create a team, get a **league link** from the league admin. To join a friend's team, ask the captain for the **invite link**.",
        "The captain sets the **starting lineup**; the league sets the lineup size.",
        "When a round opens (**1** round a day, deadline **23:30**), lineup players are paired 1v1 with the opposing team — your opponent is on the **«Battle»** tab.",
        "Enter the result with a **screenshot of the final screen** — results without a screenshot are not accepted.",
      ],
      tips: [
        "Points for a team match: win — **3**, draw — **1**. If level: 1v1 win difference, then goal difference.",
        "A team that can't field its lineup gets a **technical defeat**.",
        "For captains: get the invite link in **My team → «Get link»**. If you renew the link, the old one stops working.",
      ],
    },
    {
      id: "fair", icon: "⚖️", title: "Disputes and fair play", sub: "Rejecting, evidence, reports",
      intro: "To avoid disputes, do everything inside the bot.",
      steps: [
        "Agreements and room IDs — only in the **bot chat**. Private Telegram messages don't count as evidence.",
        "Take a **screenshot of the final screen** after every match.",
        "If your opponent enters a wrong result, tap **«Reject»** and sort it out in chat.",
        "If you can't agree, contact an **admin** with a screenshot or video. The responsible admins are listed on the Profile page of each mode.",
        "In Team Battle, if someone else joins instead of your opponent, don't play and tap **«🚩 Someone else played»**. The admin checks the screenshot and chat and decides: no grounds, replay or technical defeat.",
      ],
      tips: [
        "Only an admin can change a confirmed result.",
        "Respect your opponent — offensive words are filtered.",
      ],
    },
  ],
};
