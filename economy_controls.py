# -*- coding: utf-8 -*-
from __future__ import annotations
"""
economy_controls.py — Hệ thống Kiểm soát Kinh tế v1.0
=====================================================
4 nhóm cơ chế siết chặt nền kinh tế, chống lạm phát và tỷ phú ảo:

1. Hố đen tiền tệ (Money Sinks)
   - Thuế lũy tiến theo tổng tài sản
   - Phí đỗ xe hàng ngày (garage parking fees)
   - Vật phẩm tiêu hao ngắn hạn (consumables)

2. Giá trị biến động (Dynamic Pricing & Inflation)
   - CPI ảo: giá xe tăng theo tổng thẻ toàn hệ thống
   - Cơ chế khan hiếm: xe cao cấp chỉ xuất hiện theo khung giờ

3. Hiệu suất giảm dần (Diminishing Returns)
   - Daily Cap: giới hạn thu nhập theo số thẻ trong ngày
   - Độ khó thẻ ảnh hưởng đến tiền thưởng

4. Bảo dưỡng và Rủi ro (Maintenance & Risk)
   - Rủi ro hỏng hóc ngẫu nhiên cho xe đang active
   - Sửa chữa yêu cầu hoàn thành review
"""

import time
import random
import math
from datetime import date, datetime
from ._safe_config import col_ready, cfg_int, cfg_str, cfg_list, cfg_set, cfg_dict
from .logger import get_logger

logger = get_logger(__name__)


# ── Helper: today key dùng Unix timestamp (chống time travel) ──
def _today_key() -> str:
    """Trả về 'YYYY-MM-DD' dùng Unix timestamp, không phụ thuộc date.today()."""
    return time.strftime("%Y-%m-%d", time.localtime(time.time()))


# ═══════════════════════════════════════════════════════════════
# CONFIG KEYS
# ═══════════════════════════════════════════════════════════════

_KEY_DAILY_CAP        = "anki_tycoon_daily_cap_data"       # {date: cards_today}
_KEY_DAILY_CAP_RESET  = "anki_tycoon_daily_cap_date"
_KEY_TOTAL_SYSTEM_CARDS = "anki_tycoon_total_system_cards"  # CPI tracking
_KEY_CPI_INDEX        = "anki_tycoon_cpi_index"             # CPI hiện tại
_KEY_GARAGE_FEES      = "anki_tycoon_garage_fees_date"      # Ngày thu phí garage cuối
_KEY_BREAKDOWN_LOG    = "anki_tycoon_breakdown_log"         # Lịch sử hỏng hóc
_KEY_CONSUMABLE_SHOP  = "anki_tycoon_consumable_cooldowns"  # Cooldown consumables


# ═══════════════════════════════════════════════════════════════
# 1. HIỆU SUẤT GIẢM DẦN (DIMINISHING RETURNS)
# ═══════════════════════════════════════════════════════════════

# Daily Cap thresholds
DAILY_CAP_TIERS = [
    (100,  1.00),    # 100 thẻ đầu: 100% tiền
    (200,  0.50),    # 101-200: 50%
    (300,  0.25),    # 201-300: 25%
    (500,  0.10),    # 301-500: 10%
    (9999, 0.05),    # >500: 5%
]

# Phí phục hồi kiến thức cho Again (knowledge recovery fee)
AGAIN_RECOVERY_FEE_RATIO = 0.001   # 0.1% số dư hiện tại
AGAIN_RECOVERY_MIN       = 2_000   # tối thiểu 2.000đ
AGAIN_RECOVERY_MAX       = 500_000 # tối đa 500.000đ


def get_daily_cards_count() -> int:
    """Trả về số thẻ đã review hôm nay (dùng cho daily cap)."""
    today = _today_key()
    data = cfg_dict(_KEY_DAILY_CAP, {})
    if data.get("date") != today:
        return 0
    return int(data.get("count", 0))


def increment_daily_cards_count() -> None:
    """Tăng số thẻ đã review hôm nay lên 1."""
    today = _today_key()
    data = cfg_dict(_KEY_DAILY_CAP, {})
    if data.get("date") != today:
        data = {"date": today, "count": 0}
    data["count"] = int(data.get("count", 0)) + 1
    cfg_set(_KEY_DAILY_CAP, data)


