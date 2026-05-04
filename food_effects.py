# -*- coding: utf-8 -*-
"""
food_effects.py — Boost từ đồ ăn uống & vật phẩm học tập.
Mở rộng: hỗ trợ effect_list (nhiều effect/item), và các effect type mới.

FIX v5.0:
  - Giới hạn: mỗi user chỉ 1 food + 1 drink active cùng lúc.
  - Daily purchase limit cho food items.
  - Time-of-day optimization (sáng/trưa/chiều/tối có bonus khác nhau).
  - Phân loại item_category: "food", "drink", "study".
"""

import time
import datetime
from .config import CONFIG_KEY_INVENTORY
from ._safe_config import col_ready, cfg_dict, cfg_list, cfg_set, cfg_str, cfg_int

_KEY_ACTIVE = "anki_tycoon_active_boosts"
_KEY_FRESH  = "anki_tycoon_food_freshness"
_KEY_PURCHASE_LOG    = "anki_tycoon_food_purchase_log"
_KEY_STUDY_PURCHASE_LOG = "anki_tycoon_study_purchase_log"

# ── Config keys cho hệ thống hủy boost & thời gian học ──────────
_KEY_DAILY_CANCEL_COUNT = "anki_tycoon_daily_cancel_count"
_KEY_DAILY_CANCEL_DATE  = "anki_tycoon_daily_cancel_date"
_KEY_CARD_TIME_VALID    = "anki_tycoon_card_time_valid_count"
_KEY_CARD_TIME_DATE     = "anki_tycoon_card_time_date"

# ── Giới hạn mua vật phẩm học tập ──────────────────────────
WEEKLY_STUDY_LIMIT = 7        # tối đa 7 món/tuần
STUDY_MAX_VALUE    = 3000000  # tối đa 3 triệu VND/tuần (tăng từ 1 triệu)

# ── Giới hạn hủy boost & thời gian học ─────────────────────
BASE_DAILY_CANCEL_LIMIT  = 10   # số lần hủy cơ bản mỗi ngày
MAX_DAILY_CANCEL_LIMIT   = 20   # tối đa có thể mở rộng
CARDS_PER_EXTRA_CANCEL   = 10   # mỗi N thẻ hợp lệ thêm 1 lần hủy
MIN_CARD_TIME_SECONDS    = 10   # thời gian tối thiểu/thẻ để tính là hợp lệ

# Danh sách item_id là đồ uống (phân loại từ shop_items.json)
DRINK_ITEM_IDS = {
    "food_tra_dao_cam_sa",
    "food_sua_chua_nep",
    "food_nuoc_mia",
    "food_ca_phe_trung",
    "food_ca_phe_den_da",
    "food_nuoc_ep_cam",
    "food_sinh_to_bo",
    "food_matcha_latte",
    "food_tra_sua",
    "food_smoothie_bo",
}

# ── Cache ánh xạ item_id → category ──────────────────────────────
# Lazy-loaded: chỉ load 1 lần từ shop_data, giảm I/O đọc file JSON
_ITEM_CATEGORY_CACHE = None     # {item_id: category_str}


def _build_item_category_cache():
    """Xây dựng cache ánh xạ item_id → category từ shop_items.json."""
    global _ITEM_CATEGORY_CACHE
    from .shop_data import get_items_map
    items_map = get_items_map()
    _ITEM_CATEGORY_CACHE = {}
    for iid, item in items_map.items():
        cat = _get_item_category(iid, item)
        _ITEM_CATEGORY_CACHE[iid] = cat

DEFAULT_EFFECTS = {
    "coffee": {
        "type": "reward_multiplier", "value": 1.5,
        "duration": 1800, "cards": 0, "expire_h": 12,
        "name": "Caffeine Boost ☕", "desc": "×1.5 tiền thưởng trong 30 phút"
    },
    "boba": {
        "type": "reward_multiplier", "value": 1.3,
        "duration": 3600, "cards": 0, "expire_h": 8,
        "name": "Sugar Rush 🧋", "desc": "×1.3 tiền thưởng trong 60 phút"
    },
    "pizza": {
        "type": "xp_bonus", "value": 2000,
        "duration": 0, "cards": 50, "expire_h": 6,
        "name": "Pizza Power 🍕", "desc": "+2.000đ/thẻ trong 50 thẻ tiếp theo"
    },
}

