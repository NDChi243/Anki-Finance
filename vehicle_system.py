# -*- coding: utf-8 -*-
from __future__ import annotations
"""
vehicle_system.py — Hệ thống xe cộ & garage (v1.2.0)
======================================================
Chức năng:
  - Mỗi user chỉ được active 1 xe duy nhất.
  - Xe có độ bền (durability), giảm theo thẻ review + thời gian thực.
  - Khi độ bền = 0, xe không còn hiệu lực, cần sửa chữa.
  - Bảo dưỡng/sửa chữa tốn thời gian và tiền (xe đắt → lâu hơn, đắt hơn).
  - Garage có giới hạn slot, phụ thuộc vào nhà ở.
  - Có thể mua thêm slot garage.
  - Hệ thống nhiên liệu: xăng / điện / manual (xe đạp).
  - Tiêu hao nhiên liệu thực tế theo nhóm xe.
  - Xe điện sạc lâu hơn xăng.
  - Xe đạp: không tốn nhiên liệu, khi active giảm xác suất emergency event.
  - Xe đắt tiền → ít bị sự cố hơn.
  - Bán xe với khấu hao theo độ bền + thời gian sử dụng.
  - Bảo dưỡng chủ động: sửa ngay khi độ bền < 100 (không cần đợi = 0).
  - Filter nâng cao trong garage: theo nhóm xe, độ bền, trạng thái, nhiên liệu.
"""

import time
import random
from ._safe_config import cfg_dict, cfg_set, col_ready, cfg_int
from .logger import get_logger

logger = get_logger(__name__)

_KEY_VEHICLE = "anki_tycoon_vehicle_data"
_KEY_GARAGE_SLOTS_BOUGHT = "anki_tycoon_garage_slots_bought"

# ─── Constants ─────────────────────────────────────────────────
BASE_GARAGE_SLOTS = 1
MAX_GARAGE_SLOTS = 20
SLOT_BUY_PRICE = 50000000      # 50M/slot

DEFAULT_DURABILITY = 100
DURABILITY_PER_CARD = 1

# Bảo dưỡng định kỳ
MAINTENANCE_INTERVAL = 50
MAINTENANCE_COST_RATIO = 0.02
MAINTENANCE_DURATION = 1800

# ─── Chi phí & thời gian sửa chữa theo nhóm xe ───────────────────
# Tỉ lệ chi phí (×giá xe) và thời gian (giây) theo nhóm + phân khúc giá
# Công thức: cost = max(min_cost, price × ratio), tuỳ theo nhóm xe

REPAIR_COST_BY_GROUP: dict = {
    # (min_cost, cost_ratio) — ratio thực tế mỗi lần sửa toàn bộ
    "xe đạp":      (50_000,    0.04),   # xe đạp: tối thiểu 50k, ~4% giá
    "xe máy":      (300_000,   0.03),   # xe máy: tối thiểu 300k, ~3% giá
    "xe máy điện": (400_000,   0.035),  # xe máy điện: linh kiện đắt hơn
    "ô tô":        (2_000_000, 0.04),   # ô tô: tối thiểu 2M, ~4% giá
    "xe điện":     (3_000_000, 0.045),  # xe điện: phụ tùng đắt, ~4.5% giá
}
REPAIR_MIN_COST = 500_000  # fallback nếu nhóm không khớp

# Thời gian sửa (giây) theo nhóm xe và ngưỡng giá
# Format: {group: [(price_threshold, duration_s), ...]} — sắp xếp từ cao xuống thấp
REPAIR_DURATION_TABLE: dict = {
    "xe đạp":      [(0, 1800)],           # luôn 30 phút
    "xe máy":      [(100_000_000, 10800), # >100M big bike: 3h
                    (50_000_000,  7200),  # >50M: 2h
                    (0,           3600)], # phổ thông: 1h
    "xe máy điện": [(100_000_000, 10800),
                    (50_000_000,  7200),
                    (0,           3600)],
    "ô tô":        [(10_000_000_000, 86400 * 5),  # siêu xe: 5 ngày
                    (5_000_000_000,  86400 * 3),  # siêu sang: 3 ngày
                    (2_000_000_000,  86400 * 2),  # luxury: 2 ngày
                    (1_000_000_000,  86400),       # premium: 1 ngày
                    (500_000_000,    43200),        # hạng C-D: 12h
                    (0,              21600)],       # hạng B: 6h
    "xe điện":     [(10_000_000_000, 86400 * 5),
                    (5_000_000_000,  86400 * 3),
                    (1_000_000_000,  86400 * 2),
                    (500_000_000,    86400),
                    (0,              28800)],       # xe điện tầm thấp: 8h
}
REPAIR_DURATION_BASE = 3600  # fallback

# ─── Nhiên liệu ──────────────────────────────────────────────────
# Mức tiêu hao nhiên liệu thực tế theo nhóm xe (đơn vị/thẻ)
# 1 thẻ ≈ 1 km di chuyển trong game
# Đơn vị: game unit (≈ lít hoặc kWh scaled)
FUEL_CONSUMPTION_PER_CARD = 1.0         # mặc định (ô tô phổ thông)

FUEL_CONSUMPTION_BY_GROUP: dict = {
    "xe đạp":      0.0,    # manual - không tiêu hao nhiên liệu
    "xe máy":      0.4,    # ~4L/100km × 0.01 km/thẻ → 0.04 scaled x10
    "xe máy điện": 0.3,    # hiệu quả hơn, ~3 kWh/100km
    "ô tô":        1.0,    # ~8L/100km baseline
    "xe điện":     0.7,    # ~15 kWh/100km, hiệu quả hơn xăng
}

# Xe đắt → tiêu hao nhiều hơn (động cơ lớn hơn, công suất cao hơn)
# Format: [(price_threshold, multiplier)]
FUEL_PREMIUM_THRESHOLD = [
    (10_000_000_000, 2.5),   # >10B siêu xe V12/W16: ×2.5 (Bugatti ~40L/100km)
    (5_000_000_000,  2.0),   # >5B  Ferrari/Lamborghini: ×2.0
    (1_000_000_000,  1.4),   # >1B  luxury V8/V6 Turbo: ×1.4
    (500_000_000,    1.2),   # >500M premium SUV: ×1.2
]

# Giá nhiên liệu thực tế VN (VND / đơn vị game)
# Xăng RON95: ~25.000đ/lít → 1 đơn vị game ≈ 1 lít → 25.000đ
FUEL_PRICE_PER_UNIT    = 25_000   # 25k VND / đơn vị xăng (≈ RON95)
# Điện: ~3.500đ/kWh (EVN tier 3) → scaled để hợp lý với gameplay
ELECTRICITY_PRICE_PER_UNIT = 4_000  # 4k VND / đơn vị điện (thực tế hơn)

