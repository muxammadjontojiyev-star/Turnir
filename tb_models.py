"""
tb_models.py — "TEAMLAR JANGI" bo'limi jadvallari (2026-10-15, 1-bosqich).

Rasmiy va shaxsiy turnirlardan TO'LIQ ajratilgan 3-bo'lim. 1-bosqichda faqat
teamlar va a'zolar (mavsum/divizion/o'yinlar — 2-bosqichda alohida jadvallar).
models.init_db() oxirida init_tb_tables() chaqiriladi (CREATE IF NOT EXISTS — idempotent).

  tb_teams    — team: nom (takrorlanmas, katta-kichik harf farqsiz), belgi (emoji),
                sardor, taklif kodi, holat (pending -> approved | rejected).
  tb_members  — a'zolik: bir kishi FAQAT bitta teamda (UNIQUE user_id);
                role: captain | member; in_lineup/lineup_pos — sardor tuzgan asosiy tarkib.
  2-bosqich: tb_seasons, tb_season_teams, tb_fixtures (team bahsi), tb_games (1v1).
  3-bosqich: tb_messages (1v1 chat), tb_games_v (ko'rinish), tb_titles (divizion chempionlari).
  2026-10-16 (ligalar): tb_leagues — har liga o'z admini, havolasi, sozlamalari bilan;
                tb_teams.league_id, tb_seasons.league_id (mavsum raqami liga ichida).
                Eski ma'lumot (league_id NULL) — tb_models_league.migrate_leagues() "asosiy" ligaga o'tkazadi.
"""

from models import get_connection


def init_tb_tables() -> None:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tb_teams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL COLLATE NOCASE UNIQUE,
                emoji TEXT,
                captain_user_id INTEGER NOT NULL,
                invite_code TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL DEFAULT 'pending',
                reject_reason TEXT,
                reviewed_by INTEGER,
                reviewed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (captain_user_id) REFERENCES users(id)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tb_teams_status ON tb_teams(status)")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tb_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL UNIQUE,
                role TEXT NOT NULL DEFAULT 'member',
                in_lineup INTEGER NOT NULL DEFAULT 0,
                lineup_pos INTEGER,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (team_id) REFERENCES tb_teams(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tb_members_team ON tb_members(team_id)")

        # ---- 2-bosqich (2026-10-16): mavsum, divizionlar, team bahslari, 1v1 o'yinlar ----
        # tb_seasons: har ligada bir vaqtda bitta faol mavsum (status != 'finished').
        #   drawn -> running -> finished; current_round — ochiq tur; last_advance_date — kunlik siljish.
        #   2026-10-16: league_id + UNIQUE(league_id, number) — eski jadval tb_models_league'da qayta quriladi.
        from tb_models_league import TB_SEASONS_DDL, create_league_table
        create_league_table(cursor)
        cursor.execute(TB_SEASONS_DDL.format(name="tb_seasons", if_not="IF NOT EXISTS"))
        # tb_season_teams: qaysi team qaysi divizionda (mavsum boshida qotadi)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tb_season_teams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                season_id INTEGER NOT NULL,
                team_id INTEGER NOT NULL,
                division INTEGER NOT NULL,
                UNIQUE (season_id, team_id),
                FOREIGN KEY (season_id) REFERENCES tb_seasons(id),
                FOREIGN KEY (team_id) REFERENCES tb_teams(id)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tb_st_div ON tb_season_teams(season_id, division)")
        # tb_fixtures: ikki team bahsi (divizion ichida bir martalik aylanma).
        #   scheduled -> open (tur ochilganda 1v1 juftliklar yaratiladi) -> finished.
        #   technical: 'home' | 'away' | 'both' — tarkibi yetmagan tomon (texnik mag'lubiyat).
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tb_fixtures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                season_id INTEGER NOT NULL,
                division INTEGER NOT NULL,
                round INTEGER NOT NULL,
                home_team_id INTEGER NOT NULL,
                away_team_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'scheduled',
                home_wins INTEGER NOT NULL DEFAULT 0,
                away_wins INTEGER NOT NULL DEFAULT 0,
                draws INTEGER NOT NULL DEFAULT 0,
                home_goals INTEGER NOT NULL DEFAULT 0,
                away_goals INTEGER NOT NULL DEFAULT 0,
                technical TEXT,
                FOREIGN KEY (season_id) REFERENCES tb_seasons(id),
                FOREIGN KEY (home_team_id) REFERENCES tb_teams(id),
                FOREIGN KEY (away_team_id) REFERENCES tb_teams(id)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tb_fx_round ON tb_fixtures(season_id, round)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tb_fx_div ON tb_fixtures(season_id, division, round)")
        # tb_games: bahs ichidagi 1v1 o'yin (score1 — home o'yinchi, score2 — away o'yinchi)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tb_games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fixture_id INTEGER NOT NULL,
                slot INTEGER NOT NULL,
                home_user_id INTEGER NOT NULL,
                away_user_id INTEGER NOT NULL,
                score1 INTEGER,
                score2 INTEGER,
                submitted_by INTEGER,
                status TEXT NOT NULL DEFAULT 'pending',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (fixture_id) REFERENCES tb_fixtures(id),
                FOREIGN KEY (home_user_id) REFERENCES users(id),
                FOREIGN KEY (away_user_id) REFERENCES users(id)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tb_games_fx ON tb_games(fixture_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tb_games_home ON tb_games(home_user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tb_games_away ON tb_games(away_user_id)")

        # ---- 3-bosqich (2026-10-16): 1v1 chat, umumiy chat modullari uchun ko'rinish, unvonlar ----
        # tb_messages: o'yin chati (match_id = tb_games.id) — pt_messages bilan bir xil tuzilma
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tb_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER NOT NULL,
                sender_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                is_read INTEGER NOT NULL DEFAULT 0,
                read_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (match_id) REFERENCES tb_games(id)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tb_messages_match ON tb_messages(match_id)")
        # tb_games_v: chat_report / chat_images / room_code kutgan ustun nomlari (player1_id, player2_id, round)
        cursor.execute("""
            CREATE VIEW IF NOT EXISTS tb_games_v AS
            SELECT g.id, g.home_user_id AS player1_id, g.away_user_id AS player2_id,
                   f.round AS round, g.score1, g.score2, g.status
            FROM tb_games g JOIN tb_fixtures f ON f.id = g.fixture_id
        """)
        # tb_titles: mavsum yakunida divizion g'oliblari (1-o'rin) — team sahifasida kubok
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tb_titles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                season_id INTEGER NOT NULL,
                season_number INTEGER NOT NULL,
                division INTEGER NOT NULL,
                team_id INTEGER NOT NULL,
                team_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (season_id, division),
                FOREIGN KEY (team_id) REFERENCES tb_teams(id)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tb_titles_team ON tb_titles(team_id)")
        from tb_fairplay import init_tb_fairplay_tables   # 2026-10-25: natija skrinshoti (tb_games.proof_token)
        init_tb_fairplay_tables(cursor)
        conn.commit()
    finally:
        conn.close()
    from tb_models_league import migrate_leagues
    migrate_leagues()                       # 2026-10-16: ligalar (idempotent)
