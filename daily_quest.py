# -*- coding: utf-8 -*-
from .logger import get_logger
logger = get_logger(__name__)
"""
daily_quest.py — 30 nhiệm vụ hàng ngày, random 3/ngày, reset lúc nửa đêm.

Mỗi quest có:
  - id, title, description
  - type: cards_easy / cards_good / cards_hard / cards_total /
          no_again_under / streak_reach / save_money /
          earn_money / no_penalty / review_session
  - target: số cần đạt
  - reward_xp, reward_money
"""

import hashlib
import time
from ._safe_config import col_ready, cfg_dict, cfg_str, cfg_set, cfg_list

_KEY_QUESTS      = "anki_tycoon_daily_quests"     # {date, quests:[{id,progress,done}]}
_KEY_QUEST_SEED  = "anki_tycoon_quest_seed"        # seed cố định của user

# ── Bảng 30 nhiệm vụ ─────────────────────────────────────────────
QUEST_POOL = [
    # --- Cards ---
    {"id":"q01","title":"Học chăm chỉ","desc":"Ôn 20 thẻ bất kỳ trong ngày","type":"cards_total","target":20,"xp":50,"money":5_000,"emoji":"📚"},
    {"id":"q02","title":"Marathon học","desc":"Ôn 50 thẻ trong ngày","type":"cards_total","target":50,"xp":120,"money":15_000,"emoji":"🏃"},
    {"id":"q03","title":"Siêu học","desc":"Ôn 100 thẻ trong ngày","type":"cards_total","target":100,"xp":250,"money":30_000,"emoji":"⚡"},
    {"id":"q04","title":"Easy Master","desc":"Bấm Easy 10 lần","type":"cards_easy","target":10,"xp":80,"money":10_000,"emoji":"✨"},
    {"id":"q05","title":"Easy Pro","desc":"Bấm Easy 25 lần","type":"cards_easy","target":25,"xp":180,"money":25_000,"emoji":"🌟"},
    {"id":"q06","title":"Good Streak","desc":"Bấm Good 15 lần","type":"cards_good","target":15,"xp":60,"money":8_000,"emoji":"👍"},
    {"id":"q07","title":"Hard Worker","desc":"Ôn 10 thẻ Hard — thử thách thật sự","type":"cards_hard","target":10,"xp":70,"money":9_000,"emoji":"💪"},
    {"id":"q08","title":"Balanced Learner","desc":"Bấm ít nhất 5 Easy + 5 Good + 5 Hard","type":"balanced","target":5,"xp":100,"money":12_000,"emoji":"⚖️"},

    # --- Again control ---
    {"id":"q09","title":"Tập trung cao","desc":"Không bấm Again quá 5 lần hôm nay","type":"no_again_under","target":5,"xp":150,"money":20_000,"emoji":"🎯"},
    {"id":"q10","title":"Không Again!","desc":"0 lần Again trong toàn buổi học","type":"no_again_under","target":0,"xp":300,"money":50_000,"emoji":"🏅"},
    {"id":"q11","title":"Kiểm soát tốt","desc":"Không bấm Again quá 10 lần","type":"no_again_under","target":10,"xp":100,"money":12_000,"emoji":"🛡️"},
    {"id":"q12","title":"Again thấp","desc":"Dưới 20 lần Again sau 30+ thẻ","type":"again_ratio","target":20,"xp":80,"money":10_000,"emoji":"📉"},

    # --- Money / Saving ---
    {"id":"q13","title":"Tiết kiệm nhỏ","desc":"Gửi ít nhất 50.000đ vào ngân hàng hôm nay","type":"save_money","target":50_000,"xp":60,"money":5_000,"emoji":"🏦"},
    {"id":"q14","title":"Nhà đầu tư","desc":"Gửi ít nhất 200.000đ vào ngân hàng","type":"save_money","target":200_000,"xp":120,"money":10_000,"emoji":"💹"},
    {"id":"q15","title":"Kiếm đủ chi","desc":"Kiếm được ít nhất 100.000đ tiền thưởng hôm nay","type":"earn_money","target":100_000,"xp":80,"money":0,"emoji":"💵"},
    {"id":"q16","title":"Ngày bội thu","desc":"Kiếm được ít nhất 300.000đ tiền thưởng","type":"earn_money","target":300_000,"xp":200,"money":0,"emoji":"💰"},
    {"id":"q17","title":"Không tiêu xài","desc":"Không mua sắm gì hôm nay","type":"no_purchase","target":0,"xp":50,"money":5_000,"emoji":"🔒"},

    # --- Streak ---
    {"id":"q18","title":"Duy trì streak","desc":"Đạt streak ít nhất 3 ngày liên tiếp","type":"streak_reach","target":3,"xp":100,"money":15_000,"emoji":"🔥"},
    {"id":"q19","title":"Streak tuần","desc":"Duy trì streak 7 ngày","type":"streak_reach","target":7,"xp":300,"money":50_000,"emoji":"🔥"},
    {"id":"q20","title":"Streak tháng","desc":"Duy trì streak 30 ngày","type":"streak_reach","target":30,"xp":1000,"money":200_000,"emoji":"🔥"},

    # --- No penalty ---
    {"id":"q21","title":"Ngày trong sạch","desc":"Không bị phạt tiền hôm nay","type":"no_penalty","target":0,"xp":80,"money":10_000,"emoji":"😇"},
    {"id":"q22","title":"Tuần không phạt","desc":"Không bị phạt 3 ngày liên tiếp (check streak)","type":"no_penalty_streak","target":3,"xp":200,"money":30_000,"emoji":"🌈"},

    # --- Session ---
    {"id":"q23","title":"Khởi động sáng","desc":"Ôn ít nhất 10 thẻ trước 10 giờ sáng","type":"morning_cards","target":10,"xp":80,"money":10_000,"emoji":"🌅"},
    {"id":"q24","title":"Ôn liên tục","desc":"Ôn ít nhất 30 thẻ trong 1 phiên không ngắt","type":"session_cards","target":30,"xp":100,"money":12_000,"emoji":"⏱️"},
    {"id":"q25","title":"Ngày dài học","desc":"Tổng thẻ ôn trong ngày ≥ 75","type":"cards_total","target":75,"xp":180,"money":22_000,"emoji":"📅"},

    # --- XP / Rank ---
    {"id":"q26","title":"Thu thập XP","desc":"Kiếm ít nhất 200 XP hôm nay","type":"earn_xp","target":200,"xp":50,"money":8_000,"emoji":"⭐"},
    {"id":"q27","title":"XP ngày vàng","desc":"Kiếm ít nhất 500 XP hôm nay","type":"earn_xp","target":500,"xp":100,"money":15_000,"emoji":"🌠"},

    # --- Mixed ---
    {"id":"q28","title":"Học mà chơi","desc":"Ôn 40 thẻ với tỷ lệ Easy+Good ≥ 70%","type":"quality_cards","target":40,"xp":150,"money":20_000,"emoji":"🎮"},
    {"id":"q29","title":"Ngày hoàn hảo","desc":"50 thẻ + 0 Again + không bị phạt","type":"perfect_day","target":50,"xp":500,"money":100_000,"emoji":"💫"},
    {"id":"q30","title":"Siêu chiến binh","desc":"100 thẻ + streak ≥ 3 + kiếm 200K+","type":"hero_day","target":100,"xp":800,"money":150_000,"emoji":"🦸"},
]