# ─── Time-of-day optimization ─────────────────────────────────
# Khung giờ có bonus riêng cho food boost
TIME_SLOTS = [
    ("morning",   6, 11, 1.15,  "🌅 Buổi sáng — Não bộ minh mẫn, ×1.15 hiệu quả!"),
    ("noon",     11, 13, 0.90,  "☀️ Buổi trưa — Cơ thể mệt mỏi, ×0.90 hiệu quả"),
    ("afternoon",13, 18, 1.05,  "🌤️ Buổi chiều — Ổn định, ×1.05 hiệu quả"),
    ("evening",  18, 23, 1.20,  "🌙 Buổi tối — Thời gian vàng, ×1.20 hiệu quả!"),
    ("late_night", 23, 6, 0.80, "🌃 Khuya — Cơ thể cần nghỉ ngơi, ×0.80 hiệu quả"),
]

def _get_current_time_slot() -> tuple:
    """Trả về (slot_name, bonus_multiplier, description) cho giờ hiện tại."""
    current_hour = time.localtime().tm_hour
    for name, start, end, bonus, desc in TIME_SLOTS:
        if start <= end:
            if start <= current_hour < end:
                return (name, bonus, desc)
        else:
            # qua nửa đêm (late_night: 23-6)
            if current_hour >= start or current_hour < end:
                return (name, bonus, desc)
    return ("unknown", 1.0, "")


def _get_item_category(item_id: str, item_data: dict = None) -> str:
    """Xác định category của item: 'food', 'drink', 'study' hoặc 'other'."""
    cat = (item_data or {}).get("category", "")
    if "Đồ uống" in cat or item_id in DRINK_ITEM_IDS:
        return "drink"
    if "Ẩm thực" in cat:
        return "food"
    if "Vật phẩm học tập" in cat:
        return "study"
    return "other"


# ─── Daily Purchase Limit ─────────────────────────────────────
# Mỗi user được mua tối đa N item food/drink mỗi ngày
DAILY_FOOD_LIMIT = 10      # max 10 food items/ngày
DAILY_DRINK_LIMIT = 10     # max 10 drink items/ngày


def _get_purchase_log() -> dict:
    return cfg_dict(_KEY_PURCHASE_LOG, {})


def _save_purchase_log(log: dict):
    cfg_set(_KEY_PURCHASE_LOG, log)


def _get_today_key() -> str:
    return time.strftime("%Y-%m-%d")


def get_daily_purchase_count(item_id: str) -> int:
    """Trả về số lượng đã mua hôm nay cho item này."""
    log = _get_purchase_log()
    today = _get_today_key()
    day_data = log.get(today, {})
    return day_data.get(item_id, 0)


def get_daily_category_count(item_category: str) -> int:
    """Trả về tổng số item đã mua hôm nay trong category này.
    Sử dụng _ITEM_CATEGORY_CACHE để tránh load lại shop_items.json mỗi lần.
    """
    global _ITEM_CATEGORY_CACHE
    if _ITEM_CATEGORY_CACHE is None:
        _build_item_category_cache()
    log = _get_purchase_log()
    today = _get_today_key()
    day_data = log.get(today, {})
    total = 0
    for item_id, cat in _ITEM_CATEGORY_CACHE.items():
        if cat == item_category:
            total += day_data.get(item_id, 0)
    return total


def record_purchase(item_id: str):
    """Ghi nhận 1 lần mua item food/drink."""
    log = _get_purchase_log()
    today = _get_today_key()
    if today not in log:
        log[today] = {}
    log[today][item_id] = log[today].get(item_id, 0) + 1
    _save_purchase_log(log)


# ── Weekly Study Purchase Tracking ──────────────────────────

def _get_week_key() -> str:
    """Trả về key tuần dạng '2025-W17' dùng Unix timestamp, chống time travel."""
    return time.strftime("%Y-W%W", time.localtime(time.time()))


def _get_study_log() -> dict:
    return cfg_dict(_KEY_STUDY_PURCHASE_LOG, {})


def _save_study_log(log: dict):
    cfg_set(_KEY_STUDY_PURCHASE_LOG, log)


def get_weekly_study_count() -> int:
    """Tổng số vật phẩm học tập đã mua trong tuần này."""
    log = _get_study_log()
    week = _get_week_key()
    week_data = log.get(week, {})
    total_items = 0
    for item_id, qty in week_data.items():
        total_items += qty
    return total_items