# Dung tích bình xăng (đơn vị game, tăng thực tế hơn)
FUEL_MAX_BY_PRICE = [
    (10_000_000_000, 120),  # siêu xe: bình lớn 80-120L
    (5_000_000_000,  100),
    (1_000_000_000,   80),
    (500_000_000,     60),
    (100_000_000,     50),  # xe máy phân khối lớn
    (50_000_000,      30),  # xe máy tầm trung
    (0,               20),  # xe máy phổ thông
]

# Dung lượng pin xe điện (đơn vị game ≈ kWh scaled)
ELECTRIC_MAX_BY_PRICE = [
    (10_000_000_000, 250),  # siêu xe điện: ~200-250 kWh
    (5_000_000_000,  180),
    (1_000_000_000,  120),  # Tesla Model S: 100 kWh
    (500_000_000,     80),  # Tesla Model 3: 75 kWh
    (100_000_000,     50),  # xe máy điện cao cấp
    (0,               25),  # xe máy điện phổ thông
]

# Thời gian sạc đầy cho xe điện (giây) — thực tế: xe đắt pin lớn sạc lâu hơn
CHARGE_DURATION_BY_PRICE = [
    (10_000_000_000, 57600),   # 16 tiếng (siêu xe điện, pin khổng lồ)
    (5_000_000_000,  43200),   # 12 tiếng
    (1_000_000_000,  28800),   # 8 tiếng
    (500_000_000,    18000),   # 5 tiếng
    (100_000_000,    10800),   # 3 tiếng (xe máy điện cao cấp)
    (0,               5400),   # 1.5 tiếng (xe máy điện phổ thông)
]

# ─── Độ bền giảm theo thời gian thực ────────────────────────────
# Khi xe đang ACTIVE (đang lái): giảm thêm theo giờ (ngoài giảm theo thẻ)
ACTIVE_DECAY_PER_HOUR: dict = {
    "xe đạp":      0.05,   # xe đạp bền
    "xe máy":      0.3,
    "xe máy điện": 0.25,
    "ô tô":        0.5,
    "xe điện":     0.4,
}
# Khi xe đang IDLE (ở garage, không dùng): lão hóa tự nhiên
PASSIVE_DECAY_PER_DAY: dict = {
    "xe đạp":      0.02,
    "xe máy":      0.05,
    "xe máy điện": 0.04,
    "ô tô":        0.1,
    "xe điện":     0.08,
}

# Cập nhật time-decay tối thiểu mỗi 30 phút
TIME_DECAY_INTERVAL_S = 1800

# ─── Bán xe ──────────────────────────────────────────────────────
SELL_DEPRECIATION_NEW = 0.15                        # Mới 100%: mất 15%
SELL_DEPRECIATION_PER_DURABILITY_LOST = 0.003       # Mỗi 1% độ bền mất → mất thêm 0.3%
SELL_DEPRECIATION_PER_DAY = 0.0005                  # Mỗi ngày sở hữu mất thêm 0.05%
SELL_DEPRECIATION_OVERALL_MAX = 0.80                # Tối đa khấu hao 80%


def _vehicle_tooltip(msg: str, period: int = 4500):
    """Hiển thị thông báo xe qua Anki tooltip — visible từ ngoài webview."""
    try:
        from aqt.utils import tooltip
        tooltip(msg, period=period)
    except Exception as e:
        logger.debug("_vehicle_tooltip: %s", e)


def _calc_repair_duration_by_group(vehicle_group: str, price: int) -> int:
    """Tính thời gian sửa chữa theo nhóm xe và giá."""
    vg = vehicle_group.lower()
    table = REPAIR_DURATION_TABLE.get(vg)
    if table:
        for threshold, duration in table:
            if price >= threshold:
                return duration
    # Fallback theo price tiers
    if price >= 10_000_000_000:
        return 86400 * 5
    elif price >= 1_000_000_000:
        return 86400
    elif price >= 100_000_000:
        return 7200
    elif price >= 10_000_000:
        return 3600
    return REPAIR_DURATION_BASE


def _calc_repair_cost_by_group(vehicle_group: str, price: int) -> int:
    """Tính chi phí sửa chữa theo nhóm xe và giá."""
    vg = vehicle_group.lower()
    min_cost, ratio = REPAIR_COST_BY_GROUP.get(vg, (REPAIR_MIN_COST, 0.04))
    return max(min_cost, int(price * ratio))


def _get_data() -> dict:
    """Lấy toàn bộ dữ liệu vehicle system."""
    return cfg_dict(_KEY_VEHICLE, {
        "active_vehicle_id": None,
        "garage": {},        # {item_id: {"durability": int, "max_durability": int, "in_repair": bool, "repair_until": float}}
        "maintenance_due": {},  # {item_id: bool} - xe cần bảo dưỡng
    })


def _save_data(data: dict):
    cfg_set(_KEY_VEHICLE, data)


# ─── Garage slots ──────────────────────────────────────────────

def get_garage_slots_bought() -> int:
    return cfg_int(_KEY_GARAGE_SLOTS_BOUGHT, 0)


def get_total_garage_slots() -> int:
    """Tổng slot garage = base + mua thêm + bonus từ housing."""
    bought = get_garage_slots_bought()
    # Bonus từ housing
    housing_bonus = 0
    try:
        from .housing_residence import get_residence
        res = get_residence()
        if res:
            rid = res.get("id", "")
            # Villa, townhouse cho thêm slot
            if rid == "villa":
                housing_bonus = 5
            elif rid == "townhouse":
                housing_bonus = 3
            elif rid == "apartment_std":
                housing_bonus = 2
            elif rid == "apartment_mini":
                housing_bonus = 1
    except Exception as e:
        logger.debug("get_total_garage_slots: %s", e)
    return BASE_GARAGE_SLOTS + bought + housing_bonus


def buy_garage_slot() -> dict:
    """Mua thêm 1 slot garage."""
    current = get_garage_slots_bought()
    total = get_total_garage_slots()
    if total >= MAX_GARAGE_SLOTS:
        return {"ok": False, "error": f"Đã đạt tối đa {MAX_GARAGE_SLOTS} slot garage."}

    price = get_slot_buy_price()
    from .balance import get_balance, set_balance_and_log
    bal = get_balance()
    if bal < price:
        return {"ok": False, "error": f"Không đủ tiền! Cần {price:,} VND.".replace(",", ".")}

    new_bal = bal - price
    set_balance_and_log(new_bal, "purchase", -price, "Mua thêm slot garage")
    cfg_set(_KEY_GARAGE_SLOTS_BOUGHT, current + 1)
    return {"ok": True, "total_slots": get_total_garage_slots(), "price": price}


