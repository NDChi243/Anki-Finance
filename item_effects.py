# -*- coding: utf-8 -*-
"""
item_effects.py — Hệ thống hiệu ứng vật phẩm trung tâm (v4).
Quản lý CẢ hiệu ứng chủ động (boost từ đồ ăn/học tập) và
hiệu ứng thụ động (từ xe cộ, hàng hiệu, công nghệ,…).

Kiến trúc:
  - Active boosts: time-limited, được kích hoạt từ inventory (giữ nguyên food_effects.py)
  - Passive effects: vĩnh viễn khi sở hữu item, tự động gộp khi review/mở shop
  - Mỗi item có thể có nhiều hiệu ứng (effect_list) thay vì 1 effect duy nhất
"""

import time
from typing import Any
from .logger import get_logger
logger = get_logger(__name__)

from ._safe_config import cfg_list, cfg_set, cfg_dict, col_ready

_KEY_PASSIVE = "anki_tycoon_passive_effects"  # {item_id: {effect_key: value}}

SET_BONUSES = [
    {
        "id": "set_focus_ecosystem",
        "name": "Focus Ecosystem",
        "emoji": "🧠",
        "required": ["tech_macbook_m3", "tech_ipad_pro", "tech_kinh_ap_trong_tam"],
        "effects": {
            "interval_boost": 0.05,
            "factor_boost": 0.03,
        },
    },
    {
        "id": "set_ai_study_desk",
        "name": "AI Study Desk",
        "emoji": "🖥️",
        "required": ["tech_bang_dieu_khien_hoc_tap", "tech_iphone16", "tech_dell_xps"],
        "effects": {
            "review_count_bonus": 8,
            "skill_cooldown_reduction": 0.05,
        },
    },
    {
        "id": "set_private_banking",
        "name": "Private Banking Suite",
        "emoji": "🏦",
        "required": ["finance_so_tiet_kiem_thong_minh", "finance_the_tin_dung_vip", "finance_chung_chi_cfa"],
        "effects": {
            "interest_speed_boost": 0.07,
            "interest_bonus": 0.05,
        },
    },
    {
        "id": "set_safety_net",
        "name": "Safety Net",
        "emoji": "🛡️",
        "required": ["ins_health", "ins_life", "ins_unemployment"],
        "effects": {
            "disease_resistance": 0.10,
            "tax_reduction": 0.02,
        },
    },
]


# ─── Danh sách effect types mở rộng ────────────────────────────────

# Active effects (time-limited, từ food/study)
ACTIVE_TYPES = {
    "reward_multiplier",    # ×N tiền thưởng khi review
    "xp_bonus",            # +N đ/thẻ
    "double_easy",         # ×N khi ease==4
    "night_owl",           # ×N khi học ban đêm
    "no_again_penalty",    # Miễn phạt Again
    "penalty_shield",      # Khiên phạt
    "movement_speed",      # Tăng tốc độ (thời gian)
    "stamina_regen",       # Hồi thể lực
    "energy_regen",        # Hồi năng lượng (mới)
    "interval_boost",      # +% interval cho thẻ vừa review
    "easy_interval_bonus", # +% interval riêng khi Easy
    "factor_boost",        # +% ease factor của thẻ
}

