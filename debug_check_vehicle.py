# -*- coding: utf-8 -*-
"""
Debug script cho lỗi "xe mua về biến mất"
Cách dùng: Copy toàn bộ file này vào Anki Debug Console (Tools > Debug Console) và chạy.
"""

import json, time, sys, os

print("=" * 60)
print("🔍 DEBUG: XE MUA VỀ BIẾN MẤT")
print("=" * 60)

# ─── 1. Kiểm tra config key ───
print("\n📌 1. KIỂM TRA CONFIG KEY 'anki_tycoon_vehicle_data'")
try:
    from aqt import mw
    raw = mw.col.get_config("anki_tycoon_vehicle_data")
    if raw is None:
        print("   ❌ Config key KHÔNG TỒN TẠI (None)")
    else:
        print(f"   ✅ Config key tồn tại")
        print(f"   Type: {type(raw).__name__}")
        if isinstance(raw, dict):
            garage = raw.get("garage", {})
            print(f"   Garage keys: {list(garage.keys())}")
            print(f"   Số xe trong garage: {len(garage)}")
            active = raw.get("active_vehicle_id")
            print(f"   Active vehicle: {active}")
            for vid, vdata in garage.items():
                print(f"     - {vid}: durab={vdata.get('durability','?')}/{vdata.get('max_durability','?')}, "
                      f"group={vdata.get('vehicle_group','?')}, seized={vdata.get('seized',False)}")
        else:
            print(f"   ⚠️  Config value KHÔNG phải dict! Giá trị: {raw!r}")
except Exception as e:
    print(f"   ❌ Lỗi đọc config: {e}")

# ─── 2. Kiểm tra cache ───
print("\n📌 2. KIỂM TRA CACHE _safe_config")
try:
    from ._safe_config import _config_cache, _cache_get, _cache_invalidate
    entry = _config_cache.get("anki_tycoon_vehicle_data")
    if entry is None:
        print("   ℹ️  Cache: không có entry cho vehicle data")
    else:
        val, ts = entry
        age = time.time() - ts
        print(f"   ✅ Cache HIT, age={age:.1f}s")
        if isinstance(val, dict):
            g = val.get("garage", {})
            print(f"   Cache garage có {len(g)} xe: {list(g.keys())}")
        else:
            print(f"   ⚠️  Cache value type={type(val).__name__}: {val!r}")
except Exception as e:
    print(f"   ❌ Lỗi đọc cache: {e}")

# ─── 3. Kiểm tra shop_items.json ───
print("\n📌 3. KIỂM TRA shop_items.json")
try:
    addon_dir = os.path.dirname(__file__)
    json_path = os.path.join(addon_dir, "shop_items.json")
    with open(json_path, "r", encoding="utf-8") as f:
        items = json.load(f)
    print(f"   Total items: {len(items)}")
    vehicles = [it for it in items if it.get("vehicle_group")]
    print(f"   Vehicles (có vehicle_group): {len(vehicles)}")
    no_vg = [it for it in items if "xe" in it.get("category","").lower() and not it.get("vehicle_group")]
    if no_vg:
        for it in no_vg:
            print(f"   ❌ {it.get('id','?')} — category='{it.get('category','')}' nhưng THIẾU vehicle_group!")
    else:
        print(f"   ✅ Tất cả items có category 'xe' đều có vehicle_group")
    # Lấy 3 xe mẫu
    for v in vehicles[:3]:
        print(f"   - {v.get('id','?')}: vehicle_group='{v.get('vehicle_group')}', price={v.get('price',0)}")
except Exception as e:
    print(f"   ❌ Lỗi đọc shop_items.json: {e}")

# ─── 4. Kiểm tra load_shop_items() ───
print("\n📌 4. KIỂM TRA load_shop_items()")
try:
    from .shop_data import load_shop_items
    items2 = load_shop_items(force_reload=True)
    print(f"   ✅ load_shop_items() trả về {len(items2)} items")
    vehicles2 = [it for it in items2 if it.get("vehicle_group")]
    print(f"   Vehicles từ load_shop_items: {len(vehicles2)}")
except Exception as e:
    print(f"   ❌ Lỗi load_shop_items: {e}")

# ─── 5. Test register_vehicle với item mẫu ───
print("\n📌 5. TEST: register_vehicle() với item mẫu")
try:
    from .vehicle_system import register_vehicle, _get_data, _save_data
    from ._safe_config import cfg_dict, cfg_set
    
    test_item_id = "_debug_test_car_001"
    test_item = {
        "id": test_item_id,
        "name": "Debug Test Car",
        "vehicle_group": "Ô tô",
        "price": 10000000,
        "category": "🚗 Showroom xe",
    }
    
    # Đọc dữ liệu hiện tại
    before_data = _get_data()
    before_garage_size = len(before_data.get("garage", {}))
    print(f"   Garage TRƯỚC khi test: {before_garage_size} xe")
    
    # Đăng ký xe test
    if test_item_id in before_data.get("garage", {}):
        print(f"   ⚠️  Xe test ĐÃ tồn tại, sẽ xoá trước...")
        del before_data["garage"][test_item_id]
        _save_data(before_data)
        print(f"   ✅ Đã xoá xe test cũ")
    
    print(f"   🔄 Đang gọi register_vehicle('{test_item_id}', test_item)...")
    register_vehicle(test_item_id, test_item)
    print(f"   ✅ register_vehicle() đã chạy xong")
    
    # Kiểm tra lại
    after_data = _get_data()
    after_garage_size = len(after_data.get("garage", {}))
    print(f"   Garage SAU khi test: {after_garage_size} xe")
    
    if test_item_id in after_data.get("garage", {}):
        print(f"   ✅ Xe test ĐÃ có trong garage!")
    else:
        print(f"   ❌ Xe test KHÔNG có trong garage!")
    
    # Xoá xe test
    g = after_data.get("garage", {})
    if test_item_id in g:
        del g[test_item_id]
        after_data["garage"] = g
        _save_data(after_data)
        print(f"   🧹 Đã dọn xe test")
    
except Exception as e:
    import traceback
    print(f"   ❌ Lỗi: {e}")
    traceback.print_exc()

# ─── 6. Kiểm tra batch mode ───
print("\n📌 6. KIỂM TRA BATCH MODE")
try:
    from ._safe_config import _batch_active, _batch_writes
    print(f"   Batch active: {_batch_active}")
    print(f"   Batch writes keys: {list(_batch_writes.keys())}")
except Exception as e:
    print(f"   ❌ Lỗi: {e}")

# ─── 7. Kiểm tra vehicle_system._get_data() ───
print("\n📌 7. KIỂM TRA _get_data() TRỰC TIẾP")
try:
    from .vehicle_system import _get_data
    data = _get_data()
    print(f"   _get_data() trả về dict keys: {list(data.keys())}")
    print(f"   Garage size: {len(data.get('garage', {}))}")
    print(f"   Active vehicle: {data.get('active_vehicle_id')}")
    print(f"   Maintenance due: {list(data.get('maintenance_due', {}).keys())}")
except Exception as e:
    print(f"   ❌ Lỗi: {e}")

print("\n" + "=" * 60)
print("✅ DEBUG COMPLETE")
print("=" * 60)