def get_slot_buy_price() -> int:
    """Giá mua slot (tăng dần theo số slot đã mua)."""
    bought = get_garage_slots_bought()
    return SLOT_BUY_PRICE * (1 + bought)


# ─── Vehicle management ────────────────────────────────────────

def _get_fuel_type(item_data: dict) -> str:
    """
    Xác định loại nhiên liệu dựa trên vehicle_group (ưu tiên) hoặc category.
    vehicle_group: "Xe đạp" | "Xe máy" | "Xe máy điện" | "Ô tô" | "Xe điện"
    """
    vg = item_data.get("vehicle_group", "").lower()
    cat = item_data.get("category", "").lower()
    if vg == "xe đạp" or "xe đạp" in cat:
        return "manual"
    if vg in ("xe điện", "xe máy điện") or "xe điện" in cat or "xe máy điện" in cat:
        return "electric"
    return "gasoline"


def _get_fuel_consumption(item_data: dict) -> float:
    """Tính mức tiêu hao nhiên liệu thực tế mỗi thẻ review dựa trên nhóm xe."""
    vg = item_data.get("vehicle_group", "Ô tô").lower()
    base = FUEL_CONSUMPTION_BY_GROUP.get(vg, FUEL_CONSUMPTION_PER_CARD)
    if base == 0.0:
        return 0.0
    # Xe đắt tiền → tiêu hao cao hơn
    price = item_data.get("price", 0)
    for threshold, mult in FUEL_PREMIUM_THRESHOLD:
        if price >= threshold:
            # Chỉ áp dụng premium nếu cùng nhóm với xe đắt
            if vg in ("ô tô", "xe máy"):
                base = max(base, base * mult)
            break
    return round(base, 3)


def _calc_max_fuel(item_data: dict, fuel_type: str) -> int:
    """Tính dung tích nhiên liệu tối đa dựa trên giá xe."""
    price = item_data.get("price", 0)
    if fuel_type == "electric":
        table = ELECTRIC_MAX_BY_PRICE
    else:
        table = FUEL_MAX_BY_PRICE
    for threshold, amount in table:
        if price >= threshold:
            return amount
    return 20


def _calc_charge_duration(item_data: dict) -> int:
    """Tính thời gian sạc đầy (giây) cho xe điện."""
    # Ưu tiên thời gian sạc riêng theo từng loại xe
    hours = item_data.get("charge_time_hours", 0)
    if hours > 0:
        return int(hours * 3600)
    # Fallback: dựa trên giá (cũ)
    price = item_data.get("price", 0)
    for threshold, duration in CHARGE_DURATION_BY_PRICE:
        if price >= threshold:
            return duration
    return 3600


def register_vehicle(item_id: str, item_data: dict):
    """Khi mua xe từ showroom, đăng ký vào garage."""
    if not col_ready():
        return
    data = _get_data()
    garage = data.get("garage", {})

    if item_id in garage:
        return

    fuel_type = _get_fuel_type(item_data)
    max_durability = _calc_max_durability(item_data)
    max_fuel = _calc_max_fuel(item_data, fuel_type)
    fuel_consumption = _get_fuel_consumption(item_data)
    vg = item_data.get("vehicle_group", "Ô tô").lower()
    now = time.time()

    entry = {
        "durability": max_durability,
        "max_durability": max_durability,
        "in_repair": False,
        "repair_until": 0,
        "maintenance_due": False,
        "fuel_type": fuel_type,
        "fuel_level": max_fuel,
        "max_fuel": max_fuel,
        "fuel_consumption": fuel_consumption,  # tiêu hao thực tế/thẻ
        "vehicle_group": vg,                   # lưu để tính decay & effects
        "purchased_at": now,                   # timestamp mua xe (cho khấu hao thời gian)
        "last_passive_decay": now,             # lần cuối áp dụng passive decay
    }

    if fuel_type == "electric":
        entry["is_charging"] = False
        entry["charge_until"] = 0

    garage[item_id] = entry
    data["garage"] = garage
    _save_data(data)


def _calc_max_durability(item_data: dict) -> int:
    """Tính độ bền tối đa dựa trên giá xe."""
    price = item_data.get("price", 0)
    if price >= 10_000_000_000:       # >10B
        return 500
    elif price >= 1_000_000_000:      # >1B
        return 300
    elif price >= 100_000_000:        # >100M
        return 200
    elif price >= 10_000_000:         # >10M
        return 150
    else:
        return DEFAULT_DURABILITY


def get_active_vehicle() -> dict | None:
    """Trả về thông tin xe đang active hoặc None."""
    data = _get_data()
    vid = data.get("active_vehicle_id")
    if not vid:
        return None
    garage = data.get("garage", {})
    info = garage.get(vid)
    if not info:
        return None

    changed = False
    now = time.time()

    # Sửa xong tự động
    if info.get("in_repair"):
        if now < info.get("repair_until", 0):
            return None
        info["in_repair"] = False
        info["repair_until"] = 0
        info["durability"] = info.get("max_durability", DEFAULT_DURABILITY)
        changed = True

    # Hết độ bền → tự dừng
    if info.get("durability", 0) <= 0:
        data["active_vehicle_id"] = None
        _save_data(data)
        return None

    # Hết nhiên liệu → tự dừng (trừ xe đạp)
    fuel_type = info.get("fuel_type", "gasoline")
    if fuel_type != "manual" and info.get("fuel_level", 1) <= 0:
        data["active_vehicle_id"] = None
        _save_data(data)
        return None

    if changed:
        _save_data(data)

    # Trả về với cả hai key để tương thích
    return {"item_id": vid, "vehicle_id": vid, **info}