# Passive effects (vĩnh viễn, từ xe/luxury/tech/bất động sản)
PASSIVE_TYPES = {
    "study_time_reduction",       # [DEPRECATED cho xe] Giảm % thời gian ôn bài (0.0-1.0) — gây dồn thẻ
    "density_reduction",          # GIẢM mật độ ôn tập: tăng interval an toàn, không phá FSRS (0.0-1.0)
    "xp_multiplier",              # ×N tổng XP nhận được
    "stock_cooldown_reduction",   # Giảm % cooldown chứng khoán
    "crypto_cooldown_reduction",  # Giảm % cooldown crypto
    "inventory_capacity",         # Tăng sức chứa kho (+N slots)
    "skill_cooldown_reduction",   # Giảm % cooldown kỹ năng
    "repair_speed",              # Tăng % tốc sửa chữa
    "passive_income_bonus",      # Tăng % thu nhập thụ động
    "interest_bonus",            # Tăng % lãi suất ngân hàng
    "tax_reduction",             # Giảm % thuế
    "disease_resistance",        # Kháng bệnh (0.0-1.0)
    "health_boost",              # Tăng điểm sức khỏe
    "energy_limit",              # Tăng giới hạn năng lượng
    "energy_regen",              # Hồi năng lượng thụ động (mới)
    "equipment_slot",            # +N slot trang bị
    "daily_reward_bonus",        # +N tiền thưởng daily
    "review_count_bonus",        # +N thẻ ôn mỗi ngày
    # Hiệu ứng tài chính
    "interest_speed_boost",      # Tăng % tốc độ tích lũy lãi (0.0-1.0)
    "instant_interest_cooldown", # Thời gian hồi (giây) cho kỹ năng thu lãi tức thì
    # Hiệu ứng học tập thực tế (MỚI)
    "interval_boost",            # Tăng % khoảng cách ôn tập (0.0-1.0 = +0% đến +100%)
    "new_card_limit_boost",      # +N thẻ mới mỗi ngày
    "easy_interval_bonus",       # Tăng % interval riêng khi bấm Easy
    "factor_boost",              # Tăng % ease factor trên thẻ
    # Hiệu ứng ảnh hưởng đến Emergency Events (MỚI)
    "emergency_resistance",      # Giảm xác suất emergency event (0.0-0.9)
    "emergency_magnetism",       # Tăng xác suất emergency event (0.0-0.9) — item "rủi ro"
    "emergency_cost_reduction",  # Giảm chi phí emergency event (0.0-0.9)
    "emergency_cost_increase",   # Tăng chi phí emergency event (0.0-0.9)
}


# ─── Helper: resolve tất cả hiệu ứng từ item data ─────────────────

def get_item_effects(item_data: dict) -> list:
    """
    Trả về danh sách effect dict từ item data.
    Hỗ trợ cả `effect` (cũ, 1 effect) và `effect_list` (mới, nhiều effect).
    """
    if "effect_list" in item_data and isinstance(item_data["effect_list"], list):
        return list(item_data["effect_list"])
    if "effect" in item_data and isinstance(item_data["effect"], dict):
        return [dict(item_data["effect"])]
    return []


def is_passive_item(item_data: dict) -> bool:
    """Kiểm tra item có hiệu ứng thụ động không."""
    cat = item_data.get("category", "")
    # Các category có passive effects
    # LƯU Ý: Dùng substring match không emoji để khớp với dữ liệu shop_items.json
    passive_cats = [
        "Showroom xe",              # "🚗 Showroom xe"
        "Cửa hàng hàng hiệu",         # "💎 Cửa hàng hàng hiệu"
        "Cửa hàng đồ công nghệ",    # "💻 Cửa hàng đồ công nghệ"
        "Thị trường bất động sản",  # "🏠 Thị trường bất động sản"
        "Bảo hiểm",                 # "🛡️ Bảo hiểm"
        "Vật phẩm tài chính",       # "🏦 Vật phẩm tài chính"
        "Sàn Crypto",              # "🪙 Sàn Crypto"
    ]
    for pc in passive_cats:
        if pc in cat:
            return True
    return False


_VEHICLE_CATS = [
    "Showroom xe",    # "🚗 Showroom xe" — tất cả xe dùng chung 1 category
]

_VEHICLE_MAX_ONLY_TYPES = {
    "study_time_reduction",
    "density_reduction",          # Giảm mật độ ôn tập (thay thế study_time_reduction)
    "xp_multiplier",
    "stock_cooldown_reduction",
    "crypto_cooldown_reduction",
    "interval_boost",
    "easy_interval_bonus",
    "factor_boost",
}


def _is_vehicle_category(cat: str) -> bool:
    """Kiểm tra category có phải phương tiện không."""
    for vc in _VEHICLE_CATS:
        if vc in cat:
            return True
    return False


def is_active_item(item_data: dict) -> bool:
    """Kiểm tra item có hiệu ứng chủ động (boost) không."""
    cat = item_data.get("category", "")
    return "Ẩm thực" in cat or "Đồ uống" in cat or "Vật phẩm học tập" in cat


# ─── Passive effects management ────────────────────────────────────

