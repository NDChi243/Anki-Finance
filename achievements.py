# -*- coding: utf-8 -*-
from __future__ import annotations
"""
achievements.py — Hệ thống Thành tựu (Achievement) Anki Finance.

Khác với Daily Quest (ngắn hạn, reset mỗi ngày) và Rank (dài hạn, tuyến tính),
Achievement là mục tiêu vĩnh viễn, đa dạng, có phần thưởng 1 lần + effect vĩnh viễn.

Trigger points gọi check_and_unlock() từ:
  - __init__.py        → card_reviewed
  - streak_system.py   → streak_updated
  - web_bridge.py      → item_purchased
  - stock_market.py    → stock_traded
  - daily_quest.py     → quest_claimed
  - emergency_events.py → emergency_handled
"""

from ._safe_config import col_ready, cfg_dict, cfg_set, cfg_str
from .logger import get_logger
logger = get_logger(__name__)


def _get_mode_suffix() -> str:
    try:
        from .config import CONFIG_KEY_GAME_MODE, DEFAULT_GAME_MODE
        return cfg_str(CONFIG_KEY_GAME_MODE, DEFAULT_GAME_MODE) or DEFAULT_GAME_MODE
    except Exception:
        return "full"


def _key_data() -> str:
    """Achievement data riêng theo mode hiện tại."""
    return f"anki_tycoon_achievement_data_{_get_mode_suffix()}"


def _key_effects() -> str:
    """Achievement passive effects riêng theo mode."""
    return f"anki_tycoon_achievement_effects_{_get_mode_suffix()}"


# Modes shortcuts
_M_BOTH = ["simple", "full"]
_M_FULL = ["full"]

# ── Achievement definitions ─────────────────────────────────────────

