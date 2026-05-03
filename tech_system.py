# -*- coding: utf-8 -*-
from __future__ import annotations
"""
tech_system.py — Hệ thống đồ công nghệ & Tech Lab (v1.0)
========================================================
Chức năng:
  - Mỗi user chỉ được active 1 tech item duy nhất.
  - Tech item có độ bền (durability), giảm theo thẻ review.
  - Khi độ bền = 0, item không còn hiệu lực, cần sửa chữa.
  - Bảo dưỡng/sửa chữa tốn thời gian và tiền.
  - Bán tech item với khấu hao theo độ bền + thời gian sử dụng.
  - Passive effects chỉ hoạt động khi item đang active.
"""

import time
from ._safe_config import cfg_dict, cfg_set

_KEY_TECH = "anki_tycoon_tech_data"

# ─── Constants ─────────────────────────────────────────────────
DEFAULT_DURABILITY = 100
DURABILITY_PER_CARD = 1          # 1 thẻ = 1 điểm độ bền

# Bảo dưỡng định kỳ
MAINTENANCE_INTERVAL = 30        # Cứ 30 thẻ thì cần bảo dưỡng
MAINTENANCE_COST_RATIO = 0.02    # 2% giá gốc mỗi lần bảo dưỡng
MAINTENANCE_DURATION = 600       # 10 phút bảo dưỡng

# Sửa chữa
REPAIR_COST_RATIO = 0.05         # 5% giá gốc mỗi lần sửa
REPAIR_DURATION = 3600           # 1 giờ sửa chữa

# Bán lại
SELL_DEPRECIATION_NEW = 0.3      # Khấu hao ngay khi mua: 30%
SELL_DEPRECIATION_PER_DURABILITY_LOST = 0.003  # Thêm 0.3% mỗi % độ bền mất


def _get_data() -> dict:
    """Lấy toàn bộ dữ liệu tech."""
    return cfg_dict(_KEY_TECH, {
        "active_tech_id": None,
        "tech_lab": {},  # {item_id: {"durability": int, "max_durability": int, "in_repair": bool, "repair_until": float, "maintenance_due": bool, "purchased_at": float}}
    })


def _save_data(data: dict):
    """Lưu dữ liệu tech."""
    cfg_set(_KEY_TECH, data)


def get_tech_summary() -> list:
    """Trả về danh sách tech items trong tech lab."""
    data = _get_data()
    tech_lab = data.get("tech_lab", {})
    active_id = data.get("active_tech_id")

    from .shop_data import get_items_map
    items_map = get_items_map()

    now = time.time()
    result = []
    for item_id, info in tech_lab.items():
        item_data = items_map.get(item_id, {})
        durability = info.get("durability", 0)
        max_durability = info.get("max_durability", DEFAULT_DURABILITY)
        durability_pct = int(durability / max_durability * 100) if max_durability > 0 else 0
        price = item_data.get("price", 0)
        sell_estimate = _calc_sell_price(price, durability, max_durability, info.get("purchased_at", now))

        result.append({
            "item_id": item_id,
            "name": item_data.get("name", item_id),
            "emoji": item_data.get("emoji", "💻"),
            "price": price,
            "is_active": item_id == active_id,
            "durability": durability,
            "max_durability": max_durability,
            "durability_pct": durability_pct,
            "in_repair": info.get("in_repair", False),
            "repair_until": info.get("repair_until", 0),
            "maintenance_due": info.get("maintenance_due", False),
            "sell_estimate": sell_estimate,
            "purchased_at": info.get("purchased_at", now),
        })
    return result


def get_active_tech() -> dict | None:
    """Trả về tech item đang active, hoặc None."""
    data = _get_data()
    active_id = data.get("active_tech_id")
    if not active_id:
        return None
    tech_lab = data.get("tech_lab", {})
    info = tech_lab.get(active_id)
    if not info:
        return None

    from .shop_data import get_items_map
    item_data = get_items_map().get(active_id, {})
    durability = info.get("durability", 0)
    max_durability = info.get("max_durability", DEFAULT_DURABILITY)
    durability_pct = int(durability / max_durability * 100) if max_durability > 0 else 0

    return {
        "item_id": active_id,
        "name": item_data.get("name", active_id),
        "emoji": item_data.get("emoji", "💻"),
        "durability": durability,
        "max_durability": max_durability,
        "durability_pct": durability_pct,
        "in_repair": info.get("in_repair", False),
        "maintenance_due": info.get("maintenance_due", False),
    }


def register_tech(item_id: str, item_data: dict):
    """Đăng ký tech item mới khi mua."""
    data = _get_data()
    tech_lab = data.setdefault("tech_lab", {})

    if item_id in tech_lab:
        return  # Đã có rồi

    max_durability = DEFAULT_DURABILITY
    tech_lab[item_id] = {
        "durability": max_durability,
        "max_durability": max_durability,
        "in_repair": False,
        "repair_until": 0,
        "maintenance_due": False,
        "purchased_at": time.time(),
    }
    _save_data(data)