def select_vehicle(item_id: str) -> dict:
    """
    Chọn 1 xe để active.
    - Nếu đang có xe active, auto stop xe cũ.
    - Kiểm tra xe có trong garage không.
    - Kiểm tra xe có đang sửa không.
    - Kiểm tra độ bền > 0.
    """
    data = _get_data()
    garage = data.get("garage", {})

    if item_id not in garage:
        return {"ok": False, "error": "Xe không có trong garage."}

    info = garage[item_id]

    if info.get("in_repair"):
        now = time.time()
        if now < info.get("repair_until", 0):
            remaining = int(info["repair_until"] - now)
            return {"ok": False, "error": f"Xe đang được sửa chữa. Còn {remaining//60} phút nữa."}
        else:
            info["in_repair"] = False
            info["repair_until"] = 0

    if info.get("durability", 0) <= 0:
        return {"ok": False, "error": "Xe đã hết độ bền. Hãy sửa chữa trước khi sử dụng."}

    if info.get("maintenance_due"):
        return {"ok": False, "error": "Xe cần bảo dưỡng. Hãy bảo dưỡng trước khi sử dụng."}

    # Kiểm tra nhiên liệu (xe đạp luôn OK)
    fuel_type = info.get("fuel_type", "gasoline")
    if fuel_type != "manual":
        fuel_level = info.get("fuel_level", 0)
        if fuel_level <= 0:
            if fuel_type == "electric":
                return {"ok": False, "error": "Xe hết điện! Hãy sạc điện trước khi lái."}
            else:
                return {"ok": False, "error": "Xe hết xăng! Hãy đổ xăng trước khi lái."}
        if info.get("is_charging", False):
            remaining = int(info.get("charge_until", 0) - time.time())
            if remaining > 0:
                return {"ok": False, "error": f"Xe đang sạc, chưa thể lái. Còn {remaining//60} phút."}

    # Dừng xe cũ nếu có
    old_vehicle = data.get("active_vehicle_id")
    data["active_vehicle_id"] = item_id
    info["activated_at"] = time.time()       # bắt đầu theo dõi time decay
    info["last_time_decay"] = time.time()    # reset thời điểm decay lần cuối
    _save_data(data)

    return {
        "ok": True,
        "vehicle_id": item_id,
        "old_vehicle_id": old_vehicle,
        "durability": info["durability"],
        "max_durability": info["max_durability"],
        "fuel_type": fuel_type,
    }


def stop_vehicle() -> dict:
    """Dừng xe đang active."""
    data = _get_data()
    old = data.get("active_vehicle_id")
    if not old:
        return {"ok": False, "error": "Không có xe nào đang active."}
    data["active_vehicle_id"] = None
    _save_data(data)
    return {"ok": True, "vehicle_id": old}


def _log_vehicle_thresholds(vid: str, old_dur: float, new_dur: float, max_dur: float,
                             fuel_type: str, old_fuel: float, new_fuel: float,
                             fuel_ran_out: bool, broke: bool):
    """Log tooltip khi xe qua các ngưỡng cảnh báo quan trọng."""
    try:
        from .shop_data import load_shop_items
        items = {i["id"]: i for i in load_shop_items()}
        name = items.get(vid, {}).get("name", vid)
        emoji = items.get(vid, {}).get("emoji", "🚗")
    except Exception as e:
        logger.debug("_log_vehicle_thresholds: %s", e)
        name, emoji = vid, "🚗"

    if broke:
        _vehicle_tooltip(f"{emoji} <b>{name}</b> hết độ bền! Cần sửa chữa trước khi dùng.", 6000)
        return

    if fuel_ran_out:
        label = "điện" if fuel_type == "electric" else "xăng"
        _vehicle_tooltip(f"{emoji} <b>{name}</b> hết {label}! Cần nạp nhiên liệu.", 5000)
        return

    if max_dur > 0:
        old_pct = old_dur / max_dur * 100
        new_pct = new_dur / max_dur * 100
        # Cảnh báo khi lần đầu vượt qua ngưỡng 20% (chỉ 1 lần)
        if old_pct > 20 >= new_pct:
            _vehicle_tooltip(f"⚠️ {emoji} <b>{name}</b> độ bền còn {new_pct:.0f}%! Cần sửa chữa sớm.", 5000)
        elif old_pct > 50 >= new_pct:
            _vehicle_tooltip(f"🔧 {emoji} <b>{name}</b> độ bền còn {new_pct:.0f}% — nên bảo dưỡng.", 4000)

    # Cảnh báo nhiên liệu thấp (< 25%)
    if fuel_type != "manual" and old_fuel > 0:
        from .shop_data import load_shop_items as _ls
        data = _get_data()
        garage = data.get("garage", {})
        info = garage.get(vid, {})
        max_fuel = info.get("max_fuel", 1)
        if max_fuel > 0:
            old_fuel_pct = old_fuel / max_fuel * 100
            new_fuel_pct = new_fuel / max_fuel * 100
            if old_fuel_pct > 25 >= new_fuel_pct:
                label = "điện" if fuel_type == "electric" else "xăng"
                _vehicle_tooltip(f"⛽ {emoji} <b>{name}</b> sắp hết {label} ({new_fuel_pct:.0f}%)!", 4000)


def consume_durability(cards: int = 1) -> dict:
    """
    Giảm độ bền + nhiên liệu của xe đang active khi review card.
    - Tiêu hao nhiên liệu theo rate thực tế của từng loại xe.
    - Thêm time-based decay mỗi 30 phút đang active.
    Gọi từ Anki hook on_review_done.
    """
    data = _get_data()
    vid = data.get("active_vehicle_id")
    if not vid:
        return {"ok": False, "error": "No active vehicle"}

    garage = data.get("garage", {})
    info = garage.get(vid)
    if not info:
        return {"ok": False, "error": "Vehicle not found in garage"}

    now = time.time()

    # ── Giảm độ bền theo thẻ ──
    old_durability = info.get("durability", 0)
    new_durability = max(0.0, old_durability - (DURABILITY_PER_CARD * cards))

    # ── Time-based active decay (thêm vào sau 30 phút active liên tục) ──
    last_time_decay = info.get("last_time_decay", info.get("activated_at", now))
    elapsed_s = now - last_time_decay
    if elapsed_s >= TIME_DECAY_INTERVAL_S:
        vg = info.get("vehicle_group", "ô tô")
        rate = ACTIVE_DECAY_PER_HOUR.get(vg, 0.5)
        time_decay = rate * (elapsed_s / 3600.0)
        new_durability = max(0.0, new_durability - time_decay)
        info["last_time_decay"] = now

    new_durability = int(new_durability)
    info["durability"] = new_durability

    # ── Tiêu hao nhiên liệu (rate thực tế theo loại xe) ──
    fuel_type = info.get("fuel_type", "gasoline")
    fuel_ran_out = False
    old_fuel = info.get("fuel_level", 0)

    if fuel_type != "manual":
        rate = info.get("fuel_consumption", FUEL_CONSUMPTION_PER_CARD)
        new_fuel = max(0.0, old_fuel - (rate * cards))
        info["fuel_level"] = round(new_fuel, 2)
        if new_fuel <= 0 and old_fuel > 0:
            fuel_ran_out = True
            data["active_vehicle_id"] = None  # hết xăng/điện → tự dừng
    else:
        new_fuel = old_fuel

    # ── Bảo dưỡng định kỳ ──
    max_durability_val = info.get("max_durability", DEFAULT_DURABILITY)
    if max_durability_val > 0:
        used = max_durability_val - new_durability
        if used > 0 and used % MAINTENANCE_INTERVAL == 0:
            info["maintenance_due"] = True

    # ── Hết độ bền → tự động stop ──
    broke = new_durability <= 0 and vid == data.get("active_vehicle_id")
    if broke:
        data["active_vehicle_id"] = None

    _save_data(data)

    # ── Tooltip log cho các ngưỡng quan trọng ──
    _log_vehicle_thresholds(vid, old_durability, new_durability, max_durability_val,
                            fuel_type, old_fuel, new_fuel, fuel_ran_out, broke)

    # ── Tiến triển sửa xe đang trong breakdown repair ──
    try:
        from .economy_controls import progress_breakdown_repair
        for gid, ginfo in garage.items():
            if ginfo.get("breakdown_repair", False):
                progress_breakdown_repair(gid)
    except Exception as e:
        logger.warning("consume_durability (breakdown repair): %s", e)

    return {
        "ok": True,
        "vehicle_id": vid,
        "item_id": vid,
        "old_durability": old_durability,
        "new_durability": new_durability,
        "broken": new_durability <= 0,
        "fuel_type": fuel_type,
        "old_fuel": old_fuel,
        "new_fuel": round(float(new_fuel), 2),
        "fuel_ran_out": fuel_ran_out,
    }


