# Kế hoạch phân chia Game Mode — Anki Finance

> **Mục tiêu:** Tách hệ thống thành 2 chế độ chơi riêng biệt — **Simple Mode** (Cơ bản) và **Full Mode** (Toàn diện / Hard) — giúp người chơi mới dễ tiếp cận và người chơi kỳ cựu có trải nghiệm sâu hơn.

> **v1.1.9 — Per-mode quests/achievements + KN rework:**
> - Quests và Achievements lưu state riêng theo mode: keys có hậu tố `_simple` / `_full`.
> - Mỗi mode có pool quest riêng (filter theo `modes` field). Achievement filter theo category (Đầu tư/Sưu tập + emergency/rugpull → Full only).
> - Migration: data cũ (không có hậu tố) auto copy sang `_full` lần đầu boot, đánh dấu `anki_tycoon_per_mode_migrated`.
> - **Rank/XP/KN shared toàn cục** (không tách theo mode), nhưng track tỷ lệ XP đóng góp Simple/Full vào mỗi rank đã đạt qua `anki_tycoon_rank_history`.
> - Random KN: 10% xác suất mỗi thẻ Good/Easy → cộng 5–10 KN.
> - Reset có 3 scope: `all` (cục bộ — wipe + cấp lại 10M), `simple` (chỉ wipe data Simple), `full` (chỉ wipe data Full). Bridge: `performResetScoped(phrase, scope)`.
> - Fix nhiều trigger thiếu: earn_money / save_money / no_purchase / streak_reach / balanced / perfect_day / hero_day / quality_cards / morning_cards / session_cards / no_penalty_streak (quests), savings_updated / net_worth_updated / crypto_traded / crypto_staked / property_purchased / stock_profit_updated / rank_changed / rugpull_victim / balance_dropped (achievements).

---

## 1. Tổng quan kiến ​​trúc

```
┌─────────────────────────────────────────────────────────┐
│                    ANKI FINANCE                           │
├────────────────────────────┬────────────────────────────┤
│     🟢 SIMPLE MODE         │       🔴 FULL MODE           │
│     (Cơ bản)               │      (Toàn diện / Hard)      │
├────────────────────────────┼────────────────────────────┤
│ ✅ Reward/penalty core     │ ✅ Tất cả Simple Mode        │
│ ✅ Streak system           │    features +                │
│ ✅ XP / Rank               │                             │
│ ✅ Daily Quest             │ ✅ 📈 Stock Market           │
│ ✅ Energy System           │ ✅ ₿ Digital Assets (Crypto) │
│ ✅ Shop + Inventory        │ ✅ 🚗 Vehicle System (Garage) │
│ ✅ Bank (tiết kiệm)        │ ✅ 🏠 Real Estate            │
│ ✅ Knowledge Base          │ ✅ 💳 Credit Banking          │
│ ✅ Goals (mục tiêu)        │ ✅ 📜 Bond System             │
│ ✅ Food / Boost            │ ✅ 🔧 Tech Lab                │
│ ✅ Living Costs            │ ✅ 🏛️ Economy Controls         │
│ ✅ Tax (cơ bản)            │ ✅ ⚡ Emergency Events         │
│ ✅ Achievements            │ ✅ 🎯 Tax nâng cao + SCT      │
│ ✅ Again Tracker           │ ✅ Study Items (weekly limit) │
│ ✅ Inactivity Penalty      │                             │
└────────────────────────────┴────────────────────────────┘
```

## 2. Cơ chế hoạt động

### 2.1. Config key

Mode được lưu trong Anki config với key:

| Key | Giá trị | Ý nghĩa |
|-----|---------|---------|
| [`anki_tycoon_game_mode`](config.py:6) | `"full"` (mặc định) | Chế độ đầy đủ |
| | `"simple"` | Chế độ đơn giản |

**Định nghĩa:** [`config.py:9-13`](config.py:9)

```python
GAME_MODE_FULL   = "full"
GAME_MODE_SIMPLE = "simple"
DEFAULT_GAME_MODE = GAME_MODE_FULL
```

### 2.2. Kiểm tra mode

Hàm kiểm tra hiện tại ở [`__init__.py:556-564`](__init__.py:556):

```python
def _is_simple_mode() -> bool:
    try:
        from ._safe_config import cfg_str
        from .config import CONFIG_KEY_GAME_MODE, DEFAULT_GAME_MODE
        mode = cfg_str(CONFIG_KEY_GAME_MODE, DEFAULT_GAME_MODE)
        return mode == "simple"
    except Exception:
        return False
```

### 2.3. Danh sách tab UI theo mode

Định nghĩa ở [`config.py:16-24`](config.py:16):

```python
SIMPLE_TABS = {
    "dashboard", "shop", "inventory", "bank", "finance",
    "quests", "achievement", "settings", "knowledge",
}
ADVANCED_TABS = {
    "realestate", "garage", "techlab",
    "stocks", "digital", "learning",
}
```

---

## 3. So sánh chi tiết 2 chế độ

### 3.1. 🟢 Simple Mode — "Học để giàu, giàu để học"

