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

# Category shop items chỉ hiển thị / cho phép mua trong Full Mode
ADVANCED_CATEGORIES = {
    "🚗 Showroom xe",
    "💻 Cửa hàng đồ công nghệ",
    "💎 Cửa hàng hàng hiệu",
    "🏠 Thị trường bất động sản",
    "🪙 Sàn Crypto",
    "🛡️ Bảo hiểm",
    "🏦 Vật phẩm tài chính",
    "🎓 Vật phẩm học tập",
}

# Hệ số nhân reward/EXP/KN trong Simple Mode
# Bù cho việc bỏ Energy System, Living Costs, Inactivity Penalty, Tax (basic)
SIMPLE_MODE_MULTIPLIER = 0.5

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