def get_vehicle_info(item_id: str) -> dict | None:
    """Trả về thông tin chi tiết của 1 xe."""
    data = _get_data()
    garage = data.get("garage", {})
    info = garage.get(item_id)
    if not info:
        return None
    return {
        "item_id": item_id,
        "is_active": data.get("active_vehicle_id") == item_id,
        **info,
    }


def _calc_sell_price(price: int, durability: int, max_durability: int,
                     purchased_at: float) -> int:
    """
    Tính giá bán ước tính:
      - Mới 100%, chưa dùng: giá gốc × (1 - 15%)
      - Giảm thêm theo độ bền đã mất (mỗi 1% độ bền mất → -0.3%)
      - Giảm thêm theo số ngày đã sở hữu
      - Khấu hao tối đa 80% (luôn bán ≥ 20% giá gốc)
    """
    if price <= 0:
        return 0
    durability_pct = durability / max_durability if max_durability > 0 else 0
    durability_lost_pct = 1.0 - durability_pct

    days_owned = max(0.0, (time.time() - purchased_at) / 86400.0)
    time_depr = SELL_DEPRECIATION_PER_DAY * days_owned

    depreciation = (SELL_DEPRECIATION_NEW
                    + durability_lost_pct * SELL_DEPRECIATION_PER_DURABILITY_LOST * 100
                    + time_depr)
    depreciation = min(depreciation, SELL_DEPRECIATION_OVERALL_MAX)
    return max(int(price * (1.0 - depreciation)), int(price * 0.20))


def _apply_passive_decay(data: dict, now: float) -> bool:
    """
    Áp dụng passive decay (lão hóa tự nhiên) cho tất cả xe.
    Trả về True nếu có thay đổi cần lưu.
    """
    changed = False
    garage = data.get("garage", {})
    active_id = data.get("active_vehicle_id")

    for vid, info in garage.items():
        if info.get("in_repair") or info.get("durability", 0) <= 0:
            continue

        last_check = info.get("last_passive_decay", now)
        elapsed_s = now - last_check
        if elapsed_s < 3600:  # check tối đa mỗi giờ
            continue

        vg = info.get("vehicle_group", "ô tô")
        is_active = (vid == active_id)

        if is_active:
            # Active decay: áp dụng nếu chưa check trong 30 phút
            last_td = info.get("last_time_decay", last_check)
            elapsed_td = now - last_td
            if elapsed_td >= TIME_DECAY_INTERVAL_S:
                rate = ACTIVE_DECAY_PER_HOUR.get(vg, 0.5)
                decay = rate * (elapsed_td / 3600.0)
                info["durability"] = max(0, int(info.get("durability", 0) - decay))
                info["last_time_decay"] = now
                changed = True
        else:
            # Passive decay: lão hóa khi xe không dùng
            rate_day = PASSIVE_DECAY_PER_DAY.get(vg, 0.1)
            decay = rate_day * (elapsed_s / 86400.0)
            if decay >= 0.1:
                info["durability"] = max(0, int(info.get("durability", 0) - decay))
                info["last_passive_decay"] = now
                changed = True

    return changed


def get_garage_summary() -> list:
    """Trả về danh sách tất cả xe trong garage kèm fuel, trạng thái & sell estimate."""
    data = _get_data()

    # Áp dụng passive decay trước khi lấy dữ liệu
    now = time.time()
    if _apply_passive_decay(data, now):
        _save_data(data)

    garage = data.get("garage", {})
    active = data.get("active_vehicle_id")
    result = []
    from .shop_data import get_items_map
    from .gui.image_manager import get_image_url
    items = get_items_map()

    for item_id, info in garage.items():
        item_data = items.get(item_id, {})
        durability = info.get("durability", 0)
        max_durability = info.get("max_durability", 1)
        durability_pct = int(durability / max_durability * 100) if max_durability > 0 else 0

        fuel_type = info.get("fuel_type", "gasoline")
        max_fuel = info.get("max_fuel", 0)
        fuel_level = round(float(info.get("fuel_level", 0)), 1)
        fuel_pct = int(fuel_level / max_fuel * 100) if max_fuel > 0 else 0

        # Kiểm tra sạc điện xong chưa
        is_charging = False
        charge_remaining = 0
        if fuel_type == "electric":
            is_charging = info.get("is_charging", False)
            charge_until = info.get("charge_until", 0)
            if is_charging and charge_until > now:
                charge_remaining = int(charge_until - now)
            elif is_charging and charge_until <= now:
                is_charging = False
                info["is_charging"] = False
                info["charge_until"] = 0
                info["fuel_level"] = max_fuel
                fuel_level = max_fuel
                fuel_pct = 100
                _save_data(data)

        # Tính giá bán ước tính
        price = item_data.get("price", 0)
        sell_estimate = _calc_sell_price(price, durability, max_durability,
                                         info.get("purchased_at", now))

        result.append({
            "item_id": item_id,
            "name": item_data.get("name", item_id),
            "emoji": item_data.get("emoji", "🚗"),
            "image_url": get_image_url(item_id),
            "vehicle_group": info.get("vehicle_group", item_data.get("vehicle_group", "Ô tô")),
            "price": price,
            "is_active": item_id == active,
            "durability": durability,
            "max_durability": max_durability,
            "durability_pct": durability_pct,
            "in_repair": info.get("in_repair", False),
            "repair_until": info.get("repair_until", 0),
            "maintenance_due": info.get("maintenance_due", False),
            "breakdown_repair": info.get("breakdown_repair", False),
            "breakdown_reviews_done": info.get("breakdown_reviews_done", 0),
            "breakdown_reviews_required": info.get("breakdown_reviews_required", 30),
            "fuel_type": fuel_type,
            "fuel_level": fuel_level,
            "max_fuel": max_fuel,
            "fuel_pct": fuel_pct,
            "fuel_consumption": info.get("fuel_consumption", FUEL_CONSUMPTION_PER_CARD),
            "is_charging": is_charging,
            "charge_remaining": charge_remaining,
            "sell_estimate": sell_estimate,
        })
    return result