def get_weekly_study_total() -> int:
    """Tổng giá trị vật phẩm học tập đã mua trong tuần này."""
    log = _get_study_log()
    week = _get_week_key()
    week_data = log.get(week, {})
    total_value = 0
    from .shop_data import load_shop_items
    items = load_shop_items()
    item_map = {i["id"]: i.get("price", 0) for i in items}
    for item_id, qty in week_data.items():
        total_value += item_map.get(item_id, 0) * qty
    return total_value


def record_study_purchase(item_id: str, price: int = 0):
    """Ghi nhận 1 lần mua vật phẩm học tập."""
    log = _get_study_log()
    week = _get_week_key()
    if week not in log:
        log[week] = {}
    log[week][item_id] = log[week].get(item_id, 0) + 1
    _save_study_log(log)


def check_daily_limit(item_id: str, item_data: dict = None) -> dict:
    """
    Kiểm tra xem item còn có thể mua hôm nay không.
    Trả về {"ok": True/False, "limit": int, "count": int, "error": str}
    """
    cat = _get_item_category(item_id, item_data)
    if cat == "study":
        # Giới hạn tuần cho vật phẩm học tập
        weekly_count = get_weekly_study_count()
        weekly_total = get_weekly_study_total()
        price = (item_data or {}).get("price", 0)
        # Kiểm tra số lượng: tối đa 7 món/tuần
        if weekly_count >= WEEKLY_STUDY_LIMIT:
            return {
                "ok": False,
                "limit": WEEKLY_STUDY_LIMIT,
                "count": weekly_count,
                "error": f"⚠️ Bạn đã mua đủ {WEEKLY_STUDY_LIMIT} vật phẩm học tập trong tuần này. Tuần sau quay lại nhé!"
            }
        # Kiểm tra tổng giá trị: tối đa 1 triệu/tuần
        if weekly_total + price > STUDY_MAX_VALUE:
            remaining = STUDY_MAX_VALUE - weekly_total
            return {
                "ok": False,
                "limit": STUDY_MAX_VALUE,
                "count": weekly_total,
                "error": f"⚠️ Đã đạt giới hạn 1 triệu VND cho vật phẩm học tập trong tuần! Còn có thể mua thêm {remaining:,} VND.".replace(",", "."),
            }
        return {"ok": True, "limit": WEEKLY_STUDY_LIMIT, "count": weekly_count}

    if cat not in ("food", "drink"):
        return {"ok": True, "limit": 999, "count": 0}

    limit = DAILY_FOOD_LIMIT if cat == "food" else DAILY_DRINK_LIMIT
    today_count = get_daily_category_count(cat)

    if today_count >= limit:
        label = "đồ ăn" if cat == "food" else "đồ uống"
        return {
            "ok": False,
            "limit": limit,
            "count": today_count,
            "error": f"⚠️ Bạn đã mua đủ {label} hôm nay ({limit}/{limit}). Hãy quay lại vào ngày mai!"
        }

    return {"ok": True, "limit": limit, "count": today_count}


def get_daily_limits_info() -> dict:
    """Trả về thông tin daily limit cho UI.
    Gom food+drink vào 1 lần đọc purchase log để giảm I/O.
    """
    global _ITEM_CATEGORY_CACHE
    if _ITEM_CATEGORY_CACHE is None:
        _build_item_category_cache()
    log = _get_purchase_log()
    today = _get_today_key()
    day_data = log.get(today, {})
    food_count = 0
    drink_count = 0
    for item_id, cat in _ITEM_CATEGORY_CACHE.items():
        cnt = day_data.get(item_id, 0)
        if cnt and cat == "food":
            food_count += cnt
        elif cnt and cat == "drink":
            drink_count += cnt
    return {
        "food": {"current": food_count, "max": DAILY_FOOD_LIMIT},
        "drink": {"current": drink_count, "max": DAILY_DRINK_LIMIT},
    }


# ── Daily Cancel Limit (hủy kích hoạt boost) ────────────────
# Mỗi ngày được hủy tối đa N lần, mỗi 10 thẻ hợp lệ thêm 1 lần, tối đa 20.

def _get_daily_cancel_count_raw() -> int:
    """Đọc số lần hủy đã dùng hôm nay từ config."""
    return cfg_int(_KEY_DAILY_CANCEL_COUNT, 0)