ACHIEVEMENTS = [
    # ── Học tập ───────────────────────────────────────────────────
    {
        "id": "ach_study_100",
        "title": "Tân binh chăm chỉ",
        "desc": "Ôn tổng cộng 100 thẻ",
        "emoji": "\U0001f4d6",
        "category": "Học tập",
        "condition": {"type": "total_cards", "target": 100},
        "reward": {"money": 150_000, "xp": 500},
        "effect": None,
    },
    {
        "id": "ach_study_1000",
        "title": "Cần cù bù thông minh",
        "desc": "Ôn tổng cộng 1.000 thẻ",
        "emoji": "\U0001f4da",
        "category": "Học tập",
        "condition": {"type": "total_cards", "target": 1000},
        "reward": {"money": 900_000, "xp": 1_750},
        "effect": {"type": "xp_bonus", "value": 100},
    },
    {
        "id": "ach_study_10k",
        "title": "Cỗ máy học tập",
        "desc": "Ôn tổng cộng 10.000 thẻ",
        "emoji": "\U0001f916",
        "category": "Học tập",
        "condition": {"type": "total_cards", "target": 10_000},
        "reward": {"money": 10_000_000, "xp": 15_000},
        "effect": {"type": "reward_multiplier", "value": 0.05},
    },
    {
        "id": "ach_study_easy_500",
        "title": "Vua Easy",
        "desc": "Bấm Easy 500 lần",
        "emoji": "\U0001f60e",
        "category": "Học tập",
        "condition": {"type": "easy_count", "target": 500},
        "reward": {"money": 350_000, "xp": 1_000},
        "effect": {"type": "easy_interval_bonus", "value": 0.03},
    },
    {
        "id": "ach_study_hard_500",
        "title": "Chiến binh Hard",
        "desc": "Bấm Hard 500 lần — không ngại thử thách",
        "emoji": "\U0001f4aa",
        "category": "Học tập",
        "condition": {"type": "hard_count", "target": 500},
        "reward": {"money": 500_000, "xp": 2_000},
        "effect": {"type": "xp_multiplier", "value": 1.03},
    },

    # ── Kỷ luật ──────────────────────────────────────────────────
    {
        "id": "ach_streak_7",
        "title": "Tuần không nghỉ",
        "desc": "Đạt streak 7 ngày",
        "emoji": "\U0001f525",
        "category": "Kỷ luật",
        "condition": {"type": "best_streak", "target": 7},
        "reward": {"money": 100_000, "xp": 1_000},
        "effect": None,
    },
    {
        "id": "ach_streak_30",
        "title": "Chiến binh tháng",
        "desc": "Đạt streak 30 ngày",
        "emoji": "\U0001f30b",
        "category": "Kỷ luật",
        "condition": {"type": "best_streak", "target": 30},
        "reward": {"money": 500_000, "xp": 5_000},
        "effect": None,
    },
    {
        "id": "ach_streak_100",
        "title": "Bất bại",
        "desc": "Đạt streak 100 ngày — kiên trì phi thường",
        "emoji": "\U0001f451",
        "category": "Kỷ luật",
        "condition": {"type": "best_streak", "target": 100},
        "reward": {"money": 5_000_000, "xp": 50_000},
        "effect": {"type": "streak_multiplier_bonus", "value": 0.25},
    },

    # ── Tài chính ────────────────────────────────────────────────
    {
        "id": "ach_networth_10m",
        "title": "100 triệu đầu tiên",
        "desc": "Đạt tổng tài sản 100 triệu VND",
        "emoji": "\U0001f4b0",
        "category": "Tài chính",
        "condition": {"type": "net_worth", "target": 100_000_000},
        "reward": {"money": 500_000, "xp": 1_000},
        "effect": None,
    },
    {
        "id": "ach_networth_1b",
        "title": "Tỷ phú",
        "desc": "Đạt tổng tài sản 1 tỷ VND",
        "emoji": "\U0001f48e",
        "category": "Tài chính",
        "condition": {"type": "net_worth", "target": 1_000_000_000},
        "reward": {"money": 5_000_000, "xp": 10_000},
        "effect": {"type": "interest_bonus", "value": 0.02},
    },
    {
        "id": "ach_networth_100b",
        "title": "Siêu tỷ phú",
        "desc": "Đạt tổng tài sản 100 tỷ VND",
        "emoji": "\U0001f3e6",
        "category": "Tài chính",
        "condition": {"type": "net_worth", "target": 100_000_000_000},
        "reward": {"money": 90_000_000, "xp": 120_000},
        "effect": {"type": "interest_bonus", "value": 0.05},
    },
    {
        "id": "ach_savings_100m",
        "title": "Người gửi tiết kiệm",
        "desc": "Có 100 triệu trong ngân hàng",
        "emoji": "\U0001f3e6",
        "category": "Tài chính",
        "condition": {"type": "total_savings", "target": 100_000_000},
        "reward": {"money": 600_000, "xp": 3_000},
        "effect": {"type": "interest_speed_boost", "value": 0.05},
    },

    # ── Đầu tư ───────────────────────────────────────────────────
    {
        "id": "ach_stock_first",
        "title": "Nhà đầu tư mới",
        "desc": "Mua cổ phiếu lần đầu tiên",
        "emoji": "\U0001f4c8",
        "category": "Đầu tư",
        "condition": {"type": "stock_first_trade", "target": 1},
        "reward": {"money": 50_000, "xp": 200},
        "effect": None,
    },
    {
        "id": "ach_stock_profit_10m",
        "title": "Lợi nhuận chứng khoán",
        "desc": "Lãi 10 triệu từ chứng khoán",
        "emoji": "\U0001f4ca",
        "category": "Đầu tư",
        "condition": {"type": "stock_total_profit", "target": 10_000_000},
        "reward": {"money": 650_000, "xp": 3_000},
        "effect": {"type": "stock_cooldown_reduction", "value": 0.03},
    },
    {
        "id": "ach_crypto_first",
        "title": "Fomo đầu tư",
        "desc": "Mua crypto lần đầu tiên",
        "emoji": "\U0001fa99",
        "category": "Đầu tư",
        "condition": {"type": "crypto_first_trade", "target": 1},
        "reward": {"money": 50_000, "xp": 200},
        "effect": None,
    },
    {
        "id": "ach_crypto_stake",
        "title": "Staker",
        "desc": "Stake crypto lần đầu tiên",
        "emoji": "\U0001f512",
        "category": "Đầu tư",
        "condition": {"type": "crypto_first_stake", "target": 1},
        "reward": {"money": 100_000, "xp": 500},
        "effect": None,
    },
    {
        "id": "ach_rental_first",
        "title": "Địa chủ",
        "desc": "Mua BĐS cho thuê lần đầu tiên",
        "emoji": "\U0001f3e0",
        "category": "Đầu tư",
        "condition": {"type": "re_first_purchase", "target": 1},
        "reward": {"money": 1_000_000, "xp": 2_500},
        "effect": None,
    },

    # ── Sưu tập ──────────────────────────────────────────────────
    {
        "id": "ach_car_first",
        "title": "Lên xe",
        "desc": "Mua xe đầu tiên",
        "emoji": "\U0001f697",
        "category": "Sưu tập",
        "condition": {"type": "own_category", "target": 1, "category": "\U0001f697 Showroom xe"},
        "reward": {"money": 250_000, "xp": 2_000},
        "effect": None,
    },
    {
        "id": "ach_car_5",
        "title": "Bộ sưu tập xe",
        "desc": "Sở hữu 5 chiếc xe",
        "emoji": "\U0001f3ce\ufe0f",
        "category": "Sưu tập",
        "condition": {"type": "own_category", "target": 5, "category": "\U0001f697 Showroom xe"},
        "reward": {"money": 1_000_000, "xp": 5_500},
        "effect": {"type": "study_time_reduction", "value": 0.02},
    },
    {
        "id": "ach_tech_3",
        "title": "Dân công nghệ",
        "desc": "Sở hữu 3 món đồ công nghệ",
        "emoji": "\U0001f4bb",
        "category": "Sưu tập",
        "condition": {"type": "own_category", "target": 3, "category": "Cửa hàng đồ công nghệ"},
        "reward": {"money": 300_000, "xp": 1_000},
        "effect": None,
    },
    {
        "id": "ach_luxury_first",
        "title": "Hàng hiệu đầu tiên",
        "desc": "Mua món hàng hiệu đầu tiên",
        "emoji": "\U0001f48d",
        "category": "Sưu tập",
        "condition": {"type": "own_category", "target": 1, "category": "\U0001f454 Cửa hàng hàng hiệu"},
        "reward": {"money": 200_000, "xp": 1_200},
        "effect": None,
    },

    # ── Sự kiện ──────────────────────────────────────────────────
    {
        "id": "ach_emergency_10",
        "title": "Sống sót",
        "desc": "Vượt qua 10 sự kiện tài chính khẩn cấp",
        "emoji": "\U0001f6e1\ufe0f",
        "category": "Sự kiện",
        "condition": {"type": "emergency_survived", "target": 10},
        "reward": {"money": 1_000_000, "xp": 5_000},
        "effect": None,
    },
    {
        "id": "ach_quest_100",
        "title": "Người làm quest",
        "desc": "Hoàn thành 100 daily quest",
        "emoji": "\U0001f3af",
        "category": "Sự kiện",
        "condition": {"type": "quest_completed", "target": 100},
        "reward": {"money": 800_000, "xp": 1_000},
        "effect": None,
    },

    # ── Rank ─────────────────────────────────────────────────────
    {
        "id": "ach_rank_doanhnhan",
        "title": "Founder chính hiệu",
        "desc": "Đạt rank Founder (Doanh nhân cấp 1)",
        "emoji": "\U0001f680",
        "category": "Rank",
        "condition": {"type": "rank_reach", "target": "dn1"},
        "reward": {"money": 20_000_000, "xp": 10_000},
        "effect": {"type": "xp_multiplier", "value": 1.05},
    },
    {
        "id": "ach_rank_typhu",
        "title": "Tỷ phú Phố Wall",
        "desc": "Đạt rank Tỷ phú",
        "emoji": "\U0001f31f",
        "category": "Rank",
        "condition": {"type": "rank_reach", "target": "typh1"},
        "reward": {"money": 25_000_000, "xp": 50_000},
        "effect": {"type": "xp_multiplier", "value": 1.10},
    },

    # ── Ẩn ───────────────────────────────────────────────────────
    {
        "id": "ach_hidden_rugpull",
        "title": "Bị lừa rồi!",
        "desc": "Dính rug pull crypto",
        "emoji": "\U0001f631",
        "category": "Ẩn",
        "condition": {"type": "rugpull_victim", "target": 1},
        "reward": {"money": 0, "xp": 1_000},
        "effect": None,
        "hidden": True,
    },
    {
        "id": "ach_hidden_poor",
        "title": "Về 0",
        "desc": "Tài khoản tụt xuống dưới 1.000₫",
        "emoji": "\U0001f480",
        "category": "Ẩn",
        "condition": {"type": "balance_drop_below", "target": 1_000},
        "reward": {"money": 10_000, "xp": 500},
        "effect": None,
        "hidden": True,
    },
]

