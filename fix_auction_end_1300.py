"""
fix_auction_end_1300.py — BIR MARTALIK (2026-11-01): barcha FAOL auksion lotlarining tugash vaqti
bugun 13:00 (Toshkent) ga belgilanadi — egasi so'rovi: yangi mavsum 13:00 da boshlanadi.

13:00 Toshkent = 08:00 UTC (ends_at bazada UTC'da saqlanadi — datetime('now')).
Faqat status='active' lotlar o'zgaradi; takliflar, pullar, yakunlanganlar TEGILMAYDI.
Takror ishga tushirish xavfsiz (bir xil qiymat yoziladi).

DIQQAT: 12:55 dan keyin taklif tushsa, o'sha lot odatdagidek 5 daqiqaga uzayadi (anti-snayper);
u holda «Yangi mavsumni boshlash» o'sha lot tugaguncha «faol auksion bor» deydi.

ISHLATISH (server papkasida):  python fix_auction_end_1300.py
"""

import os
import sqlite3

END_UTC = "2026-11-01 08:00:00"      # = 2026-11-01 13:00 Toshkent

db_path = os.getenv("DB_PATH")
if not db_path:
    from config import DB_PATH as db_path

conn = sqlite3.connect(db_path, timeout=15)
conn.row_factory = sqlite3.Row
try:
    rows = conn.execute("SELECT l.id, lg.name AS league, l.club_name, l.current_bid, l.ends_at FROM auction_lots l "
                        "JOIN leagues lg ON lg.id = l.league_id WHERE l.status = 'active' ORDER BY l.id").fetchall()
    if not rows:
        print("Faol auksion lot yo'q — hech narsa o'zgarmadi.")
    for r in rows:
        print(f"#{r['id']} {r['league']} — {r['club_name']}: taklif {r['current_bid'] or '-'}; eski tugash (UTC) {r['ends_at']}")
    cur = conn.execute("UPDATE auction_lots SET ends_at = ? WHERE status = 'active'", (END_UTC,))
    conn.commit()
    print(f"\n✅ {cur.rowcount} ta lot tugash vaqti: bugun 13:00 (Toshkent) = {END_UTC} UTC")
finally:
    conn.close()
