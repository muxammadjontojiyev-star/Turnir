"""
cosmetics.py — DO'KON → BEZAKLAR: profil ramkalari va profil kartasi orqa fonlari (2026-10-30).

Egasi so'rovi: avatar ramkasi va profil sahifasiga turli orqa fonlar, eF Token bilan sotib olinadi.
Faqat ko'rinish — o'yin natijasiga ta'sir qilmaydi. Ko'rinadi: o'z Profil sahifasi va boshqalar
reytingdan ochadigan o'yinchi profili (/profile, /players/{id}/profile -> "cosmetics").

Katalog — COSMETICS (id -> tur, narx). Dizayn — static/cosmetics.css (.cos-frame-<id> / .cos-bg-<id>),
nomlar — static/texts_shop.js (cos_<id>). Yangi bezak: shu yerga bir qator + CSS + nom.
Sotib olish bir martalik va doimiy; bir vaqtda bitta ramka va bitta fon qo'llanadi (yechib qo'yish mumkin).
Pul — wallet.wallet_change ('cosmetic', ref = user_cosmetics.id); BEGIN IMMEDIATE (qoida #38).
"""

import logging

from models import get_connection
from shop_core import _tx
from wallet import get_balance, wallet_change

logger = logging.getLogger(__name__)

KIND_FRAME, KIND_BG = "frame", "bg"
TX_COSMETIC = "cosmetic"
COSMETICS: dict[str, dict] = {
    # ramkalar (avatar atrofida)
    "neon":     {"kind": KIND_FRAME, "price": 150},
    "ice":      {"kind": KIND_FRAME, "price": 200},
    "emerald":  {"kind": KIND_FRAME, "price": 200},
    "gold":     {"kind": KIND_FRAME, "price": 300},
    "fire":     {"kind": KIND_FRAME, "price": 400},
    "champion": {"kind": KIND_FRAME, "price": 600},
    # profil kartasi orqa fonlari
    # 2026-10-31: egasi qarori — stadium/sunset/pitch/cyber SOTUVDAN olindi ("sale": False): sotib olganlarda
    # qoladi (ko'rinadi, qo'llash/yechish mumkin), yangi xarid yo'q. galaxy/luxury — 200 eF.
    "stadium":  {"kind": KIND_BG, "price": 200, "sale": False},
    "sunset":   {"kind": KIND_BG, "price": 200, "sale": False},
    "pitch":    {"kind": KIND_BG, "price": 250, "sale": False},
    "cyber":    {"kind": KIND_BG, "price": 250, "sale": False},
    "galaxy":   {"kind": KIND_BG, "price": 200},
    "luxury":   {"kind": KIND_BG, "price": 200},
    # 2026-10-31: futbolchilar rasmli fonlar (static/images/bg-<nom>.jpg, egasi yuborgan rasmlardan):
    # Ronaldo va Messi — qimmatroq, Real Madrid jamoaviy — o'rtacha, qolganlari — oddiy narx
    "pl_ronaldo_pt":  {"kind": KIND_BG, "price": 700},
    "pl_ronaldo_cr7": {"kind": KIND_BG, "price": 700},
    "pl_messi_10":    {"kind": KIND_BG, "price": 700},
    "pl_messi_barca": {"kind": KIND_BG, "price": 700},
    "pl_real_zidane": {"kind": KIND_BG, "price": 500},
    "pl_real_stars":  {"kind": KIND_BG, "price": 500},
    "pl_neymar":      {"kind": KIND_BG, "price": 350},
    "pl_kaka":        {"kind": KIND_BG, "price": 350},
    "pl_bale":        {"kind": KIND_BG, "price": 350},
    "pl_pedri":       {"kind": KIND_BG, "price": 350},
    "pl_bellingham":  {"kind": KIND_BG, "price": 350},
}
_EQUIP_COL = {KIND_FRAME: "frame", KIND_BG: "bg"}