def activate_tech(item_id: str) -> dict:
    """Kích hoạt tech item. Chỉ 1 item được active."""
    data = _get_data()
    tech_lab = data.get("tech_lab", {})
    info = tech_lab.get(item_id)
    if not info:
        return {"ok": False, "error": "Tech item không tồn tại trong tech lab."}

    if info.get("in_repair"):
        now = time.time()
        if now < info.get("repair_until", 0):
            remaining = int(info["repair_until"] - now)
            return {"ok": False, "error": f"Tech item đang được sửa chữa. Còn {remaining//60} phút nữa."}
        else:
            info["in_repair"] = False
            info["repair_until"] = 0

    if info.get("durability", 0) <= 0:
        return {"ok": False, "error": "Tech item đã hết độ bền. Hãy sửa chữa trước khi sử dụng."}

    if info.get("maintenance_due"):
        return {"ok": False, "error": "Tech item cần bảo dưỡng. Hãy bảo dưỡng trước khi sử dụng."}

    # Deactivate old tech
    old_active = data.get("active_tech_id")
    data["active_tech_id"] = item_id
    _save_data(data)

    # Unregister old passive, register new passive
    try:
        from .item_effects import unregister_passive_effect, register_passive_effect
        if old_active:
            unregister_passive_effect(old_active)
        from .shop_data import get_items_map
        item_data = get_items_map().get(item_id, {})
        if item_data:
            register_passive_effect(item_id, item_data)
    except Exception:
        pass

    return {
        "ok": True,
        "item_id": item_id,
        "name": info.get("name", item_id),
        "old_item_id": old_active,
    }


def deactivate_tech() -> dict:
    """Tắt tech item đang active."""
    data = _get_data()
    old_active = data.get("active_tech_id")
    if not old_active:
        return {"ok": False, "error": "Không có tech item nào đang active."}

    data["active_tech_id"] = None
    _save_data(data)

    try:
        from .item_effects import unregister_passive_effect
        unregister_passive_effect(old_active)
    except Exception:
        pass

    return {"ok": True, "item_id": old_active}


def consume_durability(cards: int = 1) -> dict:
    """
    Giảm độ bền của tech item đang active.
    Được gọi mỗi khi user review thẻ.
    """
    data = _get_data()
    active_id = data.get("active_tech_id")
    if not active_id:
        return {"item_id": None, "broken": False}

    tech_lab = data.get("tech_lab", {})
    info = tech_lab.get(active_id)
    if not info:
        return {"item_id": None, "broken": False}

    if info.get("in_repair"):
        # Kiểm tra sửa xong chưa
        now = time.time()
        if now >= info.get("repair_until", 0):
            info["in_repair"] = False
            info["repair_until"] = 0
            info["durability"] = info.get("max_durability", DEFAULT_DURABILITY)
        else:
            return {"item_id": active_id, "broken": False}

    if info.get("durability", 0) <= 0:
        return {"item_id": active_id, "broken": True}

    # Giảm độ bền
    old_durability = info.get("durability", 0)
    new_durability = max(0.0, old_durability - (DURABILITY_PER_CARD * cards))
    new_durability = int(new_durability)
    info["durability"] = new_durability

    # Kiểm tra bảo dưỡng định kỳ
    max_durability_val = info.get("max_durability", DEFAULT_DURABILITY)
    if max_durability_val > 0:
        used = max_durability_val - new_durability
        if used > 0 and used % MAINTENANCE_INTERVAL == 0:
            info["maintenance_due"] = True

    # Hết độ bền → tự động deactivate
    broke = new_durability <= 0
    if broke:
        data["active_tech_id"] = None
        try:
            from .item_effects import unregister_passive_effect
            unregister_passive_effect(active_id)
        except Exception:
            pass

    _save_data(data)

    return {
        "item_id": active_id,
        "old_durability": old_durability,
        "new_durability": new_durability,
        "broken": broke,
    }


def _calc_sell_price(price: int, durability: int, max_durability: int,
                     purchased_at: float) -> int:
    """Tính giá bán lại dựa trên khấu hao."""
    if price <= 0:
        return 0
    durability_pct = durability / max_durability if max_durability > 0 else 0
    durability_lost_pct = 1.0 - durability_pct

    # Khấu hao theo thời gian (mỗi ngày mất thêm 0.1%)
    age_days = (time.time() - purchased_at) / 86400
    time_depr = min(0.3, age_days * 0.001)

    depreciation = (SELL_DEPRECIATION_NEW
                    + durability_lost_pct * SELL_DEPRECIATION_PER_DURABILITY_LOST * 100
                    + time_depr)
    depreciation = min(0.9, depreciation)  # Tối đa 90% khấu hao
    sell_price = int(price * (1.0 - depreciation))
    return max(0, sell_price)


