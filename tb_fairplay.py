"""
tb_fairplay.py — "TEAMLAR JANGI": halol o'yin dalillari (2026-10-25).

3-bosqich — natija skrinshoti (majburiy):
  Natijani kiritgan o'yinchi avval yakun ekrani skrinshotini o'yin chatiga yuboradi
  (mavjud chat_images tizimi: POST /chat/image, mode='tb' — rasm chatda ham dalil bo'lib qoladi,
  raqibga bot orqali boradi). So'ng /tb/game/submit ga shu rasm tokeni (proof_token) beriladi.
  Server tekshiradi: token shu o'yinga va SHU o'yinchiga tegishli (tb_proof_valid).
  tb_games.proof_token — raqib tasdiqlashdan oldin, admin nizoda ko'radi.
  Rad etilsa token tozalanadi (qayta kiritishda yangi skrinshot).
  Admin natijani qo'ysa (tb_admin_set) — skrinshot talab qilinmaydi.

4-bosqich — «Boshqa odam o'ynadi» shikoyati (tb_reports):
  O'yin ishtirokchisi raqibi ustidan shikoyat qiladi (bir o'yinga bir marta — UNIQUE, qoida #38),
  liga adminiga bot xabari boradi. Admin skrinshot va chatni ko'rib qaror qiladi:
    dismiss  — asossiz (natija o'zgarmaydi);
    replay   — natija tozalanadi, qayta o'ynash (faqat tur ochiq bo'lsa; tb_games.tb_admin_reset);
    tech     — raqibga texnik mag'lubiyat TB_TECH_SCORE (tb_games.tb_admin_set, bahs qayta hisoblanadi).
  Shikoyatchiga qaror haqida bot xabari boradi (tb_api_fairplay.py).

Migratsiya: init_tb_fairplay_tables(cursor) — tb_models.init_tb_tables ichidan (idempotent, qoida #31).
"""

import logging
import re

from models import get_connection

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"^[0-9a-f]{32}$")
TB_IMAGE_MODE = "tb"                  # chat_images.mode (chat_report.MODES kaliti)
TB_REPORT_NOTE_MAX = 300
TB_TECH_SCORE = (3, 0)                # texnik g'alaba : mag'lubiyat (shikoyatchi foydasiga)
REPORT_OPEN, REPORT_RESOLVED = "open", "resolved"
DECISIONS = ("dismiss", "replay", "tech")


def _cols(cursor, table: str) -> set[str]:
    return {r["name"] for r in cursor.execute(f"PRAGMA table_info({table})").fetchall()}


def init_tb_fairplay_tables(cursor) -> None:
    if "proof_token" not in _cols(cursor, "tb_games"):
        cursor.execute("ALTER TABLE tb_games ADD COLUMN proof_token TEXT")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tb_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER NOT NULL,
            reporter_id INTEGER NOT NULL,
            accused_id INTEGER NOT NULL,
            note TEXT,
            status TEXT NOT NULL DEFAULT 'open',
            decision TEXT,
            resolved_by INTEGER,
            resolved_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (game_id, reporter_id),
            FOREIGN KEY (game_id) REFERENCES tb_games(id),
            FOREIGN KEY (reporter_id) REFERENCES users(id),
            FOREIGN KEY (accused_id) REFERENCES users(id)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tb_reports_status ON tb_reports(status)")


def tb_proof_valid(cursor, token: str | None, game_id: int, user_id: int) -> bool:
    """Rasm shu o'yin chatiga shu o'yinchi tomonidan yuborilganmi (qoida #34, #41)."""
    if not token or not _TOKEN_RE.match(token):
        return False
    r = cursor.execute("SELECT 1 FROM chat_images WHERE token = ? AND mode = ? AND match_id = ? AND sender_id = ?",
                       (token, TB_IMAGE_MODE, game_id, user_id)).fetchone()
    return r is not None


# ------------------------------------------------------------------ 4-bosqich: shikoyat

