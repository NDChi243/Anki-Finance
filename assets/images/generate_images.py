# -*- coding: utf-8 -*-
"""Script generate ảnh SVG placeholder cho tất cả item trong shop_items.json"""
import json, os

# Đọc trực tiếp từ file JSON
# Script ở assets/images/, cần lên 3 cấp để tới root addon
ADDON_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
JSON_PATH = os.path.join(ADDON_DIR, "shop_items.json")
OUT = os.path.dirname(__file__)

with open(JSON_PATH, "r", encoding="utf-8") as f:
    ITEMS = json.load(f)

SVG_TPL = '''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400" viewBox="0 0 400 400">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{c1}"/>
      <stop offset="100%" style="stop-color:{c2}"/>
    </linearGradient>
    <linearGradient id="shine" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#ffffff15"/>
      <stop offset="100%" style="stop-color:#ffffff00"/>
    </linearGradient>
  </defs>
  <rect width="400" height="400" rx="20" fill="url(#bg)"/>
  <rect width="400" height="400" rx="20" fill="url(#shine)"/>
  <circle cx="200" cy="190" r="100" fill="#ffffff20" stroke="#ffffff30" stroke-width="2"/>
  <text x="200" y="165" text-anchor="middle" font-size="{sz}">{emoji}</text>
  <text x="200" y="315" text-anchor="middle" font-size="15" fill="#ffffffCC" font-family="sans-serif" font-weight="600">{name}</text>
  <text x="200" y="338" text-anchor="middle" font-size="11" fill="#ffffff99" font-family="sans-serif">{desc}</text>
  <text x="200" y="365" text-anchor="middle" font-size="13" fill="#ffffffBB" font-family="sans-serif" font-weight="500">{fmt}</text>
</svg>'''


def star_gradient(stars):
    m = {1: ("#f59e0b","#f97316"), 2: ("#10b981","#059669"),
         3: ("#3b82f6","#1d4ed8"), 4: ("#8b5cf6","#7c3aed"),
         5: ("#ef4444","#dc2626")}
    return m.get(stars, ("#6366f1","#8b5cf6"))


def cat_colors(cat, stars):
    if "đồ ăn" in cat:
        return star_gradient(stars) if stars else ("#f59e0b","#f97316")
    if "xe" in cat:
        return ("#3b82f6","#1d4ed8")
    if "công nghệ" in cat or "điện tử" in cat:
        return ("#6366f1","#4f46e5")
    if "hàng hiệu" in cat or "xa xỉ" in cat:
        return ("#f59e0b","#d97706")
    if "bất động" in cat:
        return ("#06b6d4","#0891b2")
    if "học tập" in cat:
        return ("#10b981","#047857")
    if "du lịch" in cat:
        return ("#ec4899","#be185d")
    if "ăn uống" in cat:
        return ("#f59e0b","#f97316")
    return ("#6366f1","#8b5cf6")


def fmt_price(p):
    if p >= 1_000_000_000:
        return f"{p/1_000_000_000:.1f}B"
    if p >= 1_000_000:
        return f"{p/1_000_000:.0f}M"
    if p >= 1_000:
        return f"{p//1000}.{p%1000//100}K"
    return f"{p}đ"


count = 0
for item in ITEMS:
    item_id = item.get("id", "")
    name = item.get("name", "")
    emoji = item.get("emoji", "📦")
    stars = item.get("stars", 0)
    cat = item.get("category", "")
    desc = item.get("description", "")[:40]
    price = item.get("price", 0)

    c1, c2 = cat_colors(cat, stars)
    sz = 80 if len(emoji) <= 2 else 64
    fmt = fmt_price(price)

    svg = SVG_TPL.format(c1=c1, c2=c2, emoji=emoji, name=name, desc=desc, sz=sz, fmt=fmt)

    path = os.path.join(OUT, f"{item_id}.svg")
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)
    count += 1
    print(f"  ✓ {item_id}.svg")

print(f"\n✅ Đã tạo {count} file ảnh SVG trong {OUT}")