_ACH_MAP = {a["id"]: a for a in ACHIEVEMENTS}

# ── Mode filtering ──────────────────────────────────────────────────
# Achievement nào chỉ thuộc Full Mode (vì cần stocks/crypto/RE/garage/tech/sự kiện).
_FULL_ONLY_CATEGORIES = {"Đầu tư", "Sưu tập"}
_FULL_ONLY_IDS = {"ach_emergency_10", "ach_hidden_rugpull"}


def _ach_modes(ach: dict) -> list:
    """Trả về list các mode mà achievement này có thể đạt được."""
    if ach.get("id", "") in _FULL_ONLY_IDS:
        return ["full"]
    if ach.get("category", "") in _FULL_ONLY_CATEGORIES:
        return ["full"]
    return ["simple", "full"]


def _ach_in_current_mode(ach: dict) -> bool:
    return _get_mode_suffix() in _ach_modes(ach)


# ── Data helpers ────────────────────────────────────────────────────

def _default_data() -> dict:
    return {
        "stats": {
            "total_cards": 0,
            "easy_count": 0,
            "hard_count": 0,
            "best_streak": 0,
            "net_worth": 0,
            "total_savings": 0,
            "stock_first_trade": False,
            "stock_total_profit": 0,
            "crypto_first_trade": False,
            "crypto_first_stake": False,
            "re_first_purchase": False,
            "emergency_survived": 0,
            "quest_completed": 0,
            "rugpull_victim": False,
            "balance_drop_below": False,
        },
        "unlocked_ids": [],
        "claimed_ids": [],
    }


