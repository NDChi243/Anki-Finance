# 🎓 Anki Finance

Biến việc ôn thẻ Anki thành trò chơi làm giàu!

## 📦 Cài đặt

1. Tải add-on từ GitHub Releases
2. Giải nén vào thư mục `addons21/anki_finance/`
3. Khởi động lại Anki

## 🔄 Cập nhật tự động từ GitHub

Add-on này được tích hợp sẵn cơ chế **Auto-Update** — tự động kiểm tra và tải bản cập nhật mới nhất từ **GitHub Releases** mà **không cần qua AnkiWeb**.

### Cách hoạt động

1. Mỗi khi khởi động Anki, add-on chạy 1 thread nền kiểm tra GitHub API
2. So sánh version hiện tại với release mới nhất
3. Nếu có bản mới → tự động tải ZIP release → giải nén đè lên thư mục hiện tại
4. Hiển thị thông báo yêu cầu khởi động lại Anki

### Cấu hình lần đầu (dành cho developer)

Mở file [`auto_update.py`](auto_update.py) và sửa 3 hằng số ở đầu file:

```python
GITHUB_USER = "your-username"    # GitHub username của bạn
GITHUB_REPO = "anki-finance"     # Tên repository
CURRENT_VERSION = "1.0.0"        # Version hiện tại
```

---

## 🚀 Hướng dẫn push lên GitHub & thiết lập Auto-Update

### Bước 1: Tạo repository trên GitHub