def start_repair(item_id: str) -> dict:
    """Bắt đầu sửa chữa tech item."""
    data = _get_data()
    tech_lab = data.get("tech_lab", {})
    info = tech_lab.get(item_id)
    if not info:
        return {"ok": False, "error": "Tech item không tồn tại."}

    if info.get("durability") >= info.get("max_durability", DEFAULT_DURABILITY):
        return {"ok": False, "error": "Tech item vẫn còn độ bền tốt, không cần sửa."}

    if info.get("in_repair"):
        return {"ok": False, "error": "Tech item đang được sửa chữa."}

    from .shop_data import get_items_map
    item_data = get_items_map().get(item_id, {})
    price = item_data.get("price", 0)

    repair_cost = max(50000, int(price * REPAIR_COST_RATIO))
    repair_duration = REPAIR_DURATION

    from .balance import get_balance, set_balance_and_log
    bal = get_balance()
    if bal < repair_cost:
        return {"ok": False, "error": f"Không đủ tiền sửa! Cần {repair_cost:,} VND.".replace(",", ".")}

    new_bal = bal - repair_cost
    set_balance_and_log(new_bal, "purchase", -repair_cost, f"Sửa chữa tech: {item_data.get('name', item_id)}")

    info["in_repair"] = True
    info["repair_until"] = time.time() + repair_duration
    info["durability"] = 0  # tạm thời = 0 trong lúc sửa

    # Nếu đang active thì deactivate
    if data.get("active_tech_id") == item_id:
        data["active_tech_id"] = None
        try:
            from .item_effects import unregister_passive_effect
            unregister_passive_effect(item_id)
        except Exception:
            pass

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
    """Bảo dưỡng tech item định kỳ."""
    data = _get_data()
    tech_lab = data.get("tech_lab", {})
    info = tech_lab.get(item_id)
    if not info:
        return {"ok": False, "error": "Tech item không tồn tại."}

    if not info.get("maintenance_due"):
        return {"ok": False, "error": "Tech item chưa cần bảo dưỡng."}

    if info.get("in_repair"):
        return {"ok": False, "error": "Tech item đang được sửa chữa, không thể bảo dưỡng."}

    from .shop_data import get_items_map
    item_data = get_items_map().get(item_id, {})
    price = item_data.get("price", 0)

    cost = max(20000, int(price * MAINTENANCE_COST_RATIO))

    from .balance import get_balance, set_balance_and_log
    bal = get_balance()
    if bal < cost:
        return {"ok": False, "error": f"Không đủ tiền bảo dưỡng! Cần {cost:,} VND.".replace(",", ".")}

    new_bal = bal - cost
    set_balance_and_log(new_bal, "purchase", -cost, f"Bảo dưỡng tech: {item_data.get('name', item_id)}")

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
        "item_name": item_data.get("name", item_id),
    }


def sell_tech(item_id: str) -> dict:
    """Bán tech item."""
    data = _get_data()
    tech_lab = data.get("tech_lab", {})
    info = tech_lab.get(item_id)
    if not info:
        return {"ok": False, "error": "Tech item không tồn tại."}

    if info.get("in_repair"):
        if time.time() < info.get("repair_until", 0):
            return {"ok": False, "error": "Tech item đang sửa chữa, không thể bán."}

    from .shop_data import get_items_map
    item_data = get_items_map().get(item_id, {})
    price = item_data.get("price", 0)

    max_durability = info.get("max_durability", DEFAULT_DURABILITY)
    durability = info.get("durability", 0)
    purchased_at = info.get("purchased_at", time.time())

    sell_price = _calc_sell_price(price, durability, max_durability, purchased_at)
    depreciation_pct = round((1.0 - sell_price / price) * 100, 1) if price > 0 else 0

    # Nếu đang active thì deactivate
    if data.get("active_tech_id") == item_id:
        data["active_tech_id"] = None
        try:
            from .item_effects import unregister_passive_effect
            unregister_passive_effect(item_id)
        except Exception:
            pass

    # Xoá khỏi tech lab
    del tech_lab[item_id]
    _save_data(data)

    # Xoá khỏi inventory
    try:
        from .inventory import remove_from_inventory
        remove_from_inventory(item_id)
    except Exception:
        pass

    # Cộng tiền
    from .balance import get_balance, set_balance_and_log
    new_bal = get_balance() + sell_price
    set_balance_and_log(new_bal, "purchase", sell_price,
                        f"Bán tech: {item_data.get('name', item_id)}")

    return {
        "ok": True,
        "sell_price": sell_price,
        "depreciation_pct": depreciation_pct,
        "item_name": item_data.get("name", item_id),
    }


def get_repair_cost_preview(item_id: str) -> dict:
    """Xem trước chi phí sửa chữa."""
    data = _get_data()
    tech_lab = data.get("tech_lab", {})
    info = tech_lab.get(item_id)
    if not info:
        return {"ok": False, "error": "Tech item không tồn tại."}

    from .shop_data import get_items_map
    item_data = get_items_map().get(item_id, {})
    price = item_data.get("price", 0)

    cost = max(50000, int(price * REPAIR_COST_RATIO))
    return {
        "ok": True,
        "cost": cost,
        "duration_s": REPAIR_DURATION,
        "duration_str": "1 giờ",
        "item_name": item_data.get("name", item_id),
    }
