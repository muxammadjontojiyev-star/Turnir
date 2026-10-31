"""
wallet_grants.py — BIR MARTALIK eF Token sovg'asi (migratsiya, 2026-10-30).

Egasi so'rovi: "Ayni vaqtda botdan foydalanayotgan barchaga 100 eF Token berilsin".
init_db() da (deploy/restart paytida) ishga tushadi: wallet_grants jadvalida shu kalit bo'lmasa —
o'sha PAYTDA users jadvalidagi HAR BIR foydalanuvchiga amount qo'shiladi (wallet_tx kind='gift')
va kalit yoziladi. Keyingi restartlarda kalit bor — hech narsa qilinmaydi (idempotent, qoida #31/#38).
Keyin qo'shilgan foydalanuvchilar bu sovg'ani olmaydi. Yangi sovg'a — yangi kalit bilan.

2026-10-31: XUSH KELIBSIZ sovg'asi (egasi so'rovi): botga YANGI qo'shilgan har kishiga bir marta WELCOME_AMOUNT
(queries_users.get_or_create_user — yangi user yaratilganda, give_welcome). Kechagi sovg'ani olganlarga berilmaydi.
Kecha sovg'adan KEYIN qo'shilganlar (sovg'asiz qolganlar) — init_db da bir marta welcome_catch_up bilan oladi.
Takror bo'lmasligi: welcome_given (telegram_id PRIMARY KEY) — FK'siz alohida belgi, shuning uchun akkaunt
o'chirilib (wallet_tx bilan birga) qayta ochilsa ham ikkinchi marta berilmaydi. Kechagi sovg'ani olganlar ham
shu jadvalga belgilanadi (welcome_catch_up).
"""

import logging

from wallet import wallet_change

logger = logging.getLogger(__name__)

TX_GIFT = "gift"
TX_WELCOME = "welcome"
WELCOME_AMOUNT = 100
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


def init_welcome_table(cur) -> None:
    cur.execute("""
        CREATE TABLE IF NOT EXISTS welcome_given (
            telegram_id INTEGER PRIMARY KEY,
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


def grant_welcome(cur, user_id: int, telegram_id: int) -> bool:
    """Ochiq tranzaksiya ichida. Belgi allaqachon bo'lsa yoki kechagi sovg'ani olgan bo'lsa — False."""
    cur.execute("INSERT OR IGNORE INTO welcome_given (telegram_id) VALUES (?)", (telegram_id,))
    if cur.rowcount == 0:
        return False
    cur.execute("SELECT 1 FROM wallet_tx WHERE user_id = ? AND kind = ? LIMIT 1", (user_id, TX_GIFT))
    if cur.fetchone():
        return False                                      # kechagi sovg'ani olgan — belgi qo'yildi, xolos
    wallet_change(cur, user_id, WELCOME_AMOUNT, TX_WELCOME)
    return True


def give_welcome(user_id: int, telegram_id: int) -> bool:
    """Yangi foydalanuvchi yaratilganda (alohida BEGIN IMMEDIATE — parallel so'rovda ham bir marta)."""
    from shop_core import _tx
    ok, given = _tx(lambda cur: (True, grant_welcome(cur, user_id, telegram_id)))
    if given:
        logger.info("Xush kelibsiz sovg'asi: user %s (tg %s) +%s eF", user_id, telegram_id, WELCOME_AMOUNT)
    return bool(given)


def welcome_catch_up(cur) -> int:
    """
    init_db (ochiq tranzaksiya). Kechagi sovg'a hali berilmagan bo'lsa (kalit yo'q) — hech narsa qilmaydi.
    1) kechagi sovg'ani olganlar welcome_given ga belgilanadi (ularga berilmaydi);
    2) belgisi yo'qlar (kechagi sovg'adan KEYIN qo'shilganlar) — WELCOME_AMOUNT oladi.
    """
    cur.execute("SELECT 1 FROM wallet_grants WHERE grant_key = ?", (LAUNCH_GIFT_KEY,))
    if not cur.fetchone():
        return 0
    cur.execute("INSERT OR IGNORE INTO welcome_given (telegram_id) SELECT DISTINCT u.telegram_id FROM users u "
                "JOIN wallet_tx t ON t.user_id = u.id AND t.kind = ?", (TX_GIFT,))
    cur.execute("SELECT id, telegram_id FROM users WHERE telegram_id NOT IN (SELECT telegram_id FROM welcome_given) ORDER BY id")
    rows = [(r["id"], r["telegram_id"]) for r in cur.fetchall()]
    n = sum(1 for uid, tg in rows if grant_welcome(cur, uid, tg))
    if n:
        logger.info("Xush kelibsiz sovg'asi: kechagi sovg'adan keyin qo'shilgan %s kishiga +%s eF", n, WELCOME_AMOUNT)
    return n
