"""
qm_core.py — TEZKOR O'YIN: onlayn raqib qidirish va 1v1 o'yin (2026-10-19).

Egasi qarorlari: botdagi HAMMA o'ynay oladi; natijalar ALOHIDA reytingga (qm_ratings) ta'sir qiladi;
suzuvchi tugma — bo'lim tanlash va ligalar sahifasida (static/qm.js).

Oqim:
  1) "Raqib qidirish" -> navbatga (qm_queue). Navbatda boshqasi bo'lsa — darhol juftlanadi.
     Navbatdagi kishi oynani yopsa (QM_QUEUE_STALE_S ichida ping yo'q) — navbatdan tushadi.
  2) Juftlangach (status 'room'): QM_ROOM_MINUTES ichida kimdir eFootball xona ID sini yuborishi
     shart — aks holda o'yin BEKOR qilinadi va natija paneli yopiladi (vaqt cho'zilmasin).
  3) Xona ID yuborilgach ('playing'): QM_PLAY_MINUTES ichida natija kiritilishi kerak, aks holda bekor.
  4) Natija kiritilgach ('awaiting'): raqib tasdiqlaydi/rad etadi; QM_CONFIRM_MINUTES ichida javob
     bermasa — natija AVTOMATIK tasdiqlanadi (cho'zishning foydasi yo'q).
  5) Tasdiqlangach ('confirmed'): reyting — natija + gol farqi (2026-10-19, egasi tanlovi):
     g'alaba QM_WIN_BASE + QM_GD_STEP×farq, mag'lubiyat −(QM_LOSS_BASE + QM_GD_STEP×farq),
     durang +QM_PTS_DRAW; farq QM_GD_CAP gacha hisoblanadi (kuchli o'yinchi yangini "yeb" ketmasin). Bir raqib bilan kuniga QM_SAME_OPP_DAILY tadan ortiq o'yin reytingga ta'sir
     qilmaydi (ball "yig'ib olish"ning oldini olish).
Muddatlar: qm_tick() (scheduler, daqiqada) va har /qm/state so'rovida (lazy) tekshiriladi.
Har o'zgartirish BEGIN IMMEDIATE ichida (qoida #38).
"""

import logging

from models import get_connection

logger = logging.getLogger(__name__)

QM_ROOM_MINUTES = 3            # juftlangach xona ID yuborish muddati
QM_PLAY_MINUTES = 40           # xona ID dan keyin natija kiritish muddati
QM_CONFIRM_MINUTES = 10        # raqib tasdiqlamasa — avtomatik tasdiq
QM_QUEUE_STALE_S = 25          # navbatda ping kelmasa — tushib qoladi
QM_ONLINE_S = 120              # "onlayn" deb hisoblanadigan oxirgi faollik
QM_BASE_RATING = 1000
QM_WIN_BASE = 10              # g'alaba: asosiy ball
QM_LOSS_BASE = 5              # mag'lubiyat: asosiy ayirma
QM_GD_STEP = 2                # har gol farqi uchun
QM_GD_CAP = 5                 # gol farqi ko'pi bilan shuncha hisoblanadi (g'alaba max +20, mag'lubiyat max −15)
QM_PTS_DRAW = 3
QM_SAME_OPP_DAILY = 3
QM_SCORE_MAX = 30
ST_ROOM, ST_PLAYING, ST_AWAITING, ST_CONFIRMED, ST_CANCELLED = (
    "room", "playing", "awaiting_confirmation", "confirmed", "cancelled")
ACTIVE = (ST_ROOM, ST_PLAYING, ST_AWAITING)


