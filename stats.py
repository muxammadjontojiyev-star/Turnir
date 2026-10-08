"""
stats.py — bot statistikasi (2026-10-08). Faqat o'qish, DB yozilmaydi (qoida #25).

Admin so'rovi: botdan qancha odam foydalanayotganini bilish — Admin paneldagi "📊 Statistika"
(GET /admin/stats) va botdagi /stats buyrug'i (faqat bosh admin). Ikkalasi shu bitta
funksiyadan oladi (qoida #26).

Manbalar:
  - users.registered_at — botga birinchi kirgan vaqt (UTC);
  - users.last_seen — ilovadagi har bir so'rovda yangilanadi (api.get_authenticated_user ->
    touch_last_seen), shuning uchun "faol" = shu davrda ilovani ochgan;
  - rejimlar: registrations (liga), wc_registrations, cl/el_participants (joriy mavsum),
    div_registrations (bugungi kun), pt_* (shaxsiy turnirlar).
Kun chegarasi — Toshkent vaqti (UTC+5, config.TOURNAMENT_TIMEZONE_OFFSET).
"""

import logging
import sqlite3

from config import TOURNAMENT_TIMEZONE_OFFSET
from models import get_connection

logger = logging.getLogger(__name__)

ONLINE_MINUTES = 5          # "hozir onlayn" — so'nggi 5 daqiqada so'rov yuborgan
GROWTH_DAYS = 14            # kunlik yangi foydalanuvchilar grafigi uchun
_TZ = f"{TOURNAMENT_TIMEZONE_OFFSET:+d} hours"


def _one(cursor, sql: str, args: tuple = ()) -> int:
    """Bitta son; jadval/ustun yo'q bo'lsa (eski baza) — 0, xato log'ga (qoida #44)."""
    try:
        r = cursor.execute(sql, args).fetchone()
        return int(r[0] or 0) if r else 0
    except sqlite3.OperationalError as exc:
        logger.warning("stats: so'rov bajarilmadi (%s): %s", exc, sql[:80])
        return 0


def get_bot_stats() -> dict:
    conn = get_connection()
    c = conn.cursor()
    try:
        today = f"date('now', '{_TZ}')"
        users = {
            "total": _one(c, "SELECT COUNT(*) FROM users"),
            "new_today": _one(c, f"SELECT COUNT(*) FROM users WHERE date(registered_at, '{_TZ}') = {today}"),
            "new_7d": _one(c, "SELECT COUNT(*) FROM users WHERE registered_at >= datetime('now', '-7 days')"),
            "new_30d": _one(c, "SELECT COUNT(*) FROM users WHERE registered_at >= datetime('now', '-30 days')"),
            "online": _one(c, f"SELECT COUNT(*) FROM users WHERE last_seen >= datetime('now', '-{ONLINE_MINUTES} minutes')"),
            "active_today": _one(c, f"SELECT COUNT(*) FROM users WHERE date(last_seen, '{_TZ}') = {today}"),
            "active_7d": _one(c, "SELECT COUNT(*) FROM users WHERE last_seen >= datetime('now', '-7 days')"),
            "active_30d": _one(c, "SELECT COUNT(*) FROM users WHERE last_seen >= datetime('now', '-30 days')"),
        }
        langs = {r[0] or "uz": r[1] for r in c.execute(
            "SELECT language, COUNT(*) FROM users GROUP BY language").fetchall()}
        growth = {r[0]: r[1] for r in c.execute(
            f"SELECT date(registered_at, '{_TZ}') AS d, COUNT(*) FROM users "
            f"WHERE registered_at >= datetime('now', '-{GROWTH_DAYS} days') GROUP BY d").fetchall()}
        days = [r[0] for r in c.execute(
            f"WITH RECURSIVE d(x) AS (SELECT date('now', '{_TZ}', '-{GROWTH_DAYS - 1} days') "
            f"UNION ALL SELECT date(x, '+1 day') FROM d WHERE x < {today}) SELECT x FROM d").fetchall()]
        modes = {
            "league": _one(c, "SELECT COUNT(*) FROM registrations"),
            "wc": _one(c, "SELECT COUNT(*) FROM wc_registrations"),
            "cl": _one(c, "SELECT COUNT(*) FROM cl_participants WHERE season = "
                          "(SELECT cl_season FROM season_state WHERE id = 1)"),
            "el": _one(c, "SELECT COUNT(*) FROM el_participants WHERE season = "
                          "(SELECT el_season FROM season_state WHERE id = 1)"),
            "division_today": _one(c, f"SELECT COUNT(*) FROM div_registrations WHERE day = {today}"),
        }
        leagues = [{"name": r[0], "players": r[1], "max": r[2]} for r in c.execute(
            "SELECT l.name, COUNT(r.id), l.max_players FROM leagues l LEFT JOIN registrations r "
            "ON r.league_id = l.id GROUP BY l.id ORDER BY l.id").fetchall()]
        pt_status = {r[0]: r[1] for r in c.execute(
            "SELECT status, COUNT(*) FROM pt_tournaments GROUP BY status").fetchall()}
        private = {
            "total": sum(pt_status.values()),
            "recruiting": pt_status.get("recruiting", 0),
            "running": pt_status.get("running", 0),
            "finished": pt_status.get("finished", 0),
            "unpaid": pt_status.get("awaiting_payment", 0) + pt_status.get("payment_review", 0),
            "players": _one(c, "SELECT COUNT(DISTINCT user_id) FROM pt_members WHERE status = 'approved'"),
            "organizers": _one(c, "SELECT COUNT(DISTINCT owner_user_id) FROM pt_tournaments"),
            "subs_active": _one(c, "SELECT COUNT(*) FROM pt_subscriptions WHERE status = 'active' "
                                   "AND expires_at > datetime('now')"),
            "paid_uzs": _one(c, "SELECT COALESCE(SUM(price_uzs), 0) FROM pt_tournaments WHERE paid_at IS NOT NULL "
                                "AND paid_via = 'one_time'")
                        + _one(c, "SELECT COALESCE(SUM(price_uzs), 0) FROM pt_subscriptions WHERE starts_at IS NOT NULL"),
        }
        now_local = c.execute(f"SELECT strftime('%d.%m.%Y %H:%M', 'now', '{_TZ}')").fetchone()[0]
    finally:
        conn.close()
    return {"users": users, "languages": langs, "growth": [{"day": d, "count": growth.get(d, 0)} for d in days],
            "modes": modes, "leagues": leagues, "private": private, "generated_at": now_local}


