"""
wallet_grants.py — BIR MARTALIK eF Token sovg'asi (migratsiya, 2026-10-30).

Egasi so'rovi: "Ayni vaqtda botdan foydalanayotgan barchaga 100 eF Token berilsin".
init_db() da (deploy/restart paytida) ishga tushadi: wallet_grants jadvalida shu kalit bo'lmasa —
o'sha PAYTDA users jadvalidagi HAR BIR foydalanuvchiga amount qo'shiladi (wallet_tx kind='gift')
va kalit yoziladi. Keyingi restartlarda kalit bor — hech narsa qilinmaydi (idempotent, qoida #31/#38).
Keyin qo'shilgan foydalanuvchilar bu sovg'ani olmaydi. Yangi sovg'a — yangi kalit bilan.
"""

import logging

from wallet import wallet_change

logger = logging.getLogger(__name__)

TX_GIFT = "gift"
LAUNCH_GIFT_KEY = "launch_gift_2026_10_30"
LAUNCH_GIFT_AMOUNT = 100


def init_grants_table(cur) -> None:
    cur.execute("""
        CREATE TABLE IF NOT EXISTS wallet_grants (
            grant_key TEXT PRIMARY KEY,
            amount INTEGER NOT NULL,
            users_count INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


def grant_once(cur, key: str, amount: int) -> int | None:
    """
    Ochiq tranzaksiya ichida (chaqiruvchi commit qiladi). Kalit allaqachon bo'lsa None,
    aks holda sovg'a olganlar soni. Kalit BIRINCHI yoziladi (INSERT OR IGNORE) — ikki jarayon
    bir vaqtda ishga tushsa, ikkinchisi yozish qulfini kutadi va 0 qator ko'rib, o'tkazib yuboradi.
    """
    cur.execute("INSERT OR IGNORE INTO wallet_grants (grant_key, amount, users_count) VALUES (?, ?, 0)", (key, amount))
    if cur.rowcount == 0:
        return None
    cur.execute("SELECT id FROM users ORDER BY id")
    ids = [r["id"] for r in cur.fetchall()]
    for uid in ids:
        wallet_change(cur, uid, amount, TX_GIFT)
    cur.execute("UPDATE wallet_grants SET users_count = ? WHERE grant_key = ?", (len(ids), key))
    logger.info("eF Token sovg'asi '%s': %s ta foydalanuvchiga +%s", key, len(ids), amount)
    return len(ids)