def init_qm_tables(cur) -> None:
    cur.execute("""
        CREATE TABLE IF NOT EXISTS qm_queue (
            user_id INTEGER PRIMARY KEY,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_ping TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    # round — chat_report/room_code/chat_images umumiy modullari kutgan ustun (doim 1)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS qm_matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player1_id INTEGER NOT NULL,
            player2_id INTEGER NOT NULL,
            round INTEGER NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'room',
            score1 INTEGER, score2 INTEGER,
            submitted_by INTEGER,
            room_code TEXT,
            rated INTEGER NOT NULL DEFAULT 1,
            delta1 INTEGER, delta2 INTEGER,
            cancel_reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            room_deadline TIMESTAMP,
            play_deadline TIMESTAMP,
            submitted_at TIMESTAMP,
            finished_at TIMESTAMP,
            FOREIGN KEY (player1_id) REFERENCES users(id),
            FOREIGN KEY (player2_id) REFERENCES users(id)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_qm_m_p1 ON qm_matches(player1_id, status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_qm_m_p2 ON qm_matches(player2_id, status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_qm_m_status ON qm_matches(status)")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS qm_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id INTEGER NOT NULL,
            sender_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            is_read INTEGER NOT NULL DEFAULT 0,
            read_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (match_id) REFERENCES qm_matches(id)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_qm_msg_match ON qm_messages(match_id)")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS qm_ratings (
            user_id INTEGER PRIMARY KEY,
            rating INTEGER NOT NULL DEFAULT 1000,
            played INTEGER NOT NULL DEFAULT 0,
            wins INTEGER NOT NULL DEFAULT 0,
            draws INTEGER NOT NULL DEFAULT 0,
            losses INTEGER NOT NULL DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_qm_rating ON qm_ratings(rating DESC)")


def _tx(fn):
    conn = get_connection()
    conn.isolation_level = None
    cur = conn.cursor()
    try:
        cur.execute("BEGIN IMMEDIATE")
        res = fn(cur)
        cur.execute("COMMIT")
        return res
    except Exception:
        try:
            cur.execute("ROLLBACK")
        except Exception:
            logger.exception("qm: ROLLBACK xatosi")
        raise
    finally:
        conn.close()


def _active_match(cur, user_id: int):
    return cur.execute(
        f"SELECT * FROM qm_matches WHERE (player1_id = ? OR player2_id = ?) AND status IN "
        f"({','.join('?' * len(ACTIVE))}) ORDER BY id DESC LIMIT 1", (user_id, user_id, *ACTIVE)).fetchone()


# ------------------------------------------------------------------ muddatlar

def _expire_cur(cur) -> list[int]:
    """Muddati o'tgan o'yinlar: room/playing -> cancelled, awaiting -> confirmed. Qaytaradi: tasdiqlanganlar."""
    cur.execute("UPDATE qm_matches SET status = ?, cancel_reason = 'no_room', finished_at = datetime('now') "
                "WHERE status = ? AND room_deadline < datetime('now')", (ST_CANCELLED, ST_ROOM))
    cur.execute("UPDATE qm_matches SET status = ?, cancel_reason = 'no_result', finished_at = datetime('now') "
                "WHERE status = ? AND play_deadline < datetime('now')", (ST_CANCELLED, ST_PLAYING))
    cur.execute("SELECT id FROM qm_matches WHERE status = ? AND submitted_at < datetime('now', ?)",
                (ST_AWAITING, f"-{QM_CONFIRM_MINUTES} minutes"))
    ids = [r["id"] for r in cur.fetchall()]
    for mid in ids:
        _confirm_cur(cur, mid)
    cur.execute("DELETE FROM qm_queue WHERE last_ping < datetime('now', ?)", (f"-{QM_QUEUE_STALE_S} seconds",))
    return ids


def qm_tick() -> int:
    """Scheduler (daqiqada bir): muddatlarni tekshiradi. Qaytaradi: avtomatik tasdiqlanganlar soni."""
    return len(_tx(_expire_cur))


# ------------------------------------------------------------------ reyting

def _rating_row(cur, user_id: int) -> dict:
    r = cur.execute("SELECT rating, played, wins, draws, losses FROM qm_ratings WHERE user_id = ?",
                    (user_id,)).fetchone()
    return dict(r) if r else {"rating": QM_BASE_RATING, "played": 0, "wins": 0, "draws": 0, "losses": 0}


def _apply(cur, user_id: int, delta: int, res: str) -> None:
    cur.execute("INSERT OR IGNORE INTO qm_ratings (user_id, rating) VALUES (?, ?)", (user_id, QM_BASE_RATING))
    col = {"w": "wins", "d": "draws", "l": "losses"}[res]
    cur.execute(f"UPDATE qm_ratings SET rating = MAX(0, rating + ?), played = played + 1, {col} = {col} + 1, "
                "updated_at = datetime('now') WHERE user_id = ?", (delta, user_id))


def qm_points(a: int, b: int) -> tuple[int, int]:
    """(g'olib balli, mag'lub balli) gol farqi bo'yicha. Durangda ishlatilmaydi."""
    gd = min(abs(a - b), QM_GD_CAP)
    return QM_WIN_BASE + QM_GD_STEP * gd, -(QM_LOSS_BASE + QM_GD_STEP * gd)


def _confirm_cur(cur, match_id: int) -> None:
    m = cur.execute("SELECT * FROM qm_matches WHERE id = ?", (match_id,)).fetchone()
    if not m or m["status"] == ST_CONFIRMED:
        return
    p1, p2 = m["player1_id"], m["player2_id"]
    n_today = cur.execute(
        "SELECT COUNT(*) AS c FROM qm_matches WHERE status = ? AND rated = 1 AND date(finished_at) = date('now') "
        "AND ((player1_id = ? AND player2_id = ?) OR (player1_id = ? AND player2_id = ?))",
        (ST_CONFIRMED, p1, p2, p2, p1)).fetchone()["c"]
    rated = n_today < QM_SAME_OPP_DAILY
    s1, s2 = m["score1"], m["score2"]
    win, loss = qm_points(s1, s2)
    if s1 > s2:
        d1, d2, r1, r2 = win, loss, "w", "l"
    elif s1 < s2:
        d1, d2, r1, r2 = loss, win, "l", "w"
    else:
        d1 = d2 = QM_PTS_DRAW
        r1 = r2 = "d"
    if not rated:
        d1 = d2 = 0
    _apply(cur, p1, d1, r1)
    _apply(cur, p2, d2, r2)
    cur.execute("UPDATE qm_matches SET status = ?, rated = ?, delta1 = ?, delta2 = ?, finished_at = datetime('now') "
                "WHERE id = ?", (ST_CONFIRMED, 1 if rated else 0, d1, d2, match_id))


# ------------------------------------------------------------------ qidirish

def qm_search(user_id: int) -> dict:
    """
    Navbatga turadi yoki darhol juftlanadi. Qaytaradi: {matched: match_id | None, opponent_id}.
    Faol o'yini bo'lsa — o'sha qaytadi.
    """
    def run(cur):
        _expire_cur(cur)
        m = _active_match(cur, user_id)
        if m:
            return {"matched": m["id"], "opponent_id": None, "existing": True}
        cur.execute("SELECT q.user_id FROM qm_queue q WHERE q.user_id != ? AND q.last_ping >= datetime('now', ?) "
                    "ORDER BY q.joined_at LIMIT 1", (user_id, f"-{QM_QUEUE_STALE_S} seconds"))
        opp = cur.fetchone()
        if not opp:
            cur.execute("INSERT INTO qm_queue (user_id) VALUES (?) ON CONFLICT(user_id) DO UPDATE SET "
                        "last_ping = datetime('now')", (user_id,))
            return {"matched": None, "opponent_id": None}
        opp_id = opp["user_id"]
        cur.execute("DELETE FROM qm_queue WHERE user_id IN (?, ?)", (user_id, opp_id))
        cur.execute("INSERT INTO qm_matches (player1_id, player2_id, status, room_deadline) "
                    "VALUES (?, ?, ?, datetime('now', ?))", (opp_id, user_id, ST_ROOM, f"+{QM_ROOM_MINUTES} minutes"))
        mid = cur.lastrowid
        logger.info("Tezkor o'yin #%s: %s vs %s", mid, opp_id, user_id)
        return {"matched": mid, "opponent_id": opp_id}
    return _tx(run)


def qm_cancel(user_id: int) -> dict:
    """Navbatdan chiqish yoki (faqat 'room' bosqichida) o'yinni bekor qilish."""
    def run(cur):
        cur.execute("DELETE FROM qm_queue WHERE user_id = ?", (user_id,))
        m = _active_match(cur, user_id)
        if m and m["status"] == ST_ROOM:
            cur.execute("UPDATE qm_matches SET status = ?, cancel_reason = 'cancelled', finished_at = datetime('now') "
                        "WHERE id = ?", (ST_CANCELLED, m["id"]))
            return {"cancelled_match": m["id"]}
        return {"cancelled_match": None}
    return _tx(run)


def qm_room_allowed(user_id: int, match_id: int) -> tuple[bool, str]:
    """Xona ID yuborish mumkinmi (o'yin faol va muddati o'tmagan). Sabablar: match_not_found, match_closed."""
    def run(cur):
        _expire_cur(cur)
        m = cur.execute("SELECT player1_id, player2_id, status FROM qm_matches WHERE id = ?", (match_id,)).fetchone()
        if not m or user_id not in (m["player1_id"], m["player2_id"]):
            return False, "match_not_found"
        return (True, "ok") if m["status"] in ACTIVE else (False, "match_closed")
    return _tx(run)


def qm_set_room(user_id: int, match_id: int, code: str) -> tuple[bool, str]:
    """Xona ID yuborilgach (room_code.send_room_code chat xabarini yozadi): room -> playing."""
    def run(cur):
        m = cur.execute("SELECT * FROM qm_matches WHERE id = ?", (match_id,)).fetchone()
        if not m or user_id not in (m["player1_id"], m["player2_id"]):
            return False, "match_not_found"
        if m["status"] == ST_ROOM:
            cur.execute("UPDATE qm_matches SET status = ?, room_code = ?, play_deadline = datetime('now', ?) "
                        "WHERE id = ?", (ST_PLAYING, code, f"+{QM_PLAY_MINUTES} minutes", match_id))
        elif m["status"] in (ST_PLAYING, ST_AWAITING):
            cur.execute("UPDATE qm_matches SET room_code = ? WHERE id = ?", (code, match_id))
        else:
            return False, "match_closed"
        return True, "ok"
    return _tx(run)


def _valid_score(x) -> int | None:
    try:
        v = int(x)
    except (TypeError, ValueError):
        return None
    return v if 0 <= v <= QM_SCORE_MAX else None


def qm_submit(user_id: int, my_score, opp_score) -> tuple[bool, str | dict]:
    """Sabablar: bad_score, no_match, no_room_yet, already_submitted."""
    mine, opp = _valid_score(my_score), _valid_score(opp_score)
    if mine is None or opp is None:
        return False, "bad_score"

    def run(cur):
        _expire_cur(cur)
        m = _active_match(cur, user_id)
        if not m:
            return False, "no_match"
        if m["status"] == ST_ROOM:
            return False, "no_room_yet"
        if m["status"] == ST_AWAITING:
            return False, "already_submitted"
        s1, s2 = (mine, opp) if user_id == m["player1_id"] else (opp, mine)
        cur.execute("UPDATE qm_matches SET score1 = ?, score2 = ?, submitted_by = ?, status = ?, "
                    "submitted_at = datetime('now') WHERE id = ?", (s1, s2, user_id, ST_AWAITING, m["id"]))
        opp_id = m["player2_id"] if user_id == m["player1_id"] else m["player1_id"]
        return True, {"match_id": m["id"], "opponent_id": opp_id}
    return _tx(run)


def qm_confirm(user_id: int, accept: bool) -> tuple[bool, str | dict]:
    """Sabablar: no_match, nothing_to_confirm, own_submission."""
    def run(cur):
        _expire_cur(cur)
        m = _active_match(cur, user_id)
        if not m:
            return False, "no_match"
        if m["status"] != ST_AWAITING:
            return False, "nothing_to_confirm"
        if m["submitted_by"] == user_id:
            return False, "own_submission"
        if accept:
            _confirm_cur(cur, m["id"])
        else:
            cur.execute("UPDATE qm_matches SET status = ?, score1 = NULL, score2 = NULL, submitted_by = NULL, "
                        "submitted_at = NULL WHERE id = ?", (ST_PLAYING, m["id"]))
        return True, {"match_id": m["id"], "submitter_id": m["submitted_by"], "accepted": bool(accept)}
    return _tx(run)