QUEST_COUNT_PER_DAY = 3


def _today() -> str:
    """Trả về 'YYYY-MM-DD' dùng Unix timestamp, chống time travel."""
    return time.strftime("%Y-%m-%d", time.localtime(time.time()))


def _get_user_seed() -> int:
    """Seed cố định cho user — tạo 1 lần, lưu vĩnh viễn để rotation nhất quán."""
    if not col_ready(): return 42
    seed = cfg_dict(_KEY_QUEST_SEED, {})
    if not seed.get("value"):
        import random, time
        val = random.randint(100_000, 999_999)
        cfg_set(_KEY_QUEST_SEED, {"value": val})
        return val
    return int(seed["value"])


def _pick_quests_for_date(date_str: str) -> list:
    """Chọn QUEST_COUNT_PER_DAY quest cho ngày bằng hàm deterministic."""
    seed_str = f"{_get_user_seed()}_{date_str}"
    h = int(hashlib.sha256(seed_str.encode()).hexdigest(), 16)
    pool = QUEST_POOL.copy()
    picked = []
    for i in range(QUEST_COUNT_PER_DAY):
        idx = (h >> (i * 8)) % len(pool)
        picked.append(pool.pop(idx))
    return picked


def _load_today() -> dict:
    if not col_ready(): return {}
    return cfg_dict(_KEY_QUESTS, {})