def _load_data() -> dict:
    if not col_ready():
        return _default_data()
    d = cfg_dict(_key_data(), _default_data())
    # Đảm bảo đủ keys
    def_data = _default_data()
    for k, v in def_data.items():
        if k not in d:
            d[k] = v
        elif isinstance(v, dict) and isinstance(d[k], dict):
            for sk, sv in v.items():
                if sk not in d[k]:
                    d[k][sk] = sv
    return d


def _save_data(data: dict):
    cfg_set(_key_data(), data)


def _load_effects() -> dict:
    return cfg_dict(_key_effects(), {})


def _save_effects(effects: dict):
    cfg_set(_key_effects(), effects)


# ── Core logic ──────────────────────────────────────────────────────

def _get_stat(data: dict, key: str):
    """Lấy 1 stat từ data['stats'], an toàn với bool/int."""
    stats = data.get("stats", {})
    val = stats.get(key, 0)
    return val


def _set_stat(data: dict, key: str, value):
    stats = data.get("stats", {})
    old = stats.get(key, 0)
    if isinstance(value, bool):
        # bool: chỉ set True, không set lại False
        if value:
            stats[key] = True
    elif isinstance(value, (int, float)):
        # int/float: chỉ update nếu value > old
        if value > old:
            stats[key] = value
    data["stats"] = stats