_LABELS = {
    "uz": {"title": "📊 Bot statistikasi", "users": "👥 Foydalanuvchilar", "total": "Jami", "today": "Bugun yangi",
           "d7": "7 kunda yangi", "d30": "30 kunda yangi", "active": "🔥 Faollik", "online": "Hozir onlayn",
           "act_today": "Bugun kirgan", "act7": "7 kunda kirgan", "act30": "30 kunda kirgan",
           "modes": "🏆 Rasmiy turnirlar", "league": "Ligalar", "wc": "Jahon chempionati", "cl": "Chempionlar ligasi",
           "el": "Yevropa ligasi", "div": "Divizion (bugun)", "pt": "⚔️ Shaxsiy turnirlar", "pt_total": "Jami turnir",
           "pt_live": "Yig'ilmoqda / davom etmoqda", "pt_players": "Ishtirokchilar", "pt_org": "Tashkilotchilar",
           "pt_subs": "Faol obunalar", "pt_paid": "Tushum (so'm)", "langs": "🌐 Til", "at": "Holat"},
    "ru": {"title": "📊 Статистика бота", "users": "👥 Пользователи", "total": "Всего", "today": "Новых сегодня",
           "d7": "Новых за 7 дней", "d30": "Новых за 30 дней", "active": "🔥 Активность", "online": "Сейчас онлайн",
           "act_today": "Заходили сегодня", "act7": "Заходили за 7 дней", "act30": "Заходили за 30 дней",
           "modes": "🏆 Официальные турниры", "league": "Лиги", "wc": "Чемпионат мира", "cl": "Лига чемпионов",
           "el": "Лига Европы", "div": "Дивизион (сегодня)", "pt": "⚔️ Частные турниры", "pt_total": "Всего турниров",
           "pt_live": "Набор / идут", "pt_players": "Участники", "pt_org": "Организаторы",
           "pt_subs": "Активные подписки", "pt_paid": "Выручка (сум)", "langs": "🌐 Язык", "at": "Данные на"},
    "en": {"title": "📊 Bot statistics", "users": "👥 Users", "total": "Total", "today": "New today",
           "d7": "New in 7 days", "d30": "New in 30 days", "active": "🔥 Activity", "online": "Online now",
           "act_today": "Opened today", "act7": "Opened in 7 days", "act30": "Opened in 30 days",
           "modes": "🏆 Official tournaments", "league": "Leagues", "wc": "World Cup", "cl": "Champions League",
           "el": "Europa League", "div": "Division (today)", "pt": "⚔️ Private tournaments", "pt_total": "Tournaments",
           "pt_live": "Gathering / running", "pt_players": "Players", "pt_org": "Organizers",
           "pt_subs": "Active subscriptions", "pt_paid": "Revenue (UZS)", "langs": "🌐 Language", "at": "As of"},
}


def _n(x: int) -> str:
    return f"{x:,}".replace(",", " ")


def format_stats_text(s: dict, lang: str | None = "uz") -> str:
    """/stats buyrug'i uchun matn (HTML emas — oddiy matn, foydalanuvchi ma'lumoti yo'q)."""
    L = _LABELS.get(lang or "uz", _LABELS["uz"])
    u, m, p = s["users"], s["modes"], s["private"]
    langs = " · ".join(f"{k.upper()} {_n(v)}" for k, v in sorted(s["languages"].items(), key=lambda kv: -kv[1]))
    lines = [
        L["title"], "",
        L["users"], f"• {L['total']}: {_n(u['total'])}", f"• {L['today']}: {_n(u['new_today'])}",
        f"• {L['d7']}: {_n(u['new_7d'])}", f"• {L['d30']}: {_n(u['new_30d'])}", "",
        L["active"], f"• {L['online']}: {_n(u['online'])}", f"• {L['act_today']}: {_n(u['active_today'])}",
        f"• {L['act7']}: {_n(u['active_7d'])}", f"• {L['act30']}: {_n(u['active_30d'])}", "",
        L["modes"], f"• {L['league']}: {_n(m['league'])}", f"• {L['wc']}: {_n(m['wc'])}",
        f"• {L['cl']}: {_n(m['cl'])}", f"• {L['el']}: {_n(m['el'])}", f"• {L['div']}: {_n(m['division_today'])}", "",
        L["pt"], f"• {L['pt_total']}: {_n(p['total'])}", f"• {L['pt_live']}: {_n(p['recruiting'])} / {_n(p['running'])}",
        f"• {L['pt_players']}: {_n(p['players'])}", f"• {L['pt_org']}: {_n(p['organizers'])}",
        f"• {L['pt_subs']}: {_n(p['subs_active'])}", f"• {L['pt_paid']}: {_n(p['paid_uzs'])}", "",
        f"{L['langs']}: {langs}", f"🕒 {L['at']}: {s['generated_at']}",
    ]
    return "\n".join(lines)
