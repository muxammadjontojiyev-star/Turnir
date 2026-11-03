// =============================================================
//  guide_bot_en.js — guide robot «Robi»: ENGLISH (translation of guide_bot_uz.js, 2026-11-03).
//  Structure and numbers — as in guide_bot_uz.js (source). Shown by guide_bot.js.
// =============================================================

var GBOT_I18N = window.GBOT_I18N || {};
window.GBOT_I18N = GBOT_I18N;

GBOT_I18N.en = {
  ui: {
    name: "Robi", role: "your guide", next: "Next ›", prev: "‹ Back", again: "🔁 From the start",
    more: "📖 Learn more", bye: "👋 Thanks, Robi!", bye_reply: "Anytime! I'm right here if you need me 😊",
    hide: "Hide", close: "Close", sound_on: "🔊", sound_off: "🔇", speak: "🗣",
  },
  hub: {
    hint: "Hi! I'm Robi 🤖 Want a quick tour of the sections? Tap me!",
    say: [
      "Hi! 👋 I'm **Robi** — your guide in this bot. There are 3 big sections here. Let me introduce them one by one!",
      "🏆 **Official tournaments** — the bot's main competitions: Leagues, Champions League, Europa League, Conference League, Asian CL, Division and the World Cup. The bot runs them itself.",
      "In official tournaments the rules are the same for everyone, there's a shared rating, and winners get trophies, prizes and 🪙 **eF Tokens**. The most serious battles are here! 💪",
      "🎟 **Private tournaments** — here **you** are the organizer! Create a closed tournament for friends or your group: you choose the format, the number of players and the deadlines.",
      "Invite friends with an **invite link** — only people with the link can join. The bot calculates the table, play-offs and champion; you just play 😉",
      "🛡 **Team battle** — you play not alone but **as a team**. Create a team or join a friend's. When two teams meet, players play 1v1, and the team with more wins takes it.",
      "In short: 🏆 **Official** — run by the bot, open to all. 🎟 **Private** — run by you, invite only. 🛡 **Teams** — team vs team.",
      "Two more secrets 🤫 The ⚡ button is **Quick match**: find an opponent right now, no waiting. And the 📖 **Guide** explains every rule in detail. Got a question? Tap me!",
    ],
  },
  modes: {
    hint: "Want to see how the modes are connected? 🔗",
    say: [
      "This is **Official tournaments** 🏆 The modes here are linked like a chain. Let me show you how! 🔗",
      "⚽ **Leagues** — everything starts here. Pick one club and play every opponent in your league home and away all season. Leagues are in 4 regions: Europe, Asia, South and North America.",
      "Your league position is a ticket to the cups 🎫 The best of the European leagues go to the **Champions League**, the next ones to the **Europa League**, and the ones after them to the **Conference League**.",
      "In the Asian leagues (Uzbekistan, Saudi Arabia, UAE, Japan) places 1–8 go to the **Asian Champions League**. The American leagues don't give cup spots yet.",
      "Spots are given **when the league season ends**. The higher you finish, the stronger the cup you'll play in! 🌟",
      "📅 **Division** — a daily mode: sign up every day, the bot gives you a random opponent, and points add up in the rating. At the end of the season the rating's **TOP-48** qualify for the **World Cup**! 🌍",
      "🌍 **World Cup** — 48 national teams: groups, then play-offs. The only way in is through the Division — so don't skip it 😉",
      "Play well in any mode and you earn trophies, prizes and 🪙 **eF Tokens**. Tokens are spent in the shop and the auction. Pick a mode — I'm inside too and will tell you about it! 🤖",
    ],
  },
  league: {
    hint: "Want me to explain the leagues? Tap! ⚽",
    say: [
      "Welcome to the Leagues! ⚽ This is the bot's main mode: you play one club for the whole season.",
      "Pick a region in the tabs above: Europe, Asia, S. and N. America. Leagues open **in order** — the next one stays locked until the previous one is full 🔒",
      "Choose a free club in an open league. When the league is full, the draw is made and rounds begin: every day at **23:30** **2** new rounds open ⏰",
      "A win is **3** points, a draw **1**. Your opponent confirms the result. Results can be entered **1 h 45 min** after a round opens.",
      "Your final position gives cup spots: from European leagues — UCL, UEL and Conference League, from Asian leagues — Asian CL. Higher place, bigger cup! 🏆",
      "There are awards too: the **Golden Ball** for the winner, the **Golden Boot** for the top scorer, and 🪙 **eF Tokens** by position (1st place — 300).",
      "One request 🙏 **finish the season**. If you leave, you get no reward, and next season you'll pick a club 24 hours after everyone else.",
    ],
  },
  cl: {
    hint: "Want to hear about the Champions League? ⭐",
    say: [
      "⭐ **Champions League** — Europe's strongest cup! The best players of the European leagues meet here: **36** in total.",
      "How to get in? By your end-of-season league position: top-5 leagues — places 1–4, the others — 1–3, 1–2 or only 1st. The spot is **yours** — you keep it even if you change clubs.",
      "First the **league phase**: everyone in one table, each plays **8** different opponents. **1** round a day, deadline **23:30**.",
      "Places **1–8** go straight to the round of 16, places **9–24** play the play-off round. Then round of 16, quarter-finals, semi-finals and the final! 🔥",
      "The further you go, the more 🪙 eF Tokens. The champion gets **500**! Good luck! 🍀",
    ],
  },
  el: {
    hint: "Want to hear about the Europa League? 🟠",
    say: [
      "🟠 **Europa League** — Europe's second cup. Those who just missed the Champions League come here: **36** in total.",
      "How to get in? The places right after the UCL spots: top-5 leagues — 5–8, the others — 4–6, 3–4 or 2nd.",
      "Same format as the UCL: **league phase** — each plays **8** different opponents, **1** round a day, deadline **23:30**.",
      "Places **1–8** go straight to the round of 16, **9–24** to the play-off round. Then quarter-finals, semi-finals and the final! 🔥",
      "The champion gets **350** 🪙 eF Tokens. Finish higher in your league and see you in the UCL next season! 😉",
    ],
  },
  co: {
    hint: "Want to hear about the Conference League? 🟢",
    say: [
      "🟢 **Conference League** — Europe's third cup. The places after the Europa League compete here: **36** in total.",
      "How to get in? Top-5 leagues — places 9–12, the others — 7–9, 5–6 or 3rd — at the end of the league season.",
      "The league phase is shorter here: each plays **6** different opponents. **1** round a day, deadline **23:30**.",
      "Then the play-offs: round of 16, quarter-finals, semi-finals and the final. Every win is a step to the trophy! 🏆",
      "The champion gets **250** 🪙 eF Tokens. This cup is a stepping stone to the big ones! 🪜",
    ],
  },
  ac: {
    hint: "Want to hear about the Asian Champions League? 🌏",
    say: [
      "🌏 **Asian Champions League** — Asia's strongest cup! **32** players in total.",
      "How to get in? Places **1–8** of the Uzbekistan Superliga, Saudi Pro League, UAE Pro League and J1 League — at the end of the league season.",
      "First the **league phase**: everyone in one table, each plays **8** different opponents. **1** round a day, deadline **23:30**.",
      "Places **1–8** go straight to the round of 16, **9–24** to the play-off round. Then quarter-finals, semi-finals and the final! 🔥",
      "The champion gets **350** 🪙 eF Tokens. Becoming the champion of Asia is a big honor! 🏅",
    ],
  },
  division: {
    hint: "Want me to explain how the Division works? 📅",
    say: [
      "📅 **Division** — a battle every day! No club picking here: sign up each day and the bot gives you a **random opponent**.",
      "Daily schedule: **17:00–20:00** — sign-up, **20:00** — draw, until **16:00** next day — play and enter the result ⏰",
      "Points: win **+15**, draw **+10**, loss **−10**. Everyone starts at **1500**. A match not played in time is a 0:0 draw.",
      "If the number of players is odd, one of you is left without an opponent — no worries, spin the **wheel** and get 5, 10 or 15 points 🎡",
      "Most importantly: at the end of the season the rating's **TOP-48** qualify for the **World Cup**! 🌍 Play every day — the points keep adding up.",
    ],
  },
  wc: {
    hint: "Want to hear about the World Cup? 🌍",
    say: [
      "🌍 Welcome to the **World Cup**! Here you play with a **national team**, not a club. **48** players: **12** groups of 4.",
      "Who takes part? Only the **TOP-48** of the **Division** season rating. The list is renewed every season — play well in the Division! 💪",
      "Choose your national team — it decides your group. The group stage has **3** rounds: **1** a day, deadline **23:30**.",
      "**32** go to the play-offs: group winners, runners-up and the **8** best third places. Then from the round of 32 to the final! 🏆",
      "By stage you earn 🪙 eF Tokens (the champion gets **500**) and there's the WC **Golden Boot**. Play for your country's glory! 🇺🇿",
    ],
  },
  pt: {
    hint: "Want me to show how to create your own tournament? 🎟",
    say: [
      "🎟 **Private tournaments**! Here you are the organizer. Create your own tournament for friends, a group or a team.",
      "Tap **«+ Create a tournament»** and pick a format: League, Champions League, Europa League, World Cup or Free format (groups + play-offs).",
      "Choose the number of players, then send your friends the **invite link** — whoever taps it joins the tournament 🔗",
      "When it's full, tap **«Start tournament»**. The bot calculates the table, play-offs and champion. You set round deadlines, settle disputes and can appoint a helper admin 👑",
      "Unlike official tournaments, the **organizer** sets the rules and it's for invited players only. Have fun playing with friends! 😄",
    ],
  },
  tb: {
    hint: "Want to hear about Team battle? 🛡",
    say: [
      "🛡 **Team battle** — here we fight not alone but **as a team**! When two teams meet, players play 1v1, and the team with more wins takes it.",
      "To create a team, get a **league link** from the league admin. Want to join a friend's team? Ask the captain for an **invite link** 🔗",
      "The captain sets the **starting lineup**. When a round opens (**1** a day, deadline **23:30**), lineup players are paired 1v1 with the other team — your opponent is in the **«Battle»** tab.",
      "Enter the result with a **screenshot of the final screen** — no screenshot, no result 📸 A team without a full lineup gets a technical loss.",
      "Per match: a win is **3** points, a draw **1**. Support your teammates — together we're stronger! 🤝",
    ],
  },
};