def _get_daily_cancel_date() -> str:
    """Đọc ngày ghi nhận hủy từ config."""
    return cfg_str(_KEY_DAILY_CANCEL_DATE, "")

def _set_daily_cancel_count(val: int):
    cfg_set(_KEY_DAILY_CANCEL_COUNT, val)

def _set_daily_cancel_date(val: str):
    cfg_set(_KEY_DAILY_CANCEL_DATE, val)


def get_daily_cancel_count() -> int:
    """Trả về số lần hủy boost đã dùng hôm nay.
    Tự động reset nếu sang ngày mới.
    """
    today = _get_today_key()
    if _get_daily_cancel_date() != today:
        _set_daily_cancel_count(0)
        _set_daily_cancel_date(today)
        return 0
    return _get_daily_cancel_count_raw()


def get_today_valid_card_count() -> int:
    """Trả về số thẻ học hợp lệ (time_per_card >= 10s) hôm nay.
    Tự động reset nếu sang ngày mới.
    """
    today = _get_today_key()
    date = cfg_str(_KEY_CARD_TIME_DATE, "")
    if date != today:
        cfg_set(_KEY_CARD_TIME_VALID, 0)
        cfg_set(_KEY_CARD_TIME_DATE, today)
        return 0
    return cfg_int(_KEY_CARD_TIME_VALID, 0)


def record_card_review_time(time_seconds: float):
    """Ghi nhận thời gian ôn 1 thẻ.
    Nếu time_seconds >= MIN_CARD_TIME_SECONDS (10s), tính là thẻ hợp lệ
    để mở rộng giới hạn hủy boost.
    """
    if time_seconds < MIN_CARD_TIME_SECONDS:
        return  # không đủ thời gian → không tính
    today = _get_today_key()
    date = cfg_str(_KEY_CARD_TIME_DATE, "")
    if date != today:
        cfg_set(_KEY_CARD_TIME_VALID, 0)
        cfg_set(_KEY_CARD_TIME_DATE, today)
    count = cfg_int(_KEY_CARD_TIME_VALID, 0) + 1
    cfg_set(_KEY_CARD_TIME_VALID, count)


def get_daily_cancel_limit() -> dict:
    """Tính toán limit hủy boost hôm nay.
    Công thức: limit = min(MAX, BASE + floor(valid_cards / CARDS_PER_EXTRA_CANCEL))

    Trả về: {
        "base_limit": 10,
        "max_limit": 20,
        "extra_from_cards": 5,      # số lần được thêm từ học thẻ
        "limit": 15,                # limit thực tế hôm nay
        "used": 3,                  # đã dùng
        "remaining": 12,            # còn lại
        "total_valid_cards": 50,    # tổng thẻ hợp lệ hôm nay
        "cards_for_next": 0,        # cần thêm ? thẻ để có thêm 1 lần hủy
    }
    """
    valid_cards = get_today_valid_card_count()
    extra = valid_cards // CARDS_PER_EXTRA_CANCEL
    limit = BASE_DAILY_CANCEL_LIMIT + extra
    if limit > MAX_DAILY_CANCEL_LIMIT:
        limit = MAX_DAILY_CANCEL_LIMIT
    used = get_daily_cancel_count()
    remaining = max(0, limit - used)

    # Tính xem cần thêm bao nhiêu thẻ để có thêm 1 lần hủy
    next_extra = extra + 1
    next_limit = BASE_DAILY_CANCEL_LIMIT + next_extra
    if next_limit > MAX_DAILY_CANCEL_LIMIT:
        cards_for_next = 0  # đã đạt max
    else:
        cards_for_next = (next_extra * CARDS_PER_EXTRA_CANCEL) - valid_cards

    return {
        "base_limit": BASE_DAILY_CANCEL_LIMIT,
        "max_limit": MAX_DAILY_CANCEL_LIMIT,
        "extra_from_cards": extra,
        "limit": limit,
        "used": used,
        "remaining": remaining,
        "total_valid_cards": valid_cards,
        "cards_needed_for_next": max(0, cards_for_next),
    }