def get_daily_cap_multiplier() -> tuple[float, dict]:
    """
    Tính hệ số daily cap dựa trên số thẻ đã review hôm nay.
    
    Returns:
        (multiplier: float, tier_info: dict)
        multiplier: 1.0 = 100%, 0.5 = 50%, etc.
        tier_info: thông tin tier hiện tại để hiển thị UI
    """
    cards_today = get_daily_cards_count()
    
    # Số thẻ HIỆN TẠI đã review → xét tier dựa trên số này
    # (vì increment chưa được gọi, đây là số thẻ TRƯỚC khi review thẻ này)
    for threshold, mult in DAILY_CAP_TIERS:
        if cards_today < threshold:
            # Tìm tier name
            prev_threshold = 0
            for t, _ in DAILY_CAP_TIERS:
                if t >= threshold:
                    break
                prev_threshold = t
            
            tier_name = f"{prev_threshold+1}-{threshold}" if threshold < 9999 else f">={prev_threshold+1}"
            if threshold == 100:
                tier_name = "1-100"
            
            return (mult, {
                "tier": tier_name,
                "multiplier": mult,
                "mult_pct": int(mult * 100),
                "cards_today": cards_today,
                "next_threshold": threshold,
                "cards_until_next": max(0, threshold - cards_today),
            })
    
    return (0.05, {
        "tier": "500+",
        "multiplier": 0.05,
        "mult_pct": 5,
        "cards_today": cards_today,
        "next_threshold": None,
        "cards_until_next": None,
    })


def get_again_recovery_fee() -> int:
    """
    Tính phí phục hồi kiến thức cho thẻ Again.
    Again không những không có tiền mà còn mất phí.
    
    Công thức: max(min, min(max, balance * ratio))
    """
    try:
        from .balance import get_balance
        bal = get_balance()
        fee = max(AGAIN_RECOVERY_MIN, min(AGAIN_RECOVERY_MAX, int(bal * AGAIN_RECOVERY_FEE_RATIO)))
        return fee
    except Exception as e:
        logger.debug("get_again_recovery_fee: %s", e)
        return AGAIN_RECOVERY_MIN


# ═══════════════════════════════════════════════════════════════
# 2. CPI ẢO & DYNAMIC PRICING
# ═══════════════════════════════════════════════════════════════

CPI_CARDS_PER_TICK = 500    # Cứ 500 thẻ toàn hệ thống → CPI tăng
CPI_INCREASE_RATE  = 0.01   # Mỗi tick tăng 1% giá


def get_total_system_cards() -> int:
    """Trả về tổng số thẻ đã review toàn hệ thống."""
    return cfg_int(_KEY_TOTAL_SYSTEM_CARDS, 0)


def increment_total_system_cards() -> None:
    """Tăng tổng số thẻ toàn hệ thống (gọi từ card_reviewed hook)."""
    total = get_total_system_cards() + 1
    cfg_set(_KEY_TOTAL_SYSTEM_CARDS, total)
    
    # Kiểm tra CPI tick
    prev_total = total - 1
    prev_tick = prev_total // CPI_CARDS_PER_TICK
    curr_tick = total // CPI_CARDS_PER_TICK
    
    if curr_tick > prev_tick:
        # Tăng CPI
        _increase_cpi()


def get_cpi_index() -> float:
    """Trả về CPI index hiện tại (1.0 = base, 1.5 = giá tăng 50%)."""
    cpi = cfg_dict(_KEY_CPI_INDEX, {"index": 1.0, "last_update": 0})
    return float(cpi.get("index", 1.0))


def _increase_cpi() -> None:
    """Tăng CPI lên 1 tick."""
    cpi = cfg_dict(_KEY_CPI_INDEX, {"index": 1.0, "last_update": 0})
    current = float(cpi.get("index", 1.0))
    new_index = round(current * (1.0 + CPI_INCREASE_RATE), 4)
    cpi["index"] = new_index
    cpi["last_update"] = int(time.time())
    cpi["total_cards"] = get_total_system_cards()
    cfg_set(_KEY_CPI_INDEX, cpi)


def apply_cpi_to_price(base_price: int) -> int:
    """
    Áp dụng CPI vào giá gốc.
    CPI chỉ ảnh hưởng đến xe cộ (vehicle categories).
    """
    cpi = get_cpi_index()
    return int(base_price * cpi)