def _save_today(data: dict):
    cfg_set(_KEY_QUESTS, data)


def get_daily_quests() -> list:
    """
    Trả về 3 quest của ngày hôm nay (tạo mới nếu cần).
    Mỗi quest có thêm: progress, done, reward_claimed.
    """
    today = _today()
    data  = _load_today()

    if data.get("date") != today:
        # Ngày mới — tạo quest mới
        quests = _pick_quests_for_date(today)
        new_data = {
            "date":   today,
            "quests": [
                {**q, "progress": 0, "done": False, "reward_claimed": False}
                for q in quests
            ]
        }
        _save_today(new_data)
        return new_data["quests"]

    return data.get("quests", [])


def update_quest_progress(quest_type: str, value: int,
                          set_absolute: bool = False) -> list:
    """
    Cập nhật progress cho quest theo type.
    value: delta (set_absolute=False) hoặc giá trị tuyệt đối.
    Trả về list quest vừa complete (để show notification).
    """
    if not col_ready(): return []
    today = _today()
    data  = _load_today()
    if data.get("date") != today:
        get_daily_quests()   # init
        data = _load_today()

    quests    = data.get("quests", [])
    just_done = []

    for q in quests:
        if q.get("done"): continue
        if q["type"] != quest_type: continue

        old_prog = q.get("progress", 0)
        if set_absolute:
            q["progress"] = value
        else:
            q["progress"] = old_prog + value

        # Check completion
        _check_completion(q)
        if q["done"] and not q.get("_notified"):
            just_done.append(q)
            q["_notified"] = True

    data["quests"] = quests
    _save_today(data)
    return just_done


def _check_completion(q: dict):
    """Kiểm tra quest có hoàn thành không."""
    prog   = q.get("progress", 0)
    target = q.get("target", 1)
    qtype  = q.get("type", "")

    if qtype == "no_again_under":
        # Hoàn thành nếu prog (= số again) <= target
        q["done"] = prog <= target
    elif qtype == "no_purchase":
        q["done"] = prog == 0
    elif qtype == "no_penalty":
        q["done"] = prog == 0
    else:
        q["done"] = prog >= target


def claim_quest_reward(quest_id: str) -> dict:
    """Nhận thưởng quest — ghi vào balance và XP."""
    if not col_ready():
        return {"ok": False, "error": "Chưa sẵn sàng"}
    today = _today()
    data  = _load_today()
    if data.get("date") != today:
        return {"ok": False, "error": "Không tìm thấy quest hôm nay"}

    quests = data.get("quests", [])
    q = next((x for x in quests if x["id"] == quest_id), None)
    if not q:
        return {"ok": False, "error": "Quest không tồn tại"}
    if not q.get("done"):
        return {"ok": False, "error": "Quest chưa hoàn thành"}
    if q.get("reward_claimed"):
        return {"ok": False, "error": "Đã nhận thưởng rồi"}

    # Cộng tiền và XP
    money = int(q.get("money", 0))
    xp    = int(q.get("xp", 0))

    from .balance import get_balance, set_balance_and_log
    from .rank_system import add_xp
    from .transactions import add_transaction

    new_bal = get_balance() + money
    if money > 0:
        set_balance_and_log(new_bal, "quest", money, f"Quest: {q['title']}")
        add_transaction("reward", money, f"🎯 Quest: {q['title']}")
    if xp > 0:
        add_xp(xp)

    q["reward_claimed"] = True
    data["quests"] = quests
    _save_today(data)

    # Achievement trigger
    try:
        from .achievements import check_and_unlock
        check_and_unlock("quest_claimed", 1)
    except Exception as e:
        logger.debug("claim_quest_reward: achievements trigger — %s", e)

    return {"ok": True, "money": money, "xp": xp, "quest_title": q["title"]}


def get_quest_summary() -> dict:
    quests = get_daily_quests()
    done   = sum(1 for q in quests if q.get("done"))
    claimed = sum(1 for q in quests if q.get("reward_claimed"))
    return {
        "quests":  quests,
        "total":   len(quests),
        "done":    done,
        "claimed": claimed,
        "all_done": done == len(quests),
    }