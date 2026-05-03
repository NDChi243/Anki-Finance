# -*- coding: utf-8 -*-
"""
inventory.py — Hệ thống inventory & slot limits (v2.0)
======================================================
- Quản lý danh sách item trong kho
- Giới hạn số lượng item dựa trên nhà ở + item bonus
- Garage riêng cho xe (xem vehicle_system.py)
"""

from .config import CONFIG_KEY_INVENTORY
from ._safe_config import cfg_list, cfg_set

# Base slots mặc định
BASE_INVENTORY_SLOTS = 50


def get_inventory() -> list:
    return cfg_list(CONFIG_KEY_INVENTORY, [])


def get_max_inventory_slots() -> int:
    """
    Tính tổng số slot tối đa.
    = base + bonus từ housing + bonus từ passive items.
    """
    slots = BASE_INVENTORY_SLOTS

    # Bonus từ housing
    try:
        from .housing_residence import get_residence
        res = get_residence()
        if res:
            rid = res.get("id", "")
            if rid == "villa":
                slots += 100
            elif rid == "townhouse":
                slots += 60
            elif rid == "apartment_std":
                slots += 40
            elif rid == "apartment_mini":
                slots += 20
            elif rid == "room_ktx":
                slots += 10
    except Exception:
        pass

    # Bonus từ passive effects (inventory_capacity)
    try:
        from .item_effects import get_all_passive_effects
        passive = get_all_passive_effects()
        slots += int(passive.get("inventory_capacity", 0))
    except Exception:
        pass

    return slots


def get_used_slots() -> int:
    """Trả về số slot đã dùng."""
    return len(get_inventory())


def get_inventory_slots_info() -> dict:
    """Trả về thông tin slot cho UI."""
    return {
        "used": get_used_slots(),
        "max": get_max_inventory_slots(),
        "remaining": get_max_inventory_slots() - get_used_slots(),
    }


def can_add_to_inventory() -> bool:
    """Kiểm tra còn slot trống không."""
    return get_used_slots() < get_max_inventory_slots()


def add_to_inventory(item_id: str):
    """
    Thêm item vào kho.
    LƯU Ý: Không kiểm tra slot ở đây để tránh break các module khác.
    Việc kiểm tra slot được thực hiện ở web_bridge.buyItem() và các nơi gọi.
    """
    inv = get_inventory()
    inv.append(item_id)
    cfg_set(CONFIG_KEY_INVENTORY, inv)


def has_item(item_id: str) -> bool:
    return item_id in get_inventory()


def count_item(item_id: str) -> int:
    return get_inventory().count(item_id)


def remove_from_inventory(item_id: str) -> bool:
    """Xoá 1 item khỏi inventory. Trả về True nếu thành công."""
    inv = get_inventory()
    if item_id in inv:
        inv.remove(item_id)
        cfg_set(CONFIG_KEY_INVENTORY, inv)
        # Đồng thời xoá passive effect nếu có
        try:
            from .item_effects import unregister_passive_effect
            unregister_passive_effect(item_id)
        except Exception:
            pass
        return True
    return False


def get_unique_items() -> list:
    """Trả về danh sách item_id duy nhất trong kho."""
    from collections import Counter
    return list(Counter(get_inventory()).keys())
