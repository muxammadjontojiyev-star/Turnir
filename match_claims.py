"""
match_claims.py — «RAQIB YOZMADI / O'YNAMADI — TEXNIK G'ALABA» so'rovlari va ADMIN KO'RIB CHIQISHI (2026-11-06).

  * Ishtirokchi yozishma skrinshotlari (CLAIM_MAX_IMAGES gacha) va izoh bilan so'rov yuboradi — HECH QACHON
    avtomatik tasdiqlanmaydi. Ko'radi: bosh admin + rejim admini (ligada — o'sha liga admini), match_modes.can_review.
  * Admin: «3:0 berish» (TECH_WIN — so'rovchi foydasiga, rejimning admin funksiyasi bilan) yoki «Rad etish».
  * Shu ro'yxatda skrinshotli natijaga raqib bildirgan E'TIROZLAR ham (match_shots.status='disputed'):
    «Natija to'g'ri» yoki to'g'ri hisobni kiritib «Tuzatish».
Jadvallar — match_claims, match_claim_images (migratsiya, qoida #31).
"""

import io
import logging
import time

from models import get_connection

logger = logging.getLogger(__name__)

TECH_WIN = (3, 0)
CLAIM_MAX_IMAGES = 3
CLAIM_NOTE_MAX = 500
CLAIM_IMG_MAX = 1400
CLAIM_IMG_Q = 78
CLAIM_DAILY_LIMIT = 5
ADMIN_LIST_LIMIT = 100


def migrate_match_claims(cur) -> None:
    cur.execute("CREATE TABLE IF NOT EXISTS match_claims (id INTEGER PRIMARY KEY AUTOINCREMENT, mode TEXT NOT NULL, "
                "match_id INTEGER NOT NULL, claimant_id INTEGER NOT NULL, opponent_id INTEGER NOT NULL, note TEXT, "
                "status TEXT NOT NULL DEFAULT 'open', decided_by INTEGER, decided_at REAL, created_at REAL)")
    cur.execute("CREATE TABLE IF NOT EXISTS match_claim_images (claim_id INTEGER NOT NULL, idx INTEGER NOT NULL, "
                "img BLOB, PRIMARY KEY (claim_id, idx))")


def _jpeg(raw: bytes) -> bytes:
    from PIL import Image, ImageOps
    im = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGB")
    im.thumbnail((CLAIM_IMG_MAX, CLAIM_IMG_MAX))
    out = io.BytesIO()
    im.save(out, "JPEG", quality=CLAIM_IMG_Q)
    return out.getvalue()


def create_claim(user_id: int, mode: str, match_id: int, images: list[bytes], note: str) -> tuple[bool, str | dict]:
    from match_modes import MODES, get_match
    if mode not in MODES:
        return False, "bad_mode"
    m = get_match(mode, match_id)
    if not m:
        return False, "match_not_found"
    if user_id not in (m["player1_id"], m["player2_id"]) or not m["player2_id"]:
        return False, "not_participant"
    if not images:
        return False, "no_images"
    try:
        imgs = [_jpeg(b) for b in images[:CLAIM_MAX_IMAGES]]
    except Exception:
        return False, "bad_image"
    opp = m["player2_id"] if user_id == m["player1_id"] else m["player1_id"]
    day_ago = time.time() - 86400
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("BEGIN IMMEDIATE")
        if cur.execute("SELECT 1 FROM match_claims WHERE mode = ? AND match_id = ? AND status = 'open'",
                       (mode, match_id)).fetchone():
            conn.rollback()
            return False, "claim_exists"
        n = cur.execute("SELECT COUNT(*) AS n FROM match_claims WHERE claimant_id = ? AND created_at > ?",
                        (user_id, day_ago)).fetchone()["n"]
        if n >= CLAIM_DAILY_LIMIT:
            conn.rollback()
            return False, "daily_limit"
        cur.execute("INSERT INTO match_claims (mode, match_id, claimant_id, opponent_id, note, created_at) "
                    "VALUES (?,?,?,?,?,?)", (mode, match_id, user_id, opp, (note or "").strip()[:CLAIM_NOTE_MAX], time.time()))
        cid = cur.lastrowid
        for i, b in enumerate(imgs):
            cur.execute("INSERT INTO match_claim_images (claim_id, idx, img) VALUES (?,?,?)", (cid, i, b))
        conn.commit()
    finally:
        conn.close()
    logger.info("TEXNIK G'ALABA so'rovi #%s: %s #%s (user %s)", cid, mode, match_id, user_id)
    return True, {"id": cid, "match": m, "opponent_id": opp}