def _get_passive_raw() -> dict:
    return cfg_dict(_KEY_PASSIVE, {})


def _save_passive(d: dict):
    cfg_set(_KEY_PASSIVE, d)


def _get_owned_item_ids() -> set[str]:
    """Đọc item đang sở hữu để tính set bonus động."""
    try:
        from .inventory import get_inventory
        return set(get_inventory())
    except Exception as e:
        logger.debug("_get_owned_item_ids: %s", e)
        return set(_get_passive_raw().keys())


def get_active_set_bonuses() -> list[dict]:
    owned = _get_owned_item_ids()
    active = []
    for bonus in SET_BONUSES:
        required = set(bonus.get("required", []))
        if required and required.issubset(owned):
            active.append(bonus)
    return active


def _merge_effect_value(aggregated: dict, etype: str, evalue: Any):
    if not isinstance(evalue, (int, float)):
        return
    if etype in aggregated:
        ag = aggregated[etype]
        if not isinstance(ag, (int, float)):
            return
        if etype in ("inventory_capacity", "equipment_slot", "review_count_bonus",
                     "health_boost", "daily_reward_bonus", "new_card_limit_boost"):
            aggregated[etype] = ag + evalue
        elif etype in ("study_time_reduction", "density_reduction",
                       "stock_cooldown_reduction",
                       "crypto_cooldown_reduction", "skill_cooldown_reduction",
                       "tax_reduction", "disease_resistance", "interest_speed_boost",
                       "interval_boost", "easy_interval_bonus", "factor_boost",
                       "emergency_resistance", "emergency_magnetism",
                       "emergency_cost_reduction", "emergency_cost_increase"):
            aggregated[etype] = min(0.9, ag + evalue)
        elif etype == "xp_multiplier":
            aggregated[etype] = ag * evalue
        elif etype == "interest_bonus":
            aggregated[etype] = min(1.0, ag + evalue)
        elif etype in ("passive_income_bonus", "repair_speed"):
            aggregated[etype] = ag * (1.0 + evalue)
        elif isinstance(evalue, bool):
            aggregated[etype] = ag or evalue
    else:
        if etype in ("passive_income_bonus", "repair_speed"):
            aggregated[etype] = 1.0 + evalue
        else:
            aggregated[etype] = evalue


def register_passive_effect(item_id: str, item_data: dict):
    """
    Khi mua item có passive effect, đăng ký effect vào hệ thống.
    Gọi từ web_bridge.buyItem().
    """
    if not col_ready():
        return
    if not is_passive_item(item_data):
        return

    effects = get_item_effects(item_data)
    if not effects:
        return

    passive = _get_passive_raw()
    # Gom tất cả effect của item này
    item_effects = {}
    for e in effects:
        etype = e.get("type", "")
        if etype in PASSIVE_TYPES:
            val = e.get("value", 0)
            # Nếu đã có effect type này, lấy giá trị cao nhất (stack additive)
            if etype in item_effects:
                if isinstance(val, (int, float)) and isinstance(item_effects[etype], (int, float)):
                    item_effects[etype] += val
            else:
                item_effects[etype] = val

    if item_effects:
        passive[item_id] = {
            "effects": item_effects,
            "name": item_data.get("name", item_id),
            "emoji": item_data.get("emoji", "\U0001f4e6"),
            "category": item_data.get("category", ""),
            "price": item_data.get("price", 0),
        }
        _save_passive(passive)


def unregister_passive_effect(item_id: str):
    """Xoá passive effect khi item bị bán/xoá."""
    passive = _get_passive_raw()
    if item_id in passive:
        del passive[item_id]
        _save_passive(passive)