# ─── Repair & Maintenance ──────────────────────────────────────

def start_repair(item_id: str) -> dict:
    """Bắt đầu sửa chữa xe."""
    data = _get_data()
    garage = data.get("garage", {})
    info = garage.get(item_id)
    if not info:
        return {"ok": False, "error": "Xe không có trong garage."}

    if info.get("durability") >= info.get("max_durability", DEFAULT_DURABILITY):
        return {"ok": False, "error": "Xe vẫn còn độ bền tốt, không cần sửa."}

    # Tính chi phí sửa dựa trên nhóm xe + giá xe
    from .shop_data import get_items_map
    items = get_items_map()
    item_data = items.get(item_id, {})
    price = item_data.get("price", 0)

    # Lấy vehicle_group từ garage entry (đã lưu lúc đăng ký)
    vehicle_group = info.get("vehicle_group", item_data.get("vehicle_group", "ô tô"))
    repair_cost     = _calc_repair_cost_by_group(vehicle_group, price)
    repair_duration = _calc_repair_duration_by_group(vehicle_group, price)

    # Kiểm tra tiền
    from .balance import get_balance, set_balance_and_log
    bal = get_balance()
    if bal < repair_cost:
        return {"ok": False, "error": f"Không đủ tiền sửa! Cần {repair_cost:,} VND.".replace(",", ".")}

    new_bal = bal - repair_cost
    set_balance_and_log(new_bal, "purchase", -repair_cost, f"Sửa chữa xe: {item_data.get('name', item_id)}")

    # Nếu xe đang active, stop
    if data.get("active_vehicle_id") == item_id:
        data["active_vehicle_id"] = None

    info["in_repair"] = True
    info["repair_until"] = time.time() + repair_duration
    info["durability"] = 0  # tạm thời = 0 trong lúc sửa
    _save_data(data)

    hours = repair_duration // 3600
    mins = (repair_duration % 3600) // 60
    time_str = f"{hours}h{mins}p" if hours > 0 else f"{mins} phút"

    return {
        "ok": True,
        "cost": repair_cost,
        "duration_s": repair_duration,
        "duration_str": time_str,
        "item_name": item_data.get("name", item_id),
    }


def do_maintenance(item_id: str) -> dict:
    """Bảo dưỡng xe định kỳ."""
    data = _get_data()
    garage = data.get("garage", {})
    info = garage.get(item_id)
    if not info:
        return {"ok": False, "error": "Xe không có trong garage."}

    if not info.get("maintenance_due"):
        return {"ok": False, "error": "Xe chưa cần bảo dưỡng."}

    from .shop_data import get_items_map
    items = get_items_map()
    item_data = items.get(item_id, {})
    price = item_data.get("price", 0)
    cost = max(int(price * MAINTENANCE_COST_RATIO), 200000)

    from .balance import get_balance, set_balance_and_log
    bal = get_balance()
    if bal < cost:
        return {"ok": False, "error": f"Không đủ tiền bảo dưỡng! Cần {cost:,} VND.".replace(",", ".")}

    new_bal = bal - cost
    set_balance_and_log(new_bal, "purchase", -cost, f"Bảo dưỡng xe: {item_data.get('name', item_id)}")

    info["maintenance_due"] = False
    # Bảo dưỡng phục hồi 20% độ bền
    max_durability = info.get("max_durability", DEFAULT_DURABILITY)
    info["durability"] = min(max_durability, info.get("durability", 0) + int(max_durability * 0.2))
    _save_data(data)

    return {
        "ok": True,
        "cost": cost,
        "new_durability": info["durability"],
        "max_durability": max_durability,
    }


def get_repair_cost_preview(item_id: str) -> dict:
    """Xem trước chi phí sửa chữa."""
    from .shop_data import get_items_map
    items = get_items_map()
    item_data = items.get(item_id, {})
    price = item_data.get("price", 0)

    # Lấy vehicle_group từ garage nếu có
    data = _get_data()
    garage = data.get("garage", {})
    info = garage.get(item_id, {})
    vehicle_group = info.get("vehicle_group", item_data.get("vehicle_group", "ô tô"))

    cost     = _calc_repair_cost_by_group(vehicle_group, price)
    duration = _calc_repair_duration_by_group(vehicle_group, price)

    hours = duration // 3600
    mins = (duration % 3600) // 60
    days = hours // 24
    if days >= 1:
        rem_h = hours % 24
        time_str = f"{days} ngày{f' {rem_h}h' if rem_h else ''}"
    elif hours > 0:
        time_str = f"{hours}h{f'{mins}p' if mins else ''}"
    else:
        time_str = f"{mins} phút"

    return {
        "cost": cost,
        "duration_s": duration,
        "duration_str": time_str,
    }


# ─── Bảo dưỡng chủ động (sửa ngay khi độ bền < 100) ──────────