def admin_list(telegram_id: int) -> list[dict]:
    """Admin ko'radigan ochiq ishlar: texnik g'alaba so'rovlari + skrinshotli natijaga e'tirozlar."""
    from match_modes import can_review, get_match
    conn = get_connection()
    try:
        claims = conn.execute(
            "SELECT c.*, a.nickname AS claimant_name, b.nickname AS opponent_name, "
            "(SELECT COUNT(*) FROM match_claim_images i WHERE i.claim_id = c.id) AS n_img "
            "FROM match_claims c JOIN users a ON a.id = c.claimant_id JOIN users b ON b.id = c.opponent_id "
            "WHERE c.status = 'open' ORDER BY c.id LIMIT ?", (ADMIN_LIST_LIMIT,)).fetchall()
        shots = conn.execute(
            "SELECT s.id, s.mode, s.match_id, s.uploader_id, s.opponent_id, s.score1, s.score2, s.played_at, "
            "s.disputed_at, s.status, a.nickname AS uploader_name, b.nickname AS opponent_name "
            "FROM match_shots s JOIN users a ON a.id = s.uploader_id JOIN users b ON b.id = s.opponent_id "
            "WHERE s.status IN ('disputed', 'admin_pending') ORDER BY s.id LIMIT ?", (ADMIN_LIST_LIMIT,)).fetchall()
    finally:
        conn.close()
    out = []
    for r in claims:
        m = get_match(r["mode"], r["match_id"])
        if m and can_review(telegram_id, r["mode"], m):
            out.append({"kind": "tech", **dict(r), "p1": m["player1_id"], "status_match": m.get("status")})
    for r in shots:
        m = get_match(r["mode"], r["match_id"])
        if m and can_review(telegram_id, r["mode"], m):
            out.append({"kind": "shot", **dict(r), "p1": m["player1_id"], "status_match": m.get("status")})
    return out


def claim_image(claim_id: int, idx: int) -> bytes | None:
    conn = get_connection()
    try:
        r = conn.execute("SELECT img FROM match_claim_images WHERE claim_id = ? AND idx = ?", (claim_id, idx)).fetchone()
        return r["img"] if r else None
    finally:
        conn.close()


def _set_status(table: str, item_id: int, status: str, admin_uid: int, from_status: tuple[str, ...]) -> bool:
    conn = get_connection()
    try:
        q = ",".join("?" * len(from_status))
        extra = ", decided_by = ?, decided_at = ?" if table == "match_claims" else ""
        args = [status] + ([admin_uid, time.time()] if extra else []) + [item_id, *from_status]
        cur = conn.execute(f"UPDATE {table} SET status = ?{extra} WHERE id = ? AND status IN ({q})", args)
        conn.commit()
        return cur.rowcount == 1
    finally:
        conn.close()


def decide(admin: dict, kind: str, item_id: int, action: str, s1: int | None = None,
           s2: int | None = None) -> tuple[bool, str | dict]:
    """kind 'tech': action tech_win | reject. kind 'shot': action uphold | set (s1, s2 — player1/player2 tartibida)."""
    from match_modes import can_review, force_set, get_match
    table = "match_claims" if kind == "tech" else "match_shots"
    conn = get_connection()
    try:
        r = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (item_id,)).fetchone()
    finally:
        conn.close()
    if not r:
        return False, "not_found"
    m = get_match(r["mode"], r["match_id"])
    if not m:
        return False, "match_not_found"
    if not can_review(admin["telegram_id"], r["mode"], m):
        return False, "forbidden"
    open_st = ("open",) if kind == "tech" else ("disputed", "admin_pending")
    if r["status"] not in open_st:
        return False, "already_decided"
    if kind == "tech" and action == "tech_win":
        a, b = TECH_WIN if r["claimant_id"] == m["player1_id"] else TECH_WIN[::-1]
        ok, why = force_set(r["mode"], r["match_id"], a, b)
        if not ok:
            return False, why
        _set_status(table, item_id, "approved", admin["id"], open_st)
        return True, {"result": "tech_win", "score": [a, b], "item": dict(r)}
    if kind == "tech" and action == "reject":
        _set_status(table, item_id, "rejected", admin["id"], open_st)
        return True, {"result": "rejected", "item": dict(r)}
    if kind == "shot" and action == "uphold":
        if r["status"] == "admin_pending":
            ok, why = force_set(r["mode"], r["match_id"], r["score1"], r["score2"])
            if not ok:
                return False, why
        _set_status(table, item_id, "upheld", admin["id"], open_st)
        return True, {"result": "upheld", "item": dict(r)}
    if kind == "shot" and action == "set" and s1 is not None and s2 is not None:
        ok, why = force_set(r["mode"], r["match_id"], int(s1), int(s2))
        if not ok:
            return False, why
        _set_status(table, item_id, "fixed", admin["id"], open_st)
        return True, {"result": "fixed", "score": [int(s1), int(s2)], "item": dict(r)}
    return False, "bad_action"
