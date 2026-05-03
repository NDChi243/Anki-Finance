# -*- coding: utf-8 -*-
"""
Script dịch tên hiệu ứng và mô tả từ tiếng Anh sang tiếng Việt
trong shop_items.json, đảm bảo không làm hỏng cấu trúc JSON.
"""
import json
import re
import shutil
from collections import OrderedDict

# ─── Bảng dịch tên hiệu ứng (effect name) ─────────────────────────────
NAME_TRANSLATIONS = OrderedDict([
    # Caffeine
    ("Caffeine Burst ☕", "Bùng Nổ Caffeine ☕"),
    ("Caffeine Crash ☕", "Sụt Giảm Caffeine ☕"),
    ("Caffeine Jitter ☕", "Bồn Chồn Caffeine ☕"),
    # Sugar / Đường
    ("Sugar Rush 🦹", "Phấn Khích Đường 🦹"),
    ("Sugar Haze 🥣", "Mơ Màng Sau Đường 🥣"),
    ("Sugar Haze 🧃", "Mơ Màng Sau Đường 🧃"),
    ("Sugar Crash 🧊", "Tụt Đường 🧊"),
    ("Sugar Crash 🧋", "Tụt Đường 🧋"),
    # Grease / Dầu mỡ
    ("Grease Tax 🍔", "Mệt Dầu Mỡ 🍔"),
    ("Grease Tax 🍗", "Mệt Dầu Mỡ 🍗"),
    ("Grease Tax 🍛", "Mệt Dầu Mỡ 🍛"),
    ("Grease Tax 🛵", "Mệt Dầu Mỡ 🛵"),
    ("Grease Tax 🥞", "Mệt Dầu Mỡ 🥞"),
    ("Grease Tax 🥣", "Mệt Dầu Mỡ 🥣"),
    # Protein / Đạm
    ("Protein Overload 🥘", "Quá Tải Đạm 🥘"),
    ("Protein Overload 🥩", "Quá Tải Đạm 🥩"),
    # Satiety / No
    ("Satiety Drag 🥖", "Trì Trệ No 🥖"),
    ("Satiety Drain 🍗", "Hao Hụt No 🍗"),
    ("Satiety Drain 🍜", "Hao Hụt No 🍜"),
    ("Satiety Drain 🫓", "Hao Hụt No 🫓"),
    ("Satiety Fog 🍜", "Mơ Màng No 🍜"),
    ("Satiety Fog 🏺", "Mơ Màng No 🏺"),
    ("Satiety Fog 🥗", "Mơ Màng No 🥗"),
    # Food Coma / Buồn ngủ sau ăn
    ("Food Coma 🍚", "Buồn Ngủ No 🍚"),
    ("Food Coma 🥟", "Buồn Ngủ No 🥟"),
    # Stomach / Bụng
    ("Empty Stomach 🥚", "Bụng Rỗng 🥚"),
    ("Acid Drain 🍊", "Axit Dạ Dày 🍊"),
    ("Cold Drain 🥤", "Lạnh Bụng 🥤"),
    ("Digest Drain 🐌", "Khó Tiêu 🐌"),
    ("Diuretic Drain 🍵", "Lợi Tiểu 🍵"),
    ("Heat Drain 🦀", "Nóng Bụng 🦀"),
    ("Jaw Fatigue 🍘", "Mỏi Hàm 🍘"),
    # Digestive / Tiêu hóa
    ("Digestive Risk 🍣", "Rủi Ro Tiêu Hóa 🍣"),
    ("Raw Food Risk 🍣", "Nguy Cơ Đồ Sống 🍣"),
    # Fat / Béo
    ("Fat Fog 🥑", "Ngấy Béo 🥑"),
    # Spice / Cay
    ("Spice Tax 🍲", "Mệt Cay 🍲"),
    ("Spice Tax 🔥", "Mệt Cay 🔥"),
    ("Spice Tax 🫔", "Mệt Cay 🫔"),
    ("Spice Fog 🌶️", "Mờ Cay 🌶️"),
    ("Spice Fog 🫕", "Mờ Cay 🫕"),
    # Wine / Rượu
    ("Wine Haze 🥂", "Say Rượu 🥂"),
    # Matcha
    ("Matcha Calm 🍵", "Matcha Thư Thái 🍵"),
    ("Matcha Focus 🍵", "Matcha Tập Trung 🍵"),
    ("Matcha Shield 🍵", "Matcha Bảo Vệ 🍵"),
    # Night Owl
    ("Night Owl 🦉", "Cú Đêm 🦉"),
    # Boost / Focus in names (partial match handled separately)
    ("Cơm Tấm Boost 🍚", "Cơm Tấm Tăng Lực 🍚"),
    ("Bánh Xèo Focus 🥞", "Bánh Xèo Tập Trung 🥞"),
    ("Bánh Căn Focus 🥚", "Bánh Căn Tập Trung 🥚"),
    ("BBQ Feast 🥩", "BBQ Thịnh Soạn 🥩"),
    ("BBQ Power 🥩", "BBQ Tăng Lực 🥩"),
    ("Pizza Focus 🍕", "Pizza Tập Trung 🍕"),
    ("Pizza Power 🍕", "Pizza Tăng Lực 🍕"),
    ("Steak Energy 🥩", "Bít Tết Năng Lượng 🥩"),
    ("Steak Power 🥩", "Bít Tết Tăng Lực 🥩"),
    ("Prime Steak 🥩", "Bít Tết Hảo Hạng 🥩"),
    ("Super Boost 🚀", "Siêu Tăng Cường 🚀"),
    # Food items with English desc
    ("Vitamin Shield 🥤", "Khiên Vitamin 🥤"),
    ("Smoothie Vitamin 🥤", "Sinh Tố Vitamin 🥤"),
    ("Smoothie Năng Lượng 🥤", "Sinh Tố Năng Lượng 🥤"),
    ("Bơ Năng Lượng 🥑", "Bơ Năng Lượng 🥑"),
    ("Energy Burst 🏺", "Năng Lượng Bùng Nổ 🏺"),
    ("Energy Burst 🔥", "Năng Lượng Bùng Nổ 🔥"),
    ("Energy Burst 🛵", "Năng Lượng Bùng Nổ 🛵"),
    ("Energy Burst 🦑", "Năng Lượng Bùng Nổ 🦑"),
    ("Energy Burst 🧊", "Năng Lượng Bùng Nổ 🧊"),
    ("Energy Burst 🫕", "Năng Lượng Bùng Nổ 🫕"),
    ("Energy Vial ⚡", "Bình Năng Lượng ⚡"),
    ("Focus Potion 🧪", "Thuốc Tập Trung 🧪"),
    ("Extend Aura 🧪", "Hào Quang Kéo Dài 🧪"),
    ("Concentration Aura 🔮", "Hào Quang Tập Trung 🔮"),
    ("Preservation Field ⚡", "Trường Bảo Tồn ⚡"),
    ("Memory Anchor ⚓", "Mỏ Neo Ký Ức ⚓"),
    ("Memory Elixir ✨", "Thuốc Ký Ức ✨"),
    ("Sharp Cards 🃏", "Thẻ Sắc Bén 🃏"),
    ("Ease Patch 🧠", "Miếng Dán Ease 🧠"),
    ("Easy Combo 🎯", "Liên Hoàn Easy 🎯"),
    ("Again Shield 🛡️", "Khiên Again 🛡️"),
    ("Scheduler Insight 🧠", "Thấu Hiểu Lịch Trình 🧠"),
    ("Scheduler Patch 🧠", "Miếng Dán Lịch Trình 🧠"),
    ("Weekly Wisdom 📚", "Trí Tuệ Hàng Tuần 📚"),
    ("Study Dashboard 🖥️", "Bảng Điều Khiển Học 📊"),
    ("Stock Analysis 📊", "Phân Tích Chứng Khoán 📊"),
    ("Stock Pro 📊", "Chuyên Gia Chứng Khoán 📊"),
    ("eFlashcard 🔄", "Thẻ Ghi Nhớ Điện Tử 🔄"),
    ("Course Income 📚", "Thu Nhập Khóa Học 📚"),
    ("Investment Course 📚", "Khóa Học Đầu Tư 📚"),
    ("Handheld Gaming 🎮", "Chơi Game Cầm Tay 🎮"),
    ("Multitask 🖥️", "Đa Nhiệm 🖥️"),
    ("Infinite Canvas 👓", "Vải Vô Hạn 👓"),
    ("Spatial Computing 👓", "Máy Tính Không Gian 👓"),
    ("Vision OS 👓", "Vision OS 👓"),
    ("Deep Work Mode 💻", "Chế Độ Làm Việc Sâu 💻"),
    ("Desk Flow 💻", "Luồng Làm Việc 💻"),
    ("Dual Screen 🖥️", "Màn Hình Kép 🖥️"),
    ("Dual Workflow 🖥️", "Luồng Công Việc Kép 🖥️"),
    ("Mesh Network 🌐", "Mạng Lưới 🌐"),
    ("WiFi 7 Speed 🌐", "Tốc Độ WiFi 7 🌐"),
    ("Smart Interest 📒", "Lãi Suất Thông Minh 📒"),
    ("Smart Savings 📒", "Tiết Kiệm Thông Minh 📒"),
    ("Smart Pill 💊", "Thuốc Thông Minh 💊"),
])