def quick_maintenance(item_id: str) -> dict:
    """
    Bảo dưỡng/sửa ngay khi xe còn độ bền < 100 (không cần đợi = 0).
    - Chi phí = tỷ lệ % độ bền đã mất × giá xe × MAINTENANCE_COST_RATIO
    - Thời gian = MAINTENANCE_DURATION (30 phút)
    - Phục hồi 20% độ bền tối đa
    - Kết nối với item_effects: nếu có passive effect liên quan đến bảo dưỡng
    """
    data = _get_data()
    garage = data.get("garage", {})
    info = garage.get(item_id)
    if not info:
        return {"ok": False, "error": "Xe không có trong garage."}

    max_durability = info.get("max_durability", DEFAULT_DURABILITY)
    current_durability = info.get("durability", 0)

    if current_durability >= max_durability:
        return {"ok": False, "error": "Xe đã đạt độ bền tối đa, không cần bảo dưỡng."}

    if info.get("in_repair"):
        return {"ok": False, "error": "Xe đang được sửa chữa, không thể bảo dưỡng."}

    if info.get("breakdown_repair"):
        return {"ok": False, "error": "Xe đang sửa sự cố, không thể bảo dưỡng."}

    from .shop_data import get_items_map
    items = get_items_map()
    item_data = items.get(item_id, {})
    price = item_data.get("price", 0)

    # Chi phí theo % độ bền đã mất
    durability_lost_pct = 1.0 - (current_durability / max_durability if max_durability > 0 else 0)
    cost = max(int(price * MAINTENANCE_COST_RATIO * (0.5 + durability_lost_pct * 0.5)), 100000)

    # Thời gian bảo dưỡng: càng mất nhiều độ bền càng lâu
    duration = int(MAINTENANCE_DURATION * (0.5 + durability_lost_pct * 0.5))

    # Kiểm tra item effects có ảnh hưởng đến bảo dưỡng không
    effects_note = ""
    discount = 0.0
    try:
        from .item_effects import get_passive_effects_aggregated
        agg = get_passive_effects_aggregated()
        discount = agg.get("maintenance_discount", 0)
        if discount > 0:
            effects_note = f" (giảm {int(discount*100)}% nhờ hiệu ứng)"
    except Exception as e:
        logger.debug("quick_maintenance (effects): %s", e)

    # Áp dụng giảm giá từ item effects
    if discount > 0:
        cost = max(int(cost * (1 - discount)), 100000)
        duration = max(int(duration * (1 - discount)), 60)

    from .balance import get_balance, set_balance_and_log
    bal = get_balance()
    if bal < cost:
        return {"ok": False, "error": f"Không đủ tiền bảo dưỡng! Cần {cost:,} VND.".replace(",", ".")}

    new_bal = bal - cost
    set_balance_and_log(new_bal, "purchase", -cost,
                        f"Bảo dưỡng chủ động: {item_data.get('name', item_id)}")

    # Nếu xe đang active, stop
    if data.get("active_vehicle_id") == item_id:
        data["active_vehicle_id"] = None

    info["in_repair"] = True
    info["repair_until"] = time.time() + duration
    info["maintenance_due"] = False
    _save_data(data)

    hours = duration // 3600
    mins = (duration % 3600) // 60
    time_str = f"{hours}h{mins}p" if hours > 0 else f"{mins} phút"

    return {
        "ok": True,
        "cost": cost,
        "duration_s": duration,
        "duration_str": time_str + effects_note,
        "item_name": item_data.get("name", item_id),
        "durability_lost_pct": round(durability_lost_pct * 100, 1),
        "new_durability_after": min(max_durability, current_durability + int(max_durability * 0.2)),
        "max_durability": max_durability,
    }


def get_maintenance_tab_data() -> dict:
    """
    Trả về dữ liệu cho tab Bảo dưỡng/Sửa ngay.
    - Danh sách xe cần bảo dưỡng (độ bền < max)
    - Chi phí ước tính cho từng xe
    - Thời gian ước tính
    - Tổng chi phí nếu bảo dưỡng tất cả
    """
    data = _get_data()
    garage = data.get("garage", {})
    from .shop_data import get_items_map
    items = get_items_map()

    maintenance_list = []
    total_cost_all = 0
    now = time.time()

    for item_id, info in garage.items():
        if info.get("in_repair") or info.get("breakdown_repair"):
            continue

        max_durability = info.get("max_durability", DEFAULT_DURABILITY)
        current_durability = info.get("durability", 0)

        if current_durability >= max_durability:
            continue

        item_data = items.get(item_id, {})
        price = item_data.get("price", 0)

        durability_lost_pct = 1.0 - (current_durability / max_durability if max_durability > 0 else 0)
        cost = max(int(price * MAINTENANCE_COST_RATIO * (0.5 + durability_lost_pct * 0.5)), 100000)
        duration = int(MAINTENANCE_DURATION * (0.5 + durability_lost_pct * 0.5))

        hours = duration // 3600
        mins = (duration % 3600) // 60
        time_str = f"{hours}h{mins}p" if hours > 0 else f"{mins} phút"

        total_cost_all += cost

        maintenance_list.append({
            "item_id": item_id,
            "name": item_data.get("name", item_id),
            "emoji": item_data.get("emoji", "🚗"),
            "vehicle_group": info.get("vehicle_group", item_data.get("vehicle_group", "Ô tô")),
            "durability": current_durability,
            "max_durability": max_durability,
            "durability_pct": int(current_durability / max_durability * 100) if max_durability > 0 else 0,
            "cost": cost,
            "duration_s": duration,
            "duration_str": time_str,
            "maintenance_due": info.get("maintenance_due", False),
        })

    return {
        "vehicles": maintenance_list,
        "total_cost": total_cost_all,
        "count": len(maintenance_list),
    }


# ─── Nhiên liệu ──────────────────────────────────────────────────

def refuel_vehicle(item_id: str) -> dict:
    """Đổ xăng cho xe. Tính tiền dựa trên số lượng xăng cần đổ."""
    data = _get_data()
    garage = data.get("garage", {})
    info = garage.get(item_id)
    if not info:
        return {"ok": False, "error": "Xe không có trong garage."}

    fuel_type = info.get("fuel_type", "gasoline")
    if fuel_type != "gasoline":
        return {"ok": False, "error": "Xe này không dùng xăng."}

    max_fuel = info.get("max_fuel", 0)
    current = info.get("fuel_level", 0)
    if current >= max_fuel:
        return {"ok": False, "error": "Bình xăng đã đầy."}

    needed = max_fuel - current
    cost = int(needed * FUEL_PRICE_PER_UNIT)

    from .balance import get_balance, set_balance_and_log
    bal = get_balance()
    if bal < cost:
        return {"ok": False, "error": f"Không đủ tiền đổ xăng! Cần {cost:,} VND.".replace(",", ".")}

    from .shop_data import get_items_map
    items = get_items_map()
    item_data = items.get(item_id, {})

    new_bal = bal - cost
    set_balance_and_log(new_bal, "purchase", -cost,
                        f"Đổ xăng: {item_data.get('name', item_id)} ({needed} đơn vị)")

    info["fuel_level"] = max_fuel
    _save_data(data)

    return {
        "ok": True,
        "cost": cost,
        "units_added": needed,
        "fuel_level": max_fuel,
        "max_fuel": max_fuel,
        "fuel_pct": 100,
    }