def get_cpi_status() -> dict:
    """Trả về trạng thái CPI cho UI."""
    cpi = cfg_dict(_KEY_CPI_INDEX, {"index": 1.0, "last_update": 0})
    total_cards = get_total_system_cards()
    next_tick_cards = ((total_cards // CPI_CARDS_PER_TICK) + 1) * CPI_CARDS_PER_TICK
    cards_to_next = max(0, next_tick_cards - total_cards)
    
    return {
        "cpi_index": float(cpi.get("index", 1.0)),
        "cpi_pct": round((float(cpi.get("index", 1.0)) - 1.0) * 100, 2),
        "total_system_cards": total_cards,
        "cards_per_tick": CPI_CARDS_PER_TICK,
        "cards_to_next_tick": cards_to_next,
        "inflation_rate_per_tick": CPI_INCREASE_RATE * 100,
    }


# ═══════════════════════════════════════════════════════════════
# 3. PHÍ ĐỖ XE HÀNG NGÀY (GARAGE PARKING FEES)
# ═══════════════════════════════════════════════════════════════

# Phí đỗ xe theo giá trị xe (tỷ lệ %/ngày)
GARAGE_FEE_BRACKETS = [
    (10_000_000_000,  0.001),   # >10B: 0.1%/ngày
    (1_000_000_000,   0.0005),  # >1B: 0.05%/ngày
    (100_000_000,     0.0002),  # >100M: 0.02%/ngày
    (0,               0.0001),  # Còn lại: 0.01%/ngày
]

GARAGE_FEE_MIN = 5_000     # Tối thiểu 5.000đ/xe/ngày
GARAGE_FEE_MAX = 5_000_000 # Tối đa 5 triệu/xe/ngày


def calculate_garage_fees() -> dict:
    """
    Tính tổng phí đỗ xe trong garage hôm nay.
    Nếu không đủ tiền đóng, xe sẽ bị niêm phong (mất hiệu ứng buff).
    
    Returns:
        {
            "total_fees": int,
            "breakdown": [{"item_id": str, "name": str, "fee": int, "price": int}],
            "can_pay": bool,
            "shortfall": int,
            "seized_vehicles": [str]  # Xe bị niêm phong do thiếu tiền
        }
    """
    try:
        from .shop_data import load_shop_items
        from .vehicle_system import _get_data as get_veh_data, _save_data as save_veh_data
        
        items_map = {i["id"]: i for i in load_shop_items()}
        veh_data = get_veh_data()
        garage = veh_data.get("garage", {})
        
        total_fees = 0
        breakdown = []
        
        for item_id, info in garage.items():
            item = items_map.get(item_id, {})
            price = item.get("price", 0)
            
            # Tính phí theo bậc
            fee = GARAGE_FEE_MIN
            for threshold, rate in GARAGE_FEE_BRACKETS:
                if price > threshold:
                    fee = max(GARAGE_FEE_MIN, min(GARAGE_FEE_MAX, int(price * rate)))
                    break
            
            total_fees += fee
            breakdown.append({
                "item_id": item_id,
                "name": item.get("name", item_id),
                "emoji": item.get("emoji", "🚗"),
                "fee": fee,
                "price": price,
            })
        
        return {
            "total_fees": total_fees,
            "breakdown": breakdown,
            "vehicle_count": len(breakdown),
        }
    except Exception as e:
        logger.warning("calculate_garage_fees: %s", e)
        return {"total_fees": 0, "breakdown": [], "vehicle_count": 0}


def collect_garage_fees() -> dict:
    """
    Thu phí đỗ xe garage hàng ngày.
    Gọi từ _on_profile_loaded (__init__.py).
    
    Nếu không đủ tiền: đánh dấu xe bị niêm phong (seized).
    Xe bị niêm phong sẽ mất hiệu ứng buff cho đến khi đóng đủ phí.
    """
    if not col_ready():
        return {"collected": False, "reason": "not_ready"}
    
    today = _today_key()
    if cfg_str(_KEY_GARAGE_FEES, "") == today:
        return {"collected": False, "reason": "already_collected"}
    
    fee_info = calculate_garage_fees()
    if fee_info["total_fees"] <= 0:
        cfg_set(_KEY_GARAGE_FEES, today)
        return {"collected": False, "reason": "no_vehicles"}
    
    from .balance import get_balance, set_balance
    from .transactions import add_transaction
    from .vehicle_system import _get_data as get_veh_data, _save_data as save_veh_data
    
    bal = get_balance()
    total_fees = fee_info["total_fees"]
    seized = []
    
    if bal >= total_fees:
        # Đủ tiền → trừ thẳng
        new_bal = bal - total_fees
        set_balance(new_bal)
        add_transaction("garage_fee", total_fees,
                        f"Phí đỗ xe garage ({fee_info['vehicle_count']} xe) — {total_fees:,}đ".replace(",", "."))
        
        # Mở niêm phong nếu có xe đang bị seized
        veh_data = get_veh_data()
        garage = veh_data.get("garage", {})
        for item_id, info in garage.items():
            if info.get("seized", False):
                info["seized"] = False
        veh_data["garage"] = garage
        save_veh_data(veh_data)
    else:
        # Không đủ tiền → niêm phong xe từ đắt nhất đến rẻ nhất
        sorted_breakdown = sorted(fee_info["breakdown"], key=lambda x: x["price"], reverse=True)
        veh_data = get_veh_data()
        garage = veh_data.get("garage", {})
        
        remaining = bal
        total_paid = 0
        
        for entry in sorted_breakdown:
            item_id = entry["item_id"]
            fee = entry["fee"]
            
            if remaining >= fee:
                remaining -= fee
                total_paid += fee
                # Xe này không bị seized
                if item_id in garage:
                    garage[item_id]["seized"] = False
            else:
                # Không đủ tiền cho xe này → seized
                seized.append(item_id)
                if item_id in garage:
                    garage[item_id]["seized"] = True
                    garage[item_id]["seized_since"] = today
                # Các xe còn lại cũng seized
                for other in sorted_breakdown:
                    oid = other["item_id"]
                    if oid not in seized and oid != item_id:
                        # Kiểm tra nếu cũng không đủ
                        if remaining < other["fee"]:
                            seized.append(oid)
                            if oid in garage:
                                garage[oid]["seized"] = True
                                garage[oid]["seized_since"] = today
        
        if total_paid > 0:
            set_balance(remaining)
            add_transaction("garage_fee", total_paid,
                            f"Phí đỗ xe (thiếu tiền) — đã đóng {total_paid:,}đ, {len(seized)} xe bị niêm phong".replace(",", "."))
        
        veh_data["garage"] = garage
        save_veh_data(veh_data)
    
    cfg_set(_KEY_GARAGE_FEES, today)
    
    return {
        "collected": True,
        "total_fees": total_fees,
        "paid": total_fees if bal >= total_fees else sum(
            e["fee"] for e in fee_info["breakdown"] if e["item_id"] not in seized
        ),
        "seized_vehicles": seized,
        "vehicle_count": fee_info["vehicle_count"],
        "breakdown": fee_info["breakdown"],
    }


# ═══════════════════════════════════════════════════════════════
# 4. RỦI RO HỎNG HÓC NGẪU NHIÊN (RANDOM BREAKDOWNS)
# ═══════════════════════════════════════════════════════════════

# Xác suất hỏng cơ bản mỗi thẻ
BASE_BREAKDOWN_CHANCE = 0.001   # 0.1% mỗi thẻ

# Hệ số nhân xác suất theo giá xe
BREAKDOWN_PRICE_MULTIPLIERS = [
    (10_000_000_000, 5.0),     # >10B: ×5 (siêu xe hay hỏng)
    (1_000_000_000,  3.0),     # >1B: ×3
    (100_000_000,    2.0),     # >100M: ×2
    (10_000_000,     1.5),     # >10M: ×1.5
    (0,              1.0),     # Còn lại: ×1
]

# Chi phí sửa chữa khẩn cấp (tỷ lệ % giá xe)
BREAKDOWN_REPAIR_COST_RATIO = 0.03    # 3% giá xe
BREAKDOWN_REPAIR_MIN        = 100_000 # Tối thiểu 100k

# Số thẻ cần review để sửa xe (thay vì chờ thời gian)
BREAKDOWN_REVIEWS_REQUIRED = 30   # Cần 30 thẻ review để sửa xong


def check_breakdown_on_review(vehicle_item_id: str = None) -> dict:
    """
    Kiểm tra rủi ro hỏng hóc ngẫu nhiên khi review card.
    Xe càng xịn, xác suất hỏng càng cao.
    
    Returns:
        {"broken": bool, "item_id": str, "repair_cost": int, 
         "reviews_required": int, "reviews_done": int}
    """
    if not vehicle_item_id:
        return {"broken": False}
    
    try:
        from .shop_data import load_shop_items
        items_map = {i["id"]: i for i in load_shop_items()}
        item = items_map.get(vehicle_item_id, {})
        price = item.get("price", 0)
        
        # Tính xác suất hỏng
        chance = BASE_BREAKDOWN_CHANCE
        for threshold, mult in BREAKDOWN_PRICE_MULTIPLIERS:
            if price > threshold:
                chance *= mult
                break
        
        # Random roll
        if random.random() >= chance:
            return {"broken": False}
        
        # Bị hỏng!
        repair_cost = max(BREAKDOWN_REPAIR_MIN, int(price * BREAKDOWN_REPAIR_COST_RATIO))
        
        return {
            "broken": True,
            "item_id": vehicle_item_id,
            "name": item.get("name", vehicle_item_id),
            "emoji": item.get("emoji", "🚗"),
            "repair_cost": repair_cost,
            "reviews_required": BREAKDOWN_REVIEWS_REQUIRED,
            "reviews_done": 0,
        }
    except Exception as e:
        logger.warning("check_breakdown_on_review: %s", e)
        return {"broken": False}


def start_breakdown_repair(vehicle_item_id: str) -> dict:
    """
    Bắt đầu quá trình sửa xe sau khi hỏng.
    Yêu cầu: hoàn thành BREAKDOWN_REVIEWS_REQUIRED thẻ review.
    
    Returns:
        {"ok": bool, "error": str, ...}
    """
    try:
        from .vehicle_system import _get_data as get_veh_data, _save_data as save_veh_data
        
        veh_data = get_veh_data()
        garage = veh_data.get("garage", {})
        info = garage.get(vehicle_item_id)
        
        if not info:
            return {"ok": False, "error": "Xe không có trong garage."}
        
        # Đánh dấu xe đang trong quá trình sửa bằng review
        info["breakdown_repair"] = True
        info["breakdown_reviews_done"] = 0
        info["breakdown_reviews_required"] = BREAKDOWN_REVIEWS_REQUIRED
        
        # Stop active vehicle
        if veh_data.get("active_vehicle_id") == vehicle_item_id:
            veh_data["active_vehicle_id"] = None
        
        garage[vehicle_item_id] = info
        veh_data["garage"] = garage
        save_veh_data(veh_data)
        
        from .shop_data import load_shop_items
        items_map = {i["id"]: i for i in load_shop_items()}
        item = items_map.get(vehicle_item_id, {})
        
        return {
            "ok": True,
            "item_id": vehicle_item_id,
            "name": item.get("name", vehicle_item_id),
            "reviews_required": BREAKDOWN_REVIEWS_REQUIRED,
            "reviews_done": 0,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def progress_breakdown_repair(vehicle_item_id: str) -> dict:
    """
    Tiến triển sửa xe mỗi khi review 1 thẻ.
    Nếu đủ số thẻ yêu cầu, xe tự động sửa xong.
    
    Returns:
        {"still_repairing": bool, "done": bool, "progress": int/float}
    """
    try:
        from .vehicle_system import _get_data as get_veh_data, _save_data as save_veh_data
        
        veh_data = get_veh_data()
        garage = veh_data.get("garage", {})
        info = garage.get(vehicle_item_id)
        
        if not info or not info.get("breakdown_repair"):
            return {"still_repairing": False, "done": False}
        
        reviews_done = int(info.get("breakdown_reviews_done", 0)) + 1
        reviews_required = int(info.get("breakdown_reviews_required", BREAKDOWN_REVIEWS_REQUIRED))
        
        info["breakdown_reviews_done"] = reviews_done
        
        if reviews_done >= reviews_required:
            # Sửa xong!
            info["breakdown_repair"] = False
            info["breakdown_reviews_done"] = 0
            # Phục hồi độ bền
            info["durability"] = info.get("max_durability", 100)
            info["in_repair"] = False
            info["repair_until"] = 0
            
            _log_breakdown_event({
                "event": "repair_completed",
                "item_id": vehicle_item_id,
                "reviews_done": reviews_done,
                "date": _today_key(),
            })
        
        garage[vehicle_item_id] = info
        veh_data["garage"] = garage
        save_veh_data(veh_data)
        
        progress = reviews_done / max(1, reviews_required)
        
        return {
            "still_repairing": reviews_done < reviews_required,
            "done": reviews_done >= reviews_required,
            "progress": round(progress * 100, 1),
            "reviews_done": reviews_done,
            "reviews_required": reviews_required,
            "reviews_remaining": max(0, reviews_required - reviews_done),
        }
    except Exception as e:
        logger.warning("progress_breakdown_repair: %s", e)
        return {"still_repairing": False, "done": False}


def _log_breakdown_event(entry: dict) -> None:
    """Ghi log sự kiện hỏng hóc."""
    log = cfg_list(_KEY_BREAKDOWN_LOG, [])
    log.insert(0, entry)
    if len(log) > 30:
        log = log[:30]
    cfg_set(_KEY_BREAKDOWN_LOG, log)


def get_breakdown_log() -> list:
    """Trả về lịch sử hỏng hóc."""
    return cfg_list(_KEY_BREAKDOWN_LOG, [])


# ═══════════════════════════════════════════════════════════════
# 5. VẬT PHẨM TIÊU HAO (CONSUMABLES)
# ═══════════════════════════════════════════════════════════════

# Danh sách consumables đề xuất (sẽ được thêm vào shop_items.json sau)
CONSUMABLES = [
    {
        "id": "consumable_coffee_boost",
        "name": "☕ Cà phê Tăng tốc",
        "description": "Tăng 20% tiền thưởng trong 30 phút. Hiệu quả nhất khi học nhiều thẻ liên tục.",
        "price": 50_000,
        "category": "Vật phẩm tiêu hao",
        "emoji": "☕",
        "effect": {
            "type": "reward_multiplier",
            "value": 1.2,
            "duration": 1800,    # 30 phút
        },
        "stackable": False,
        "daily_limit": 3,
    },
    {
        "id": "consumable_focus_pill",
        "name": "💊 Thuốc Tập trung",
        "description": "Nhân đôi tiền thưởng cho 10 thẻ tiếp theo. Dùng cho những thẻ khó.",
        "price": 20_000,
        "category": "Vật phẩm tiêu hao",
        "emoji": "💊",
        "effect": {
            "type": "reward_multiplier",
            "value": 2.0,
            "cards": 10,
        },
        "stackable": False,
        "daily_limit": 5,
    },
    {
        "id": "consumable_energy_drink",
        "name": "🥤 Nước tăng lực",
        "description": "Hồi 50 năng lượng tức thì + tăng 15% tiền thưởng trong 15 phút.",
        "price": 35_000,
        "category": "Vật phẩm tiêu hao",
        "emoji": "🥤",
        "effect_list": [
            {"type": "energy_regen", "value": 50},
            {"type": "reward_multiplier", "value": 1.15, "duration": 900},
        ],
        "stackable": False,
        "daily_limit": 3,
    },
    {
        "id": "consumable_lucky_coin",
        "name": "🪙 Đồng xu May mắn",
        "description": "Tăng 50% tiền thưởng cho 5 thẻ tiếp theo. Dùng cho thẻ khó (Hard).",
        "price": 15_000,
        "category": "Vật phẩm tiêu hao",
        "emoji": "🪙",
        "effect": {
            "type": "reward_multiplier",
            "value": 1.5,
            "cards": 5,
        },
        "stackable": False,
        "daily_limit": 10,
    },
    {
        "id": "consumable_premium_coffee",
        "name": "☕ Cà phê Premium",
        "description": "Tăng 50% tiền thưởng + giảm 20% thời gian chờ trong 1 giờ.",
        "price": 150_000,
        "category": "Vật phẩm tiêu hao",
        "emoji": "☕",
        "effect_list": [
            {"type": "reward_multiplier", "value": 1.5, "duration": 3600},
            {"type": "movement_speed", "value": 0.2, "duration": 3600},
        ],
        "stackable": False,
        "daily_limit": 2,
    },
]

CONSUMABLE_MAP = {c["id"]: c for c in CONSUMABLES}


def get_consumable_cooldowns() -> dict:
    """Trả về trạng thái cooldown của consumables."""
    return cfg_dict(_KEY_CONSUMABLE_SHOP, {})


def can_use_consumable(consumable_id: str) -> dict:
    """
    Kiểm tra xem có thể dùng consumable không.
    Returns: {"ok": bool, "error": str, "remaining": int}
    """
    consumable = CONSUMABLE_MAP.get(consumable_id)
    if not consumable:
        return {"ok": False, "error": "Vật phẩm không tồn tại."}
    
    cooldowns = get_consumable_cooldowns()
    today = _today_key()
    info = cooldowns.get(consumable_id, {})
    
    # Reset daily limit nếu ngày mới
    if info.get("date") != today:
        info = {"date": today, "count": 0}
    
    daily_limit = consumable.get("daily_limit", 5)
    used = int(info.get("count", 0))
    
    if used >= daily_limit:
        return {"ok": False, "error": f"Đã đạt giới hạn {daily_limit} lần/ngày.", "remaining": 0}
    
    return {"ok": True, "remaining": daily_limit - used, "used": used, "daily_limit": daily_limit}


def record_consumable_use(consumable_id: str) -> None:
    """Ghi nhận 1 lần dùng consumable."""
    cooldowns = get_consumable_cooldowns()
    today = _today_key()
    info = cooldowns.get(consumable_id, {"date": today, "count": 0})
    
    if info.get("date") != today:
        info = {"date": today, "count": 0}
    
    info["count"] = int(info.get("count", 0)) + 1
    cooldowns[consumable_id] = info
    cfg_set(_KEY_CONSUMABLE_SHOP, cooldowns)


# ═══════════════════════════════════════════════════════════════
# 6. THUẾ LŨY TIẾN THEO TỔNG TÀI SẢN
# ═══════════════════════════════════════════════════════════════

# Thuế suất lũy tiến theo tổng tài sản (thu trên mỗi thẻ review)
WEALTH_TAX_BRACKETS = [
    (100_000_000_000,  0.15),   # >100 tỷ: 15% thuế trên mỗi thẻ
    (10_000_000_000,   0.10),   # >10 tỷ: 10%
    (1_000_000_000,    0.05),   # >1 tỷ: 5%
    (100_000_000,      0.02),   # >100 triệu: 2%
    (10_000_000,       0.01),   # >10 triệu: 1%
    (0,                0.00),   # Dưới 10 triệu: miễn thuế
]


def get_wealth_tax_rate(total_net_worth: int) -> float:
    """
    Trả về tỷ lệ thuế thu nhập dựa trên tổng tài sản.
    """
    for threshold, rate in WEALTH_TAX_BRACKETS:
        if total_net_worth > threshold:
            return rate
    return 0.0


def get_total_net_worth() -> int:
    """Tính tổng tài sản ròng."""
    try:
        total = 0
        from .balance import get_balance
        total += get_balance()
        
        try:
            from .bank import get_total_current_value
            total += int(get_total_current_value())
        except Exception as e:
            logger.debug("get_total_net_worth (bank): %s", e)
        
        try:
            from .stock_market import get_portfolio_summary
            ps = get_portfolio_summary()
            total += int(ps.get("total_value", 0))
        except Exception as e:
            logger.debug("get_total_net_worth (stock): %s", e)
        
        try:
            from .digital_assets import get_portfolio_summary
            cps = get_portfolio_summary()
            total += int(cps.get("total_value_vnd", 0))
        except Exception as e:
            logger.debug("get_total_net_worth (crypto): %s", e)
        
        try:
            from .bond_system import get_portfolio_summary as get_bond_summary
            bps = get_bond_summary()
            total += int(bps.get("total_value", 0))
        except Exception as e:
            logger.debug("get_total_net_worth (bonds): %s", e)
        
        return max(0, total)
    except Exception as e:
        logger.warning("get_total_net_worth: %s", e)
        return 0


def apply_wealth_tax_on_reward(gross_reward: int) -> tuple[int, int, float]:
    """
    Áp dụng thuế lũy tiến lên tiền thưởng từ thẻ review.
    
    Returns:
        tuple[int, int, float]: (net_reward, tax_amount, tax_rate)
    """
    if gross_reward <= 0:
        return (0, 0, 0.0)
    
    net_worth = get_total_net_worth()
    tax_rate = get_wealth_tax_rate(net_worth)
    
    if tax_rate <= 0:
        return (gross_reward, 0, 0.0)
    
    # Giảm thuế từ passive effects
    try:
        from .item_effects import get_all_passive_effects
        passive = get_all_passive_effects()
        reduction = float(passive.get("tax_reduction", 0.0))
        reduction = min(max(reduction, 0.0), 0.9)
        if reduction > 0:
            tax_rate = tax_rate * (1.0 - reduction)
    except Exception as e:
        logger.debug("apply_wealth_tax_on_reward: %s", e)
    
    tax_amount = int(gross_reward * tax_rate)
    net_reward = gross_reward - tax_amount
    
    return (net_reward, tax_amount, tax_rate)


def get_wealth_tax_status() -> dict:
    """Trả về trạng thái thuế lũy tiến cho UI."""
    net_worth = get_total_net_worth()
    rate = get_wealth_tax_rate(net_worth)
    
    # Tìm bracket name
    bracket_name = "Miễn thuế"
    for threshold, r in WEALTH_TAX_BRACKETS:
        if net_worth > threshold:
            if threshold >= 100_000_000_000:
                bracket_name = "Siêu tỷ phú"
            elif threshold >= 10_000_000_000:
                bracket_name = "Tỷ phú"
            elif threshold >= 1_000_000_000:
                bracket_name = "Triệu phú"
            elif threshold >= 100_000_000:
                bracket_name = "Khá giả"
            elif threshold >= 10_000_000:
                bracket_name = "Trung lưu"
            break
    
    return {
        "net_worth": net_worth,
        "tax_rate": rate,
        "tax_rate_pct": round(rate * 100, 2),
        "bracket_name": bracket_name,
    }


# ═══════════════════════════════════════════════════════════════
# 7. CƠ CHẾ KHAN HIẾM (SCARCITY)
# ═══════════════════════════════════════════════════════════════

# Danh sách xe chỉ xuất hiện vào khung giờ nhất định
SCARCE_VEHICLES = {
    # "item_id": available_hours (0-23)
    "ferrari_sf90":     list(range(20, 24)) + list(range(0, 2)),   # 20h-2h
    "lamborghini_urus": list(range(21, 24)) + list(range(0, 3)),   # 21h-3h
    "rollsroyce_ghost": list(range(6, 10)),                         # 6h-10h sáng
    "bentley_flying":   list(range(14, 18)),                        # 14h-18h
    "porsche_taycan":   list(range(10, 14)),                        # 10h-14h
    "cadillac_escalade": list(range(18, 22)),                       # 18h-22h
}


def is_vehicle_available(item_id: str) -> dict:
    """
    Kiểm tra xe có đang xuất hiện trong cửa hàng không (theo giờ).
    
    Returns:
        {"available": bool, "next_available_in": int/None}
        next_available_in: số giờ cho đến lần xuất hiện tiếp theo
    """
    hours = SCARCE_VEHICLES.get(item_id)
    if hours is None:
        # Xe không trong danh sách khan hiếm → luôn available
        return {"available": True, "next_available_in": None}
    
    current_hour = datetime.now().hour
    
    if current_hour in hours:
        return {"available": True, "next_available_in": 0}
    
    # Tìm giờ tiếp theo xe xuất hiện
    sorted_hours = sorted(hours)
    for h in sorted_hours:
        if h > current_hour:
            return {"available": False, "next_available_in": h - current_hour}
    
    # Nếu không có giờ nào > current_hour, quay vòng sang ngày hôm sau
    if sorted_hours:
        next_day_hour = sorted_hours[0] + 24
        return {"available": False, "next_available_in": next_day_hour - current_hour}
    
    return {"available": True, "next_available_in": None}


def get_all_scarcity_status() -> dict:
    """Trả về trạng thái khan hiếm cho tất cả xe."""
    result = {}
    for item_id in SCARCE_VEHICLES:
        result[item_id] = is_vehicle_available(item_id)
    return result


# ═══════════════════════════════════════════════════════════════
# 8. TỔNG HỢP: Lấy tất cả thông tin cho UI
# ═══════════════════════════════════════════════════════════════

def get_full_economy_status() -> dict:
    """Trả về tất cả thông tin kiểm soát kinh tế cho UI."""
    cap_mult, tier_info = get_daily_cap_multiplier()
    
    return {
        "daily_cap": {
            "cards_today": tier_info["cards_today"],
            "multiplier": cap_mult,
            "mult_pct": tier_info["mult_pct"],
            "tier": tier_info["tier"],
            "next_threshold": tier_info["next_threshold"],
            "cards_until_next": tier_info["cards_until_next"],
        },
        "cpi": get_cpi_status(),
        "wealth_tax": get_wealth_tax_status(),
        "garage_fees": calculate_garage_fees(),
        "scarcity": get_all_scarcity_status(),
        "again_recovery_fee": get_again_recovery_fee(),
    }