1. Vào [github.com/new](https://github.com/new)
2. Nhập tên repository (VD: `anki-finance`)
3. Chọn **Public** (cần public để người dùng khác tải được)
4. **Không** tick "Initialize with README" (vì đã có sẵn)
5. Click **Create repository**

### Bước 2: Push code lên GitHub

Mở terminal (CMD/PowerShell) tại thư mục add-on và chạy:

```bash
# Khởi tạo Git repo
cd /d "C:\Users\nguye\AppData\Roaming\Anki2\addons21\anki_finance"
git init
git add .
git commit -m "Initial commit: Anki Finance v1.0.0"

# Liên kết với GitHub repository
git remote add origin https://github.com/YOUR_USERNAME/anki-finance.git

# Push lên GitHub
git branch -M main
git push -u origin main
```

> ⚠️ Thay `YOUR_USERNAME` bằng GitHub username thật của bạn.

### Bước 3: Sửa cấu hình trong file auto_update.py

Mở file [`auto_update.py`](auto_update.py), sửa 3 dòng đầu:

```python
GITHUB_USER = "your-username"    # → Thay bằng username GitHub của bạn
GITHUB_REPO = "anki-finance"     # → Thay bằng tên repository (nếu khác)
CURRENT_VERSION = "1.0.0"        # Giữ nguyên
```

Commit và push lại:

```bash
git add auto_update.py
git commit -m "Configure GitHub username"
git push
```

### Bước 4: Tạo Release đầu tiên

Có **2 cách**:

#### Cách A: Tạo Release thủ công (qua GitHub UI)

1. Vào repository của bạn trên GitHub → **Releases** → **Create a new release**
2. **Tag version**: `v1.0.0`
3. **Release title**: `v1.0.0 - Initial Release`
4. **Description**: Ghi chú thay đổi
5. **Attach binaries**: Có thể đính kèm file ZIP (không bắt buộc)
6. Click **Publish release**

#### Cách B: Dùng Git tag + GitHub CLI

```bash
git tag -a v1.0.0 -m "Initial Release v1.0.0"
git push origin v1.0.0
```

> **Lưu ý quan trọng**: GitHub chỉ cho phép 60 requests/giờ với API unauthenticated. Nếu deploy cho nhiều người dùng, nên tạo **Personal Access Token (PAT)** và cấu hình trong `auto_update.py`.

### Bước 5: Kiểm tra auto-update

1. Tăng `CURRENT_VERSION` trong `auto_update.py` lên `1.0.1`
2. Tạo release mới trên GitHub với tag `v1.0.1`
3. Khởi động lại Anki → kiểm tra console log:
   ```
   [AnkiFinance][AutoUpdate] 🚀 Khởi động auto-updater (v1.0.0)
   [AnkiFinance][AutoUpdate] 🌐 Phiên bản mới nhất trên GitHub: v1.0.1
   [AnkiFinance][AutoUpdate] 🎉 Có bản cập nhật: v1.0.0 → v1.0.1
   ```

### Bước 6: Deploy đến người dùng khác

Người dùng chỉ cần:
1. Clone repo hoặc download release ZIP đầu tiên về máy
2. Giải nén vào `addons21/anki_finance/`
3. Mỗi lần bạn release bản mới, add-on tự động cập nhật

---

## 🔧 Cấu hình nâng cao

### Giới hạn tốc độ GitHub API

Để tránh vượt quá rate limit của GitHub, có thể tạo **Personal Access Token**:

1. Vào [GitHub Settings → Tokens](https://github.com/settings/tokens) → Generate new token
2. Chọn scope `public_repo` (đủ để đọc releases)
3. Copy token và sửa trong [`auto_update.py`](auto_update.py):

```python
# Thêm dòng này sau phần import
_GITHUB_TOKEN = "ghp_xxxxxxxxxxxxxxxxxxxx"

# Và sửa hàm _github_api_url:
def _github_api_url() -> str:
    return f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/releases/latest"
```

### Tần suất kiểm tra

Mặc định: **1 lần/ngày**. Sửa hằng số trong [`auto_update.py`](auto_update.py):

```python
_UPDATE_INTERVAL_DAYS = 1   # 0 = kiểm tra mỗi lần khởi động
```

---

## 📋 Kiến trúc hệ thống (AI Context)

### Sơ đồ phụ thuộc module

```
__init__.py          ← Entry point: hooks, on_review_done, profile_loaded
  ├── _safe_config.py   ← In-memory cache cho Anki config (cfg_int/str/list/dict)
  ├── config.py         ← Hằng số: keys, game mode, reward map
  ├── logger.py         ← Logging setup
  ├── balance.py        ← add_reward() — core loop reward calculation
  │   ├── economy_controls.py  ← Daily cap, wealth tax, again fee, garage fees, CPI
  │   ├── again_tracker.py     ← Again penalty tracking
  │   ├── tax_system.py        ← SCT, income tax, land tax
  │   ├── item_effects.py      ← Passive effects aggregation
  │   └── loan_system.py       ← Hot loan repay
  ├── food_effects.py   ← Boost activation, freshness, daily limits
  ├── item_effects.py   ← Passive effects system, set bonuses
  ├── rank_system.py    ← XP/KN, 23 ranks across 8 groups
  ├── streak_system.py  ← Daily streak, milestones
  ├── daily_quest.py    ← Daily quest tracking
  ├── goals.py          ← Player goals
  └── achievements.py   ← Achievement system

gui/web_bridge.py      ← QWebChannel bridge: JS ↔ Python calls
  └── shop_data.py         ← Load shop items from JSON (cached in memory)
  └── balance.py, inventory.py, food_effects.py, etc.

# Full Mode exclusive modules (not loaded in Simple Mode):
stock_market.py, digital_assets.py, vehicle_system.py, tech_system.py,
real_estate.py, bond_system.py, credit_banking.py, emergency_events.py,
economy_controls.py, living_costs.py, energy_system.py, kn_perks.py
```

### Key Design Patterns

| Pattern | Location | Description |
|---------|----------|-------------|
| **In-memory config cache** | [`_safe_config.py`](_safe_config.py) | `_cache` dict + `_cache_ttl` (30s) + `_cached_time()` (100ms). Cache TTL bypass cho long-lived keys qua `_LONG_CACHE_KEYS`. Batch write qua `begin_batch()`/`commit_batch()`. |
| **Game Mode gate** | [`__init__.py:_is_simple_mode()`](__init__.py:53) | Đọc `anki_tycoon_game_mode` từ config, cache kết quả vĩnh viễn (`_simple_mode_cache`) vì mode không đổi trong runtime. |
| **Single read per hot path** | [`balance.py:add_reward()`](balance.py:139) | `_simple` được đọc 1 lần đầu `add_reward()` thay vì gọi `_is_simple_mode()` 7+ lần. |
| **Local import pattern** | Nhiều file | `from .module import func` bên trong try/except để tránh ImportError khi module chưa sẵn sàng (Anki startup). |
| **Menu-based triggers** | [`__init__.py:_on_profile_loaded()`](__init__.py:610) | Tất cả daily tasks gọi từ `_on_profile_loaded`: living costs, loan interest, inactivity penalty, garage fees, etc. |
| **Batch config writes** | [`_safe_config.py:begin_batch()`](_safe_config.py:220) | Gom nhiều `cfg_set()` thành 1 lần ghi Anki collection — dùng trong `on_review_done`. |

### File Structure & Responsibilities

| File | Purpose | Hot Path? |
|------|---------|-----------|
| [`__init__.py`](__init__.py) | Entry point. Hooks: `on_review_done`, `on_profile_loaded`. Defines `_is_simple_mode()`. | ✅ Yes |
| [`_safe_config.py`](_safe_config.py) | Config cache layer. `cfg_int/str/list/dict/set`, batch writes, cache invalidation. | ✅ Yes |
| [`config.py`](config.py) | Constants: config keys, game mode values, reward map, advanced categories. | ✅ Yes |
| [`balance.py`](balance.py) | `add_reward()` — core reward calc. Stats tracking, purchase recording. | ✅ Yes |
| [`logger.py`](logger.py) | Logging setup, `get_logger()`, `log_error()`, `log_warning()`. | ✅ Yes |
| [`food_effects.py`](food_effects.py) | Boost system: activate/consume/deactivate, freshness, daily limits. | ✅ Yes |
| [`item_effects.py`](item_effects.py) | Passive effects: register/unregister, aggregation, set bonuses, effects application. | ✅ Yes |
| [`rank_system.py`](rank_system.py) | Rank calc (23 ranks, 8 groups), XP/KN management, Progressive Ladder. | ✅ Yes |
| [`streak_system.py`](streak_system.py) | Daily streak tracking, milestone detection. | ✅ Yes |
| [`daily_quest.py`](daily_quest.py) | Daily quest generation and tracking. | ❌ No |
| [`goals.py`](goals.py) | Player financial goals. | ❌ No |
| [`achievements.py`](achievements.py) | Achievement unlock system. | ❌ No |
| [`again_tracker.py`](again_tracker.py) | "Again" penalty tracking and daily summary. | ✅ Yes |
| [`shop_data.py`](shop_data.py) | Load shop items from JSON (cached in memory, 60s TTL). | ❌ No |
| [`transactions.py`](transactions.py) | Transaction history (ledger). | ❌ No |
| [`economy_controls.py`](economy_controls.py) | Daily cap, wealth tax, again fee, garage fees, CPI, scarcity. Full Mode only. | ✅ Yes |
| [`tax_system.py`](tax_system.py) | SCT, income tax, land tax. Full Mode only. | ❌ No |
| [`energy_system.py`](energy_system.py) | Energy/stamina system. Full Mode only. | ❌ No |
| [`living_costs.py`](living_costs.py) | Daily living costs deduction. Full Mode only. | ❌ No |
| [`loan_system.py`](loan_system.py) | Hot loan system. Full Mode only. | ❌ No |
| [`stock_market.py`](stock_market.py) | Stock trading: limit/stop-loss orders, dividends. Full Mode only. | ❌ No |
| [`digital_assets.py`](digital_assets.py) | Crypto: staking, market cycles. Full Mode only. | ❌ No |
| [`vehicle_system.py`](vehicle_system.py) | Vehicles: durability, fuel, maintenance. Full Mode only. | ❌ No |
| [`tech_system.py`](tech_system.py) | Tech lab items. Full Mode only. | ❌ No |
| [`real_estate.py`](real_estate.py) | Real estate: rent, upgrade, market value. Full Mode only. | ❌ No |
| [`bond_system.py`](bond_system.py) | Bonds: coupon, maturity. Full Mode only. | ❌ No |
| [`credit_banking.py`](credit_banking.py) | Credit cards, loans, credit score. Full Mode only. | ❌ No |
| [`emergency_events.py`](emergency_events.py) | Random financial events. Full Mode only. | ❌ No |
| [`kn_perks.py`](kn_perks.py) | Knowledge perks system. Full Mode only. | ❌ No |
| [`inventory.py`](inventory.py) | Player inventory management. | ❌ No |
| [`bank.py`](bank.py) | Savings, term deposits, demand deposits. | ❌ No |
| [`finance.py`](finance.py) | Budget, money jars, monthly tracking. | ❌ No |
| [`housing_residence.py`](housing_residence.py) | Housing/residence system. | ❌ No |
| [`reset_manager.py`](reset_manager.py) | Game reset functionality. | ❌ No |
| [`finance_quiz.py`](finance_quiz.py) | Financial literacy quiz. | ❌ No |
| [`knowledge_base.py`](knowledge_base.py) | Knowledge base notes. | ❌ No |
| [`debug_tools.py`](debug_tools.py) | Debug utilities. | ❌ No |

### Config Key Naming Convention

Tất cả state được lưu trong Anki `mw.col` config với prefix `anki_tycoon_`:

| Key Pattern | Example | Type | Description |
|-------------|---------|------|-------------|
| `anki_tycoon_balance` | `15000000` | int | Số dư tiền mặt |
| `anki_tycoon_stats` | `{cards: 42, ...}` | dict | Thống kê học tập |
| `anki_tycoon_budget` | `{month: ..., budget: ...}` | dict | Ngân sách tháng |
| `anki_tycoon_game_mode` | `"full"`/`"simple"` | str | Chế độ chơi |
| `anki_tycoon_daily_*` | Date-based | int/str | Daily reset counters |
| `anki_tycoon_vehicle_*` | Vehicle state | dict | Xe cộ (Full Mode) |
| `anki_tycoon_re_*` | RE portfolio | dict | BĐS (Full Mode) |
| `anki_tycoon_stocks_*` | Stock portfolio | dict | Chứng khoán (Full Mode) |
| `anki_tycoon_crypto_*` | Crypto portfolio | dict | Crypto (Full Mode) |

### Hot Path Analysis (on_review_done)

Đây là function quan trọng nhất về performance — chạy mỗi khi người dùng review 1 thẻ:

```
on_review_done()
  ├── begin_batch()                    ← Bật batch mode
  ├── add_reward(ease)                 ← Core reward calc
  │   ├── _is_simple_mode() [1 lần]   ← Game mode check (cached)
  │   ├── _consume_energy_and_stamina() ← Full Mode only
  │   ├── _apply_food_penalties()      ← Boost effects
  │   ├── apply_wealth_tax_on_reward() ← Full Mode only
  │   └── _apply_loan_repay()          ← Full Mode only
  ├── _apply_study_effects()           ← Item/vehicle effects
  ├── _apply_energy_regen()            ← Energy regen
  ├── _update_gamification()           ← Streak, XP, rank, quest
  ├── stock_record_review()            ← Full Mode only
  ├── economy controls                 ← Full Mode only (daily cap, CPI)
  └── commit_batch()                   ← Ghi 1 lần xuống Anki col
```

**Performance rules cho AI:**
- Không thêm `time.time()` gọi trực tiếp — dùng `_cached_time()` từ [`_safe_config.py`](_safe_config.py)
- Không thêm `cfg_set` bên ngoài `begin_batch()`/`commit_batch()` scope
- Cache kết quả `_is_simple_mode()` — game mode không đổi trong runtime
- Tránh import heavy modules trong hot path — ưu tiên import sẵn đầu file

### Game Mode Architecture

| Aspect | Simple Mode | Full Mode |
|--------|------------|-----------|
| **Target** | Người mới, casual | Người chơi hardcore |
| **Features** | 8-10 core: reward, streak, rank, shop, bank, goals, quests, achievements | 25+ features: thêm stocks, crypto, vehicles, real estate, bonds, credit, tech lab, economy controls |
| **Tabs** | dashboard, shop, inventory, bank, finance, quests, achievement, settings, knowledge | Tất cả tabs |
| **Advanced Categories** | Bị ẩn và block mua | Đầy đủ |
| **Reward multiplier** | 0.5× (bù vì không có chi phí) | 1.0× (có living costs, tax) |
| **Economy Controls** | Không (daily cap không tăng, wealth tax bỏ qua) | Đầy đủ (daily cap, wealth tax, CPI, again fee) |
| **Energy System** | Bỏ qua | Đầy đủ |
| **SCT Tax** | Không áp dụng | Đầy đủ |

---

## 📝 License

MIT License
