# -*- coding: utf-8 -*-
"""
inventory.py — Hệ thống inventory & slot limits (v2.0)
======================================================
- Quản lý danh sách item trong kho
- Giới hạn số lượng item dựa trên nhà ở + item bonus
- Garage riêng cho xe (xem vehicle_system.py)
"""

from .config import CONFIG_KEY_INVENTORY
from .logger import get_logger
logger = get_logger(__name__)
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
    except Exception as e:
        logger.debug("get_max_inventory_slots: housing bonus — %s", e)

    # Bonus từ passive effects (inventory_capacity)
    try:
        from .item_effects import get_all_passive_effects
        passive = get_all_passive_effects()
        slots += int(passive.get("inventory_capacity", 0))
    except Exception as e:
        logger.debug("get_max_inventory_slots: passive effects — %s", e)

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
        except Exception as e:
            logger.debug("remove_from_inventory: unregister_passive_effect — %s", e)
        return True
    return False


def get_unique_items() -> list:
    """Trả về danh sách item_id duy nhất trong kho."""
    from collections import Counter
    return list(Counter(get_inventory()).keys())


# ─── Unified Inventory API ──────────────────────────────────────

def get_categorized_inventory() -> dict:
    """
    Trả về inventory đã phân loại: items thường, xe (garage), tech.
    Dùng cho UI Inventory unified với sub-tabs.
    """
    from .shop_data import load_shop_items, get_items_map
    from .gui.image_manager import get_image_url
    from .item_effects import get_item_effects, format_item_effects_html, get_item_effect_descriptions

    inv = get_inventory()
    items_map = get_items_map()
    
    # Lấy freshness info
    try:
        from .food_effects import _get_fresh, get_effect_for_item, _get_item_category
    except ImportError:
        _get_fresh = lambda: {}
        get_effect_for_item = lambda iid, item: {}
        _get_item_category = lambda iid, item: ""

    fresh = _get_fresh()
    
    # Đếm số lượng mỗi item trong inventory
    counts = {}
    for iid in inv:
        counts[iid] = counts.get(iid, 0) + 1

    # Freshness slots by item_id
    slots_by_item = {}
    for sid, info in fresh.items():
        iid = info.get("item_id", "")
        if iid:
            slots_by_item.setdefault(iid, []).append(sid)

    # Phân loại
    regular_items = []
    vehicle_ids = set()
    tech_ids = set()
    
    # Lấy danh sách xe và tech từ garage/tech_lab
    try:
        from .vehicle_system import _get_data as _get_vehicle_data
        vdata = _get_vehicle_data()
        vehicle_ids = set(vdata.get("garage", {}).keys())
    except Exception:
        pass
    
    try:
        from .tech_system import _get_data as _get_tech_data
        tdata = _get_tech_data()
        tech_ids = set(tdata.get("tech_lab", {}).keys())
    except Exception:
        pass

    now = __import__('time').time()

    for iid, qty in counts.items():
        item = items_map.get(iid)
        if not item:
            continue

        # Nếu là xe hoặc tech, skip (sẽ lấy từ garage/tech_lab API riêng)
        if iid in vehicle_ids or iid in tech_ids:
            continue

        entry = {**item, "quantity": qty}
        url = get_image_url(iid)
        entry["image_url"] = url if url else ""

        item_cat = _get_item_category(iid, item) if callable(_get_item_category) else ""
        if item_cat in ("food", "drink") or item_cat == "study":
            effect = get_effect_for_item(iid, item) if callable(get_effect_for_item) else {}
            entry["effect"] = effect
            entry["is_food"] = (item_cat in ("food", "drink"))
            entry["is_study"] = (item_cat == "study")
            entry["expire_h"] = item.get("expire_h", effect.get("expire_h", 24) if effect else 24)

            real_slots = slots_by_item.get(iid, [])
            entry["food_slots"] = []
            for sid in real_slots:
                finfo = fresh[sid]
                buy_ts = float(finfo.get("buy_ts", now))
                expire_h = float(finfo.get("expire_h", 24))
                elapsed_h = (now - buy_ts) / 3600
                remaining_h = max(0.0, expire_h - elapsed_h)
                fresh_pct = round(remaining_h / expire_h * 100, 1) if expire_h > 0 else 0
                entry["food_slots"].append({
                    "slot_id": sid,
                    "remaining_h": round(remaining_h, 2),
                    "fresh_pct": fresh_pct,
                })
            entry["active_slot"] = real_slots[0] if real_slots else ""
        else:
            entry["is_food"] = False
            entry["is_study"] = False
            entry["food_slots"] = []
            entry["active_slot"] = ""
            try:
                eff_list = get_item_effects(item)
                if eff_list:
                    entry["effect_descriptions"] = get_item_effect_descriptions(item)
                    entry["effect_html"] = format_item_effects_html(eff_list)
            except Exception:
                pass
        
        # Thêm item_type để phân loại
        entry["item_type"] = _categorize_item_type(item, item_cat)
        regular_items.append(entry)

    return {
        "regular_items": regular_items,
        "total_count": len(inv),
        "unique_count": len(counts),
    }


def _categorize_item_type(item: dict, item_cat: str = "") -> str:
    """Phân loại item type dựa trên category và effect."""
    cat = (item.get("category", "") + item_cat).lower()
    
    if "ẩm thực" in cat or "đồ uống" in cat or item_cat in ("food", "drink"):
        return "food"
    if "vật phẩm học tập" in cat or "study" in cat or item_cat == "study":
        return "study"
    if "vật phẩm tài chính" in cat or "finance" in cat:
        return "finance"
    if "xa xỉ" in cat or "luxury" in cat:
        return "luxury"
    if "du lịch" in cat or "travel" in cat:
        return "travel"
    if "điện tử" in cat or "electronics" in cat:
        return "electronics"
    if "sức khỏe" in cat or "health" in cat:
        return "health"
    return "other"


def get_inventory_slots_used() -> int:
    """Trả về số slot inventory đã dùng."""
    return len(get_inventory())