def record_cancel() -> dict:
    """Ghi nhận 1 lần hủy boost. Tự động reset nếu sang ngày mới.
    Trả về: {"ok": True/False, "remaining": int, "limit": int, "error": str}
    """
    today = _get_today_key()
    if _get_daily_cancel_date() != today:
        _set_daily_cancel_count(0)
        _set_daily_cancel_date(today)

    limit_info = get_daily_cancel_limit()
    if limit_info["remaining"] <= 0:
        return {
            "ok": False,
            "remaining": 0,
            "limit": limit_info["limit"],
            "error": (
                f"⚠️ Bạn đã hết lượt hủy hôm nay ({limit_info['limit']}/{limit_info['limit']}). "
                f"Học thêm {limit_info['cards_needed_for_next']} thẻ "
                f"(mỗi thẻ ≥{MIN_CARD_TIME_SECONDS}s) để mở thêm 1 lượt hủy!"
            ),
        }

    current = _get_daily_cancel_count_raw() + 1
    _set_daily_cancel_count(current)
    new_remaining = limit_info["remaining"] - 1
    return {"ok": True, "remaining": new_remaining, "limit": limit_info["limit"]}


# ── Helpers: Active Boosts & Freshness ───────────────────────

def _get_active() -> list:
    """Đọc danh sách active boosts từ Anki config."""
    val = cfg_list(_KEY_ACTIVE, [])
    return val if isinstance(val, list) else []


def _save_active(lst: list):
    """Ghi danh sách active boosts xuống Anki config."""
    cfg_set(_KEY_ACTIVE, lst)


def _get_fresh() -> dict:
    """Đọc dictionary freshness từ Anki config."""
    return cfg_dict(_KEY_FRESH, {})


def _save_fresh(d: dict):
    """Ghi dictionary freshness xuống Anki config."""
    cfg_set(_KEY_FRESH, d)


# ── Freshness ────────────────────────────────────────────────

def register_food_purchase(item_id: str, slot_id: str, expire_h: float):
    if not col_ready():
        return
    freshness = _get_fresh()
    freshness[slot_id] = {
        "item_id":  item_id,
        "buy_ts":   time.time(),
        "expire_h": float(expire_h),
    }
    _save_fresh(freshness)


def get_spoiled_slots() -> list:
    if not col_ready():
        return []
    freshness = _get_fresh()
    now = time.time()
    return [
        sid for sid, info in freshness.items()
        if now - float(info.get("buy_ts", 0) or 0) > float(info.get("expire_h", 24) or 24) * 3600
    ]


def remove_freshness_slot(slot_id: str):
    freshness = _get_fresh()
    if slot_id in freshness:
        freshness.pop(slot_id, None)
        _save_fresh(freshness)


def check_and_spoil_food() -> list:
    if not col_ready():
        return []
    from .inventory import get_inventory
    spoiled_slots = get_spoiled_slots()
    if not spoiled_slots:
        return []

    freshness     = _get_fresh()
    spoiled_items = []
    inv           = get_inventory()

    for slot_id in spoiled_slots:
        info = freshness.get(slot_id, {})
        item_id = info.get("item_id", "")
        if item_id in inv:
            inv.remove(item_id)
            spoiled_items.append(item_id)
        freshness.pop(slot_id, None)

    cfg_set(CONFIG_KEY_INVENTORY, inv)
    _save_fresh(freshness)
    return spoiled_items


# ── Active Boosts ────────────────────────────────────────────

def get_active_boosts() -> list:
    boosts = _get_active()
    now = time.time()
    valid = []
    for b in boosts:
        exp = b.get("expire_ts")
        if exp is not None and now > exp:
            continue
        cards_left = b.get("cards_left")
        if cards_left is not None and cards_left <= 0:
            continue
        valid.append(b)
    if len(valid) != len(boosts):
        _save_active(valid)
    return valid


# ── Hằng số giới hạn ─────────────────────────────
MAX_MULTIPLIER = 50.0  # cap tối đa reward_multiplier (chống overflow)


def _has_active_boost_of_category(item_category: str) -> bool:
    """Kiểm tra đã có boost active trong category (food/drink) này chưa."""
    boosts = get_active_boosts()
    for b in boosts:
        cat = b.get("item_category", "other")
        if cat == item_category:
            return True
    return False


