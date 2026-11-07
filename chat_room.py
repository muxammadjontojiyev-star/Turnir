"""
chat_room.py — XONA ID ALMASHINUVI — qo'lda natija sharti (2026-11-07, egasi: «tex win dan ko'p hisob kiritish uchun
chatda bir tomon xona ID yuborgan, ikkinchi tomon esa uni o'qib nusxalagan bo'lishi kerak»; «har qanday qo'lda natija»).

  * «Yuborilgan ID» — shu o'yin bot chatidagi xabar: «🎮 Xona ID: <kod>» (room_code.py tugmasi) yoki matndagi
    alohida 8 xonali son (o'yinchilar ID ni qo'lda yozganda; chatda u ham bosib nusxalanadi).
  * «Nusxalangan» — RAQIB tomoni chatda o'sha ID ni bosgan (static/crule.js → POST /crule/room-copy). Telegram
    xabaridagi ID hisobga olinmaydi — shuning uchun xona ID endi Telegramda ko'rsatilmaydi (notify_room_code_app).
  * Kim yuborgani farqi yo'q: A yuborib B nusxalasa ham, B yuborib A nusxalasa ham — ikkalasi natija kirita oladi.
"""

import logging
import re
import time

from models import get_connection

logger = logging.getLogger(__name__)

ROOM_PREFIX_RE = re.compile(r"^🎮 Xona ID:\s*([A-Za-z0-9]{4,16})\s*$")   # room_code.ROOM_CODE_PREFIX bilan bir xil
ROOM_DIGITS_RE = re.compile(r"(?<!\d)(\d{8})(?!\d)")                     # api.js chatTextWithCopyableIds bilan bir xil
ROOM_CODE_MAX = 16


def migrate_room_copies(cur) -> None:
    cur.execute("CREATE TABLE IF NOT EXISTS room_copies (id INTEGER PRIMARY KEY AUTOINCREMENT, mode TEXT NOT NULL, "
                "match_id INTEGER NOT NULL, user_id INTEGER NOT NULL, code TEXT NOT NULL, created_at REAL NOT NULL, "
                "UNIQUE(mode, match_id, user_id, code))")


def codes_in(text: str) -> set[str]:
    t = str(text or "").strip()
    m = ROOM_PREFIX_RE.match(t)
    out = {m.group(1).upper()} if m else set()
    return out | {x for x in ROOM_DIGITS_RE.findall(t)}


def sent_codes(mode: str, match_id: int) -> dict[int, set[str]]:
    """{sender_user_id: {kodlar}} — shu o'yin chatida kim qaysi xona ID ni yuborgan."""
    from chat_report import MODES as CHAT_MODES
    cfg = CHAT_MODES.get(mode)
    if not cfg:
        return {}
    sql = f"SELECT sender_id, text FROM {cfg['msg_table']} WHERE match_id = ?"
    args: list = [int(match_id)]
    if cfg.get("playoff") is not None:
        sql += " AND is_playoff = ?"
        args.append(int(cfg["playoff"]))
    conn = get_connection()
    try:
        rows = conn.execute(sql, args).fetchall()
    finally:
        conn.close()
    out: dict[int, set[str]] = {}
    for r in rows:
        c = codes_in(r["text"])
        if c:
            out.setdefault(int(r["sender_id"]), set()).update(c)
    return out


def _copied(mode: str, match_id: int, user_id: int) -> set[str]:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT code FROM room_copies WHERE mode = ? AND match_id = ? AND user_id = ?",
                            (mode, int(match_id), int(user_id))).fetchall()
    except Exception:
        return set()                                    # jadval hali yo'q (migratsiyadan oldin)
    finally:
        conn.close()
    return {str(r["code"]).upper() for r in rows}


def record_copy(mode: str, match: dict, me: int, code: str) -> tuple[bool, str]:
    """Raqib yuborgan ID ni men nusxaladim — yozib qo'yiladi (takror bosish — bir marta)."""
    p1, p2 = match.get("player1_id"), match.get("player2_id")
    if me not in (p1, p2) or not p1 or not p2:
        return False, "not_participant"
    code = re.sub(r"[^A-Za-z0-9]", "", str(code or ""))[:ROOM_CODE_MAX].upper()
    opp = p2 if me == p1 else p1
    if not code or code not in sent_codes(mode, int(match["id"])).get(opp, set()):
        return False, "room_not_from_opponent"          # o'z ID im yoki chatda yo'q kod — sanalmaydi
    conn = get_connection()
    try:
        conn.execute("INSERT OR IGNORE INTO room_copies (mode, match_id, user_id, code, created_at) VALUES (?,?,?,?,?)",
                     (mode, int(match["id"]), me, code, time.time()))
        conn.commit()
    finally:
        conn.close()
    logger.info("XONA ID: %s #%s — user %s nusxaladi: %s", mode, match["id"], me, code)
    return True, "ok"


def room_check(mode: str, match_id: int, me: int, opp: int) -> tuple[bool, str]:
    """(ok, sabab): bir tomon yuborgan ID ni ikkinchi tomon nusxalaganmi."""
    sent = sent_codes(mode, match_id)
    mine, theirs = sent.get(me, set()), sent.get(opp, set())
    if (theirs & _copied(mode, match_id, me)) or (mine & _copied(mode, match_id, opp)):
        return True, "ok"
    if theirs:
        return False, "room_you_not_copied"            # raqib yubordi — siz chatda bosib nusxalamagansiz
    if mine:
        return False, "room_opp_not_copied"            # siz yubordingiz — raqib hali nusxalamagan
    return False, "room_not_sent"