def tb_report_create(user_id: int, game_id: int, note: str | None) -> tuple[bool, str | dict]:
    """Sabablar: game_not_found, not_your_game, already_reported, note_too_long."""
    note = " ".join(str(note or "").split()) or None
    if note and len(note) > TB_REPORT_NOTE_MAX:
        return False, "note_too_long"
    conn = get_connection()
    conn.isolation_level = None
    cur = conn.cursor()
    cur.execute("BEGIN IMMEDIATE")
    try:
        g = cur.execute("SELECT home_user_id, away_user_id FROM tb_games WHERE id = ?", (game_id,)).fetchone()
        if not g:
            cur.execute("ROLLBACK")
            return False, "game_not_found"
        if user_id not in (g["home_user_id"], g["away_user_id"]):
            cur.execute("ROLLBACK")
            return False, "not_your_game"
        if cur.execute("SELECT 1 FROM tb_reports WHERE game_id = ? AND reporter_id = ?",
                       (game_id, user_id)).fetchone():
            cur.execute("ROLLBACK")
            return False, "already_reported"
        accused = g["away_user_id"] if user_id == g["home_user_id"] else g["home_user_id"]
        cur.execute("INSERT INTO tb_reports (game_id, reporter_id, accused_id, note) VALUES (?, ?, ?, ?)",
                    (game_id, user_id, accused, note))
        rid = cur.lastrowid
        cur.execute("COMMIT")
        logger.info("TB shikoyat #%s: game=%s reporter=%s accused=%s", rid, game_id, user_id, accused)
        return True, {"report_id": rid}
    except Exception:
        cur.execute("ROLLBACK")
        raise
    finally:
        conn.close()


def tb_my_reports(user_id: int, game_ids: list[int]) -> dict[int, dict]:
    """{game_id: {status, decision}} — Jang kartasida «shikoyat yuborilgan» holati uchun."""
    if not game_ids:
        return {}
    conn = get_connection()
    try:
        marks = ",".join("?" * len(game_ids))
        rows = conn.cursor().execute(f"SELECT game_id, status, decision FROM tb_reports WHERE reporter_id = ? "
                                     f"AND game_id IN ({marks})", (user_id, *game_ids)).fetchall()
        return {r["game_id"]: {"status": r["status"], "decision": r["decision"]} for r in rows}
    finally:
        conn.close()


_REPORT_SQL = (
    "SELECT r.id, r.game_id, r.note, r.status, r.decision, r.created_at, r.resolved_at, "
    "r.reporter_id, r.accused_id, g.score1, g.score2, g.status AS game_status, g.proof_token, g.slot, "
    "g.home_user_id, f.round, f.status AS fixture_status, s.league_id, ht.name AS home_team, at.name AS away_team, "
    "ru.username AS reporter_username, ru.nickname AS reporter_nick, "
    "au.username AS accused_username, au.nickname AS accused_nick "
    "FROM tb_reports r JOIN tb_games g ON g.id = r.game_id JOIN tb_fixtures f ON f.id = g.fixture_id "
    "JOIN tb_seasons s ON s.id = f.season_id "
    "JOIN tb_teams ht ON ht.id = f.home_team_id JOIN tb_teams at ON at.id = f.away_team_id "
    "JOIN users ru ON ru.id = r.reporter_id JOIN users au ON au.id = r.accused_id "
)


def tb_reports_list(league_id: int, status: str | None = REPORT_OPEN, limit: int = 50) -> list[dict]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        if status:
            cur.execute(_REPORT_SQL + "WHERE s.league_id = ? AND r.status = ? ORDER BY r.id DESC LIMIT ?",
                        (league_id, status, limit))
        else:
            cur.execute(_REPORT_SQL + "WHERE s.league_id = ? ORDER BY r.id DESC LIMIT ?", (league_id, limit))
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def tb_report_get(report_id: int) -> dict | None:
    conn = get_connection()
    try:
        r = conn.cursor().execute(_REPORT_SQL + "WHERE r.id = ?", (report_id,)).fetchone()
        return dict(r) if r else None
    finally:
        conn.close()


def tb_report_resolve(report_id: int, decision: str, admin_user_id: int) -> tuple[bool, str | dict]:
    """Sabablar: bad_decision, report_not_found, already_resolved, round_closed, game_not_found."""
    if decision not in DECISIONS:
        return False, "bad_decision"
    rep = tb_report_get(report_id)
    if not rep:
        return False, "report_not_found"
    if rep["status"] != REPORT_OPEN:
        return False, "already_resolved"
    from tb_games import tb_admin_reset, tb_admin_set
    if decision == "replay":
        ok, why = tb_admin_reset(rep["game_id"])
        if not ok:
            return False, why
    elif decision == "tech":
        win, loss = TB_TECH_SCORE
        reporter_home = rep["reporter_id"] == rep["home_user_id"]
        ok, why = tb_admin_set(rep["game_id"], *((win, loss) if reporter_home else (loss, win)))
        if not ok:
            return False, why
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE tb_reports SET status = ?, decision = ?, resolved_by = ?, resolved_at = CURRENT_TIMESTAMP "
                    "WHERE id = ? AND status = ?", (REPORT_RESOLVED, decision, admin_user_id, report_id, REPORT_OPEN))
        conn.commit()
    finally:
        conn.close()
    logger.info("TB shikoyat #%s: qaror=%s (admin=%s)", report_id, decision, admin_user_id)
    return True, {"report_id": report_id, "decision": decision, "game_id": rep["game_id"],
                  "reporter_id": rep["reporter_id"]}
