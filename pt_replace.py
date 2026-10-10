"""
pt_replace.py — SHAXSIY turnir: ishtirokchini boshqa odamga almashtirish (2026-10-10).

Admin so'rovi: sodda bo'lsin — tashkilotchi (yoki turnir admini) a'zoni tanlaydi va yangi odamning
Telegram ID yoki @username'ini yozadi. Rasmiy rejimlardagi participant_admin.py naqshi:
O'RIN SAQLANADI — guruh/klub, o'yinlar, natijalar, chat joyida qoladi; faqat odam (user_id) almashadi.

Ko'chiriladi (FAQAT shu turnir doirasida):
  pt_members (user_id, telegram_id), pt_matches (player1_id, player2_id, submitted_by),
  pt_messages.sender_id (shu turnir o'yinlari), pt_support_threads.member_user_id va
  pt_support_messages.sender_id (member roli), pt_tournaments.champion_user_id.
Sabablar: not_found, not_owner, finished, member_not_found, cannot_replace_owner,
          user_not_found, same_user, already_member.
"""

import logging

from pt_core import STATUS_FINISHED, is_manager
from pt_members import _find_user, _owner_info, _tx

logger = logging.getLogger(__name__)

_CLOSED = (STATUS_FINISHED, "cancelled", "rejected")


def pt_replace_member(tid: int, manager_id: int, old_user_id: int, query: str) -> tuple[bool, str | dict]:
    def run(cursor):
        t = _owner_info(cursor, tid)
        if not t:
            return False, "not_found"
        if not is_manager(cursor, tid, manager_id, t["owner_user_id"]):
            return False, "not_owner"
        if t["status"] in _CLOSED:
            return False, "finished"
        if old_user_id == t["owner_user_id"]:
            return False, "cannot_replace_owner"
        cursor.execute("SELECT m.telegram_id, m.team_name, u.language FROM pt_members m "
                       "LEFT JOIN users u ON u.id = m.user_id "
                       "WHERE m.tournament_id = ? AND m.user_id = ? AND m.status = 'approved'", (tid, old_user_id))
        old = cursor.fetchone()
        if not old:
            return False, "member_not_found"
        new = _find_user(cursor, query)
        if not new:
            return False, "user_not_found"
        if new["id"] == old_user_id:
            return False, "same_user"
        cursor.execute("SELECT status FROM pt_members WHERE tournament_id = ? AND user_id = ?", (tid, new["id"]))
        ex = cursor.fetchone()
        if ex and ex["status"] == "approved":
            return False, "already_member"
        if ex:                                     # yangi odamning kutilayotgan so'rovi — o'rniga o'tadi
            cursor.execute("DELETE FROM pt_members WHERE tournament_id = ? AND user_id = ?", (tid, new["id"]))

        new_id = new["id"]
        cursor.execute("UPDATE pt_members SET user_id = ?, telegram_id = ? WHERE tournament_id = ? AND user_id = ?",
                       (new_id, new["telegram_id"], tid, old_user_id))
        moved = 0
        for col in ("player1_id", "player2_id", "submitted_by"):   # ustun nomlari kod ichida qat'iy
            cursor.execute(f"UPDATE pt_matches SET {col} = ? WHERE tournament_id = ? AND {col} = ?",
                           (new_id, tid, old_user_id))
            moved += cursor.rowcount or 0
        cursor.execute("UPDATE pt_messages SET sender_id = ? WHERE sender_id = ? AND match_id IN "
                       "(SELECT id FROM pt_matches WHERE tournament_id = ?)", (new_id, old_user_id, tid))
        cursor.execute("UPDATE OR IGNORE pt_support_threads SET member_user_id = ? "
                       "WHERE tournament_id = ? AND member_user_id = ?", (new_id, tid, old_user_id))
        cursor.execute("UPDATE pt_support_messages SET sender_id = ? WHERE sender_id = ? AND sender_role = 'member' "
                       "AND thread_id IN (SELECT id FROM pt_support_threads WHERE tournament_id = ?)",
                       (new_id, old_user_id, tid))
        cursor.execute("UPDATE pt_tournaments SET champion_user_id = ?, updated_at = CURRENT_TIMESTAMP "
                       "WHERE id = ? AND champion_user_id = ?", (new_id, tid, old_user_id))
        logger.info("PT #%s: ishtirokchi almashtirildi %s -> %s (o'yin ustunlari: %s)",
                    tid, old_user_id, new_id, moved)
        return True, {"name": t["name"], "team_name": old["team_name"],
                      "old": {"telegram_id": old["telegram_id"], "language": old["language"]},
                      "new": {"user_id": new_id, "telegram_id": new["telegram_id"], "language": new["language"],
                              "nickname": new["nickname"], "username": new["username"]}}
    return _tx(run)