def repair_crypto_passive_effects():
    """Migration: đăng ký passive effects cho crypto items đã mua trước khi có fix."""
    if not col_ready():
        return
    try:
        from .inventory import get_inventory
        from .shop_data import load_shop_items
        inv_ids = set(get_inventory())
        if not inv_ids:
            return
        items_map = {i["id"]: i for i in load_shop_items()}
        passive = _get_passive_raw()
        changed = False
        for item_id in inv_ids:
            item = items_map.get(item_id)
            if not item or not item.get("is_digital_asset"):
                continue
            if item_id in passive:
                continue
            effects = get_item_effects(item)
            passive_effs = {}
            for e in effects:
                etype = e.get("type", "")
                val = e.get("value")
                if etype in PASSIVE_TYPES and isinstance(val, (int, float)):
                    passive_effs[etype] = passive_effs.get(etype, 0) + val
            if passive_effs:
                passive[item_id] = {
                    "effects":  passive_effs,
                    "name":     item.get("name", item_id),
                    "emoji":    item.get("emoji", "🪙"),
                    "category": item.get("category", ""),
                    "price":    item.get("price", 0),
                }
                changed = True
        if changed:
            _save_passive(passive)
    except Exception as e:
        logger.debug("_scan_digital_asset_passives: %s", e)


def get_all_passive_effects() -> dict:
    """
    Trả về dict gộp tất cả passive effects đang active.
    {
        "study_time_reduction": 0.25,
        "xp_multiplier": 1.5,
        "inventory_capacity": 20,
        ...
    }

    QUY TẮC STACK (v4.5):
      - Phương tiện (xe hơi, xe máy, xe điện, xe đạp):
        Các effect thiên về học/speed chỉ lấy chiếc mạnh nhất (max()).
        Các effect kiểu tài chính/slot vẫn cộng dồn theo luật chung.
      - Các category khác (hàng hiệu, công nghệ, BĐS, bảo hiểm, tài chính):
        Cộng dồn như cũ (additive / multiplicative tuỳ loại).
    """
    passive = _get_passive_raw()
    aggregated = {}
    # Lưu riêng vehicle effects để xử lý max sau
    vehicle_agg = {}

    for item_id, info in passive.items():
        cat = info.get("category", "")
        effects = info.get("effects", {})
        is_vehicle = _is_vehicle_category(cat)

        for etype, evalue in effects.items():
            if not isinstance(evalue, (int, float)):
                continue

            if is_vehicle:
                # Vehicle: gom riêng, một số effect sẽ lấy max(), số còn lại cộng theo luật chung
                if etype in vehicle_agg:
                    vehicle_agg[etype] = max(vehicle_agg[etype], evalue)
                else:
                    vehicle_agg[etype] = evalue
            else:
                # Non-vehicle: cộng dồn như cũ
                _merge_effect_value(aggregated, etype, evalue)

    # Hợp nhất vehicle effects vào aggregated.
    for etype, evalue in vehicle_agg.items():
        if etype in _VEHICLE_MAX_ONLY_TYPES:
            if etype in aggregated:
                ag = aggregated[etype]
                if isinstance(ag, (int, float)):
                    # Với hiệu ứng học/tốc độ, chỉ lấy chiếc mạnh nhất.
                    aggregated[etype] = max(ag, evalue)
                else:
                    aggregated[etype] = evalue
            else:
                aggregated[etype] = evalue
        else:
            _merge_effect_value(aggregated, etype, evalue)

    for bonus in get_active_set_bonuses():
        for etype, evalue in bonus.get("effects", {}).items():
            _merge_effect_value(aggregated, etype, evalue)

    # ── Tích hợp permanent effects từ achievements ──
    try:
        from .achievements import get_permanent_effects
        ach_effects = get_permanent_effects()
        for etype, evalue in ach_effects.items():
            _merge_effect_value(aggregated, etype, evalue)
    except Exception as e:
        logger.debug("get_all_passive_effects: achievements effects — %s", e)

    return aggregated


def get_passive_effects_summary() -> list:
    """
    Trả về danh sách passive effects đang active để hiển thị UI.
    """
    passive = _get_passive_raw()
    result = []
    for item_id, info in passive.items():
        for etype, evalue in info.get("effects", {}).items():
            result.append({
                "item_id": item_id,
                "name": info.get("name", item_id),
                "emoji": info.get("emoji", "\U0001f4e6"),
                "type": etype,
                "value": evalue,
                "description": format_effect_desc(etype, evalue),
            })
    for bonus in get_active_set_bonuses():
        for etype, evalue in bonus.get("effects", {}).items():
            result.append({
                "item_id": bonus.get("id", "set_bonus"),
                "name": bonus.get("name", "Set Bonus"),
                "emoji": bonus.get("emoji", "✨"),
                "type": etype,
                "value": evalue,
                "description": format_effect_desc(etype, evalue),
            })
    return result