Dành cho người mới bắt đầu hoặc ai muốn trải nghiệm nhẹ nhàng, tập trung vào học tập.

| Tính năng | Mô tả |
|-----------|-------|
| **💰 Reward/Penalty** | Thưởng tiền khi ôn thẻ đúng, phạt khi Again |
| **🔥 Streak** | Chuỗi ngày ôn bài liên tục, nhân thưởng |
| **⭐ XP / Rank** | Tích lũy EXP thăng cấp rank |
| **📋 Daily Quest** | Nhiệm vụ hàng ngày, phần thưởng bằng tiền/KN |
| **⚡ Energy System** | Năng lượng học tập, hồi theo thời gian |
| **🛒 Shop** | Mua item cơ bản (food, drink, study items) |
| **🎒 Inventory** | Quản lý vật phẩm trong kho |
| **🏦 Bank** | Gửi tiết kiệm không kỳ hạn + có kỳ hạn |
| **🧠 Knowledge Base** | Ghi chú kiến thức tài chính |
| **🎯 Goals** | Đặt mục tiêu tiết kiệm |
| **🍔 Food / Boost** | Kích hoạt buff từ đồ ăn, đồ uống |
| **🏠 Living Costs** | Chi phí sinh hoạt hàng ngày |
| **🏛️ Tax (cơ bản)** | Thuế tài sản cơ bản |
| **🏆 Achievements** | Thành tựu mở khoá |
| **📊 Again Tracker** | Theo dõi số thẻ Again + phạt luỹ tiến |
| **💤 Inactivity Penalty** | Phí duy trì khi vắng mặt |

**Tab hiển thị:** Dashboard, Shop, Inventory, Bank, Finance, Quests, Achievement, Settings, Knowledge

### 3.2. 🔴 Full Mode — "Đế chế tài chính toàn diện"

Dành cho người chơi kỳ cựu, muốn trải nghiệm đầy đủ mọi hệ thống kinh tế.

Bao gồm **tất cả tính năng của Simple Mode** + các hệ thống nâng cao sau:

| Tính năng | Mô tả | File chính |
|-----------|-------|------------|
| **📈 Stock Market** | Mua/bán cổ phiếu, cổ tức, phiên giao dịch, lệnh limit/stop-loss | [`stock_market.py`](stock_market.py) |
| **₿ Digital Assets** | Mua/bán crypto, staking yield, thị trường biến động | [`digital_assets.py`](digital_assets.py) |
| **🚗 Vehicle System** | Xe cộ (xăng/điện), độ bền, nhiên liệu, bảo dưỡng, sự cố | [`vehicle_system.py`](vehicle_system.py) |
| **🏠 Real Estate** | Đầu tư BĐS, cho thuê, nâng cấp, giá thị trường | [`real_estate.py`](real_estate.py) |
| **💳 Credit Banking** | Điểm tín dụng, thẻ tín dụng, vay ngân hàng, trả góp | [`credit_banking.py`](credit_banking.py) |
| **📜 Bond System** | Mua trái phiếu, coupon hàng ngày, đáo hạn | [`bond_system.py`](bond_system.py) |
| **🔧 Tech Lab** | Thiết bị công nghệ, độ bền, active/passive effects | [`tech_system.py`](tech_system.py) |
| **🏛️ Economy Controls** | Phí garage, giới hạn thẻ/ngày, kiểm soát kinh tế | [`economy_controls.py`](economy_controls.py) |
| **⚡ Emergency Events** | Sự kiện tài chính bất ngờ (15%/ngày) | [`emergency_events.py`](emergency_events.py) |
| **🎯 Thuế nâng cao (SCT)** | Thuế tiêu thụ đặc biệt khi mua hàng | [`tax_system.py`](tax_system.py) |
| **📚 Study Items** | Vật phẩm học tập (weekly limit) | [`food_effects.py`](food_effects.py) |
| **🔗 KN Perks** | Mở khoá đặc quyền bằng điểm Kiến Thức | [`kn_perks.py`](kn_perks.py) |

**Tab hiển thị thêm:** Real Estate, Garage, Tech Lab, Stocks, Digital Assets, Learning

---

## 4. Luồng hoạt động theo mode

### 4.1. Khi khởi động app ([`__init__.py:_on_profile_loaded()`](__init__.py:462))

```python
_is_simple = _is_simple_mode()

# ── Luôn chạy (cả 2 mode) ──
_ensure_new_player()           # Khởi tạo người chơi mới
_inject_topbar()               # Thanh topbar
_collect_daily_tax()           # Thuế cơ bản
_collect_daily_living_costs()  # Chi phí sinh hoạt
_accrue_loan_interest()        # Lãi vay nóng
_seed_knowledge()             # Knowledge base

# ── Chỉ Full Mode ──
if not _is_simple:
    _auto_collect_rent()           # Tiền thuê BĐS
    _update_stock_prices()         # Cập nhật giá CK
    _update_crypto_prices()        # Cập nhật giá Crypto
    _auto_collect_staking_yield()  # Yield staking
    _check_emergency_event()       # Sự kiện bất ngờ
    _process_daily_credit_banking()# Thẻ tín dụng + vay
    _auto_collect_bond_coupon()    # Coupon trái phiếu
    _collect_garage_fees()         # Phí đỗ xe
    # Migration + Repair
    repair_crypto_passive_effects()
    repair_vehicle_inventory_migration()
```