def activate_boost(item_id: str, effect: dict, slot_id: str) -> dict:
    if not col_ready():
        return {"ok": False, "error": "Chưa sẵn sàng."}

    # ── Xác định category ──
    # FIX: effect dict không có key "category", nên _get_item_category
    # không thể xác định đúng category. Fallback lookup từ shop_items.json
    item_category = _get_item_category(item_id, effect)
    if item_category == "other":
        try:
            from .shop_data import load_shop_items
            shop_items = load_shop_items()
            match = next((i for i in shop_items if i["id"] == item_id), None)
            if match:
                item_category = _get_item_category(item_id, match)
        except Exception:
            pass

    # ── Kiểm tra giới hạn: 1 food + 1 drink + 1 study ──
    if item_category in ("food", "drink", "study"):
        if _has_active_boost_of_category(item_category):
            label_map = {"food": "đồ ăn", "drink": "đồ uống", "study": "vật phẩm học tập"}
            label = label_map.get(item_category, item_category)
            return {"ok": False, "error": f"⚠️ Bạn đang có hiệu ứng {label} active! Hãy đợi hiệu ứng hiện tại kết thúc trước khi dùng cái mới."}

    # ── Kiểm tra inventory ──
    inv = cfg_list("anki_tycoon_inventory", [])
    if item_id not in inv:
        return {"ok": False, "error": "Không tìm thấy vật phẩm trong kho."}
    inv.remove(item_id)
    cfg_set("anki_tycoon_inventory", inv)
    remove_freshness_slot(slot_id)

    now = time.time()

    # Kiểm tra nếu có _all_effects (từ effect_list)
    all_effects = effect.get("_all_effects", [effect])
    if not all_effects:
        all_effects = [effect]

    # ── Time-of-day optimization ──
    slot_name, time_bonus, time_desc = _get_current_time_slot()

    # Tạo boost record chính từ effect đầu tiên
    primary = all_effects[0]
    duration = int(primary.get("duration", 0) or 0)
    cards    = int(primary.get("cards", 0) or 0)

    # Bug fix: khi không có duration/cards → dùng expire_h làm fallback,
    # tránh tạo boost vô hạn (expire_ts=None, cards_left=None cùng lúc)
    if duration <= 0 and cards <= 0:
        max_expire_h = max(
            (float(e.get("expire_h", 0) or 0) for e in all_effects),
            default=0.0,
        )
        if max_expire_h > 0:
            duration = int(max_expire_h * 3600)

    # Apply time bonus vào value (chỉ cho reward_multiplier, xp_bonus)
    adjusted_effects = []
    for eff in all_effects:
        e = dict(eff)
        etype = e.get("type", "")
        if etype in ("reward_multiplier",) and time_bonus != 1.0:
            val = float(e.get("value", 1.0))
            e["value"] = round(val * time_bonus, 3)
            e["desc"] = e.get("desc", "") + f" ({time_desc})"
        adjusted_effects.append(e)

    primary_adj = adjusted_effects[0]
    boost = {
        "id":             slot_id,
        "item_id":        item_id,
        "item_category":  item_category,
        "type":           primary_adj.get("type", "reward_multiplier"),
        "value":          primary_adj.get("value", 1.0),
        "name":           primary_adj.get("name", item_id),
        "desc":           primary_adj.get("desc", ""),
        "start_ts":       now,
        "expire_ts":      (now + duration) if duration > 0 else None,
        "cards_left":     cards if cards > 0 else None,
        "time_slot":      slot_name,
        "time_bonus":     time_bonus,
        # Lưu tất cả effects để consume_boost_card xử lý
        "effect_list":    adjusted_effects,
    }

    # Áp dụng hiệu ứng 1 lần ngay tại activation (trước khi lưu boost)
    for eff in adjusted_effects:
        etype = eff.get("type", "")
        val   = eff.get("value", 0) or 0
        if etype == "energy_burst":
            # Hồi năng lượng tức thì khi dùng item
            try:
                from .energy_system import restore_energy
                restore_energy(int(val))
            except Exception:
                pass
        elif etype == "effect_extend":
            # Kéo dài thời gian các boost đang active khác
            ext_s = int(val)
            if ext_s > 0:
                existing = _get_active()
                for b in existing:
                    if b.get("expire_ts") is not None:
                        b["expire_ts"] += ext_s
                _save_active(existing)
        elif etype == "item_preserve":
            # Kéo dài hạn sử dụng tất cả items trong kho
            ext_h = float(val)
            if ext_h > 0:
                freshness = _get_fresh()
                for sid in freshness:
                    freshness[sid]["expire_h"] = (
                        float(freshness[sid].get("expire_h", 24) or 24) + ext_h
                    )
                _save_fresh(freshness)

    boosts = _get_active()
    boosts.append(boost)
    _save_active(boosts)

    # Gom mô tả từ tất cả effects
    descs = [e.get("desc", "") for e in adjusted_effects if e.get("desc")]
    message = " | ".join(descs) if descs else effect.get("desc", "Boost đã kích hoạt!")

    return {"ok": True, "boost": boost, "message": message}


