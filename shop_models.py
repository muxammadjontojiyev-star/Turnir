"""
shop_models.py — DO'KON va ILOVA VALYUTASI (eF Token) jadvallari (2026-10-30).

Jadvallar (init_db -> init_shop_tables, idempotent — CREATE IF NOT EXISTS):
  - wallets       — har ishtirokchining balansi (user_id PK). Balans FAQAT wallet.py orqali o'zgaradi.
  - wallet_tx     — har o'zgarish yozuvi (daftar): +sotib olish, −auksion (keyingi bosqich), admin.
                    (kind, ref_id) UNIQUE — bitta buyurtma ikki marta balansga tushmaydi (qoida #38).
  - shop_packages — valyuta paketlari (bosh admin paneldan: qo'shish / narx / yoqish-o'chirish).
  - shop_orders   — sotib olish buyurtmalari: karta + chek. status: review -> approved | rejected.
                    coins/price_uzs — buyurtma paytidagi nusxa (paket narxi keyin o'zgarsa ham).
"""


def init_shop_tables(cur) -> None:
    cur.execute("""
        CREATE TABLE IF NOT EXISTS wallets (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER NOT NULL DEFAULT 0 CHECK (balance >= 0),
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS wallet_tx (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            balance_after INTEGER NOT NULL,
            kind TEXT NOT NULL,
            ref_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_wallet_tx_user ON wallet_tx(user_id, id)")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_wallet_tx_ref ON wallet_tx(kind, ref_id) "
                "WHERE ref_id IS NOT NULL")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS shop_packages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            coins INTEGER NOT NULL,
            price_uzs INTEGER NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS shop_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            package_id INTEGER NOT NULL,
            coins INTEGER NOT NULL,
            price_uzs INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'review',
            receipt BLOB NOT NULL,
            receipt_mime TEXT NOT NULL,
            reject_reason TEXT,
            reviewed_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            reviewed_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (package_id) REFERENCES shop_packages(id)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_shop_orders_user ON shop_orders(user_id, id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_shop_orders_status ON shop_orders(status, id)")