# ─── Format effect descriptions ───────────────────────────────────

def format_effect_desc(effect_type: str, value: Any) -> str:
    """Tạo mô tả ngắn cho 1 effect type + value."""
    if effect_type == "reward_multiplier":
        return f"×{value} tiền thưởng"
    elif effect_type == "xp_bonus":
        return f"+{value:,}₫/thẻ"
    elif effect_type == "double_easy":
        return f"×{value} khi Easy"
    elif effect_type == "night_owl":
        return f"×{value} ban đêm"
    elif effect_type == "no_again_penalty":
        return "🛡️ Miễn phạt Again"
    elif effect_type == "penalty_shield":
        return "🛡️ Khiên phạt"
    elif effect_type == "movement_speed":
        return f"⚡ Tốc độ +{int(value*100)}%"
    elif effect_type == "stamina_regen":
        return f"🔋 Hồi {value} thể lực"
    elif effect_type == "stamina_cost":
        return f"💪 -{value} thể lực mỗi thẻ"
    elif effect_type == "reward_penalty":
        pct = int(value * 100)
        return f"📉 Giảm {pct}% tiền thưởng"
    elif effect_type == "energy_regen":
        return f"⚡ Hồi {value} năng lượng khi ôn bài"  # MỚI
    elif effect_type == "study_time_reduction":
        pct = int(value * 100)
        return f"⏱ Giảm {pct}% thời gian ôn bài"
    elif effect_type == "density_reduction":
        pct = int(value * 100)
        return f"🌿 Giảm {pct}% mật độ ôn tập"
    elif effect_type == "xp_multiplier":
        return f"×{value} tổng XP"
    elif effect_type == "stock_cooldown_reduction":
        pct = int(value * 100)
        return f"📉 Giảm {pct}% cooldown CK"
    elif effect_type == "crypto_cooldown_reduction":
        pct = int(value * 100)
        return f"🪙 Giảm {pct}% phí giao dịch Crypto"
    elif effect_type == "inventory_capacity":
        return f"🎒 +{value} slot kho"
    elif effect_type == "skill_cooldown_reduction":
        pct = int(value * 100)
        return f"⚡ Giảm {pct}% cooldown kỹ năng"
    elif effect_type == "repair_speed":
        pct = int(value * 100)
        return f"🔧 Tăng {pct}% tốc sửa chữa"
    elif effect_type == "passive_income_bonus":
        pct = int(value * 100)
        return f"🏠 +{pct}% thu nhập thụ động"
    elif effect_type == "interest_bonus":
        pct = int(value * 100)
        return f"🏦 +{pct}% lãi suất"
    elif effect_type == "tax_reduction":
        pct = int(value * 100)
        return f"💰 Giảm {pct}% thuế"
    elif effect_type == "disease_resistance":
        pct = int(value * 100)
        return f"💪 Kháng bệnh {pct}%"
    elif effect_type == "health_boost":
        return f"❤️ +{value} sức khỏe"
    elif effect_type == "energy_limit":
        return f"⚡ +{value} năng lượng tối đa"
    elif effect_type == "equipment_slot":
        return f"🔓 +{value} slot trang bị"
    elif effect_type == "daily_reward_bonus":
        return f"🎁 +{value:,}₫ thưởng ngày"
    elif effect_type == "review_count_bonus":
        return f"📝 +{value} thẻ/ngày"
    elif effect_type == "interest_speed_boost":
        pct = int(value * 100)
        return f"⚡ Lãi NH +{pct}% tốc độ"
    elif effect_type == "instant_interest_cooldown":
        hours = int(value / 3600)
        if hours >= 24:
            days = hours // 24
            return f"⏳ Thu lãi tức thì (hồi {days} ngày)"
        return f"⏳ Thu lãi tức thì (hồi {hours}h)"
    elif effect_type == "interval_boost":
        pct = int(value * 100)
        return f"📈 Tăng {pct}% khoảng cách ôn tập"
    elif effect_type == "new_card_limit_boost":
        return f"🆕 +{value} thẻ mới/ngày"
    elif effect_type == "easy_interval_bonus":
        pct = int(value * 100)
        return f"🎯 Easy +{pct}% khoảng cách ôn"
    elif effect_type == "factor_boost":
        pct = int(value * 100)
        return f"🧠 +{pct}% ease factor thẻ"
    elif effect_type == "energy_save":
        pct = int(value * 100)
        return f"⚡ Tiết kiệm {pct}% năng lượng"
    elif effect_type == "fuel_efficiency":
        pct = int(value * 100)
        return f"⛽ Hiệu suất nhiên liệu +{pct}%"
    elif effect_type == "emergency_resistance":
        pct = int(value * 100)
        return f"🛡️ Giảm {pct}% rủi ro khủng hoảng"
    elif effect_type == "emergency_magnetism":
        pct = int(value * 100)
        return f"⚠️ Tăng {pct}% rủi ro khủng hoảng"
    elif effect_type == "emergency_cost_reduction":
        pct = int(value * 100)
        return f"💰 Giảm {pct}% chi phí khủng hoảng"
    elif effect_type == "emergency_cost_increase":
        pct = int(value * 100)
        return f"💸 Tăng {pct}% chi phí khủng hoảng"
    return f"{effect_type}: {value}"