def _check_condition(ach: dict, data: dict) -> bool:
    """Kiểm tra 1 achievement đã đủ điều kiện unlock chưa."""
    cond = ach.get("condition", {})
    ctype = cond.get("type", "")
    target = cond.get("target", 1)
    stats = data.get("stats", {})

    if ctype == "total_cards":
        return stats.get("total_cards", 0) >= target
    elif ctype == "easy_count":
        return stats.get("easy_count", 0) >= target
    elif ctype == "hard_count":
        return stats.get("hard_count", 0) >= target
    elif ctype == "best_streak":
        return stats.get("best_streak", 0) >= target
    elif ctype == "net_worth":
        return stats.get("net_worth", 0) >= target
    elif ctype == "total_savings":
        return stats.get("total_savings", 0) >= target
    elif ctype == "stock_first_trade":
        return bool(stats.get("stock_first_trade", False))
    elif ctype == "stock_total_profit":
        return stats.get("stock_total_profit", 0) >= target
    elif ctype == "crypto_first_trade":
        return bool(stats.get("crypto_first_trade", False))
    elif ctype == "crypto_first_stake":
        return bool(stats.get("crypto_first_stake", False))
    elif ctype == "re_first_purchase":
        return bool(stats.get("re_first_purchase", False))
    elif ctype == "emergency_survived":
        return stats.get("emergency_survived", 0) >= target
    elif ctype == "quest_completed":
        return stats.get("quest_completed", 0) >= target
    elif ctype == "rank_reach":
        return stats.get("current_rank_id", "") >= target
    elif ctype == "rugpull_victim":
        return bool(stats.get("rugpull_victim", False))
    elif ctype == "balance_drop_below":
        return bool(stats.get("balance_drop_below", False))
    elif ctype == "own_category":
        # Kiểm tra từ inventory
        return _count_owned_in_category(cond.get("category", "")) >= target
    return False


def _count_owned_in_category(category: str) -> int:
    """Đếm số item RIÊNG BIỆT đang sở hữu trong 1 category (không tính trùng)."""
    try:
        from .inventory import get_unique_items
        # Dùng get_unique_items() để đếm item riêng biệt, tránh trùng lặp
        inv = get_unique_items()
        if not inv:
            return 0
        from .shop_data import load_shop_items
        items = {i["id"]: i for i in load_shop_items()}
        count = 0
        for item_id in inv:
            item = items.get(item_id)
            if item and category in item.get("category", ""):
                count += 1
        return count
    except Exception as e:
        logger.warning("_count_owned_in_category: %s", e)
        return 0


def _get_net_worth() -> int:
    """Tính tổng tài sản ròng."""
    try:
        from .balance import get_balance
        bal = get_balance()
        total = bal
        try:
            from .bank import get_total_current_value
            total += int(get_total_current_value())
        except Exception as e:
            logger.debug("_get_net_worth: bank total_current_value — %s", e)
        try:
            from .stock_market import get_portfolio_summary
            ps = get_portfolio_summary()
            total += int(ps.get("total_value", 0))
        except Exception as e:
            logger.debug("_get_net_worth: stocks portfolio_summary — %s", e)
        try:
            from .digital_assets import get_portfolio_summary
            cps = get_portfolio_summary()
            total += int(cps.get("total_value_vnd", 0))
        except Exception as e:
            logger.debug("_get_net_worth: crypto portfolio_summary — %s", e)
        return max(0, total)
    except Exception as e:
        logger.warning("_get_net_worth: %s", e)
        return 0


def _get_total_savings() -> int:
    """Tổng tiền gửi ngân hàng."""
    try:
        from .bank import get_total_savings
        return get_total_savings()
    except Exception as e:
        logger.warning("_get_total_savings: %s", e)
        return 0