### 4.2. Khi review thẻ ([`__init__.py:on_review_done()`](__init__.py:51))

```python
_is_simple = _is_simple_mode()

# Luôn chạy:
#   - add_reward(ease) — thưởng/phạt
#   - record_card_review_time() — tốc độ học
#   - _apply_energy_regen() — hồi năng lượng
#   - _apply_study_effects() — can thiệp scheduler
#   - check_and_unlock(achievement) — thành tựu
#   - _update_gamification() — streak, XP, quest

# Chỉ Full Mode:
if not _is_simple:
    stock_record_review(1)        # Ghi nhận review cho CK
    crypto_record_review(1)       # Ghi nhận review cho Crypto
    bond_record_review(1)         # Ghi nhận review cho Bond
    # Economy Controls:
    increment_daily_cards_count()
    increment_total_system_cards()
    check_breakdown_on_review()   # Sự cố xe ngẫu nhiên
    consume_durability(1)         # Hao mòn xe
    tech_consume_durability(1)    # Hao mòn tech
```

---

## 5. Quy tắc khi thêm tính năng mới

Khi AI được yêu cầu thêm tính năng mới, AI phải:

```
1. XÁC ĐỊNH mode của tính năng:
   - Là tính năng CỐT LÕI (ai cũng cần)? → Simple Mode + Full Mode
   - Là tính năng NÂNG CAO (phức tạp)?  → Chỉ Full Mode
   - Không chắc?                        → Hỏi hoặc thêm vào Full Mode

2. KIỂM TRA mode gateway:
   - Nếu feature chỉ dành cho Full Mode → thêm `if _is_simple_mode(): return`
   - Nếu feature cho cả 2 mode          → không cần check

3. THÊM code:
   - Luôn dùng `_is_simple_mode()` hoặc `_is_simple` variable
   - KHÔNG hardcode mode string ở nhiều nơi
   - Dùng hằng số từ config.py: GAME_MODE_FULL, GAME_MODE_SIMPLE

4. CẬP NHẬT tab UI:
   - Thêm tab mới vào SIMPLE_TABS hoặc ADVANCED_TABS trong config.py
   - JS router (tycoon-router.js) tự động lọc tab theo mode
```

---

## 6. Quy tắc đặt tên

| Pattern | Ví dụ | Khi nào dùng |
|---------|-------|-------------|
| `_is_simple_mode()` | `if _is_simple_mode(): return` | Kiểm tra mode ở Python backend |
| `GAME_MODE_FULL` / `GAME_MODE_SIMPLE` | `mode = cfg_str(CONFIG_KEY_GAME_MODE, GAME_MODE_FULL)` | So sánh mode string |
| `CONFIG_KEY_GAME_MODE` | `"anki_tycoon_game_mode"` | Key lưu trong Anki config |
| `SIMPLE_TABS` / `ADVANCED_TABS` | Set of tab IDs | Lọc tab UI theo mode |

---

## 7. Files liên quan

| File | Vai trò |
|------|---------|
| [`config.py`](config.py) | Hằng số mode, danh sách tab |
| [`__init__.py`](__init__.py) | Kiểm tra mode, điều hướng luồng |
| [`_safe_config.py`](_safe_config.py) | Đọc/ghi config an toàn |
| [`gui/web_bridge.py`](gui/web_bridge.py) | Bridge Python → JS (có thể expose mode cho UI) |
| [`gui/JS/tycoon-router.js`](gui/JS/tycoon-router.js) | Router UI, lọc tab theo mode |
| [`gui/JS/tycoon-init.js`](gui/JS/tycoon-init.js) | Khởi tạo UI, đọc mode |

---

## 8. "Done" Checklist

- [x] Config key `anki_tycoon_game_mode` định nghĩa
- [x] Hằng số `GAME_MODE_FULL` / `GAME_MODE_SIMPLE` trong [`config.py`](config.py)
- [x] Danh sách tab [`SIMPLE_TABS` / `ADVANCED_TABS`](config.py:16-23)
- [x] Hàm `_is_simple_mode()` trong [`__init__.py`](__init__.py)
- [x] Backend điều hướng: review hook + startup hook kiểm tra mode
- [x] UI lọc tab theo mode (qua JS router)

---

## 9. Kết luận

- **Simple Mode**: 15+ tính năng cốt lõi — đủ để trải nghiệm game hoá học tập
- **Full Mode**: 25+ tính năng — toàn bộ hệ thống kinh tế mô phỏng
- **Dễ mở rộng**: Thêm tính năng mới chỉ cần xác định mode và thêm `if _is_simple_mode(): return`
- **Zero risk**: Mode check đơn giản, không ảnh hưởng performance, dễ test
