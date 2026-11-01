"""
season_rewards_notify.py — MAVSUM MUKOFOTI bot xabarlari (2026-11-01). Scheduler (daqiqada) chaqiradi.
Har mukofot bir marta: avval notified=1, keyin xabar (yuborilmasa ham token balansda — qoida #37).
Xabar tarkibi: turnir nomi + har qism (o'rin / bosqich / Oltin to'p ...) + jami. Matn — texts.py reward_notify.
"""

import json
import logging

logger = logging.getLogger(__name__)
NOTICE_BATCH = 50                    # bir chaqiruvda ko'pi bilan (Telegram cheklovlari uchun)

TITLES = {
    "uz": {"league": "Liga", "cl": "Chempionlar ligasi", "el": "Yevropa ligasi", "ac": "Osiyo Chempionlar ligasi",
           "wc": "Jahon chempionati", "co": "Konferensiya ligasi"},
    "ru": {"league": "Лига", "cl": "Лига чемпионов", "el": "Лига Европы", "ac": "Азиатская лига чемпионов",
           "wc": "Чемпионат мира", "co": "Лига конференций"},
    "en": {"league": "League", "cl": "Champions League", "el": "Europa League", "ac": "Asian Champions League",
           "wc": "World Cup", "co": "Conference League"},
}
STAGES = {
    "uz": {"league": "Liga bosqichi", "group": "Guruh bosqichi", "playin": "Pley-in", "r32": "1/16 final",
           "r16": "1/8 final", "r8": "1/4 final", "r4": "1/2 final", "third": "3-o'rin", "finalist": "Finalchi",
           "champion": "🏆 Chempion"},
    "ru": {"league": "Общий этап", "group": "Групповой этап", "playin": "Плей-ин", "r32": "1/16 финала",
           "r16": "1/8 финала", "r8": "1/4 финала", "r4": "1/2 финала", "third": "3-е место", "finalist": "Финалист",
           "champion": "🏆 Чемпион"},
    "en": {"league": "League phase", "group": "Group stage", "playin": "Play-in", "r32": "Round of 32",
           "r16": "Round of 16", "r8": "Quarter-final", "r4": "Semi-final", "third": "3rd place", "finalist": "Finalist",
           "champion": "🏆 Champion"},
}
EXTRA = {
    "uz": {"pos": "{lg} — {n}-o'rin", "golden_ball": "⚽ Oltin to'p", "golden_boot": "👟 Oltin butsa"},
    "ru": {"pos": "{lg} — {n}-е место", "golden_ball": "⚽ Золотой мяч", "golden_boot": "👟 Золотая бутса"},
    "en": {"pos": "{lg} — place {n}", "golden_ball": "⚽ Golden Ball", "golden_boot": "👟 Golden Boot"},
}


def _lang(lang: str | None) -> str:
    return lang if lang in TITLES else "uz"


def _part_text(p: dict, lang: str) -> str:
    if p["k"] == "stage":
        return STAGES[lang].get(p["s"], p["s"])
    return EXTRA[lang].get(p["k"], p["k"]).format(lg=p.get("lg", ""), n=p.get("n", ""))


def reward_lines(detail: str, lang: str | None) -> str:
    lg = _lang(lang)
    return "\n".join(f"• {_part_text(p, lg)}: +{p['a']} eF" for p in json.loads(detail or "[]"))


async def reward_send_notices() -> int:
    from models import get_connection
    conn = get_connection()
    try:
        rows = [dict(r) for r in conn.execute(
            "SELECT s.id, s.kind, s.season, s.telegram_id, s.amount, s.detail, "
            "(SELECT language FROM users WHERE id = s.user_id) AS lang "
            "FROM season_rewards s WHERE s.notified = 0 ORDER BY s.id LIMIT ?", (NOTICE_BATCH,)).fetchall()]
        if rows:
            conn.execute(f"UPDATE season_rewards SET notified = 1 WHERE id IN ({','.join('?' * len(rows))})",
                         [r["id"] for r in rows])
            conn.commit()
    finally:
        conn.close()
    from notify import notify_user
    for r in rows:
        lg = _lang(r["lang"])
        try:
            await notify_user(r["telegram_id"], "reward_notify", r["lang"], open_button_key="btn_open_app",
                              title=TITLES[lg][r["kind"]], season=r["season"], lines=reward_lines(r["detail"], lg),
                              total=r["amount"])
        except Exception as exc:
            logger.warning("Mukofot xabari (%s) yuborilmadi: %s", r["telegram_id"], exc)
    return len(rows)