def _apply_effect_to_system(effect: dict | None):
    """Ghi effect vĩnh viễn từ achievement vào config riêng."""
    if not effect:
        return
    etype = effect.get("type", "")
    evalue = effect.get("value", 0)
    if not etype or not evalue:
        return

    effects = _load_effects()
    old = effects.get(etype, 0)

    if etype in ("xp_multiplier", "reward_multiplier", "streak_multiplier_bonus",
                  "interest_bonus", "interest_speed_boost",
                  "stock_cooldown_reduction", "study_time_reduction",
                  "easy_interval_bonus"):
        # Cộng dồn additive cho các effect cùng type
        effects[etype] = old + evalue
    elif etype == "xp_bonus":
        effects[etype] = old + evalue
    else:
        effects[etype] = old + evalue

    _save_effects(effects)


def get_permanent_effects() -> dict:
    """Trả về dict effect vĩnh viễn từ achievements đã claim.
    Dùng để tích hợp vào item_effects.get_all_passive_effects()."""
    return _load_effects()


def check_and_unlock(trigger_type: str, trigger_value=None) -> list:
    """
    Kiểm tra tất cả achievements, unlock nếu đủ điều kiện.
    Gọi từ các trigger point trong game.

    Args:
        trigger_type: Loại trigger (card_reviewed, streak_updated, ...)
        trigger_value: Giá trị kèm theo (ease, streak_count, ...)

    Returns:
        list[dict]: Danh sách achievements vừa unlock (để show notification)
    """
    if not col_ready():
        return []

    data = _load_data()
    # Lưu trigger_value vào stats nếu cần
    _handle_trigger(data, trigger_type, trigger_value)

    # Track rank để kiểm tra rank_reach
    if trigger_type == "rank_changed":
        data["stats"]["current_rank_id"] = str(trigger_value)

    # Kiểm tra tất cả achievements chưa unlock — chỉ trong mode hiện tại
    just_unlocked = []
    for ach in ACHIEVEMENTS:
        if not _ach_in_current_mode(ach):
            continue
        aid = ach["id"]
        if aid in data.get("unlocked_ids", []):
            continue
        if _check_condition(ach, data):
            unlocked = data.setdefault("unlocked_ids", [])
            unlocked.append(aid)
            just_unlocked.append(ach)

    if just_unlocked:
        _save_data(data)
        # Tự động apply effect (nhưng chưa claim)
        # Effect chỉ apply sau khi claim

    return just_unlocked


def _handle_trigger(data: dict, trigger_type: str, trigger_value):
    """Cập nhật stats dựa trên trigger."""
    stats = data.setdefault("stats", {})

    if trigger_type == "card_reviewed":
        ease = int(trigger_value) if trigger_value else 0
        stats["total_cards"] = stats.get("total_cards", 0) + 1
        if ease == 4:  # Easy (4 trong Anki)
            stats["easy_count"] = stats.get("easy_count", 0) + 1
        elif ease == 2:  # Hard (2 trong Anki)
            stats["hard_count"] = stats.get("hard_count", 0) + 1

    elif trigger_type == "streak_updated":
        streak = int(trigger_value) if trigger_value else 0
        if streak > stats.get("best_streak", 0):
            stats["best_streak"] = streak

    elif trigger_type == "net_worth_updated":
        nw = int(trigger_value) if trigger_value else _get_net_worth()
        if nw > stats.get("net_worth", 0):
            stats["net_worth"] = nw

    elif trigger_type == "savings_updated":
        sv = int(trigger_value) if trigger_value else _get_total_savings()
        if sv > stats.get("total_savings", 0):
            stats["total_savings"] = sv

    elif trigger_type == "item_purchased":
        # Kiểm tra category của item
        item_id = str(trigger_value) if trigger_value else ""
        try:
            from .shop_data import load_shop_items
            items = {i["id"]: i for i in load_shop_items()}
            item = items.get(item_id)
            if item:
                cat = item.get("category", "")
                if "\u00d4 t\u00f4" in cat or "Showroom xe" in cat:
                    pass  # own_category tự đếm từ inventory
        except Exception as e:
            logger.debug("_handle_trigger item_purchased: %s", e)

    elif trigger_type == "stock_traded":
        stats["stock_first_trade"] = True

    elif trigger_type == "stock_profit_updated":
        profit = int(trigger_value) if trigger_value else 0
        current = stats.get("stock_total_profit", 0)
        if profit > current:
            stats["stock_total_profit"] = profit

    elif trigger_type == "crypto_traded":
        stats["crypto_first_trade"] = True

    elif trigger_type == "crypto_staked":
        stats["crypto_first_stake"] = True

    elif trigger_type == "property_purchased":
        stats["re_first_purchase"] = True

    elif trigger_type == "quest_claimed":
        stats["quest_completed"] = stats.get("quest_completed", 0) + 1

    elif trigger_type == "emergency_handled":
        stats["emergency_survived"] = stats.get("emergency_survived", 0) + 1

    elif trigger_type == "rugpull_victim":
        stats["rugpull_victim"] = True

    elif trigger_type == "balance_dropped":
        stats["balance_drop_below"] = True

    elif trigger_type == "rank_changed":
        stats["current_rank_id"] = str(trigger_value)

    data["stats"] = stats