def consume_boost_card(ease: int) -> dict:
    """
    Xử lý active boosts khi review card.
    Mở rộng: hỗ trợ movement_speed, stamina_regen, energy_limit,
    interval_boost, easy_interval_bonus, factor_boost,
    và xử lý cả effect_list trong active boost.

    v1.0.7 — Thêm trade-off (penalty) effects:
      - stamina_cost: -X thể lực khi review
      - reward_penalty: ×(1 - value) giảm tiền thưởng
    """
    import datetime
    boosts = get_active_boosts()
    if not boosts:
        return {"multiplier": 1.0, "bonus": 0, "shield": False,
                "movement_speed": 0, "stamina_regen": 0, "energy_regen": 0, "energy_limit": 0,
                "interval_boost": 0.0, "easy_interval_bonus": 0.0, "factor_boost": 0.0,
                "stamina_cost": 0, "reward_penalty": 0.0}

    multiplier = 1.0
    bonus      = 0
    shield     = False
    movement_speed = 0
    stamina_regen  = 0
    energy_regen   = 0
    energy_limit   = 0
    interval_boost = 0.0
    easy_interval_bonus = 0.0
    factor_boost = 0.0
    # --- Trade-off / Penalty fields ---
    stamina_cost  = 0
    reward_penalty = 0.0   # 0 = no penalty, 0.1 = -10%, 0.5 = -50%
    # --- v1.1.0 Energy management ---
    energy_reduce  = 1.0   # 1.0 = bình thường, 0.5 = tiêu 50% NL/thẻ
    energy_shield  = False  # True = không tốn NL trong thẻ này
    updated    = []

    now = time.time()
    current_hour = datetime.datetime.now().hour

    for b in boosts:
        # Xử lý effect_list nếu có (multi-effect từ food/study items)
        effect_list = b.get("effect_list", [])
        if not effect_list:
            effect_list = [b]  # fallback: dùng chính boost record

        for eff in effect_list:
            etype = eff.get("type", b.get("type", ""))
            val   = eff.get("value", b.get("value", 0)) or 0

            if etype == "reward_multiplier":
                multiplier *= float(val)
                # Cap multiplier để chống overflow khi stack nhiều đồ
                if multiplier > MAX_MULTIPLIER:
                    multiplier = MAX_MULTIPLIER
            elif etype == "xp_bonus":
                bonus += int(val)
            elif etype == "penalty_shield":
                shield = True
            elif etype == "no_again_penalty":
                shield = True
            elif etype == "double_easy" and ease == 4:
                multiplier *= float(val)
            elif etype == "night_owl" and current_hour >= 22:
                multiplier *= float(val)
            elif etype == "movement_speed":
                movement_speed = max(movement_speed, float(val))
            elif etype == "stamina_regen":
                stamina_regen += int(val)
            elif etype == "energy_regen":
                energy_regen += int(val)
            elif etype == "energy_limit":
                energy_limit = max(energy_limit, int(val))
            elif etype == "interval_boost":
                interval_boost += float(val)
            elif etype == "easy_interval_bonus" and ease == 4:
                easy_interval_bonus += float(val)
            elif etype == "factor_boost":
                factor_boost += float(val)
            # --- v1.0.7 Trade-off / Penalty effects ---
            elif etype == "stamina_cost":
                stamina_cost += int(val)
            elif etype == "reward_penalty":
                # reward_penalty: value là % bị trừ (0.1 = -10%)
                reward_penalty = max(reward_penalty, float(val))
            # --- v1.1.0 Energy management ---
            elif etype == "energy_reduce":
                # value = tỉ lệ NL còn lại sau reduce (0.5 = giảm 50%)
                energy_reduce = min(energy_reduce, float(val))
            elif etype == "energy_shield":
                energy_shield = True

        if b.get("cards_left") is not None:
            b["cards_left"] = max(0, int(b["cards_left"]) - 1)
        updated.append(b)

    _save_active(updated)
    return {
        "multiplier": multiplier,
        "bonus": bonus,
        "shield": shield,
        "movement_speed": movement_speed,
        "stamina_regen": stamina_regen,
        "energy_regen": energy_regen,
        "energy_limit": energy_limit,
        "interval_boost": interval_boost,
        "easy_interval_bonus": easy_interval_bonus,
        "factor_boost": factor_boost,
        # --- v1.0.7 Trade-off / Penalty ---
        "stamina_cost": stamina_cost,
        "reward_penalty": reward_penalty,
        # --- v1.1.0 Energy management ---
        "energy_reduce": energy_reduce,
        "energy_shield": energy_shield,
    }