def init_cosmetics_tables(cur) -> None:
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_cosmetics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            item_id TEXT NOT NULL,
            price INTEGER NOT NULL,
            bought_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (user_id, item_id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_cosmetic_equip (
            user_id INTEGER PRIMARY KEY,
            frame TEXT,
            bg TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)


def _equipped(cur, user_id: int) -> dict:
    cur.execute("SELECT frame, bg FROM user_cosmetic_equip WHERE user_id = ?", (user_id,))
    r = cur.fetchone()
    eq = {"frame": r["frame"], "bg": r["bg"]} if r else {"frame": None, "bg": None}
    return {k: v if v in COSMETICS else None for k, v in eq.items()}       # katalogdan olib tashlangan bo'lsa


def get_equipped(user_id: int) -> dict:
    """Profil javoblari uchun: {"frame": id|None, "bg": id|None}."""
    conn = get_connection()
    try:
        return _equipped(conn.cursor(), user_id)
    finally:
        conn.close()


def cos_state(user_id: int) -> dict:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT item_id FROM user_cosmetics WHERE user_id = ?", (user_id,))
        owned = [r["item_id"] for r in cur.fetchall() if r["item_id"] in COSMETICS]
        # sotuvdan olinganlar — faqat egasiga (o'zinikini qo'llash/yechish uchun) ko'rinadi
        catalog = [{"id": k, **v, "sale": v.get("sale", True)} for k, v in COSMETICS.items()
                   if v.get("sale", True) or k in owned]
        return {"balance": get_balance(cur, user_id), "owned": owned, "equipped": _equipped(cur, user_id),
                "catalog": catalog}
    finally:
        conn.close()


def _set_equip(cur, user_id: int, kind: str, item_id: str | None) -> None:
    col = _EQUIP_COL[kind]                                # faqat ichki qiymat — SQL inyeksiya yo'q
    cur.execute(f"INSERT INTO user_cosmetic_equip (user_id, {col}) VALUES (?, ?) "
                f"ON CONFLICT(user_id) DO UPDATE SET {col} = excluded.{col}", (user_id, item_id))


def cos_buy(user_id: int, item_id: str) -> tuple[bool, str | dict]:
    """Sotib oladi va darhol qo'llaydi. Sabablar: not_found, already_owned, insufficient."""
    item = COSMETICS.get(item_id or "")

    def run(cur):
        if not item or not item.get("sale", True):          # sotuvdan olingan — yangi xarid yo'q
            return False, "not_found"
        cur.execute("SELECT 1 FROM user_cosmetics WHERE user_id = ? AND item_id = ?", (user_id, item_id))
        if cur.fetchone():
            return False, "already_owned"
        cur.execute("INSERT INTO user_cosmetics (user_id, item_id, price) VALUES (?, ?, ?)", (user_id, item_id, item["price"]))
        try:
            balance = wallet_change(cur, user_id, -item["price"], TX_COSMETIC, cur.lastrowid)
        except ValueError:
            return False, "insufficient"
        _set_equip(cur, user_id, item["kind"], item_id)
        return True, {"balance": balance, "equipped": _equipped(cur, user_id)}

    ok, r = _tx(run)
    if ok:
        logger.info("BEZAK: user %s — %s (%s eF)", user_id, item_id, item["price"])
    return ok, r


def cos_equip(user_id: int, kind: str, item_id: str | None) -> tuple[bool, str | dict]:
    """Qo'llash (item_id) yoki yechish (None). Sabablar: bad_kind, not_found, not_owned."""
    if kind not in _EQUIP_COL:
        return False, "bad_kind"

    def run(cur):
        if item_id is not None:
            item = COSMETICS.get(item_id)
            if not item or item["kind"] != kind:
                return False, "not_found"
            cur.execute("SELECT 1 FROM user_cosmetics WHERE user_id = ? AND item_id = ?", (user_id, item_id))
            if not cur.fetchone():
                return False, "not_owned"
        _set_equip(cur, user_id, kind, item_id)
        return True, {"equipped": _equipped(cur, user_id)}

    return _tx(run)