# ── Public API ──────────────────────────────────────────────────────

def claim_reward(achievement_id: str) -> dict:
    """
    Nhận thưởng của 1 achievement đã unlock.

    Returns:
        {"ok": True, "money": int, "xp": int, "effect": dict|None}
        hoặc {"ok": False, "error": str}
    """
    if not col_ready():
        return {"ok": False, "error": "Chưa sẵn sàng"}

    ach = _ACH_MAP.get(achievement_id)
    if not ach:
        return {"ok": False, "error": "Achievement không tồn tại"}

    data = _load_data()
    unlocked = data.get("unlocked_ids", [])
    claimed = data.get("claimed_ids", [])

    if achievement_id not in unlocked:
        return {"ok": False, "error": "Chưa mở khóa achievement này"}
    if achievement_id in claimed:
        return {"ok": False, "error": "Đã nhận thưởng rồi"}

    # Cộng tiền
    money = int(ach.get("reward", {}).get("money", 0))
    xp = int(ach.get("reward", {}).get("xp", 0))

    from .balance import get_balance, set_balance_and_log
    if money > 0:
        new_bal = get_balance() + money
        set_balance_and_log(new_bal, "achievement", money,
                           f"\U0001f3c6 Thành tựu: {ach['title']}")
        from .transactions import add_transaction
        add_transaction("reward", money, f"\U0001f3c6 {ach['title']}")

    from .rank_system import add_xp
    if xp > 0:
        add_xp(xp)

    # Apply effect vĩnh viễn
    effect = ach.get("effect")
    if effect:
        _apply_effect_to_system(effect)

    # Đánh dấu đã claim
    claimed.append(achievement_id)
    data["claimed_ids"] = claimed
    _save_data(data)

    return {
        "ok": True,
        "money": money,
        "xp": xp,
        "effect": effect,
        "title": ach["title"],
    }


