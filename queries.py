"""
queries.py — FACADE (2026-07-03, audit C1).

Kod 10 modulga bo'lindi (qoida #21: fayl 200-300 qator):
  queries_users.py — Foydalanuvchilar CRUD + liga ro'yxatdan o'tish (registrations).
  queries_leagues.py — Ligalar CRUD, qur'a sanasi, natijalarni saqlash/tiklash, matchday reset/reopen.
  queries_matchdays.py — Matchday deadline/lock mantiqi, ochiq tur, bildirishnoma navbatlari.
  queries_matches.py — Liga o'yinlari: ro'yxat, natija kiritish/tasdiqlash, auto-resolve, admin resolve/fix.
  queries_chat.py — Liga o'yin ichidagi chat: access, xabarlar, unread, typing, last_seen.
  queries_wc.py — World Cup: ro'yxatdan o'tish, guruh ma'lumotlari, qur'a sanasi.
  queries_wc_matches.py — WC guruh o'yinlari: ochiq tur, natija kiritish/tasdiqlash, deadline + avtomatik 0:0.
  queries_wc_admin.py — WC admin amallari: fix/set-score/reset, o'yinchini olib tashlash, jadval tuzatish.
  queries_wc_playoff.py — WC play-off: bracket qurish, round ochilishi, g'olibni keyingi bosqichga o'tkazish.
  queries_wc_playoff_results.py — WC play-off: natija kiritish/tasdiqlash, foydalanuvchi o'yinlari, chempion.

Barcha eski importlar (`from queries import X`, `import queries`) o'zgarishsiz
ishlaydi. Yangi kod to'g'ridan-to'g'ri tegishli moduldan import qilgani ma'qul.
"""

from queries_users import *  # noqa: F401,F403
from queries_leagues import *  # noqa: F401,F403
from queries_matchdays import *  # noqa: F401,F403
from queries_matches import *  # noqa: F401,F403
from queries_chat import *  # noqa: F401,F403
from queries_wc import *  # noqa: F401,F403
from queries_wc_matches import *  # noqa: F401,F403
from queries_wc_admin import *  # noqa: F401,F403
from queries_wc_playoff import *  # noqa: F401,F403
from queries_wc_playoff_results import *  # noqa: F401,F403
