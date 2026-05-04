# -*- coding: utf-8 -*-

import json
import os
import time

from .logger import get_logger
logger = get_logger(__name__)

# ── In-memory cache cho shop items ──────────────────────────────
# Tránh đọc file JSON từ disk mỗi lần gọi (có thể 5-10 lần/tab)
_shop_cache = None
_shop_cache_ts = 0.0
_SHOP_CACHE_TTL = 60.0  # Cache 60 giây, đủ cho 1 phiên làm việc


def load_shop_items(force_reload: bool = False) -> list:
    """Load shop items từ JSON, có cache trong memory.
    
    Args:
        force_reload: Bỏ qua cache, load lại từ disk.
    """
    global _shop_cache, _shop_cache_ts
    now = time.time()
    if not force_reload and _shop_cache is not None and (now - _shop_cache_ts) < _SHOP_CACHE_TTL:
        logger.debug("load_shop_items: dùng cache (%.1fs old)", now - _shop_cache_ts)
        return _shop_cache

    addon_dir = os.path.dirname(__file__)  # root addon
    json_path = os.path.join(addon_dir, "shop_items.json")
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            raw_items = json.load(f)
            logger.info("load_shop_items: đã load %d items từ shop_items.json", len(raw_items))
            
            # --- AUTO-FIX BẮT ĐẦU: Tự động thêm vehicle_group nếu file JSON bị thiếu ---
            fix_count = 0
            for item in raw_items:
                category = item.get("category", "").lower()
                # Nhận diện xe qua category (ví dụ: "🚗 showroom xe")
                if "xe" in category and "vehicle_group" not in item:
                    # Gán mặc định là Ô tô để hệ thống đăng ký vào Garage thay vì Inventory
                    item["vehicle_group"] = "Ô tô"
                    fix_count += 1
            if fix_count:
                logger.warning("load_shop_items: auto-fix đã thêm vehicle_group cho %d item", fix_count)
            # --- AUTO-FIX KẾT THÚC ---

            _shop_cache = raw_items
            _shop_cache_ts = now
            return _shop_cache
    except Exception as e:
        logger.warning("load_shop_items: lỗi đọc file shop_items.json: %s", e)
        result = _default_items()
        _shop_cache = result
        _shop_cache_ts = now
        return result


def get_item(item_id: str) -> dict | None:
    """Lấy 1 item từ shop theo id, không cần load lại toàn bộ."""
    items = load_shop_items()
    for item in items:
        if item.get("id") == item_id:
            return item
    return None


def get_items_map() -> dict:
    """Trả về dict {item_id: item} để tra cứu nhanh."""
    items = load_shop_items()
    return {i["id"]: i for i in items}


def _default_items() -> list:
    return [
        {"id": "coffee",        "name": "Cà phê Starbucks",    "description": "Uống để tỉnh học bài",            "category": "Đồ ăn uống",  "price": 85000,         "emoji": "☕"},
        {"id": "boba",          "name": "Trà sữa Gong Cha",    "description": "Topping đầy đủ, size L",           "category": "Đồ ăn uống",  "price": 65000,         "emoji": "🧋"},
        {"id": "airpods",       "name": "AirPods Pro 2",       "description": "Chống ồn chủ động thế hệ 2",      "category": "Điện tử",     "price": 6000000,       "emoji": "🎧"},
        {"id": "ps5",           "name": "PlayStation 5",       "description": "Console thế hệ mới của Sony",     "category": "Điện tử",     "price": 15000000,      "emoji": "🎮"},
        {"id": "iphone16",      "name": "iPhone 16 Pro Max",   "description": "8GB RAM / 256GB — Titanium Black", "category": "Điện tử",     "price": 40000000,      "emoji": "📱"},
        {"id": "macbook_m3",    "name": "MacBook Pro M3",      "description": "16GB RAM / 512GB SSD",            "category": "Điện tử",     "price": 45000000,      "emoji": "💻"},
        {"id": "vacation_dalat","name": "Du lịch Đà Lạt",      "description": "Gói 3N2Đ, khách sạn 4 sao",      "category": "Du lịch",     "price": 3000000,       "emoji": "🌸"},
        {"id": "vacation_bali", "name": "Du lịch Bali",        "description": "Gói 5N4Đ, villa riêng",           "category": "Du lịch",     "price": 25000000,      "emoji": "🏝️"},
        # ── Xe cộ (fallback) ──────────────────────────────────────
        # vehicle_group bắt buộc để xe được đăng ký vào garage, không vào inventory
        {"id": "honda_civic",   "name": "Honda Civic 2024",    "description": "Sedan hạng C, 1.5L Turbo",        "category": "🚗 Showroom xe", "price": 800000000,     "emoji": "🚗",  "vehicle_group": "Ô tô",      "car_type": "Sedan"},
        {"id": "tesla_model3",  "name": "Tesla Model 3",       "description": "Xe điện, phạm vi 570km",          "category": "🚗 Showroom xe", "price": 1500000000,    "emoji": "⚡",  "vehicle_group": "Xe điện",   "car_type": "Sedan", "fuel_type": "electric"},
        {"id": "rolex",         "name": "Rolex Submariner",    "description": "Đồng hồ luxury huyền thoại",      "category": "Xa xỉ phẩm", "price": 400000000,     "emoji": "⌚"},
        {"id": "lamborghini",   "name": "Lamborghini Huracán", "description": "Siêu xe V10, 630 mã lực",         "category": "🚗 Showroom xe", "price": 15000000000,   "emoji": "🏎️", "vehicle_group": "Ô tô",      "car_type": "Supercar"},
    ]