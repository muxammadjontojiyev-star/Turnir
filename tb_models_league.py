"""
tb_models_league.py — "TEAMLAR JANGI": ligalar jadvali va migratsiya (2026-10-16).

Egasi qarori: bo'limda ALOHIDA LIGALAR — har ligada o'z teamlari, o'z mavsumi/jadvali,
ligani bitta odam (liga admini) boshqaradi, uni bosh admin tayinlaydi. Teamlar ligaga
faqat liga taklif havolasi orqali kiradi (t.me/<bot>?start=tbl_<kod>).

  tb_leagues  — nom (takrorlanmas), belgi, admin_user_id (NULL — faqat bosh admin),
                invite_code, sozlamalar: lineup_min/lineup_max (asosiy tarkib), division_size.
  migrate_leagues() — idempotent:
    1) tb_teams.league_id ustuni (ALTER TABLE ADD COLUMN);
    2) eski tb_seasons (number UNIQUE, league_id yo'q) -> yangi tuzilma (league_id,
       UNIQUE(league_id, number)) — SQLite "12 qadam" usuli, foreign_keys vaqtincha OFF;
    3) league_id'si yo'q eski team/mavsumlar "asosiy" ligaga (TB_DEFAULT_LEAGUE_NAME) o'tadi.
"""

import logging
import secrets

from models import get_connection

logger = logging.getLogger(__name__)

TB_DEFAULT_LEAGUE_NAME = "Teamlar jangi"
TB_DEFAULT_LEAGUE_EMOJI = "⚔️"
TB_LEAGUE_CODE_BYTES = 6

TB_SEASONS_DDL = """
    CREATE TABLE {if_not} {name} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        league_id INTEGER,
        number INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'drawn',
        division_size INTEGER NOT NULL,
        total_rounds INTEGER NOT NULL DEFAULT 0,
        current_round INTEGER NOT NULL DEFAULT 0,
        last_advance_date TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        started_at TIMESTAMP,
        finished_at TIMESTAMP,
        UNIQUE (league_id, number),
        FOREIGN KEY (league_id) REFERENCES tb_leagues(id)
    )
"""
_SEASON_COPY_COLS = ("id, number, status, division_size, total_rounds, current_round, "
                     "last_advance_date, created_at, started_at, finished_at")


def create_league_table(cursor) -> None:
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tb_leagues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL COLLATE NOCASE UNIQUE,
            emoji TEXT,
            admin_user_id INTEGER,
            invite_code TEXT NOT NULL UNIQUE,
            lineup_min INTEGER NOT NULL DEFAULT 6,
            lineup_max INTEGER NOT NULL DEFAULT 20,
            division_size INTEGER NOT NULL DEFAULT 10,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (admin_user_id) REFERENCES users(id)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tb_leagues_admin ON tb_leagues(admin_user_id)")


def _cols(cur, table: str) -> set[str]:
    return {r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()}


def _rebuild_seasons(conn) -> None:
    """Eski tb_seasons -> league_id'li tuzilma. id'lar saqlanadi (bahslar unga bog'langan)."""
    conn.commit()
    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        conn.executescript(
            "BEGIN;"
            + TB_SEASONS_DDL.format(name="tb_seasons_new", if_not="") + ";"
            + f"INSERT INTO tb_seasons_new ({_SEASON_COPY_COLS}) SELECT {_SEASON_COPY_COLS} FROM tb_seasons;"
            "DROP TABLE tb_seasons;"
            "ALTER TABLE tb_seasons_new RENAME TO tb_seasons;"
            "COMMIT;"
        )
    finally:
        conn.execute("PRAGMA foreign_keys = ON")
    logger.info("TB: tb_seasons jadvali ligalar uchun qayta qurildi")


def migrate_leagues() -> None:
    conn = get_connection()
    try:
        cur = conn.cursor()
        create_league_table(cur)
        if "league_id" not in _cols(cur, "tb_teams"):
            cur.execute("ALTER TABLE tb_teams ADD COLUMN league_id INTEGER REFERENCES tb_leagues(id)")
        from tb_logos import init_logo_table
        init_logo_table(cur)                    # 2026-10-16: galereyadan logo (tb_logos, logo_ver)
        conn.commit()
        if "league_id" not in _cols(cur, "tb_seasons"):
            _rebuild_seasons(conn)
            cur = conn.cursor()
        from tb_ucl import init_ucl_columns
        init_ucl_columns(cur)                   # 2026-10-18: UCL formati (qayta qurilgandan KEYIN)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tb_teams_league ON tb_teams(league_id, status)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tb_seasons_league ON tb_seasons(league_id, status)")
        orphan_t = cur.execute("SELECT COUNT(*) FROM tb_teams WHERE league_id IS NULL").fetchone()[0]
        orphan_s = cur.execute("SELECT COUNT(*) FROM tb_seasons WHERE league_id IS NULL").fetchone()[0]
        if orphan_t or orphan_s:
            r = cur.execute("SELECT id FROM tb_leagues WHERE name = ? COLLATE NOCASE",
                            (TB_DEFAULT_LEAGUE_NAME,)).fetchone()
            if r:
                lid = r[0]
            else:
                cur.execute("INSERT INTO tb_leagues (name, emoji, invite_code) VALUES (?, ?, ?)",
                            (TB_DEFAULT_LEAGUE_NAME, TB_DEFAULT_LEAGUE_EMOJI,
                             secrets.token_urlsafe(TB_LEAGUE_CODE_BYTES)))
                lid = cur.lastrowid
            cur.execute("UPDATE tb_teams SET league_id = ? WHERE league_id IS NULL", (lid,))
            cur.execute("UPDATE tb_seasons SET league_id = ? WHERE league_id IS NULL", (lid,))
            logger.info("TB: %s team va %s mavsum '%s' ligasiga o'tkazildi", orphan_t, orphan_s,
                        TB_DEFAULT_LEAGUE_NAME)
        conn.commit()
    finally:
        conn.close()