def get_all_achievements() -> list:
    """
    Trả về tất cả achievements kèm trạng thái unlock/progress/claimed.

    Returns:
        list[dict] — mỗi dict có: id, title, desc, emoji, category,
                     hidden, unlocked, reward_claimed, condition,
                     progress_current, progress_target, progress_percent
    """
    data = _load_data()
    unlocked_set = set(data.get("unlocked_ids", []))
    claimed_set = set(data.get("claimed_ids", []))
    stats = data.get("stats", {})

    result = []
    for ach in ACHIEVEMENTS:
        # Filter theo mode hiện tại — Simple Mode không thấy ach Đầu tư/Sưu tập/...
        if not _ach_in_current_mode(ach):
            continue
        aid = ach["id"]
        unlocked = aid in unlocked_set
        claimed = aid in claimed_set

        entry = {
            "id": aid,
            "title": ach["title"],
            "desc": ach["desc"],
            "emoji": ach["emoji"],
            "category": ach["category"],
            "hidden": ach.get("hidden", False),
            "unlocked": unlocked,
            "reward_claimed": claimed,
            "reward": ach.get("reward", {}),
            "effect": ach.get("effect"),
        }

        # Progress
        cond = ach.get("condition", {})
        ctype = cond.get("type", "")
        target = cond.get("target", 1)

        if ctype == "total_cards":
            current = stats.get("total_cards", 0)
        elif ctype == "easy_count":
            current = stats.get("easy_count", 0)
        elif ctype == "hard_count":
            current = stats.get("hard_count", 0)
        elif ctype == "best_streak":
            current = stats.get("best_streak", 0)
        elif ctype == "net_worth":
            current = stats.get("net_worth", 0)
        elif ctype == "total_savings":
            current = stats.get("total_savings", 0)
        elif ctype == "stock_first_trade":
            current = 1 if stats.get("stock_first_trade") else 0
            target = 1
        elif ctype == "stock_total_profit":
            current = stats.get("stock_total_profit", 0)
        elif ctype == "crypto_first_trade":
            current = 1 if stats.get("crypto_first_trade") else 0
            target = 1
        elif ctype == "crypto_first_stake":
            current = 1 if stats.get("crypto_first_stake") else 0
            target = 1
        elif ctype == "re_first_purchase":
            current = 1 if stats.get("re_first_purchase") else 0
            target = 1
        elif ctype == "emergency_survived":
            current = stats.get("emergency_survived", 0)
        elif ctype == "quest_completed":
            current = stats.get("quest_completed", 0)
        elif ctype == "rank_reach":
            current = stats.get("current_rank_id", "")
            # Progress = số rank đã qua so với target
            try:
                from .rank_system import RANKS
                target_idx = next((i for i, r in enumerate(RANKS) if r["id"] == target), -1)
                current_idx = next((i for i, r in enumerate(RANKS) if r["id"] == current), -1)
                if target_idx > 0:
                    pct = min(100, max(0, current_idx / target_idx * 100))
                    entry["progress_current"] = current
                    entry["progress_target"] = target
                    entry["progress_percent"] = round(pct, 1)
            except Exception as e:
                logger.debug("get_achievements_list: rank_reach progress — %s", e)
            # Không set current/target mặc định
        elif ctype == "rugpull_victim":
            current = 1 if stats.get("rugpull_victim") else 0
            target = 1
        elif ctype == "balance_drop_below":
            current = 1 if stats.get("balance_drop_below") else 0
            target = 1
        elif ctype == "own_category":
            current = _count_owned_in_category(cond.get("category", ""))
        else:
            current = 0

        if ctype != "rank_reach":
            entry["progress_current"] = current
            entry["progress_target"] = target
            if target > 0:
                pct = min(100.0, current / target * 100)
                entry["progress_percent"] = round(pct, 1)
            else:
                entry["progress_percent"] = 0.0

        result.append(entry)

    return result


def get_unlocked_count() -> int:
    """Số lượng achievement đã unlock."""
    data = _load_data()
    return len(data.get("unlocked_ids", []))

def get_total_count() -> int:
    """Tổng số achievements (không tính hidden) trong mode hiện tại."""
    return len([a for a in ACHIEVEMENTS
                if not a.get("hidden", False) and _ach_in_current_mode(a)])

def get_all_count() -> int:
    """Tổng số achievements kể cả hidden trong mode hiện tại."""
    return len([a for a in ACHIEVEMENTS if _ach_in_current_mode(a)])

def get_recent_unlocked(limit: int = 3) -> list:
    """Trả về N achievements unlock gần nhất."""
    data = _load_data()
    unlocked_ids = data.get("unlocked_ids", [])
    recent = []
    for aid in reversed(unlocked_ids):
        ach = _ACH_MAP.get(aid)
        if ach:
            recent.append({
                "id": aid,
                "title": ach["title"],
                "emoji": ach["emoji"],
                "category": ach["category"],
            })
        if len(recent) >= limit:
            break
    return recent
