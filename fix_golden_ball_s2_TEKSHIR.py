"""
fix_golden_ball_s2.py — BIR MARTALIK tuzatish (2026-08).

Muammo: 2-mavsum Oltin to'pi (golden_ball) noto'g'ri egasiga berilgan.
Sabab: eski season_prizes.calculate_league_prizes tenglikda (ochko teng) faqat
max(points) olardi va birinchi uchraganni tanlardi — gol farqi/gol hisobga
olinmasdi. Kod TUZATILDI (endi ochko→gol farqi→gol), lekin 2-mavsum ALLAQACHON
yakunlangan va noto'g'ri yozuv DB'da qolgan.

Bu skript o'sha bitta yozuvni to'g'ri egasiga ko'chiradi. XAVFSIZ:
  - Avval joriy holatni KO'RSATADI (kim olgan).
  - Yangi egani username yoki telegram_id bo'yicha TOPADI va ko'rsatadi.
  - CONFIRM=True bo'lmasa HECH NARSA o'zgartirmaydi (faqat ko'rsatadi).
  - Faqat golden_ball, season_kind='league', berilgan season_number yozuvini
    yangilaydi (user_id + telegram_id). Boshqa sovrinlarga TEGMAYDI.

ISHLATISH:
  1. Quyidagi 3 sozlamani to'ldiring (SEASON_NUMBER, yangi ega, CONFIRM).
  2. Avval CONFIRM=False bilan ishga tushiring — holatni ko'ring.
  3. To'g'ri bo'lsa CONFIRM=True qilib qayta ishga tushiring.

  python fix_golden_ball_s2.py
"""

import os
import sqlite3

# ─── SOZLAMALAR (to'ldiring) ─────────────────────────────────────────────
SEASON_NUMBER = 2            # qaysi mavsum golden_ball'i tuzatiladi

# Yangi egani BITTA usul bilan bering (qolganini None qoldiring):
NEW_OWNER_NICKNAME = "Raxmonberdiyev"    # to'ldirildi (Serie A g'olibi, Torino)
NEW_OWNER_USERNAME = None    # masalan: "TorinoUser"  (@ SIZ)
NEW_OWNER_TELEGRAM_ID = None # masalan: 123456789

CONFIRM = False              # TEKSHIRISH: faqat ko'rsatadi, O'ZGARTIRMAYDI
# ─────────────────────────────────────────────────────────────────────────

DB_PATH = os.getenv("DB_PATH", "efootball_bot.db")


def _fetch_owner(cursor, nickname, username, telegram_id):
    """Yangi egani telegram_id, username yoki nickname bo'yicha topadi."""
    if telegram_id is not None:
        cursor.execute(
            "SELECT id, telegram_id, nickname, username FROM users WHERE telegram_id = ?",
            (telegram_id,),
        )
        return cursor.fetchall()
    if username is not None:
        uname = username.lstrip("@")
        cursor.execute(
            "SELECT id, telegram_id, nickname, username FROM users WHERE username = ?",
            (uname,),
        )
        return cursor.fetchall()
    if nickname is not None:
        cursor.execute(
            "SELECT id, telegram_id, nickname, username FROM users "
            "WHERE nickname = ? COLLATE NOCASE",
            (nickname.strip(),),
        )
        return cursor.fetchall()
    return []


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        # 1) Joriy golden_ball yozuvi (season_number, league)
        cursor.execute(
            "SELECT sp.id, sp.user_id, sp.telegram_id, u.nickname, u.username "
            "FROM season_prizes sp "
            "LEFT JOIN users u ON u.id = sp.user_id "
            "WHERE sp.prize_type = 'golden_ball' AND sp.season_kind = 'league' "
            "AND sp.season_number = ?",
            (SEASON_NUMBER,),
        )
        rows = cursor.fetchall()
        if not rows:
            print(f"❌ {SEASON_NUMBER}-mavsumda golden_ball yozuvi topilmadi.")
            return
        if len(rows) > 1:
            print(f"⚠️ {SEASON_NUMBER}-mavsumda {len(rows)} ta golden_ball yozuvi bor "
                  "(kutilmagan). Skript to'xtatildi — qo'lda tekshiring.")
            for r in rows:
                print(f"   id={r['id']} user_id={r['user_id']} "
                      f"nickname={r['nickname']} @{r['username']}")
            return

        cur = rows[0]
        print("── JORIY holat ──")
        print(f"  golden_ball yozuvi id={cur['id']}")
        print(f"  Hozirgi ega: nickname={cur['nickname']} @{cur['username']} "
              f"(user_id={cur['user_id']}, telegram_id={cur['telegram_id']})")

        # 2) Yangi ega
        owners = _fetch_owner(cursor, NEW_OWNER_NICKNAME, NEW_OWNER_USERNAME,
                              NEW_OWNER_TELEGRAM_ID)
        if not owners:
            print("\n❌ Yangi ega topilmadi. NEW_OWNER_NICKNAME / NEW_OWNER_USERNAME / "
                  "NEW_OWNER_TELEGRAM_ID dan birini to'g'ri to'ldiring.")
            print("   Maslahat: find_user.py bilan aniq username/telegram_id ni toping.")
            return
        if len(owners) > 1:
            print(f"\n⚠️ '{NEW_OWNER_NICKNAME}' nomi bilan {len(owners)} ta o'yinchi bor "
                  "(dublikat ism). Aniq bo'lishi uchun telegram_id yoki username ishlating:")
            for o in owners:
                uname = ("@" + o["username"]) if o["username"] else "—"
                print(f"   telegram_id={o['telegram_id']}  nickname={o['nickname']}  {uname}")
            print("   Skript to'xtatildi — noto'g'ri odamga bermaslik uchun.")
            return
        owner = owners[0]
        print("\n── YANGI ega (topildi) ──")
        print(f"  nickname={owner['nickname']} @{owner['username']} "
              f"(user_id={owner['id']}, telegram_id={owner['telegram_id']})")

        if owner["id"] == cur["user_id"]:
            print("\n✅ Yangi ega allaqachon shu sovrin egasi — o'zgartirish shart emas.")
            return

        # 3) Yozish (faqat CONFIRM=True)
        if not CONFIRM:
            print("\n⚠️ CONFIRM=False — HECH NARSA o'zgartirilmadi (quruq ko'rsatish).")
            print("   To'g'ri bo'lsa CONFIRM=True qilib qayta ishga tushiring.")
            return

        cursor.execute(
            "UPDATE season_prizes SET user_id = ?, telegram_id = ? WHERE id = ?",
            (owner["id"], owner["telegram_id"], cur["id"]),
        )
        conn.commit()
        print(f"\n✅ TUZATILDI: golden_ball (id={cur['id']}) endi "
              f"{owner['nickname']} @{owner['username']} ga tegishli.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