def recharge_vehicle(item_id: str) -> dict:
    """Sạc điện cho xe. Tốn thời gian (xe càng đắt sạc càng lâu)."""
    data = _get_data()
    garage = data.get("garage", {})
    info = garage.get(item_id)
    if not info:
        return {"ok": False, "error": "Xe không có trong garage."}

    fuel_type = info.get("fuel_type", "gasoline")
    if fuel_type != "electric":
        return {"ok": False, "error": "Xe này không dùng điện."}

    max_fuel = info.get("max_fuel", 0)
    current = info.get("fuel_level", 0)
    if current >= max_fuel:
        return {"ok": False, "error": "Xe đã đầy điện."}

    if info.get("is_charging", False):
        remaining = int(info.get("charge_until", 0) - time.time())
        if remaining > 0:
            return {"ok": False, "error": f"Xe đang sạc. Còn {remaining//60} phút nữa."}

    from .shop_data import get_items_map
    items = get_items_map()
    item_data = items.get(item_id, {})
    charge_duration = _calc_charge_duration(item_data)

    # Tính tiền điện
    needed = max_fuel - current
    cost = int(needed * ELECTRICITY_PRICE_PER_UNIT)

    from .balance import get_balance, set_balance_and_log
    bal = get_balance()
    if bal < cost:
        return {"ok": False, "error": f"Không đủ tiền sạc điện! Cần {cost:,} VND.".replace(",", ".")}

    new_bal = bal - cost
    set_balance_and_log(new_bal, "purchase", -cost,
                        f"Sạc điện: {item_data.get('name', item_id)}")

    info["is_charging"] = True
    info["charge_until"] = time.time() + charge_duration
    _save_data(data)

    hours = charge_duration // 3600
    mins = (charge_duration % 3600) // 60
    time_str = f"{hours}h{mins}p" if hours > 0 else f"{mins} phút"

    return {
        "ok": True,
        "cost": cost,
        "charge_duration_s": charge_duration,
        "charge_duration_str": time_str,
    }


# ─── Bán xe ──────────────────────────────────────────────────────

def sell_vehicle(item_id: str) -> dict:
    """
    Bán xe với khấu hao theo độ bền + thời gian sở hữu:
    - Mới 100%, chưa dùng: giá gốc × (1 - 15%)
    - Mỗi 1% độ bền mất → -0.3%
    - Mỗi ngày sở hữu → -0.05%
    - Khấu hao tối đa 80% (bán ≥ 20% giá gốc)
    """
    data = _get_data()
    garage = data.get("garage", {})
    info = garage.get(item_id)
    if not info:
        return {"ok": False, "error": "Xe không có trong garage."}

    if data.get("active_vehicle_id") == item_id:
        return {"ok": False, "error": "Hãy dừng xe trước khi bán."}

    if info.get("in_repair"):
        if time.time() < info.get("repair_until", 0):
            return {"ok": False, "error": "Xe đang sửa chữa, không thể bán."}

    if info.get("breakdown_repair"):
        return {"ok": False, "error": "Xe đang trong quá trình sửa sự cố, không thể bán."}

    from .shop_data import get_items_map
    items = get_items_map()
    item_data = items.get(item_id, {})

    price = item_data.get("price", 0)
    if price <= 0:
        return {"ok": False, "error": "Xe này không có giá trị."}

    max_durability = info.get("max_durability", 1)
    durability = info.get("durability", 0)
    purchased_at = info.get("purchased_at", time.time())

    sell_price = _calc_sell_price(price, durability, max_durability, purchased_at)

    # Tính % khấu hao để hiển thị
    depreciation_pct = round((1.0 - sell_price / price) * 100, 1) if price > 0 else 0

    # Xoá khỏi garage
    del garage[item_id]
    if data.get("active_vehicle_id") == item_id:
        data["active_vehicle_id"] = None
    _save_data(data)

    # Cộng tiền
    from .balance import get_balance, set_balance_and_log
    new_bal = get_balance() + sell_price
    set_balance_and_log(new_bal, "purchase", sell_price,
                        f"Bán xe: {item_data.get('name', item_id)}")

    try:
        from .item_effects import unregister_passive_effect
        unregister_passive_effect(item_id)
    except Exception as e:
        logger.warning("sell_vehicle (unregister passive): %s", e)

    return {
        "ok": True,
        "sell_price": sell_price,
        "depreciation_pct": depreciation_pct,
        "item_name": item_data.get("name", item_id),
    }


# ─── Effects cho Emergency System ────────────────────────────────

def get_active_vehicle_effects() -> dict:
    """
    Trả về các effect TẠM THỜI khi xe đang active (đang lái).
    Cộng thêm vào passive effects từ item_effects.
    Hiệu quả giảm dần khi độ bền thấp (< 50%).
    """
    effects: dict = {}
    try:
        av = get_active_vehicle()
        if not av:
            return effects
        vg        = av.get("vehicle_group", "").lower()
        fuel_type = av.get("fuel_type", "gasoline")
        dur       = av.get("durability", 0)
        max_dur   = av.get("max_durability", 100)
        # Hệ số hiệu quả: 100% bền = 1.0, 50% bền = 0.7, 20% bền = 0.4
        eff_factor = round(min(1.0, max(0.3, dur / max_dur if max_dur > 0 else 1.0)), 3)

        if fuel_type == "manual" or vg == "xe đạp":
            # Đạp xe: healthy lifestyle → giảm rủi ro tai nạn + tăng sức khỏe
            effects["emergency_resistance"] = round(0.15 * eff_factor, 3)
            effects["health_boost"]         = round(0.5  * eff_factor, 2)
        elif vg in ("xe máy", "xe máy điện"):
            # Xe máy: linh hoạt, nhưng rủi ro hơn ô tô → chỉ giảm nhẹ
            effects["emergency_resistance"] = round(0.04 * eff_factor, 3)
        elif vg == "ô tô":
            # Ô tô: an toàn, thoải mái → giảm rủi ro tai nạn đáng kể
            effects["emergency_resistance"] = round(0.08 * eff_factor, 3)
        elif vg == "xe điện":
            # Xe điện: công nghệ cao, an toàn nhất, eco-friendly → bonus kép
            effects["emergency_resistance"]   = round(0.12 * eff_factor, 3)
            effects["emergency_cost_reduction"] = round(0.05 * eff_factor, 3)
    except Exception as e:
        logger.debug("get_active_vehicle_effects: %s", e)
    return effects


def get_vehicle_fuel_cost_info(item_id: str) -> dict:
    """
    Trả về thông tin chi phí nhiên liệu thực tế cho 1 xe.
    Dùng để hiển thị trong UI: giá/đơn vị, mức tiêu hao, chi phí/100 thẻ.
    """
    data  = _get_data()
    info  = data.get("garage", {}).get(item_id, {})
    if not info:
        return {}
    fuel_type   = info.get("fuel_type", "gasoline")
    consumption = info.get("fuel_consumption", FUEL_CONSUMPTION_PER_CARD)
    max_fuel    = info.get("max_fuel", 0)
    price_per_unit = ELECTRICITY_PRICE_PER_UNIT if fuel_type == "electric" else FUEL_PRICE_PER_UNIT
    cost_per_100 = int(consumption * 100 * price_per_unit)
    full_tank_cost = int(max_fuel * price_per_unit)
    return {
        "fuel_type":         fuel_type,
        "consumption":       consumption,
        "price_per_unit":    price_per_unit,
        "cost_per_100_cards": cost_per_100,
        "full_tank_cost":    full_tank_cost,
        "range_on_full":     int(max_fuel / consumption) if consumption > 0 else 9999,
    }