def format_item_effects_html(effects: list) -> str:
    """Tạo HTML string hiển thị danh sách effect cho item card."""
    if not effects:
        return ""
    parts = []
    for e in effects:
        desc = format_effect_desc(e.get("type", ""), e.get("value", 0))
        dur = e.get("duration", 0)
        cards = e.get("cards", 0)
        suffix = ""
        if dur > 0 and dur < 86400:
            mins = dur // 60
            suffix = f" ({mins}p)"
        elif dur >= 86400:
            days = dur // 86400
            suffix = f" ({days} ngày)"
        if cards > 0:
            suffix = f" ({cards} thẻ)"
        parts.append(f"<span class='effect-tag'>{desc}{suffix}</span>")
    return " ".join(parts)


# ─── Apply effects khi review card ────────────────────────────────

def apply_all_effects(ease: int, current_multiplier: float = 1.0, current_bonus: int = 0) -> dict:
    """
    Kết hợp active boosts (từ food_effects.consume_boost_card) và passive effects.
    Gọi từ Anki hook khi review card.
    Trả về:
      {"multiplier": float, "bonus": int, "shield": bool, "effects_applied": [...]}
    """
    from .food_effects import consume_boost_card
    active_result = consume_boost_card(ease)

    multiplier = active_result.get("multiplier", 1.0)
    bonus = active_result.get("bonus", 0)
    shield = active_result.get("shield", False)

    # Apply passive effects
    passive = get_all_passive_effects()

    # xp_multiplier nhân với tổng multiplier
    if "xp_multiplier" in passive:
        multiplier *= float(passive["xp_multiplier"])

    # study_time_reduction sẽ được xử lý riêng ở Anki hook (giảm interval)
    # inventory_capacity được dùng ở chỗ khác
    # Các effect khác (stock_cooldown_reduction,...) xử lý ở module tương ứng

    return {
        "multiplier": multiplier,
        "bonus": bonus,
        "shield": shield,
        "passive_effects": passive,
    }


# ─── Kiểm tra item có effect gì để hiển thị trong shop ───────────

def get_item_effect_descriptions(item_data: dict) -> list:
    """
    Trả về danh sách mô tả effect có thể đọc được cho 1 item, dùng trong shop card.
    """
    effects = get_item_effects(item_data)
    if not effects:
        return []

    descs = []
    for e in effects:
        etype = e.get("type", "")
        val = e.get("value", 0)
        # Duration info
        dur = e.get("duration", 0)
        cards = e.get("cards", 0)
        time_str = ""
        if dur > 0:
            if dur < 3600:
                time_str = f" trong {dur//60} phút"
            elif dur < 86400:
                time_str = f" trong {dur//3600} giờ"
            else:
                time_str = f" trong {dur//86400} ngày"
        if cards > 0:
            time_str = f" trong {cards} thẻ"

        desc = format_effect_desc(etype, val)
        descs.append(f"{desc}{time_str}")
    return descs
