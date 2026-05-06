# -*- coding: utf-8 -*-

CONFIG_KEY_BALANCE      = "anki_tycoon_balance"
CONFIG_KEY_INVENTORY    = "anki_tycoon_inventory"
CONFIG_KEY_STATS        = "anki_tycoon_stats"
CONFIG_KEY_GAME_MODE    = "anki_tycoon_game_mode"

# ── Game Mode ──────────────────────────────────────────────────────
# "full"   = Chế độ đầy đủ — tất cả tính năng (Stocks, Crypto, Garage, BĐS, ...)
# "simple" = Chế độ đơn giản — chỉ giữ core tính năng học tập cơ bản
GAME_MODE_FULL   = "full"
GAME_MODE_SIMPLE = "simple"
DEFAULT_GAME_MODE = GAME_MODE_FULL

# Danh sách tab hiển thị ở mỗi chế độ
SIMPLE_TABS = {
    "dashboard", "shop", "inventory", "bank", "finance",
    "quests", "achievement", "settings", "knowledge",
}
# Tab nào bị ẩn trong Simple Mode
ADVANCED_TABS = {
    "realestate", "garage", "techlab",
    "stocks", "digital", "learning",
}

REWARD_MAP = {
    1: 500,     # Again — phí phục hồi kiến thức
    2: 15000,   # Hard — khuyến khích đối mặt kiến thức khó
    3: 10000,   # Good — trung bình
    4: 5000,    # Easy — dễ nên thưởng thấp
}

REWARD_LABELS = {
    1: "Again",
    2: "Hard",
    3: "Good",
    4: "Easy",
}
