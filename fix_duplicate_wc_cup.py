"""
BIR MARTALIK TUZATISH SKRIPTI — ishlatilgach o'chirib tashlash mumkin.

Maqsad: WC chempioni profilida 2 ta 'Jahon Chempionati Kubogi' ko'rinib qolgan
(Mavsum 1 va Mavsum 2). 2-mavsum hali boshlanmagani uchun ENG YANGISI (eng katta
season_number) o'chiriladi, Mavsum 1 qoladi.

XAVFSIZLIK:
- Faqat bitta foydalanuvchining (TARGET_USERNAME) 'wc_cup' sovrinlaridan
  ENG YANGISINI o'chiradi.
- Agar u foydalanuvchida 1 tadan ortiq wc_cup bo'lmasa — HECH NARSA qilmaydi.
- O'chirishdan oldin nima o'chishini ekranga chiqaradi.
- boshqa turdagi sovrinlarga (golden_ball, league_cup, wc_golden_boot) TEGMAYDI.

ISHLATISH (server terminalida, loyiha papkasida):
    python3 fix_duplicate_wc_cup.py

Agar boshqa foydalanuvchi bo'lsa, quyidagi TARGET_USERNAME ni o'zgartiring.
"""

from models import get_connection

# Skrinshotdagi chempion (Telegram username, @ BELGISIZ — DB shunday saqlaydi)
TARGET_USERNAME = "az1zbek_005_10"


def main():
    conn = get_connection()
    cursor = conn.cursor()

    # 1) Foydalanuvchini topamiz
    cursor.execute(
        "SELECT id, telegram_id, nickname, username FROM users WHERE username = ?",
        (TARGET_USERNAME,),
    )
    user = cursor.fetchone()
    if user is None:
        print(f"❌ '{TARGET_USERNAME}' username'li foydalanuvchi topilmadi. "
              f"TARGET_USERNAME ni tekshiring.")
        conn.close()
        return

    uid = user["id"]
    tg = user["telegram_id"]
    print(f"👤 Foydalanuvchi: id={uid}, telegram_id={tg}, "
          f"nickname={user['nickname']}, username=@{user['username']}")

    # 2) Uning barcha wc_cup sovrinlari (telegram_id yoki user_id bo'yicha —
    #    reset'dan keyin user_id o'zgargan bo'lishi mumkin, telegram_id doimiy)
    cursor.execute(
        """
        SELECT id, season_number, season_kind, user_id, telegram_id, awarded_at
        FROM season_prizes
        WHERE prize_type = 'wc_cup'
          AND (telegram_id = ? OR (telegram_id IS NULL AND user_id = ?))
        ORDER BY season_number DESC, id DESC
        """,
        (tg, uid),
    )
    cups = cursor.fetchall()
    print(f"\n🏆 Topilgan wc_cup sovrinlari: {len(cups)} ta")
    for c in cups:
        print(f"   - prize_id={c['id']}, Mavsum {c['season_number']}, "
              f"awarded_at={c['awarded_at']}")

    if len(cups) <= 1:
        print("\n✅ 1 tadan ortiq kubok yo'q — o'chirishga hojat yo'q. Hech narsa qilinmadi.")
        conn.close()
        return

    # 3) ENG YANGISINI (birinchi qator — season_number DESC) o'chiramiz
    victim = cups[0]
    print(f"\n🗑  O'chiriladi: prize_id={victim['id']} (Mavsum {victim['season_number']} — eng yangi)")
    print(f"✅ Qoladi: Mavsum {cups[1]['season_number']} va (agar bo'lsa) qolganlari")

    cursor.execute("DELETE FROM season_prizes WHERE id = ?", (victim["id"],))
    conn.commit()
    print(f"\n✔️  Tayyor. {cursor.rowcount} ta yozuv o'chirildi.")

    # 4) Tekshiruv
    cursor.execute(
        "SELECT COUNT(*) AS n FROM season_prizes WHERE prize_type = 'wc_cup' "
        "AND (telegram_id = ? OR (telegram_id IS NULL AND user_id = ?))",
        (tg, uid),
    )
    print(f"   Endi wc_cup soni: {cursor.fetchone()['n']} ta")
    conn.close()


if __name__ == "__main__":
    main()
