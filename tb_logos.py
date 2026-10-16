"""
tb_logos.py — "TEAMLAR JANGI": team va liga logolari (galereyadagi rasm, 2026-10-16).

Egasi so'rovi: logo bot bergan stikerlardan (emoji) emas, foydalanuvchining o'z galereyasidan.
  * Liga logosini — liga admini (yoki bosh admin), team logosini — team sardori o'zgartiradi.
  * Frontend rasmni 256x256 kvadratga kesib siqadi (tb_logo.js); server faqat imzo bo'yicha
    JPEG/PNG/WEBP va hajmni (TB_LOGO_MAX_BYTES) tekshiradi (qoida #41).
  * Baytlar ALOHIDA tb_logos jadvalida (ro'yxat so'rovlari og'irlashmasin, qoida #32);
    tb_teams.logo_ver / tb_leagues.logo_ver — versiya (NULL — logo yo'q, emoji ko'rsatiladi).
    URL /tb/logo/<kind>/<id>?v=<ver> — versiya o'zgarsa brauzer keshi yangilanadi.
  * Logo — ommaviy ko'rinadigan bezak (jadvalda hamma ko'radi), shuning uchun GET ochiq;
    <img> so'rovi Telegram sarlavhasini yubora olmaydi.
"""

import base64
import binascii
import logging

from models import get_connection
from pt_payment import detect_image_mime

logger = logging.getLogger(__name__)

TB_LOGO_MAX_BYTES = 400_000        # 256px rasm odatda 20–120 KB
TB_LOGO_KINDS = {"team": "tb_teams", "league": "tb_leagues"}   # jadval nomi KODDAN (qoida #29)


def init_logo_table(cursor) -> None:
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tb_logos (
            kind TEXT NOT NULL,
            ref_id INTEGER NOT NULL,
            data BLOB NOT NULL,
            mime TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (kind, ref_id)
        )
    """)
    for table in TB_LOGO_KINDS.values():
        cols = {r[1] for r in cursor.execute(f"PRAGMA table_info({table})").fetchall()}
        if "logo_ver" not in cols:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN logo_ver INTEGER")


def decode_logo(image_base64: str) -> tuple[bytes | None, str]:
    """base64 (data: prefiksi bilan ham) -> (baytlar, mime) yoki (None, sabab)."""
    raw = (image_base64 or "").strip()
    if raw.startswith("data:") and "," in raw:
        raw = raw.split(",", 1)[1]
    if not raw:
        return None, "empty_image"
    if len(raw) > TB_LOGO_MAX_BYTES * 4 // 3 + 16:
        return None, "image_too_large"
    try:
        data = base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError):
        return None, "bad_image"
    if len(data) > TB_LOGO_MAX_BYTES:
        return None, "image_too_large"
    mime = detect_image_mime(data)
    return (data, mime) if mime else (None, "bad_image")


def tb_set_logo(kind: str, ref_id: int, image_base64: str | None) -> tuple[bool, str | dict]:
    """
    Logo qo'yish (image_base64) yoki olib tashlash (None/bo'sh). Ruxsat — chaqiruvchi endpointda.
    Sabablar: bad_kind, not_found, empty_image, image_too_large, bad_image.
    """
    table = TB_LOGO_KINDS.get(kind)
    if not table:
        return False, "bad_kind"
    data = mime = None
    if image_base64:
        data, why = decode_logo(image_base64)
        if data is None:
            return False, why
        mime = why
    conn = get_connection()
    try:
        cur = conn.cursor()
        if not cur.execute(f"SELECT 1 FROM {table} WHERE id = ?", (ref_id,)).fetchone():
            return False, "not_found"
        if data is None:
            cur.execute("DELETE FROM tb_logos WHERE kind = ? AND ref_id = ?", (kind, ref_id))
            cur.execute(f"UPDATE {table} SET logo_ver = NULL WHERE id = ?", (ref_id,))
            ver = None
        else:
            cur.execute("INSERT INTO tb_logos (kind, ref_id, data, mime) VALUES (?, ?, ?, ?) "
                        "ON CONFLICT(kind, ref_id) DO UPDATE SET data = excluded.data, mime = excluded.mime, "
                        "updated_at = CURRENT_TIMESTAMP", (kind, ref_id, data, mime))
            cur.execute(f"UPDATE {table} SET logo_ver = COALESCE(logo_ver, 0) + 1 WHERE id = ?", (ref_id,))
            ver = cur.execute(f"SELECT logo_ver FROM {table} WHERE id = ?", (ref_id,)).fetchone()[0]
        conn.commit()
        logger.info("TB: %s #%s logosi %s", kind, ref_id, "yangilandi" if ver else "olib tashlandi")
        return True, {"logo_ver": ver}
    finally:
        conn.close()


def tb_get_logo(kind: str, ref_id: int) -> tuple[bytes, str] | None:
    if kind not in TB_LOGO_KINDS:
        return None
    conn = get_connection()
    try:
        r = conn.cursor().execute("SELECT data, mime FROM tb_logos WHERE kind = ? AND ref_id = ?",
                                  (kind, ref_id)).fetchone()
        return (bytes(r["data"]), r["mime"]) if r else None
    finally:
        conn.close()


def delete_logo_cur(cur, kind: str, ref_id: int) -> None:
    """Team/liga o'chirilganda (o'sha tranzaksiya ichida) logosi ham o'chadi."""
    cur.execute("DELETE FROM tb_logos WHERE kind = ? AND ref_id = ?", (kind, ref_id))