def get_effect_for_item(item_id: str, item_data: dict = None) -> dict:
    """
    Lấy effect dict cho item. Hỗ trợ cả `effect` (1) và `effect_list` (nhiều).
    Khi có effect_list, trả về effect đầu tiên làm primary để tương thích ngược,
    nhưng lưu toàn bộ list vào boost record.
    """
    if item_data:
        # Nếu có effect_list, lấy effect đầu làm primary
        if "effect_list" in item_data and isinstance(item_data["effect_list"], list):
            el = item_data["effect_list"]
            if el:
                e = dict(el[0])
                e.setdefault("name", item_data.get("name", item_id))
                e.setdefault("desc", f"Boost từ {item_data.get('name', item_id)}")
                # Lưu toàn bộ effect_list vào key _all_effects để activate_boost xử lý
                e["_all_effects"] = el
                return e
        if "effect" in item_data and isinstance(item_data["effect"], dict):
            e = dict(item_data["effect"])
            e.setdefault("name", item_data.get("name", item_id))
            e.setdefault("desc", f"Boost từ {item_data.get('name', item_id)}")
            return e
    return DEFAULT_EFFECTS.get(item_id, {
        "type": "reward_multiplier", "value": 1.2,
        "duration": 1800, "cards": 0, "expire_h": 12,
        "name": item_id, "desc": "×1.2 tiền thưởng trong 30 phút"
    })


def get_boosts_summary() -> list:
    boosts = get_active_boosts()
    now    = time.time()
    result = []
    for b in boosts:
        remaining_s = None
        exp = b.get("expire_ts")
        if exp is not None:
            remaining_s = max(0, exp - now)
        result.append({
            "id":             b.get("id"),
            "item_id":        b.get("item_id"),
            "item_category":  b.get("item_category", "other"),
            "name":           b.get("name"),
            "desc":           b.get("desc"),
            "type":           b.get("type"),
            "value":          b.get("value"),
            "remaining_s":    remaining_s,
            "cards_left":     b.get("cards_left"),
            "time_slot":      b.get("time_slot", ""),
            "time_bonus":     b.get("time_bonus", 1.0),
        })
    return result


def deactivate_boost(slot_id: str) -> dict:
    """
    Hủy kích hoạt 1 boost đang active.
    - Kiểm tra daily cancel limit (mặc định 10 lần/ngày, mở rộng đến 20)
    - Mỗi 10 thẻ học hợp lệ (≥10s) thêm 1 lần hủy
    - Không hoàn tiền
    - Xóa boost khỏi danh sách active
    """
    if not col_ready():
        return {"ok": False, "error": "Chưa sẵn sàng."}

    # ── Kiểm tra daily cancel limit ──
    cancel_check = record_cancel()
    if not cancel_check["ok"]:
        return {
            "ok": False,
            "error": cancel_check.get("error", "⚠️ Bạn đã hết lượt hủy hôm nay!"),
            "remaining": cancel_check.get("remaining", 0),
            "limit": cancel_check.get("limit", BASE_DAILY_CANCEL_LIMIT),
        }

    # Dùng get_active_boosts() thay vì _get_active() để lọc boost đã hết hạn
    boosts = get_active_boosts()
    found = None
    for b in boosts:
        if b.get("id") == slot_id:
            found = b
            break

    if not found:
        return {"ok": False, "error": "Hiệu ứng đã hết hạn hoặc không tồn tại."}

    boosts.remove(found)
    _save_active(boosts)
    return {
        "ok": True,
        "message": f"Đã hủy hiệu ứng {found.get('name', '')}",
        "remaining": cancel_check.get("remaining", 0),
        "limit": cancel_check.get("limit", BASE_DAILY_CANCEL_LIMIT),
    }
