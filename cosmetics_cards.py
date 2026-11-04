"""
cosmetics_cards.py — DO'KON → BEZAKLAR: «O'YIN KARTASI FONI» (2026-11-04, egasi so'rovi).

Ishtirokchining SHAXSIY O'YINCHI KARTASI (player_card.py) uchun ramkali fon — egasi yuborgan rasmlar,
static/images/card-<nom>.jpg; karta Divizion qur'asida, Profilda va reytingdan ochilgan profilda ko'rinadi.
  * Tur — KIND_CARD ("card"); katalog cosmetics.COSMETICS ga qo'shiladi (sotib olish / qo'llash o'sha).
  * SOTUV bosh admin kaliti bilan yoqiladi (cosmetic_settings.card_sale_on, standart — O'CHIQ): egasi
    «keyinroq sotamiz» dedi. O'chiq paytda do'konda faqat bosh adminga ko'rinadi va u bepul qo'llab
    ko'ra oladi (ko'rib chiqish uchun); boshqalarga ko'rinmaydi, sotib olinmaydi.
  * Qo'llangan fon — user_cosmetic_equip.card (migratsiya, qoida #31).
"""

import logging

from models import get_connection

logger = logging.getLogger(__name__)

KIND_CARD = "card"
SETTING_SALE = "card_sale_on"
# 2026-11-04 (v2): egasi — «fonda karta ramkasi, futbolchi o'rnida ISHTIROKCHI rasmi» (player_card.py).
# Avvalgi 5 ta rasm (futbolchili) olib tashlandi; egasi futbolchisiz ramkali fonlarni yuboradi — har biri
# shu yerga bir qator: "card_<nom>": {"kind": KIND_CARD, "price": N}, rasm — static/images/card-<nom>.jpg
# (static/player_card.css .pcard-bg-card_<nom>), nom — static/texts_shop.js cos_card_<nom>.
# Bo'sh bo'lsa — hamma kartasi standart (bepul, CSS) ramkada; do'kon bo'limi ko'rinmaydi.
CARD_ITEMS: dict[str, dict] = {}


def migrate_cards(cur) -> None:
    cols = {r["name"] for r in cur.execute("PRAGMA table_info(user_cosmetic_equip)")}
    if "card" not in cols:
        cur.execute("ALTER TABLE user_cosmetic_equip ADD COLUMN card TEXT")
    cur.execute("CREATE TABLE IF NOT EXISTS cosmetic_settings (key TEXT PRIMARY KEY, value TEXT)")


def card_sale_on(cur) -> bool:
    try:
        r = cur.execute("SELECT value FROM cosmetic_settings WHERE key = ?", (SETTING_SALE,)).fetchone()
    except Exception:            # migratsiyadan oldin — o'chiq
        return False
    return bool(r and r["value"] == "1")


def get_card_sale() -> bool:
    conn = get_connection()
    try:
        return card_sale_on(conn.cursor())
    finally:
        conn.close()


def set_card_sale(on: bool) -> bool:
    conn = get_connection()
    try:
        conn.execute("INSERT INTO cosmetic_settings (key, value) VALUES (?, ?) "
                     "ON CONFLICT(key) DO UPDATE SET value = excluded.value", (SETTING_SALE, "1" if on else "0"))
        conn.commit()
    finally:
        conn.close()
    logger.info("BEZAK: o'yin kartasi fonlari sotuvi — %s", "YOQILDI" if on else "O'CHIRILDI")
    return bool(on)


def cards_for_users(user_ids) -> dict[int, str | None]:
    """{user_id: qo'llangan karta foni id | None} — Divizion o'yin kartasi uchun."""
    ids = [int(u) for u in user_ids if u]
    if not ids:
        return {}
    conn = get_connection()
    try:
        q = ",".join("?" * len(ids))
        rows = conn.execute(f"SELECT user_id, card FROM user_cosmetic_equip WHERE user_id IN ({q})", ids).fetchall()
        return {r["user_id"]: (r["card"] if r["card"] in CARD_ITEMS else None) for r in rows}
    except Exception:            # ustun hali yo'q — fonsiz
        return {}
    finally:
        conn.close()