# ─── Bảng dịch mô tả (desc) - thay thế từ/cụm từ tiếng Anh ──────────
DESC_REPLACEMENTS = OrderedDict([
    # stamina -> thể lực
    ("-1 stamina", "-1 thể lực"),
    ("-{value} stamina", "-{value} thể lực"),
    ("+{value} stamina", "+{value} thể lực"),
    # boost -> tăng cường (only standalone uses, not in "Boost" as name)
    # energy -> năng lượng
    # recovery -> hồi phục
    # stock -> chứng khoán
])


def fix_desc(desc: str) -> str:
    """Sửa các từ tiếng Anh còn sót trong desc."""
    if not desc:
        return desc
    replacements = [
        ("sugar crash", "tụt đường"),
        ("Sugar crash", "Tụt đường"),
    ]
    for old, new in replacements:
        if old in desc:
            desc = desc.replace(old, new)
    return desc


def translate_effect_name(name: str) -> str:
    """Dịch tên hiệu ứng nếu có trong bảng."""
    if not name:
        return name
    if name in NAME_TRANSLATIONS:
        return NAME_TRANSLATIONS[name]
    return name


def main():
    # Đọc file
    with open('shop_items.json', 'r', encoding='utf-8') as f:
        items = json.load(f)

    changes = 0
    name_changes = 0
    desc_changes = 0

    for item in items:
        effects = []
        if 'effect_list' in item and isinstance(item['effect_list'], list):
            effects = item['effect_list']
        elif 'effect' in item and isinstance(item['effect'], dict):
            effects = [item['effect']]

        for eff in effects:
            # Dịch tên
            old_name = eff.get('name', '')
            new_name = translate_effect_name(old_name)
            if old_name and new_name != old_name:
                eff['name'] = new_name
                name_changes += 1
                changes += 1
                print(f"  Đổi tên: '{old_name}' -> '{new_name}'")

            # Dịch desc
            old_desc = eff.get('desc', '')
            new_desc = fix_desc(old_desc)
            if old_desc and new_desc != old_desc:
                eff['desc'] = new_desc
                desc_changes += 1
                changes += 1
                print(f"  Sửa desc: '{old_desc}' -> '{new_desc}'")

    # Ghi lại file
    with open('shop_items.json', 'w', encoding='utf-8') as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Hoàn thành! Đã thực hiện {changes} thay đổi:")
    print(f"   - Tên hiệu ứng: {name_changes}")
    print(f"   - Mô tả: {desc_changes}")


if __name__ == '__main__':
    main()
