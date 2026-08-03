"""
cl_playin.py — ChL yangi format play-off kirish qur'asi (2026-08).

Yagona umumiy reyting (36 klub) 8 tur tugagach:
  - TOP-8 → to'g'ridan asosiy setkaga (seed 1..8).
  - 9-24 o'rin (16 ta) → PLEY-IN juftlari (reyting bo'yicha, kuchli past bilan):
    (9,24), (10,23), (11,22), (12,21), (13,20), (14,19), (15,18), (16,17).
  - Setka joylashuvi (real ChL uslubi): seed_k ↔ (8-k)-chi pley-in juftligi g'olibi.
    Ya'ni r16 pos p (0..7): sideA = seed[p], sideB = pley-in g'olibi[7-p].
    Shunda seed-1 (pos0) eng past pley-in juftligi (16-17) g'olibi bilan tushadi.

Bu modul faqat SOF hisoblash qiladi (DB yozmaydi) — cl_playoff.cl_po_start uni
chaqirib natijani cl_playoff_matches'ga yozadi (qoida #25/#27: mantiq handlerdan
alohida).
"""

# Pley-in juftliklari umumiy reytingdagi o'rinlar (1-indeksli) bilan.
# Har juftlik: (yuqori_orin, quyi_orin). Tartib — kuch bo'yicha (birinchisi eng kuchli).
CL_PLAYIN_PAIRS = [(9, 24), (10, 23), (11, 22), (12, 21),
                   (13, 20), (14, 19), (15, 18), (16, 17)]
CL_SEED_COUNT = 8          # to'g'ridan setkaga o'tadiganlar (top-8)
CL_PLAYIN_SLOTS = 16       # pley-inga tushadigan o'rinlar (9..24)
CL_QUALIFY_TOTAL = 24      # play-offga jami jalb qilinadigan o'rinlar


def build_playin_draw(ranking_user_ids: list[int]) -> dict:
    """
    Umumiy reyting tartibidagi user_id ro'yxatidan pley-in qur'asini quradi.

    ranking_user_ids: reyting bo'yicha SARALANGAN user_id lar (0-index = 1-o'rin).
                      Kamida CL_QUALIFY_TOTAL (24) ta bo'lishi kutiladi.

    Qaytaradi:
      {
        "seeds":  [user_id, ...]              # top-8, pos tartibida (0=seed1)
        "playin": [(high_id, low_id), ...]    # 8 juft, kuch tartibida
                                              #   [0]=(9,24) ... [7]=(16,17)
      }
    Chekka holat: 24 dan kam bo'lsa — mavjudicha (playin juftliklari to'liq
    bo'lmasligi mumkin) qaytadi; chaqiruvchi (cl_po_qualified) yetarlilikni
    alohida tekshiradi.
    """
    seeds = ranking_user_ids[:CL_SEED_COUNT]
    playin = []
    for (hi, lo) in CL_PLAYIN_PAIRS:
        hi_idx, lo_idx = hi - 1, lo - 1
        if hi_idx < len(ranking_user_ids) and lo_idx < len(ranking_user_ids):
            playin.append((ranking_user_ids[hi_idx], ranking_user_ids[lo_idx]))
    return {"seeds": seeds, "playin": playin}


def r16_slot_for_playin_position(playin_pos: int) -> int:
    """
    Pley-in juftligi (pos 0..7) g'olibi asosiy setkada qaysi r16 pozitsiyasiga
    borishini qaytaradi. Real ChL uslubi: eng kuchli pley-in juftligi (pos 0 =
    9-24) eng past seed (seed-8, r16 pos7) bilan; eng zaif pley-in juftligi
    (pos 7 = 16-17) eng kuchli seed (seed-1, r16 pos0) bilan.

    => r16_pos = CL_SEED_COUNT - 1 - playin_pos.
    """
    return CL_SEED_COUNT - 1 - playin_pos
