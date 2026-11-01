"""
wallet.py — ilova valyutasi (eF Token) balansi (2026-10-30).

Balans FAQAT shu modul orqali o'zgaradi va har o'zgarish wallet_tx daftariga yoziladi.
Funksiyalar OCHIQ tranzaksiya ichida chaqiriladi (chaqiruvchi BEGIN IMMEDIATE / COMMIT qiladi).
Manfiy balans bo'lmaydi: wallet_change yetmasa ValueError("insufficient") (keyingi bosqich — auksion).
"""

TX_PURCHASE = "purchase"      # do'kondan sotib olish (ref_id = shop_orders.id)


def get_balance(cursor, user_id: int) -> int:
    cursor.execute("SELECT balance FROM wallets WHERE user_id = ?", (user_id,))
    r = cursor.fetchone()
    return int(r["balance"]) if r else 0


def wallet_change(cursor, user_id: int, amount: int, kind: str, ref_id: int | None = None) -> int:
    """Balansni amount ga o'zgartiradi (+/−), daftarga yozadi, yangi balansni qaytaradi."""
    new_balance = get_balance(cursor, user_id) + int(amount)
    if new_balance < 0:
        raise ValueError("insufficient")
    cursor.execute(
        "INSERT INTO wallets (user_id, balance) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET "
        "balance = excluded.balance, updated_at = CURRENT_TIMESTAMP", (user_id, new_balance))
    cursor.execute("INSERT INTO wallet_tx (user_id, amount, balance_after, kind, ref_id) VALUES (?, ?, ?, ?, ?)",
                   (user_id, int(amount), new_balance, kind, ref_id))
    return new_balance


WALLET_TOP_N = 10      # 2026-11-01: bosh admin — eng ko'p eF Tokeni borlar


def wallet_top(limit: int = WALLET_TOP_N) -> dict:
    """2026-11-01 (egasi so'rovi): eng boy ishtirokchilar + jami muomaladagi eF Token va egalari soni."""
    from models import get_connection
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT w.user_id, w.balance, u.telegram_id, u.nickname, u.username FROM wallets w "
            "JOIN users u ON u.id = w.user_id WHERE w.balance > 0 ORDER BY w.balance DESC, w.user_id LIMIT ?",
            (limit,)).fetchall()
        tot = conn.execute("SELECT COUNT(*) AS n, COALESCE(SUM(balance), 0) AS s FROM wallets w "
                           "JOIN users u ON u.id = w.user_id WHERE w.balance > 0").fetchone()
        return {"top": [dict(r) for r in rows], "holders": tot["n"], "total": tot["s"]}
    finally:
        conn.close()
