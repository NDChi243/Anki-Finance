# -*- coding: utf-8 -*-
from __future__ import annotations
"""
stock_market.py — Thị trường chứng khoán Anki Finance.

Phase 2:
  - 15 mã cổ phiếu VN30 representative
  - Giả lập giá biến động ngẫu nhiên (random walk + mean reversion)
  - Mua / Bán cổ phiếu với quy tắc T+2, phiên giao dịch
  - Quản lý danh mục đầu tư (portfolio)
  - Tính P&L, VN-Index mô phỏng
  - Đếm ngược phiên giao dịch & thời gian có thể bán
  - Cổ tức (Dividends) — trả tiền mặt định kỳ
  - Corporate Actions — split, bonus shares, rights issue
"""

import time
import math
import random
from datetime import datetime, timedelta
from ._safe_config import col_ready, cfg_int, cfg_dict, cfg_list, cfg_set

# ── Config keys ──────────────────────────────────────────────
_KEY_MARKET        = "anki_tycoon_stocks_market"         # dict{symbol: stock_data}
_KEY_PORTFOLIO     = "anki_tycoon_stocks_portfolio"      # list[holding]
_KEY_LAST_UPDATE   = "anki_tycoon_stocks_last_update"    # float timestamp
_KEY_HISTORY       = "anki_tycoon_stocks_price_history"  # dict{symbol: [[ts,price],...]}
_KEY_TXNS          = "anki_tycoon_stocks_transactions"   # list[txn]
_KEY_REVIEW_COUNT       = "anki_tycoon_stocks_review_count"          # int — số thẻ đã ôn từ lần cập nhật cuối
_KEY_SIMULATED_SESSION  = "anki_tycoon_stocks_simulated_session"     # str | None — "morning"/"afternoon" từ review-based session
_KEY_DIVIDENDS     = "anki_tycoon_stocks_dividends"      # dict{symbol: {"last_div": float, "total_paid": int}}
_KEY_CORP_ACTIONS  = "anki_tycoon_stocks_corp_actions"   # list[{"type": str, "symbol": str, ...}]
_KEY_DIV_EVENTS    = "anki_tycoon_stocks_div_events"     # list[{"symbol": str, "amount": int, "ts": float}]
_KEY_CA_EVENTS     = "anki_tycoon_stocks_ca_events"      # list[{"type": str, "symbol": str, "desc": str, "ts": float}]

UPDATE_INTERVAL_SECS = 4 * 3600        # 4 giờ (dự phòng nếu không mở app lâu)
MAX_HISTORY_ENTRIES  = 50
MAX_ACCUMULATE_DAYS  = 30
SECS_PER_DAY         = 86400
# REVIEWS_PER_UPDATE có slight randomness: 40-60 thẻ thay vì 50 cố định
_REVIEWS_BASE        = 50
_REVIEWS_RANGE       = 10              # ±10 → range 40-60

def _get_reviews_threshold() -> int:
    """Trả về số thẻ cần ôn để update giá, có randomness ±10."""
    return _REVIEWS_BASE + random.randint(-_REVIEWS_RANGE, _REVIEWS_RANGE)

# ── Dividend constants ────────────────────────────────────────
# Tham khảo tỷ lệ cổ tức thực tế tại Việt Nam (2023-2025):
#   Ngân hàng:    1.5-3.5%/năm  (VCB ~2.5%, BID ~2.0%, TCB ~3.0%)
#   Thực phẩm:    4-7%/năm      (VNM ~6.5%, MSN ~4.0%)
#   Thép:         2-5%/năm      (HPG ~3.0%)
#   Công nghệ:    1-3%/năm      (FPT ~2.5%)
#   Bán lẻ:       1-4%/năm      (MWG ~2.0%)
#   Dầu khí:      4-8%/năm      (GAS ~6.0%)
#   Bất động sản: 0-2%/năm      (VHM ~1.0%)
#   Đa ngành:     1-3%/năm      (VIC ~1.5%)
#   Chứng khoán:  2-5%/năm      (SSI ~3.5%)
#
# Trong game: mỗi lần update giá tương đương ~1 tháng,
# nên chia tỷ lệ năm cho 12 để ra yield mỗi lần.
DIV_CHANCE          = 0.30            # 30% mỗi lần update giá (tăng nhẹ so với 25% cũ)
DIV_PRICE_THRESHOLD = 0.85            # Chỉ trả cổ tức nếu giá > 85% base_price (nới lỏng)

# Yield theo ngành (% base_price mỗi lần update, tương đương ~1 tháng)
# Công thức: yield_tháng = yield_năm / 12
DIV_YIELD_BY_SECTOR = {
    "Ngân hàng":       (0.0012, 0.0029),   # 1.5-3.5%/năm → 0.12-0.29%/tháng
    "Thực phẩm":       (0.0033, 0.0058),   # 4-7%/năm
    "Thép":            (0.0017, 0.0042),   # 2-5%/năm
    "Công nghệ":       (0.0008, 0.0025),   # 1-3%/năm
    "Bán lẻ":          (0.0008, 0.0033),   # 1-4%/năm
    "Dầu khí":         (0.0033, 0.0067),   # 4-8%/năm
    "Bất động sản":    (0.0000, 0.0017),   # 0-2%/năm
    "Đa ngành":        (0.0008, 0.0025),   # 1-3%/năm
    "Chứng khoán":     (0.0017, 0.0042),   # 2-5%/năm
}
# Fallback nếu sector không có trong dict
DIV_FALLBACK_YIELD   = (0.0010, 0.0030)   # 1-3%/năm

# ── Corporate Action constants ────────────────────────────────
SPLIT_PRICE_THRESHOLD = 2.0           # Giá > 200% base → có thể split
SPLIT_CHANCE          = 0.02          # 2% mỗi lần update
BONUS_CHANCE          = 0.03          # 3% nếu change_pct > 5%
BONUS_MIN_CHANGE      = 5.0           # % tăng tối thiểu để bonus
BONUS_RATIO_MIN       = 0.05          # 5% bonus shares
BONUS_RATIO_MAX       = 0.10          # 10% bonus shares
RIGHTS_PRICE_THRESHOLD = 0.70         # Giá < 70% base → rights issue
RIGHTS_CHANCE          = 0.015        # 1.5% mỗi lần update
RIGHTS_DISCOUNT        = 0.80         # Giá ưu đãi = 80% thị trường
RIGHTS_RATIO           = 0.10         # 10% số lượng đang nắm giữ

# ── Vietnam Stock Exchange Trading Sessions ─────────────────
# Phiên sáng: 09:00 - 11:30  (2.5 giờ)
# Phiên chiều: 13:00 - 15:00 (2 giờ)
MORNING_START  = 9 * 3600      # 09:00 tính bằng giây từ 00:00
MORNING_END    = 11 * 3600 + 30 * 60     # 11:30
AFTERNOON_START = 13 * 3600   # 13:00
AFTERNOON_END  = 15 * 3600    # 15:00

# ── T+ Settlement Rules ────────────────────────────────────
# Việt Nam: T+2 (chứng khoán về 2 ngày làm việc sau khi mua)
# Đơn giản hoá: dùng T+2_DAYS = 2 ngày calendar
T_PLUS_DAYS = 2

# ── Danh sách mã VN30 representative ─────────────────────────
STOCK_MASTER = [
    # (symbol, company_name, short_name, sector, sector_emoji, base_price, volatility)
    ("VCB", "Vietcombank",                     "Ngân hàng Ngoại thương",     "Ngân hàng",       "🏦", 85000,  0.012),
    ("BID", "BIDV",                            "Ngân hàng Đầu tư",           "Ngân hàng",       "🏦", 42000,  0.013),
    ("TCB", "Techcombank",                     "Ngân hàng Kỹ thương",        "Ngân hàng",       "🏦", 38000,  0.015),
    ("ACB", "ACB",                             "Ngân hàng Á Châu",           "Ngân hàng",       "🏦", 28000,  0.014),
    ("MBB", "MB Bank",                         "Ngân hàng Quân đội",         "Ngân hàng",       "🏦", 22000,  0.015),
    ("STB", "Sacombank",                       "Ngân hàng Sài Gòn Thương Tín","Ngân hàng",      "🏦", 18000,  0.016),
    ("VIC", "Vingroup",                        "Tập đoàn Vingroup",          "Đa ngành",        "🏢", 65000,  0.018),
    ("VHM", "Vinhomes",                        "Vinhomes",                   "Bất động sản",    "🏠", 42000,  0.017),
    ("VNM", "Vinamilk",                        "Sữa Việt Nam",               "Thực phẩm",       "🥛", 72000,  0.010),
    ("MSN", "Masan Group",                     "Tập đoàn Masan",             "Đa ngành",        "🏢", 62000,  0.016),
    ("HPG", "Hòa Phát",                        "Tập đoàn Hòa Phát",          "Thép",            "🏗️", 29000,  0.020),
    ("FPT", "FPT Corporation",                 "Công ty FPT",                "Công nghệ",       "💻", 112000, 0.022),
    ("MWG", "Mobile World Group",              "Thế giới Di động",           "Bán lẻ",          "🛒", 48000,  0.019),
    ("SSI", "SSI Securities",                  "Chứng khoán SSI",            "Chứng khoán",     "📊", 26000,  0.025),
    ("GAS", "Petrovietnam Gas",                "PV Gas",                     "Dầu khí",         "⛽", 75000,  0.018),
]

# ── Helpers ──────────────────────────────────────────────────

def _now() -> float:
    return time.time()


def _random_normal(mu: float = 0.0, sigma: float = 1.0) -> float:
    """Box-Muller transform — trả về số ngẫu nhiên phân phối chuẩn."""
    u1 = random.random()
    u2 = random.random()
    return mu + sigma * math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)


# ── Seeded PRNG cho deterministic price simulation ──────────
_SEEDED_RNG = None

def _init_seeded_rng(seed: int):
    """Khởi tạo RNG với seed cố định dựa trên timestamp (làm tròn theo interval)."""
    global _SEEDED_RNG
    _SEEDED_RNG = random.Random(seed)

def _seeded_random() -> float:
    """Lấy số ngẫu nhiên từ seeded RNG (0..1)."""
    global _SEEDED_RNG
    if _SEEDED_RNG is None:
        _SEEDED_RNG = random.Random(int(_now()))
    return _SEEDED_RNG.random()

def _seeded_normal(mu: float = 0.0, sigma: float = 1.0) -> float:
    """Box-Muller với seeded RNG."""
    u1 = _seeded_random()
    u2 = _seeded_random()
    return mu + sigma * math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)


# ── Trading Session Helpers ─────────────────────────────────

def _seconds_from_midnight(dt: datetime = None) -> int:
    """Số giây từ 00:00 của datetime cho trước (hoặc bây giờ)."""
    if dt is None:
        dt = datetime.now()
    return dt.hour * 3600 + dt.minute * 60 + dt.second

def _is_trading_session() -> bool:
    """Kiểm tra hiện tại có đang trong phiên giao dịch không (theo giờ VN)."""
    sec = _seconds_from_midnight()
    if MORNING_START <= sec < MORNING_END:
        return True
    if AFTERNOON_START <= sec < AFTERNOON_END:
        return True
    return False

def _next_trading_session() -> dict:
    """
    Tính thời gian đến phiên giao dịch kế tiếp.
    Trả về dict: {in_session, next_label, seconds_until, session_name}
    """
    now = datetime.now()
    sec_now = _seconds_from_midnight(now)

    # Đang trong phiên → trả về thông tin phiên hiện tại, seconds_until=0
    if MORNING_START <= sec_now < MORNING_END:
        return {
            "in_session": True,
            "session_name": "Phiên sáng",
            "session_start": MORNING_START,
            "session_end": MORNING_END,
            "seconds_until_end": MORNING_END - sec_now,
            "seconds_until_next": 0,
        }
    if AFTERNOON_START <= sec_now < AFTERNOON_END:
        return {
            "in_session": True,
            "session_name": "Phiên chiều",
            "session_start": AFTERNOON_START,
            "session_end": AFTERNOON_END,
            "seconds_until_end": AFTERNOON_END - sec_now,
            "seconds_until_next": 0,
        }

    # Ngoài phiên: tính phiên kế tiếp
    # Nếu trước 9h sáng → phiên sáng hôm nay
    if sec_now < MORNING_START:
        return {
            "in_session": False,
            "session_name": "Phiên sáng",
            "session_start": MORNING_START,
            "session_end": MORNING_END,
            "seconds_until_next": MORNING_START - sec_now,
            "seconds_until_end": 0,
        }
    # Nếu 11:30 - 13:00 → nghỉ trưa, phiên chiều hôm nay
    if MORNING_END <= sec_now < AFTERNOON_START:
        return {
            "in_session": False,
            "session_name": "Phiên chiều",
            "session_start": AFTERNOON_START,
            "session_end": AFTERNOON_END,
            "seconds_until_next": AFTERNOON_START - sec_now,
            "seconds_until_end": 0,
        }
    # Sau 15:00 → phiên sáng ngày mai
    # Tính đến 9h sáng hôm sau
    tomorrow = now + timedelta(days=1)
    tomorrow_9am = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
    seconds_until = int((tomorrow_9am - now).total_seconds())
    return {
        "in_session": False,
        "session_name": "Phiên sáng",
        "session_start": MORNING_START,
        "session_end": MORNING_END,
        "seconds_until_next": seconds_until,
        "seconds_until_end": 0,
    }


# ── T+ Settlement Helpers ──────────────────────────────────

def _is_working_day(d: datetime) -> bool:
    """Kiểm tra ngày có phải ngày làm việc không (T2-T6)."""
    return d.weekday() < 5  # 0=Monday .. 4=Friday

def _next_working_day(d: datetime) -> datetime:
    """Trả về ngày làm việc tiếp theo (hôm sau nếu hôm nay là working day)."""
    nxt = d + timedelta(days=1)
    while not _is_working_day(nxt):
        nxt += timedelta(days=1)
    return nxt

def _add_working_days(d: datetime, n: int) -> datetime:
    """Cộng n ngày làm việc vào datetime d."""
    current = d
    added = 0
    while added < n:
        current += timedelta(days=1)
        if _is_working_day(current):
            added += 1
    return current

def _compute_tplus_release(purchase_ts: float) -> float:
    """
    Tính thời điểm (timestamp) cổ phiếu được release (có thể bán).
    Dùng T+2: 2 ngày làm việc sau ngày mua.
    Hỗ trợ stock_cooldown_reduction từ passive effects (giảm thời gian chờ T+2).
    """
    buy_dt = datetime.fromtimestamp(purchase_ts)
    # Tính T+1 (ngày làm việc đầu tiên sau mua)
    t1_dt = _add_working_days(buy_dt, 1)
    # Tính T+2 (ngày làm việc thứ hai)
    t2_dt = _add_working_days(t1_dt, 1)
    # Cả 2 đều release lúc 9h sáng
    t1_dt = t1_dt.replace(hour=9, minute=0, second=0, microsecond=0)
    t2_dt = t2_dt.replace(hour=9, minute=0, second=0, microsecond=0)

    # Đọc stock_cooldown_reduction từ passive effects
    try:
        from .item_effects import get_all_passive_effects
        passive = get_all_passive_effects()
        reduction = float(passive.get("stock_cooldown_reduction", 0.0))
        reduction = min(reduction, 0.9)  # cap 90%
        if reduction > 0:
            # Nội suy tuyến tính giữa T+1 và T+2 dựa trên % giảm
            gap = t2_dt.timestamp() - t1_dt.timestamp()
            release_ts = t1_dt.timestamp() + gap * (1.0 - reduction)
            return release_ts
    except Exception:
        pass

    return t2_dt.timestamp()


def _get_market() -> dict:
    return cfg_dict(_KEY_MARKET, {})


def _save_market(data: dict):
    cfg_set(_KEY_MARKET, data)


def _get_portfolio() -> list:
    return cfg_list(_KEY_PORTFOLIO, [])


def _save_portfolio(p: list):
    cfg_set(_KEY_PORTFOLIO, p)


def _get_history() -> dict:
    return cfg_dict(_KEY_HISTORY, {})


def _save_history(h: dict):
    cfg_set(_KEY_HISTORY, h)


def _get_txns() -> list:
    return cfg_list(_KEY_TXNS, [])


def _save_txns(t: list):
    cfg_set(_KEY_TXNS, t)


def _fmt_ts(ts: float = None) -> str:
    dt = datetime.fromtimestamp(ts if ts is not None else _now())
    return dt.strftime("%d/%m/%Y %H:%M")


def _cfg_get_raw(key: str, default=None):
    """Lấy raw config value (hỗ trợ float/ int/ str, không ép kiểu dict)."""
    if not col_ready():
        return default
    try:
        from aqt import mw
        if mw is None or mw.col is None:
            return default
        return mw.col.get_config(key, default)
    except Exception:
        return default


# ── Khởi tạo / Seed ─────────────────────────────────────────

def _seed_market_if_empty(market: dict) -> dict:
    """Nếu thị trường chưa có dữ liệu, tạo mới với giá mặc định."""
    if market and any(
        isinstance(v, dict) and v.get("current_price", 0) > 0 for v in market.values()
    ):
        return market

    now = _now()
    seeded = {}
    for sym, name, short, sector, emoji, base, vol in STOCK_MASTER:
        seeded[sym] = {
            "symbol":          sym,
            "company_name":    name,
            "short_name":      short,
            "sector":          sector,
            "sector_emoji":    emoji,
            "base_price":      base,
            "current_price":   base,
            "previous_close":  base,
            "open_price":      base,
            "high":            base,
            "low":             base,
            "volume":          0,
            "change":          0,
            "change_pct":      0.0,
            "volatility":      vol,
            "last_updated":    now,
        }
    return seeded


# ── Price Simulation ─────────────────────────────────────────

def _simulate_price_changes(market: dict) -> dict:
    """
    Random walk + mean reversion cho từng mã.
    Dùng seeded RNG (PRNG) để kết quả đồng nhất trong 1 lần gọi.
    Cập nhật: current_price, high, low, volume, change, change_pct
    """
    now = _now()
    updated = {}

    for sym, stock in market.items():
        if not isinstance(stock, dict):
            continue

        base      = float(stock.get("base_price", 10000))
        prev_close = float(stock.get("previous_close", base))
        cur       = float(stock.get("current_price", base))
        vol       = float(stock.get("volatility", 0.015))

        # Random walk — seeded PRNG
        daily_return = _seeded_normal(0.0, vol)
        # Mean reversion: kéo về base_price nếu đang xa
        mean_rev = 0.05 * (base - cur) / base
        change_pct = daily_return + mean_rev
        new_price = cur * (1.0 + change_pct)

        # Floor / ceiling
        min_price = base * 0.01
        max_price = base * 3.0
        new_price = max(min_price, min(new_price, max_price))
        new_price = round(new_price, -1)  # Làm tròn về hàng chục (VND)

        # Volume ngẫu nhiên — seeded
        avg_volume = int(_seeded_random() * 1_800_000) + 200_000
        vol_mult   = _seeded_random() * 1.0 + 0.5
        volume     = int(avg_volume * vol_mult)

        # High / Low
        high = max(prev_close, new_price, float(stock.get("open_price", prev_close)))
        low  = min(prev_close, new_price, float(stock.get("open_price", prev_close)))
        # Thêm biên nhỏ — seeded
        spread_high = new_price * (_seeded_random() * 0.007 + 1.001)
        spread_low  = new_price * (_seeded_random() * 0.007 + 0.992)
        high = max(high, spread_high)
        low  = min(low, spread_low)

        change   = int(new_price - prev_close)
        change_pct_val = round((change / prev_close) * 100, 2) if prev_close > 0 else 0.0

        updated[sym] = {
            **stock,
            "previous_close": int(prev_close) if stock.get("previous_close") else int(cur),
            "open_price":     int(stock.get("open_price", cur)),
            "current_price":  int(new_price),
            "high":           int(high),
            "low":            int(low),
            "volume":         volume,
            "change":         int(change),
            "change_pct":     change_pct_val,
            "last_updated":   now,
        }

    return updated


def _append_history(market: dict):
    """Thêm entry price history cho mỗi mã."""
    hist = _get_history()
    for sym, stock in market.items():
        if not isinstance(stock, dict):
            continue
        price = stock.get("current_price", 0)
        ts    = stock.get("last_updated", _now())
        if sym not in hist or not isinstance(hist[sym], list):
            hist[sym] = []
        hist[sym].append([ts, price])
        # Giới hạn
        if len(hist[sym]) > MAX_HISTORY_ENTRIES:
            hist[sym] = hist[sym][-MAX_HISTORY_ENTRIES:]
    _save_history(hist)


# ════════════════════════════════════════════════════════════════
#  Dividend System
# ════════════════════════════════════════════════════════════════

def _get_dividend_data() -> dict:
    """{symbol: {"last_div": float, "total_paid": int, "yield_pct": float}}"""
    return cfg_dict(_KEY_DIVIDENDS, {})

def _save_dividend_data(data: dict):
    cfg_set(_KEY_DIVIDENDS, data)

def _get_div_events() -> list:
    return cfg_list(_KEY_DIV_EVENTS, [])

def _save_div_events(events: list):
    cfg_set(_KEY_DIV_EVENTS, events)

def _process_dividends(market: dict) -> list:
    """
    Xử lý cổ tức tiền mặt cho tất cả stock.
    Sử dụng tỷ lệ cổ tức theo ngành tham khảo thực tế Việt Nam.
    Chỉ trả nếu giá > DIV_PRICE_THRESHOLD (85%) base_price.
    Mỗi stock có DIV_CHANCE (30%) được trả cổ tức mỗi lần update.
    Trả về list event dict.
    """
    now = _now()
    div_data = _get_dividend_data()
    portfolio = _get_portfolio()
    events = []

    for sym, stock in market.items():
        if not isinstance(stock, dict):
            continue
        base_price = float(stock.get("base_price", 0))
        cur_price = float(stock.get("current_price", 0))
        sector = stock.get("sector", "")
        if base_price <= 0 or cur_price <= 0:
            continue

        # Random seed deterministic
        cycle = int(now // UPDATE_INTERVAL_SECS) if UPDATE_INTERVAL_SECS > 0 else int(now)
        seed = hash(f"div_{sym}_{cycle}") & 0x7FFFFFFF
        rng = random.Random(seed)

        # Check chance
        if rng.random() >= DIV_CHANCE:
            continue
        # Check price threshold
        if cur_price < base_price * DIV_PRICE_THRESHOLD:
            continue

        # Lấy yield range theo ngành (tham khảo thực tế)
        yield_range = DIV_YIELD_BY_SECTOR.get(sector, DIV_FALLBACK_YIELD)
        # Tính cổ tức per share dựa trên yield theo ngành
        div_per_share = int(base_price * rng.uniform(yield_range[0], yield_range[1]))
        div_per_share = max(100, div_per_share)  # tối thiểu 100đ/cp

        # Cập nhật dividend data
        if sym not in div_data:
            div_data[sym] = {"last_div": 0, "total_paid": 0, "yield_pct": 0.0}
        div_data[sym]["last_div"] = now
        div_data[sym]["total_paid"] = div_data[sym].get("total_paid", 0) + div_per_share
        div_data[sym]["yield_pct"] = round((div_per_share / base_price) * 100, 2)

        # Trả cổ tức cho holder
        total_div_paid = 0
        for holding in portfolio:
            if holding.get("symbol") == sym:
                shares = holding.get("shares", 0)
                if shares > 0:
                    div_amount = div_per_share * shares
                    total_div_paid += div_amount
                    # Ghi nhận vào holding
                    holding["total_dividends"] = holding.get("total_dividends", 0) + div_amount

        # Ghi event
        event = {
            "type": "dividend",
            "symbol": sym,
            "div_per_share": div_per_share,
            "total_paid": total_div_paid,
            "timestamp": now,
            "date": _fmt_ts(now),
        }
        events.append(event)

        # Ghi vào balance nếu có holder
        if total_div_paid > 0:
            try:
                from .balance import get_balance, set_balance_and_log
                from .transactions import add_transaction
                new_bal = get_balance() + total_div_paid
                set_balance_and_log(new_bal, "dividend", total_div_paid,
                                    f"Cổ tức {sym} ({div_per_share:,}đ/cp)".replace(",", "."))
                add_transaction("dividend", total_div_paid,
                                f"💰 Cổ tức {sym}: {total_div_paid:,}đ ({div_per_share:,}đ/cp × {sum(h.get('shares',0) for h in portfolio if h.get('symbol')==sym)} cp)".replace(",", "."),
                                {"symbol": sym, "div_per_share": div_per_share, "total": total_div_paid})
            except Exception:
                pass

    _save_dividend_data(div_data)
    if portfolio:
        _save_portfolio(portfolio)

    # Lưu events vào lịch sử
    if events:
        div_history = _get_div_events()
        div_history.extend(events)
        if len(div_history) > 100:
            div_history = div_history[-100:]
        _save_div_events(div_history)

    return events


def get_dividend_history(symbol: str = None, limit: int = 20) -> list:
    """Lịch sử cổ tức đã nhận."""
    events = _get_div_events()
    if symbol:
        symbol = symbol.upper()
        events = [e for e in events if e.get("symbol") == symbol]
    events_sorted = sorted(events, key=lambda e: e.get("timestamp", 0), reverse=True)
    return events_sorted[:limit]


def get_dividend_summary() -> dict:
    """Tổng quan cổ tức: tổng đã nhận, số lần, yield trung bình."""
    div_data = _get_dividend_data()
    total_received = sum(d.get("total_paid", 0) for d in div_data.values())
    symbols_with_div = len([d for d in div_data.values() if d.get("total_paid", 0) > 0])
    avg_yield = 0.0
    if symbols_with_div > 0:
        yields = [d.get("yield_pct", 0) for d in div_data.values() if d.get("total_paid", 0) > 0]
        avg_yield = round(sum(yields) / len(yields), 2) if yields else 0.0
    return {
        "total_received": total_received,
        "symbol_count": symbols_with_div,
        "avg_yield_pct": avg_yield,
        "recent": get_dividend_history(limit=5),
    }


# ════════════════════════════════════════════════════════════════
#  Corporate Actions
# ════════════════════════════════════════════════════════════════

def _get_corp_action_data() -> list:
    return cfg_list(_KEY_CORP_ACTIONS, [])

def _save_corp_action_data(data: list):
    cfg_set(_KEY_CORP_ACTIONS, data)

def _get_ca_events() -> list:
    return cfg_list(_KEY_CA_EVENTS, [])

def _save_ca_events(events: list):
    cfg_set(_KEY_CA_EVENTS, events)

def _process_corporate_actions(market: dict) -> list:
    """
    Xử lý corporate actions cho tất cả stock:
      - Stock split (giá > 200% base)
      - Bonus shares (tăng > 5% trong phiên)
      - Rights issue (giá < 70% base)
    Trả về list event dict.
    """
    now = _now()
    portfolio = _get_portfolio()
    events = []

    for sym, stock in market.items():
        if not isinstance(stock, dict):
            continue

        if sym not in [h["symbol"] for h in portfolio]:
            continue  # Chỉ xử lý nếu có holder

        base_price = float(stock.get("base_price", 0))
        cur_price = float(stock.get("current_price", 0))
        change_pct = float(stock.get("change_pct", 0))
        if base_price <= 0:
            continue

        cycle = int(now // UPDATE_INTERVAL_SECS) if UPDATE_INTERVAL_SECS > 0 else int(now)
        seed = hash(f"ca_{sym}_{cycle}") & 0x7FFFFFFF
        rng = random.Random(seed)

        # ── Stock Split ──
        if cur_price >= base_price * SPLIT_PRICE_THRESHOLD and rng.random() < SPLIT_CHANCE:
            # Chọn tỷ lệ split
            ratios = [2, 3, 5]
            ratio = rng.choice(ratios)
            for holding in portfolio:
                if holding.get("symbol") == sym:
                    old_shares = holding["shares"]
                    new_shares = old_shares * ratio
                    new_avg_cost = int(holding.get("avg_cost", 0) / ratio)
                    holding["shares"] = new_shares
                    holding["avg_cost"] = max(1000, new_avg_cost)
                    # total_invested không đổi
                    holding["bonus_shares"] = holding.get("bonus_shares", 0) + (new_shares - old_shares)

            # Cập nhật giá thị trường
            if sym in market and isinstance(market[sym], dict):
                market[sym]["current_price"] = int(cur_price / ratio)
                market[sym]["base_price"] = int(base_price / ratio)

            event = {
                "type": "stock_split",
                "symbol": sym,
                "ratio": ratio,
                "desc": f"🔀 {sym} tách cổ phiếu tỷ lệ {ratio}:1",
                "timestamp": now,
                "date": _fmt_ts(now),
            }
            events.append(event)

            try:
                from .transactions import add_transaction
                add_transaction("stock_split", 0,
                                f"🔀 {sym} tách cổ phiếu tỷ lệ {ratio}:1",
                                {"symbol": sym, "ratio": ratio})
            except Exception:
                pass
            continue

        # ── Bonus Shares ──
        if change_pct > BONUS_MIN_CHANGE and rng.random() < BONUS_CHANCE:
            bonus_pct = rng.uniform(BONUS_RATIO_MIN, BONUS_RATIO_MAX)
            for holding in portfolio:
                if holding.get("symbol") == sym:
                    old_shares = holding["shares"]
                    bonus_shares = max(1, int(old_shares * bonus_pct))
                    new_shares = old_shares + bonus_shares
                    # avg_cost giảm (pha loãng)
                    invested = holding.get("total_invested", 0)
                    new_avg_cost = int(invested / new_shares) if new_shares > 0 else 0
                    holding["shares"] = new_shares
                    holding["avg_cost"] = max(1000, new_avg_cost)
                    holding["bonus_shares"] = holding.get("bonus_shares", 0) + bonus_shares

            event = {
                "type": "bonus_share",
                "symbol": sym,
                "bonus_pct": round(bonus_pct * 100, 1),
                "desc": f"🎁 {sym} phát cổ phiếu thưởng {round(bonus_pct*100,1)}%",
                "timestamp": now,
                "date": _fmt_ts(now),
            }
            events.append(event)

            try:
                from .transactions import add_transaction
                add_transaction("bonus_share", 0,
                                f"🎁 {sym} cổ phiếu thưởng {round(bonus_pct*100,1)}%",
                                {"symbol": sym, "bonus_pct": round(bonus_pct*100,1)})
            except Exception:
                pass
            continue

        # ── Rights Issue ──
        if cur_price < base_price * RIGHTS_PRICE_THRESHOLD and rng.random() < RIGHTS_CHANCE:
            for holding in portfolio:
                if holding.get("symbol") == sym:
                    shares = holding["shares"]
                    rights_shares = max(1, int(shares * RIGHTS_RATIO))
                    preferred_price = int(cur_price * RIGHTS_DISCOUNT)
                    cost = preferred_price * rights_shares

                    # Tự động thực hiện quyền (mua thêm)
                    try:
                        from .balance import get_balance, set_balance
                        bal = get_balance()
                        if bal >= cost:
                            set_balance(bal - cost)
                            new_shares = shares + rights_shares
                            invested = holding.get("total_invested", 0) + cost
                            holding["shares"] = new_shares
                            holding["total_invested"] = invested
                            holding["avg_cost"] = int(invested / new_shares)
                            holding["bonus_shares"] = holding.get("bonus_shares", 0) + rights_shares

                            event = {
                                "type": "rights_issue",
                                "symbol": sym,
                                "rights_shares": rights_shares,
                                "preferred_price": preferred_price,
                                "cost": cost,
                                "desc": f"📋 {sym} phát hành quyền mua: +{rights_shares} cp giá {preferred_price:,}đ".replace(",", "."),
                                "timestamp": now,
                                "date": _fmt_ts(now),
                            }
                            events.append(event)

                            try:
                                from .transactions import add_transaction
                                add_transaction("rights_issue", cost,
                                                f"📋 {sym} quyền mua: {rights_shares} cp × {preferred_price:,}đ".replace(",","."),
                                                {"symbol": sym, "shares": rights_shares, "price": preferred_price})
                            except Exception:
                                pass
                    except Exception:
                        pass

    if portfolio:
        _save_portfolio(portfolio)

    # Lưu events
    if events:
        ca_history = _get_ca_events()
        ca_history.extend(events)
        if len(ca_history) > 100:
            ca_history = ca_history[-100:]
        _save_ca_events(ca_history)

    return events


def get_corporate_action_history(limit: int = 20) -> list:
    """Lịch sử corporate actions."""
    events = _get_ca_events()
    events_sorted = sorted(events, key=lambda e: e.get("timestamp", 0), reverse=True)
    return events_sorted[:limit]


# ════════════════════════════════════════════════════════════════
#  Limit / Stop-Loss Orders
# ════════════════════════════════════════════════════════════════

_KEY_LIMIT_ORDERS = "anki_tycoon_stocks_limit_orders"  # list[order]

def _get_limit_orders() -> list:
    """Đọc danh sách limit/stop-loss orders từ config."""
    return cfg_list(_KEY_LIMIT_ORDERS, [])

def _save_limit_orders(orders: list):
    """Lưu danh sách orders."""
    cfg_set(_KEY_LIMIT_ORDERS, orders)

def place_limit_order(symbol: str, order_type: str, trigger_price: int,
                      quantity: int, direction: str = "buy") -> dict:
    """
    Đặt lệnh Limit / Stop-Loss.

    Parameters:
      symbol        — mã cổ phiếu (VD: "VCB")
      order_type    — "limit" hoặc "stop_loss"
      trigger_price — giá kích hoạt (VND)
      quantity      — số lượng cổ phiếu
      direction     — "buy" hoặc "sell"

    Trả về {ok, error, order_id, ...}
    """
    if not col_ready():
        return {"ok": False, "error": "Collection chưa sẵn sàng."}
    if symbol.upper() not in {s[0] for s in STOCK_MASTER}:
        return {"ok": False, "error": f"Mã {symbol} không tồn tại."}
    if order_type not in ("limit", "stop_loss"):
        return {"ok": False, "error": "Loại lệnh phải là 'limit' hoặc 'stop_loss'."}
    if direction not in ("buy", "sell"):
        return {"ok": False, "error": "Chiều giao dịch phải là 'buy' hoặc 'sell'."}
    if trigger_price <= 0 or quantity <= 0:
        return {"ok": False, "error": "Giá và số lượng phải > 0."}
    if quantity > 1_000_000:
        return {"ok": False, "error": "Số lượng vượt quá giới hạn (1.000.000 CP)."}

    symbol = symbol.upper()
    orders = _get_limit_orders()

    order = {
        "order_id":      f"{symbol}_{order_type}_{int(_now() * 1000)}_{len(orders)}",
        "symbol":        symbol,
        "order_type":    order_type,
        "direction":     direction,
        "trigger_price": trigger_price,
        "quantity":      quantity,
        "filled_qty":    0,
        "status":        "active",       # active | partially_filled | filled | cancelled | expired
        "created_at":    _now(),
        "created_at_str": _fmt_ts(),
    }
    orders.append(order)
    _save_limit_orders(orders)

    label = "Limit" if order_type == "limit" else "Stop-Loss"
    return {
        "ok":       True,
        "order_id": order["order_id"],
        "message":  f"✅ Đã đặt lệnh {label} {direction} {symbol}: {quantity:,} CP @ {trigger_price:,}đ".replace(",", "."),
    }


def cancel_limit_order(order_id: str) -> dict:
    """Huỷ lệnh limit/stop-loss đang active."""
    orders = _get_limit_orders()
    for o in orders:
        if o.get("order_id") == order_id and o.get("status") == "active":
            o["status"] = "cancelled"
            o["cancelled_at"] = _now()
            _save_limit_orders(orders)
            return {"ok": True, "message": f"✅ Đã huỷ lệnh {order_id}."}
    return {"ok": False, "error": f"Không tìm thấy lệnh active với ID {order_id}."}


def get_limit_orders(status: str = None) -> list:
    """
    Lấy danh sách limit/stop-loss orders.
    status: None = tất cả, "active", "filled", "cancelled", "expired"
    """
    orders = _get_limit_orders()
    orders_sorted = sorted(orders, key=lambda o: o.get("created_at", 0), reverse=True)
    if status:
        orders_sorted = [o for o in orders_sorted if o.get("status") == status]
    return orders_sorted


def _process_limit_orders(market: dict) -> list:
    """
    Xử lý tất cả limit/stop-loss orders đang active.
    Chạy sau mỗi lần update giá.

    - Limit buy:  nếu giá hiện tại <= trigger_price → mua
    - Limit sell: nếu giá hiện tại >= trigger_price → bán
    - Stop-loss:  nếu giá hiện tại <= trigger_price → bán (cắt lỗ)

    Trả về list các order đã được khớp (filled).
    """
    if not col_ready():
        return []

    orders = _get_limit_orders()
    if not orders:
        return []

    portfolio = _get_portfolio()
    from .balance import get_balance, set_balance
    filled_orders = []
    changed = False

    for o in orders:
        if o.get("status") != "active":
            continue
        sym = o["symbol"]
        stock = market.get(sym)
        if not isinstance(stock, dict):
            continue
        cur_price = float(stock.get("current_price", 0))
        if cur_price <= 0:
            continue

        trigger = o["trigger_price"]
        direction = o["direction"]
        order_type = o["order_type"]
        remaining = o["quantity"] - o.get("filled_qty", 0)
        if remaining <= 0:
            continue

        should_execute = False
        if order_type == "limit":
            if direction == "buy" and cur_price <= trigger:
                should_execute = True
            elif direction == "sell" and cur_price >= trigger:
                should_execute = True
        elif order_type == "stop_loss":
            # Stop-loss: bán khi giá giảm xuống <= trigger
            if direction == "sell" and cur_price <= trigger:
                should_execute = True

        if not should_execute:
            continue

        # --- Thực hiện lệnh ---
        if direction == "buy":
            total_cost = cur_price * remaining
            bal = get_balance()
            if bal < total_cost:
                # Không đủ tiền → mua tối đa có thể
                max_buy = int(bal // cur_price)
                if max_buy <= 0:
                    continue
                remaining = max_buy
                total_cost = cur_price * remaining
                o["status"] = "partially_filled"
            else:
                o["status"] = "filled"

            # Trừ tiền
            set_balance(get_balance() - total_cost)

            # Thêm vào portfolio
            holding = next((h for h in portfolio if h["symbol"] == sym), None)
            if holding:
                old_shares = holding["shares"]
                old_cost = holding["total_invested"]
                new_shares = old_shares + remaining
                new_cost = old_cost + total_cost
                holding["shares"] = new_shares
                holding["avg_cost"] = int(new_cost / new_shares)
                holding["total_invested"] = new_cost
            else:
                portfolio.append({
                    "symbol": sym,
                    "shares": remaining,
                    "avg_cost": cur_price,
                    "total_invested": total_cost,
                    "purchased_at": _now(),
                    "transactions": [],
                })

            # Ghi giao dịch
            try:
                from .transactions import add_transaction
                add_transaction("stock_buy", total_cost,
                    f"📈 [Limit] Mua {remaining} CP {sym} giá {cur_price:,}đ".replace(",", "."),
                    {"symbol": sym, "shares": remaining, "price": cur_price, "order_type": order_type})
            except Exception:
                pass

        elif direction == "sell":
            holding = next((h for h in portfolio if h["symbol"] == sym), None)
            if not holding or holding["shares"] <= 0:
                o["status"] = "expired"
                changed = True
                continue

            sell_qty = min(remaining, holding["shares"])
            total_received = cur_price * sell_qty

            # Cộng tiền
            set_balance(get_balance() + total_received)

            # Cập nhật portfolio
            if holding["shares"] == sell_qty:
                portfolio.remove(holding)
            else:
                portion = sell_qty / holding["shares"]
                deducted = int(holding["total_invested"] * portion)
                holding["shares"] -= sell_qty
                holding["total_invested"] -= deducted

            o["filled_qty"] = o.get("filled_qty", 0) + sell_qty
            if o["filled_qty"] >= o["quantity"]:
                o["status"] = "filled"
            else:
                o["status"] = "partially_filled"

            # Ghi giao dịch
            try:
                from .transactions import add_transaction
                add_transaction("stock_sell", total_received,
                    f"📉 [{'Stop-Loss' if order_type == 'stop_loss' else 'Limit'}] Bán {sell_qty} CP {sym} giá {cur_price:,}đ".replace(",", "."),
                    {"symbol": sym, "shares": sell_qty, "price": cur_price, "order_type": order_type})
            except Exception:
                pass

        o["filled_at"] = _now()
        o["filled_price"] = cur_price
        filled_orders.append(o)
        changed = True

    if changed:
        _save_portfolio(portfolio)
        _save_limit_orders(orders)

    return filled_orders


# ════════════════════════════════════════════════════════════════
#  Market News & Random Events
# ════════════════════════════════════════════════════════════════

_KEY_MARKET_NEWS      = "anki_tycoon_stocks_market_news"       # dict: {cycle: news_item}
_KEY_NEWS_HISTORY     = "anki_tycoon_stocks_news_history"      # list[news_item]

# ── Tin tức thị trường tham khảo thực tế ─────────────────────
# Mỗi tin có: id, title (tiếng Việt), sector (ảnh hưởng ngành),
# impact_range (tuple min/max % thay đổi giá), probability (0-1)
MARKET_NEWS_TEMPLATES = [
    # --- Ngân hàng ---
    {"id": "bank_rate_cut",       "title": "🏦 NHNN giảm lãi suất điều hành",
     "sector": "Ngân hàng",       "impact_range": (0.02, 0.05), "probability": 0.08},
    {"id": "bank_rate_hike",      "title": "🏦 NHNN tăng lãi suất điều hành",
     "sector": "Ngân hàng",       "impact_range": (-0.04, -0.01), "probability": 0.06},
    {"id": "bank_profit_up",      "title": "📊 Lợi nhuận ngân hàng quý này tăng trưởng vượt kỳ vọng",
     "sector": "Ngân hàng",       "impact_range": (0.01, 0.03), "probability": 0.10},
    {"id": "bad_debt_warning",    "title": "⚠️ Nợ xấu ngành ngân hàng có dấu hiệu gia tăng",
     "sector": "Ngân hàng",       "impact_range": (-0.03, -0.01), "probability": 0.07},
    # --- Bất động sản ---
    {"id": "realty_boom",         "title": "🏠 Thị trường BĐS phục hồi mạnh, giao dịch tăng đột biến",
     "sector": "Bất động sản",    "impact_range": (0.03, 0.07), "probability": 0.07},
    {"id": "realty_slowdown",     "title": "🏠 Thị trường BĐS trầm lắng, thanh khoản thấp",
     "sector": "Bất động sản",    "impact_range": (-0.05, -0.02), "probability": 0.07},
    {"id": "realty_policy",       "title": "📜 Chính phủ ban hành chính sách mới hỗ trợ BĐS",
     "sector": "Bất động sản",    "impact_range": (0.02, 0.04), "probability": 0.06},
    # --- Thực phẩm ---
    {"id": "food_export_boost",   "title": "🌾 Xuất khẩu nông sản tăng mạnh nhờ đơn hàng lớn từ Trung Quốc",
     "sector": "Thực phẩm",       "impact_range": (0.02, 0.05), "probability": 0.08},
    {"id": "food_price_hike",     "title": "📈 Giá nguyên liệu đầu vào tăng, biên lợi nhuận ngành thực phẩm bị thu hẹp",
     "sector": "Thực phẩm",       "impact_range": (-0.03, -0.01), "probability": 0.07},
    {"id": "dairy_competition",   "title": "🥛 Cạnh tranh sữa gay gắt, các hãng nước ngoài gia nhập thị trường",
     "sector": "Thực phẩm",       "impact_range": (-0.02, -0.01), "probability": 0.06},
    # --- Thép ---
    {"id": "steel_tariff",        "title": "🏗️ Mỹ áp thuế chống bán phá giá thép nhập khẩu từ Việt Nam",
     "sector": "Thép",            "impact_range": (-0.06, -0.02), "probability": 0.06},
    {"id": "steel_demand",        "title": "🏗️ Nhu cầu thép xây dựng trong nước tăng cao mùa cao điểm",
     "sector": "Thép",            "impact_range": (0.02, 0.05), "probability": 0.08},
    {"id": "steel_infrastructure","title": "🏗️ Hàng loạt dự án hạ tầng mới được phê duyệt, thép hưởng lợi",
     "sector": "Thép",            "impact_range": (0.03, 0.06), "probability": 0.07},
    # --- Công nghệ ---
    {"id": "tech_ai_boom",        "title": "🤖 Bùng nổ đầu tư AI tại Việt Nam, các công ty công nghệ hưởng lợi",
     "sector": "Công nghệ",       "impact_range": (0.03, 0.08), "probability": 0.07},
    {"id": "tech_cyber_attack",   "title": "💻 Cảnh báo tấn công mạng quy mô lớn nhắm vào doanh nghiệp công nghệ",
     "sector": "Công nghệ",       "impact_range": (-0.04, -0.01), "probability": 0.05},
    {"id": "tech_talent_drain",   "title": "👨‍💻 Chảy máu chất xám ngành công nghệ, nhân tài ra nước ngoài",
     "sector": "Công nghệ",       "impact_range": (-0.02, -0.01), "probability": 0.06},
    # --- Bán lẻ ---
    {"id": "retail_consumer_boost","title": "🛒 Chi tiêu tiêu dùng cuối năm tăng vọt, ngành bán lẻ hưởng lợi",
     "sector": "Bán lẻ",          "impact_range": (0.02, 0.05), "probability": 0.09},
    {"id": "retail_ecommerce",    "title": "📦 Thương mại điện tử tăng trưởng nóng, chuỗi cửa hàng truyền thống gặp khó",
     "sector": "Bán lẻ",          "impact_range": (-0.03, 0.01), "probability": 0.07},
    {"id": "retail_supply_chain", "title": "🚚 Đứt gãy chuỗi cung ứng, hàng tồn kho ngành bán lẻ tăng cao",
     "sector": "Bán lẻ",          "impact_range": (-0.03, -0.01), "probability": 0.06},
    # --- Chứng khoán ---
    {"id": "sec_market_up",       "title": "📈 VN-Index vượt đỉnh lịch sử, tâm lý nhà đầu tư hưng phấn",
     "sector": "Chứng khoán",     "impact_range": (0.04, 0.08), "probability": 0.06},
    {"id": "sec_market_crash",    "title": "📉 Thị trường chứng khoán lao dốc, nhà đầu tư tháo chạy",
     "sector": "Chứng khoán",     "impact_range": (-0.08, -0.03), "probability": 0.05},
    {"id": "sec_foreign_inflow",  "title": "🌍 Khối ngoại giải ngân mạnh, mua ròng hàng nghìn tỷ đồng",
     "sector": "Chứng khoán",     "impact_range": (0.02, 0.05), "probability": 0.07},
    # --- Dầu khí ---
    {"id": "oil_price_surge",     "title": "⛽ Giá dầu thế giới tăng vọt do căng thẳng địa chính trị",
     "sector": "Dầu khí",         "impact_range": (0.04, 0.08), "probability": 0.07},
    {"id": "oil_price_crash",     "title": "⛽ Giá dầu lao dốc do OPEC+ tăng sản lượng",
     "sector": "Dầu khí",         "impact_range": (-0.06, -0.02), "probability": 0.06},
    {"id": "gas_discovery",       "title": "⛽ Phát hiện mỏ khí đốt mới lớn nhất trong thập kỷ",
     "sector": "Dầu khí",         "impact_range": (0.03, 0.06), "probability": 0.05},
    # --- Đa ngành ---
    {"id": "conglomerate_merger", "title": "🏢 Tập đoàn lớn công bố kế hoạch M&A chiến lược",
     "sector": "Đa ngành",        "impact_range": (0.02, 0.05), "probability": 0.06},
    {"id": "conglomerate_debt",   "title": "🏢 Trái phiếu doanh nghiệp đáo hạn, áp lực thanh khoản gia tăng",
     "sector": "Đa ngành",        "impact_range": (-0.04, -0.01), "probability": 0.06},
    # --- Tin vĩ mô (ảnh hưởng toàn thị trường) ---
    {"id": "macro_gdp_growth",    "title": "📊 GDP Việt Nam quý này tăng trưởng vượt dự báo",
     "sector": None,              "impact_range": (0.01, 0.03), "probability": 0.08},
    {"id": "macro_inflation",     "title": "📊 Lạm phát tăng cao, áp lực lên mặt bằng giá chung",
     "sector": None,              "impact_range": (-0.03, -0.01), "probability": 0.07},
    {"id": "macro_fdi_inflow",    "title": "🌍 Vốn FDI đăng ký mới đạt kỷ lục, tín hiệu tích cực cho nền kinh tế",
     "sector": None,              "impact_range": (0.01, 0.04), "probability": 0.07},
    {"id": "macro_typhoon",       "title": "🌪️ Bão lũ gây thiệt hại nặng nề tại các tỉnh miền Trung",
     "sector": None,              "impact_range": (-0.03, -0.01), "probability": 0.05},
    {"id": "macro_trade_war",     "title": "🌐 Căng thẳng thương mại Mỹ-Trung leo thang, tác động đến xuất khẩu",
     "sector": None,              "impact_range": (-0.04, -0.01), "probability": 0.05},
]

NEWS_CHANCE          = 0.60   # 60% mỗi lần update có tin
NEWS_MIN_ITEMS       = 1      # số tin tối thiểu
NEWS_MAX_ITEMS       = 3      # số tin tối đa
NEWS_MAX_HISTORY     = 50     # giữ tối đa 50 tin trong lịch sử

# Cache news cycle để tránh tạo lại tin trong cùng cycle
_NEWS_CYCLE_CACHE = {}

def _get_news_history() -> list:
    return cfg_list(_KEY_NEWS_HISTORY, [])

def _save_news_history(news_list: list):
    cfg_set(_KEY_NEWS_HISTORY, news_list)

def _get_news_for_cycle() -> list | None:
    """Lấy tin tức đã tạo cho cycle hiện tại từ cache."""
    global _NEWS_CYCLE_CACHE
    cycle = int(_now() // UPDATE_INTERVAL_SECS) if UPDATE_INTERVAL_SECS > 0 else int(_now())
    return _NEWS_CYCLE_CACHE.get(cycle)

def _set_news_for_cycle(news: list):
    """Lưu tin tức cho cycle hiện tại vào cache."""
    global _NEWS_CYCLE_CACHE
    cycle = int(_now() // UPDATE_INTERVAL_SECS) if UPDATE_INTERVAL_SECS > 0 else int(_now())
    _NEWS_CYCLE_CACHE[cycle] = news
    keys = sorted(_NEWS_CYCLE_CACHE.keys())
    if len(keys) > 5:
        for k in keys[:-5]:
            del _NEWS_CYCLE_CACHE[k]

def _generate_market_news() -> list:
    """
    Tạo tin tức thị trường ngẫu nhiên cho cycle hiện tại.
    Dùng seeded RNG để deterministic trong cùng cycle.
    Trả về list các news dict.
    """
    cached = _get_news_for_cycle()
    if cached is not None:
        return cached

    cycle = int(_now() // UPDATE_INTERVAL_SECS) if UPDATE_INTERVAL_SECS > 0 else int(_now())
    seed = hash(f"news_{cycle}") & 0x7FFFFFFF
    rng = random.Random(seed)

    news_list = []
    if rng.random() < NEWS_CHANCE:
        num_items = rng.randint(NEWS_MIN_ITEMS, NEWS_MAX_ITEMS)
        # Lọc template có probability phù hợp
        available = [t for t in MARKET_NEWS_TEMPLATES if rng.random() < t["probability"]]
        if not available:
            available = MARKET_NEWS_TEMPLATES
        selected = rng.sample(available, min(num_items, len(available)))
        for t in selected:
            impact_pct = rng.uniform(t["impact_range"][0], t["impact_range"][1])
            news_list.append({
                "id":         t["id"],
                "title":      t["title"],
                "sector":     t["sector"],
                "impact_pct": round(impact_pct, 4),
                "cycle":      cycle,
                "timestamp":  _now(),
                "date":       _fmt_ts(),
            })

    _set_news_for_cycle(news_list)
    return news_list


def _apply_news_impact(market: dict) -> list:
    """
    Áp dụng ảnh hưởng của tin tức lên giá cổ phiếu.
    Chạy sau _simulate_price_changes, trước _process_dividends.

    - Tin theo sector: chỉ ảnh hưởng mã thuộc ngành đó
    - Tin vĩ mô (sector=None): ảnh hưởng toàn bộ thị trường (giảm 50% impact)
    Trả về list news đã áp dụng.
    """
    news_list = _generate_market_news()
    if not news_list:
        return []

    applied = []
    for news in news_list:
        impact = news["impact_pct"]
        sector = news["sector"]
        affected = []
        for sym, stock in market.items():
            if not isinstance(stock, dict):
                continue
            cur = float(stock.get("current_price", 0))
            if cur <= 0:
                continue
            if sector is None:
                # Tin vĩ mô: ảnh hưởng toàn thị trường với 50% impact
                adj = cur * (1.0 + impact * 0.5)
            elif stock.get("sector") == sector:
                adj = cur * (1.0 + impact)
            else:
                continue
            adj = max(adj, cur * 0.5)  # không giảm quá 50%
            adj = min(adj, cur * 1.5)  # không tăng quá 50%
            stock["current_price"] = int(adj)
            stock["change"] = int(adj - float(stock.get("previous_close", cur)))
            stock["change_pct"] = round(((adj - float(stock.get("previous_close", cur))) / float(stock.get("previous_close", cur))) * 100, 2) if float(stock.get("previous_close", 0)) > 0 else 0.0
            affected.append(sym)

        news["affected_symbols"] = affected
        applied.append(news)

    # Lưu news vào lịch sử
    if applied:
        history = _get_news_history()
        history.extend(applied)
        if len(history) > NEWS_MAX_HISTORY:
            history = history[-NEWS_MAX_HISTORY:]
        _save_news_history(history)

    return applied


def get_market_news(limit: int = 10) -> list:
    """Lấy lịch sử tin tức thị trường gần đây."""
    history = _get_news_history()
    history_sorted = sorted(history, key=lambda n: n.get("timestamp", 0), reverse=True)
    return history_sorted[:limit]


def get_current_news() -> list:
    """Lấy tin tức của cycle hiện tại (dùng cho UI real-time)."""
    return _generate_market_news()


# ── Public API ───────────────────────────────────────────────

def _seed_rng_for_simulation():
    """
    Seed RNG dựa trên timestamp hiện tại làm tròn theo UPDATE_INTERVAL_SECS.
    Đảm bảo mọi lần gọi _simulate_price_changes trong cùng khoảng interval
    đều cho kết quả giống hệt nhau.
    """
    now = _now()
    # Làm tròn timestamp về bội số của UPDATE_INTERVAL_SECS
    interval_seed = int(now // UPDATE_INTERVAL_SECS) if UPDATE_INTERVAL_SECS > 0 else int(now)
    _init_seeded_rng(interval_seed)


def update_prices_if_needed() -> bool:
    """
    Kiểm tra và cập nhật giá nếu:
      - Chưa có dữ liệu thị trường (seed)
      - Đã hết interval UPDATE_INTERVAL_SECS
    Trả về True nếu có cập nhật.
    """
    if not col_ready():
        return False

    market = _get_market()
    now    = _now()
    last   = _cfg_get_raw(_KEY_LAST_UPDATE, 0.0)
    last_ts = float(last) if isinstance(last, (int, float)) else 0.0

    # Seed nếu rỗng
    if not market:
        market = _seed_market_if_empty(market)
        _save_market(market)
        # Update luôn lần đầu
        _seed_rng_for_simulation()
        market = _simulate_price_changes(market)
        _save_market(market)
        _append_history(market)
        cfg_set(_KEY_LAST_UPDATE, now)
        return True

    elapsed = now - last_ts
    if elapsed >= UPDATE_INTERVAL_SECS:
        # Lưu previous_close trước khi update
        for sym, stock in market.items():
            if isinstance(stock, dict):
                stock["previous_close"] = stock.get("current_price", stock.get("base_price", 0))
        _seed_rng_for_simulation()
        market = _simulate_price_changes(market)
        # Áp dụng tin tức thị trường (sau price simulation, trước dividends)
        try:
            _apply_news_impact(market)
        except Exception:
            pass
        _save_market(market)
        _append_history(market)
        cfg_set(_KEY_LAST_UPDATE, now)
        # Xử lý cổ tức + corporate actions
        try:
            _process_dividends(market)
        except Exception:
            pass
        try:
            _process_corporate_actions(market)
        except Exception:
            pass
        # Xử lý limit/stop-loss orders
        try:
            _process_limit_orders(market)
        except Exception:
            pass
        return True

    return False


def _force_update_prices():
    """
    Luôn chạy price simulation (không check interval).
    Dùng khi mở tab CK để giá luôn mới.
    """
    market = _get_market()
    if not market:
        return False
    now = _now()
    for sym, stock in market.items():
        if isinstance(stock, dict):
            stock["previous_close"] = stock.get("current_price", stock.get("base_price", 0))
    _seed_rng_for_simulation()
    market = _simulate_price_changes(market)
    # Áp dụng tin tức thị trường (sau price simulation, trước dividends)
    try:
        _apply_news_impact(market)
    except Exception:
        pass
    _save_market(market)
    _append_history(market)
    cfg_set(_KEY_LAST_UPDATE, now)
    # Xử lý cổ tức + corporate actions
    try:
        _process_dividends(market)
    except Exception:
        pass
    try:
        _process_corporate_actions(market)
    except Exception:
        pass
    # Xử lý limit/stop-loss orders
    try:
        _process_limit_orders(market)
    except Exception:
        pass
    return True


def get_market_data() -> dict:
    """
    Trả về toàn bộ thị trường (dict{symbol: stock_data}).
    - Chỉ seed / update nếu đã đến hạn (4h) hoặc lần đầu.
    - KHÔNG force update — giá chỉ thay đổi khi:
        * Lần đầu mở app
        * Đã qua 4h (dự phòng)
        * Ôn đủ REVIEWS_PER_UPDATE thẻ (50 thẻ)
    """
    update_prices_if_needed()
    return _get_market()


def get_market_data_array() -> list:
    """
    Trả về thị trường dưới dạng list (mỗi phần tử là 1 stock dict).
    Dùng cho bridge gửi sang JS — JS cần array để .filter() / .find().
    Các field name được map để JS dùng: company, price, short, ...
    """
    market = get_market_data()
    result = []
    for sym, stock in market.items():
        if isinstance(stock, dict):
            result.append({
                "symbol":     sym,
                "company":    stock.get("company_name", ""),
                "short":      stock.get("short_name", ""),
                "sector":     stock.get("sector", ""),
                "sector_emoji": stock.get("sector_emoji", "📈"),
                "price":      stock.get("current_price", 0),
                "change":     stock.get("change", 0),
                "change_pct": stock.get("change_pct", 0.0),
                "volume":     stock.get("volume", 0),
                "high":       stock.get("high", 0),
                "low":        stock.get("low", 0),
                "base_price": stock.get("base_price", 0),
            })
    return result


def _cycle_trading_session():
    """
    Chuyển đổi phiên giao dịch mô phỏng dựa trên số thẻ đã ôn.
    Cứ 50 thẻ sẽ chuyển giữa Phiên sáng ↔ Phiên chiều.
    Giữ nguyên cơ chế phiên theo giờ thực (time-based) — override này
    chỉ ảnh hưởng đến get_trading_session_info().
    """
    try:
        current_session = cfg_dict(_KEY_SIMULATED_SESSION, {}).get("session", None)
        if current_session == "morning":
            new_session = "afternoon"
        else:
            new_session = "morning"
        cfg_set(_KEY_SIMULATED_SESSION, {
            "session": new_session,
            "updated_by": "review",
            "timestamp": _now(),
        })
    except Exception:
        pass


def record_review(count: int = 1):
    """
    Ghi nhận số thẻ vừa ôn.
    Khi tổng số thẻ >= threshold (có randomness 40-60):
      - Tự động cập nhật giá
      - Chuyển phiên giao dịch mô phỏng (sáng ↔ chiều)
    Giữ nguyên cơ chế phiên theo giờ thực.
    """
    try:
        current = cfg_int(_KEY_REVIEW_COUNT, 0)
        current += count
        threshold = _get_reviews_threshold()
        if current >= threshold:
            _force_update_prices()
            _cycle_trading_session()
            cfg_set(_KEY_REVIEW_COUNT, 0)
        else:
            cfg_set(_KEY_REVIEW_COUNT, current)
    except Exception:
        pass


def get_stock_price(symbol: str) -> dict | None:
    """Trả về thông tin 1 mã cụ thể."""
    market = get_market_data()
    return market.get(symbol.upper())


def get_stock_history(symbol: str, limit: int = 50) -> list:
    """Lịch sử giá gần đây cho biểu đồ."""
    hist = _get_history()
    symbol = symbol.upper()
    entries = hist.get(symbol, [])
    return entries[-limit:]


def get_market_summary() -> dict:
    """
    Tổng quan thị trường:
      - Số mã tăng / giảm / đứng
      - Tổng volume
      - VN-Index mô phỏng
    """
    market = get_market_data()
    up = dn = flat = 0
    total_vol = 0
    total_price = 0.0
    count = 0

    for sym, stock in market.items():
        if not isinstance(stock, dict):
            continue
        chg = stock.get("change", 0) or 0
        if chg > 0:
            up += 1
        elif chg < 0:
            dn += 1
        else:
            flat += 1
        total_vol += stock.get("volume", 0) or 0
        total_price += stock.get("current_price", 0) or 0
        count += 1

    # VN-Index mô phỏng: tổng giá trị / số mã (scaled)
    vnindex = round(total_price / max(count, 1), 2) if count > 0 else 1000.0

    # Tính % thay đổi VN-Index so với phiên trước
    total_prev = sum(
        float(s.get("previous_close", s.get("current_price", 0)))
        for s in market.values() if isinstance(s, dict)
    )
    vnindex_change = 0.0
    vnindex_change_pct = 0.0
    if total_prev > 0 and count > 0:
        prev_vnindex = total_prev / count
        vnindex_change = round(vnindex - prev_vnindex, 2)
        vnindex_change_pct = round((vnindex_change / prev_vnindex) * 100, 2) if prev_vnindex else 0.0

    return {
        "vnindex":           vnindex,
        "vnindex_change":    vnindex_change,
        "vnindex_change_pct": vnindex_change_pct,
        "up":                up,
        "down":              dn,
        "flat":              flat,
        "total_volume":      total_vol,
        "last_updated":      _fmt_ts(),
    }


# ── Giao dịch ────────────────────────────────────────────────

def buy_stock(symbol: str, shares: int) -> dict:
    """Mua cổ phiếu. Trả về {ok, error, ...}."""
    print(f"[CK DEBUG] buy_stock CALLED: symbol={symbol!r}, shares={shares!r}, type(shares)={type(shares).__name__}")
    if not col_ready():
        print("[CK DEBUG] col_ready() == False")
        return {"ok": False, "error": "Collection chưa sẵn sàng."}

    if shares <= 0:
        print(f"[CK DEBUG] shares <= 0: {shares}")
        return {"ok": False, "error": "Số lượng không hợp lệ."}

    if shares > 1_000_000:
        return {"ok": False, "error": "Số lượng vượt quá giới hạn (1.000.000 CP)."}

    market = get_market_data()
    symbol = symbol.upper()
    print(f"[CK DEBUG] market keys: {list(market.keys()) if isinstance(market, dict) else type(market).__name__}")
    stock = market.get(symbol)
    if not stock:
        print(f"[CK DEBUG] stock not found for {symbol}")
        return {"ok": False, "error": f"Mã {symbol} không tồn tại."}

    price = stock.get("current_price", 0)
    print(f"[CK DEBUG] price={price!r} (type={type(price).__name__}), base_price={stock.get('base_price')}")
    total = price * shares
    print(f"[CK DEBUG] total={total!r} (type={type(total).__name__})")

    # Kiểm tra số dư
    from .balance import get_balance, set_balance
    bal = get_balance()
    print(f"[CK DEBUG] balance={bal!r}, total={total!r}, bal < total = {bal < total}")
    if bal < total:
        shortage = total - bal
        return {
            "ok": False,
            "error": f"Không đủ tiền! Cần thêm {shortage:,} VND.".replace(",", "."),
        }

    # Trừ tiền
    new_bal = bal - total
    print(f"[CK DEBUG] new_bal={new_bal!r}, calling set_balance({new_bal!r})")
    set_balance(new_bal)

    # Cập nhật portfolio
    portfolio = _get_portfolio()
    holding = next((h for h in portfolio if h["symbol"] == symbol), None)

    txn_ts = _now()
    txn = {
        "type":       "buy",
        "symbol":     symbol,
        "shares":     shares,
        "price":      price,
        "total":      total,
        "timestamp":  txn_ts,
    }

    if holding:
        # Cập nhật avg_cost
        old_shares = holding["shares"]
        old_cost   = holding["total_invested"]
        new_shares = old_shares + shares
        new_cost   = old_cost + total
        holding["shares"]          = new_shares
        holding["avg_cost"]        = int(new_cost / new_shares)
        holding["total_invested"]  = new_cost
        holding["transactions"].append(txn)
        # Cập nhật purchased_at (lần mua gần nhất) để tính T+2
        holding["purchased_at"] = max(holding.get("purchased_at", 0), txn_ts)
    else:
        portfolio.append({
            "symbol":         symbol,
            "shares":         shares,
            "avg_cost":       price,
            "total_invested": total,
            "purchased_at":   txn_ts,    # timestamp mua — dùng cho T+2
            "transactions":   [txn],
        })

    _save_portfolio(portfolio)

    # Ghi lịch sử giao dịch chứng khoán
    txns = _get_txns()
    txns.append({
        **txn,
        "company_name": stock.get("company_name", symbol),
        "sector_emoji": stock.get("sector_emoji", "📈"),
        "date":         _fmt_ts(txn.get("timestamp")),
    })
    _save_txns(txns)

    # Ghi giao dịch chung — dùng type "stock_buy" riêng
    from .transactions import add_transaction
    add_transaction("stock_buy", total,
                    f"📈 Mua {shares} CP {symbol} giá {price:,}đ".replace(",", "."),
                    {"symbol": symbol, "shares": shares, "price": price})

    # Achievement trigger
    try:
        from .achievements import check_and_unlock
        check_and_unlock("stock_traded", True)
    except Exception:
        pass

    return {
        "ok":          True,
        "symbol":      symbol,
        "shares":      shares,
        "price":       price,
        "total":       total,
        "new_balance": new_bal,
        "message":     f"✅ Đã mua {shares} cổ phiếu {symbol} giá {price:,}đ".replace(",", "."),
    }


def sell_stock(symbol: str, shares: int) -> dict:
    """Bán cổ phiếu với kiểm tra T+2."""
    if not col_ready():
        return {"ok": False, "error": "Collection chưa sẵn sàng."}

    if shares <= 0:
        return {"ok": False, "error": "Số lượng không hợp lệ."}

    symbol = symbol.upper()
    market = get_market_data()
    stock  = market.get(symbol)
    if not stock:
        return {"ok": False, "error": f"Mã {symbol} không tồn tại."}

    price = stock.get("current_price", 0)

    portfolio = _get_portfolio()
    holding = next((h for h in portfolio if h["symbol"] == symbol), None)
    if not holding:
        return {"ok": False, "error": f"Bạn không sở hữu cổ phiếu {symbol}."}

    if holding["shares"] < shares:
        return {
            "ok": False,
            "error": f"Bạn chỉ có {holding['shares']} CP {symbol}, không đủ để bán {shares} CP.",
        }

    # ── Kiểm tra T+2 ────────────────────────────────────────
    purchased_at = holding.get("purchased_at")
    if purchased_at:
        release_ts = _compute_tplus_release(purchased_at)
        now = _now()
        if now < release_ts:
            remaining = int(release_ts - now)
            hours = remaining // 3600
            mins = (remaining % 3600) // 60
            return {
                "ok": False,
                "error": f"Cổ phiếu {symbol} đang trong thời gian T+{T_PLUS_DAYS}. "
                         f"Có thể bán sau {hours}h{mins:02d} (sau {_fmt_ts(release_ts)}).",
            }

    # ── End T+2 check ───────────────────────────────────────

    total = price * shares

    # Cộng tiền
    from .balance import get_balance, set_balance
    new_bal = get_balance() + total
    set_balance(new_bal)

    # Cập nhật portfolio
    txn_ts = _now()
    txn = {
        "type":       "sell",
        "symbol":     symbol,
        "shares":     shares,
        "price":      price,
        "total":      total,
        "timestamp":  txn_ts,
    }

    old_shares = holding["shares"]
    if old_shares == shares:
        portfolio.remove(holding)
    else:
        # Giảm shares, avg_cost giữ nguyên
        portion = shares / old_shares
        deducted_invested = int(holding["total_invested"] * portion)
        holding["shares"]          = old_shares - shares
        holding["total_invested"]  = holding["total_invested"] - deducted_invested
        holding["transactions"].append(txn)

    _save_portfolio(portfolio)

    # Tính lời/lỗ (PHẢI tính trước khi dùng trong add_transaction)
    avg_cost   = holding.get("avg_cost", price)
    pnl        = (price - avg_cost) * shares
    pnl_str    = f"+{pnl:,}đ".replace(",", ".") if pnl >= 0 else f"{pnl:,}đ".replace(",", ".")

    # Ghi lịch sử
    txns = _get_txns()
    txns.append({
        **txn,
        "company_name": stock.get("company_name", symbol),
        "sector_emoji": stock.get("sector_emoji", "📈"),
        "date":         _fmt_ts(txn.get("timestamp")),
    })
    _save_txns(txns)

    from .transactions import add_transaction
    add_transaction("stock_sell", total,
                    f"📈 Bán {shares} CP {symbol} giá {price:,}đ".replace(",", "."),
                    {"symbol": symbol, "shares": shares, "price": price, "pnl": pnl})

    # Achievement trigger
    try:
        from .achievements import check_and_unlock
        check_and_unlock("stock_traded", True)
    except Exception:
        pass

    return {
        "ok":          True,
        "symbol":      symbol,
        "shares":      shares,
        "price":       price,
        "total":       total,
        "new_balance": new_bal,
        "pnl":         pnl,
        "message":     f"✅ Đã bán {shares} CP {symbol} giá {price:,}đ ({pnl_str})".replace(",", "."),
    }


# ── Portfolio ────────────────────────────────────────────────

def get_portfolio() -> list:
    """
    Trả về danh sách holdings kèm:
      - current_price (giá hiện tại)
      - market_value (giá trị thị trường)
      - pnl (lời/lỗ chưa thực hiện)
      - pnl_pct (%lời/lỗ)
      - sellable_at (thời gian T+2 release)
      - cooldown_remaining (giây còn lại)
    """
    update_prices_if_needed()
    market    = get_market_data()
    portfolio = _get_portfolio()
    now       = _now()

    result = []
    for h in portfolio:
        sym   = h["symbol"]
        stock = market.get(sym, {})
        cur_price = stock.get("current_price", h.get("avg_cost", 0))
        shares    = h["shares"]
        avg_cost  = h.get("avg_cost", 0)
        invested  = h.get("total_invested", 0)

        market_value = cur_price * shares
        pnl          = market_value - invested
        pnl_pct      = round((pnl / invested) * 100, 2) if invested > 0 else 0.0

        # T+2 info
        purchased_at = h.get("purchased_at")
        sellable_at = 0
        cooldown_remaining = 0
        can_sell = True
        if purchased_at:
            sellable_at = _compute_tplus_release(purchased_at)
            cooldown_remaining = max(0, int(sellable_at - now))
            can_sell = now >= sellable_at

        result.append({
            "symbol":        sym,
            "company":       stock.get("company_name", sym),
            "company_name":  stock.get("company_name", sym),
            "short_name":    stock.get("short_name", ""),
            "sector_emoji":  stock.get("sector_emoji", "📈"),
            "sector":        stock.get("sector", ""),
            "shares":        shares,
            "avg_cost":      avg_cost,
            "total_invested": invested,
            "current_price": cur_price,
            "market_value":  market_value,
            "pnl":           pnl,
            "pnl_pct":       pnl_pct,
            "change":        stock.get("change", 0),
            "change_pct":    stock.get("change_pct", 0.0),
            "purchased_at":  purchased_at or 0,
            "sellable_at":   sellable_at,
            "cooldown_remaining": cooldown_remaining,
            "can_sell":      can_sell,
        })

    return result


def get_portfolio_summary() -> dict:
    """Tổng quan portfolio: tổng vốn, giá trị thị trường, lợi nhuận."""
    holdings = get_portfolio()
    if not holdings:
        return {
            "total_invested":   0,
            "total_market_value": 0,
            "total_pnl":        0,
            "total_pnl_pct":    0.0,
            "count":            0,
        }

    total_invested  = sum(h["total_invested"] for h in holdings)
    total_mv        = sum(h["market_value"] for h in holdings)
    total_pnl       = total_mv - total_invested
    total_pnl_pct   = round((total_pnl / total_invested) * 100, 2) if total_invested > 0 else 0.0

    return {
        "total_invested":   total_invested,
        "total_market_value": total_mv,
        "total_pnl":        total_pnl,
        "total_pnl_pct":    total_pnl_pct,
        "count":            len(holdings),
    }


def get_stock_transactions(symbol: str = None) -> list:
    """Lịch sử giao dịch chứng khoán."""
    txns = _get_txns()
    if symbol:
        symbol = symbol.upper()
        txns = [t for t in txns if t.get("symbol") == symbol]
    # Sắp xếp mới nhất trước
    txns_sorted = sorted(txns, key=lambda t: t.get("timestamp", 0), reverse=True)
    return txns_sorted


def get_all_symbols() -> list:
    """Trả về danh sách tất cả mã CK kèm thông tin cơ bản."""
    return [
        {"symbol": sym, "company_name": name, "short_name": short,
         "sector": sector, "sector_emoji": emoji, "base_price": base, "volatility": vol}
        for sym, name, short, sector, emoji, base, vol in STOCK_MASTER
    ]


# ── Trading Session Info (Public) ───────────────────────────

def get_trading_session_info() -> dict:
    """
    Thông tin phiên giao dịch hiện tại và đếm ngược.
    Trả về dict gồm:
      in_session, session_name, seconds_until_end, seconds_until_next,
      session_start_str, session_end_str

    Cơ chế:
      - Nếu có simulated session (từ review-based), ưu tiên dùng simulated session
      - Nếu không, dùng time-based sessions (giờ thực)
    """
    # Kiểm tra simulated session từ review-based
    sim_data = cfg_dict(_KEY_SIMULATED_SESSION, {})
    sim_session = sim_data.get("session")
    
    if sim_session:
        # Simulated session override
        is_morning = sim_session == "morning"
        session_name = "Phiên sáng 📚" if is_morning else "Phiên chiều 📚"
        sess_start = MORNING_START if is_morning else AFTERNOON_START
        sess_end = MORNING_END if is_morning else AFTERNOON_END
        # Khi được kích hoạt bởi review, luôn trong phiên
        base = {
            "in_session":        True,
            "session_name":      session_name,
            "session_start":     sess_start,
            "session_end":       sess_end,
            "seconds_until_end": 3600,    # mô phỏng: còn 1h
            "seconds_until_next": 0,
        }
    else:
        # Time-based sessions (giữ nguyên cơ chế cũ)
        base = _next_trading_session()
    
    return {
        "in_session":        base["in_session"],
        "session_name":      base["session_name"],
        "seconds_until_end": base["seconds_until_end"],
        "seconds_until_next": base["seconds_until_next"],
        "session_start_str": f"{base['session_start']//3600:02d}:{(base['session_start']%3600)//60:02d}",
        "session_end_str":   f"{base['session_end']//3600:02d}:{(base['session_end']%3600)//60:02d}",
        "source":            "review" if sim_session else "time",
    }


# ── Combined Data (Fix bất đồng bộ) ─────────────────────────

# ── Bond Convertible Bridge ──────────────────────────────────

def _add_shares_directly(symbol: str, shares: int, cost_basis: int) -> dict:
    """Thêm cổ phiếu trực tiếp vào portfolio (từ trái phiếu chuyển đổi).

    Args:
        symbol: mã cổ phiếu
        shares: số lượng cổ phiếu
        cost_basis: tổng giá trị (VND) — dùng làm total_invested

    Returns:
        dict với kết quả
    """
    try:
        symbol = symbol.upper()
        market = _get_market()
        if symbol not in market:
            return {"ok": False, "error": f"Mã CK {symbol} không tồn tại trên thị trường."}

        stock_data = market[symbol]
        current_price = stock_data.get("current_price", 0)

        port = _get_portfolio()

        # Tính số lượng cổ phiếu mua được
        actual_shares = shares

        # Kiểm tra holding hiện tại
        existing = None
        for h in port:
            if h["symbol"] == symbol:
                existing = h
                break

        txn_ts = _now()
        txn = {
            "type":       "convert",
            "symbol":     symbol,
            "shares":     actual_shares,
            "price":      round(cost_basis / actual_shares) if actual_shares > 0 else 0,
            "total":      cost_basis,
            "timestamp":  txn_ts,
        }

        if existing:
            # Gộp vào holding cũ
            old_shares = existing["shares"]
            old_invested = existing["total_invested"]
            new_shares = old_shares + actual_shares
            new_invested = old_invested + cost_basis
            existing["shares"] = new_shares
            existing["total_invested"] = new_invested
            existing["avg_price"] = round(new_invested / new_shares)
            existing.setdefault("transactions", []).append(txn)
        else:
            port.append({
                "symbol":         symbol,
                "shares":         actual_shares,
                "avg_price":      round(cost_basis / actual_shares) if actual_shares > 0 else 0,
                "avg_cost":       round(cost_basis / actual_shares) if actual_shares > 0 else 0,
                "total_invested": cost_basis,
                "market_value":   int(actual_shares * current_price),
                "purchased_at":   txn_ts,
                "transactions":   [txn],
            })

        _save_portfolio(port)

        # Ghi lịch sử giao dịch chứng khoán
        txns = _get_txns()
        txns.append({
            **txn,
            "company_name": stock_data.get("company_name", symbol),
            "sector_emoji": stock_data.get("sector_emoji", "📈"),
            "date":         _fmt_ts(txn_ts),
        })
        _save_txns(txns)

        return {
            "ok": True,
            "symbol": symbol,
            "shares_added": actual_shares,
            "total_invested": cost_basis,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_all_stock_data() -> dict:
    """
    Trả về tất cả dữ liệu chứng khoán trong 1 LẦN simulation duy nhất.
    Giải pháp triệt để cho lỗi bất đồng bộ:
      - Thị trường (market array)
      - Danh mục (portfolio)
      - Tổng quan thị trường (summary)
      - Giao dịch gần đây (transactions)
      - Thông tin phiên giao dịch (trading session)
    Tất cả đều dùng CHUNG 1 snapshot giá.
    """
    # Seed RNG một lần → simulation deterministic
    _seed_rng_for_simulation()

    # 1) Update prices nếu cần
    update_prices_if_needed()
    market = _get_market()

    # 2) Build market array
    market_array = []
    for sym, stock in market.items():
        if isinstance(stock, dict):
            market_array.append({
                "symbol":     sym,
                "company":    stock.get("company_name", ""),
                "short":      stock.get("short_name", ""),
                "sector":     stock.get("sector", ""),
                "sector_emoji": stock.get("sector_emoji", "📈"),
                "price":      stock.get("current_price", 0),
                "change":     stock.get("change", 0),
                "change_pct": stock.get("change_pct", 0.0),
                "volume":     stock.get("volume", 0),
                "high":       stock.get("high", 0),
                "low":        stock.get("low", 0),
                "base_price": stock.get("base_price", 0),
            })

    # 3) Build market summary
    up = dn = flat = 0
    total_vol = 0
    total_price = 0.0
    count = 0
    for sym, stock in market.items():
        if not isinstance(stock, dict):
            continue
        chg = stock.get("change", 0) or 0
        if chg > 0:
            up += 1
        elif chg < 0:
            dn += 1
        else:
            flat += 1
        total_vol += stock.get("volume", 0) or 0
        total_price += stock.get("current_price", 0) or 0
        count += 1
    vnindex = round(total_price / max(count, 1), 2) if count > 0 else 1000.0
    total_prev = sum(
        float(s.get("previous_close", s.get("current_price", 0)))
        for s in market.values() if isinstance(s, dict)
    )
    vnindex_change = 0.0
    vnindex_change_pct = 0.0
    if total_prev > 0 and count > 0:
        prev_vnindex = total_prev / count
        vnindex_change = round(vnindex - prev_vnindex, 2)
        vnindex_change_pct = round((vnindex_change / prev_vnindex) * 100, 2) if prev_vnindex else 0.0
    summary = {
        "vnindex":           vnindex,
        "vnindex_change":    vnindex_change,
        "vnindex_change_pct": vnindex_change_pct,
        "up":                up,
        "down":              dn,
        "flat":              flat,
        "total_volume":      total_vol,
        "last_updated":      _fmt_ts(),
    }

    # 4) Build portfolio (dùng market data đã load)
    portfolio_raw = _get_portfolio()
    now = _now()
    portfolio_list = []
    for h in portfolio_raw:
        sym   = h["symbol"]
        stock = market.get(sym, {})
        cur_price = stock.get("current_price", h.get("avg_cost", 0))
        shares    = h["shares"]
        avg_cost  = h.get("avg_cost", 0)
        invested  = h.get("total_invested", 0)
        market_value = cur_price * shares
        pnl          = market_value - invested
        pnl_pct      = round((pnl / invested) * 100, 2) if invested > 0 else 0.0
        purchased_at = h.get("purchased_at")
        sellable_at = 0
        cooldown_remaining = 0
        can_sell = True
        if purchased_at:
            sellable_at = _compute_tplus_release(purchased_at)
            cooldown_remaining = max(0, int(sellable_at - now))
            can_sell = now >= sellable_at
        portfolio_list.append({
            "symbol":        sym,
            "company":       stock.get("company_name", sym),
            "company_name":  stock.get("company_name", sym),
            "short_name":    stock.get("short_name", ""),
            "sector_emoji":  stock.get("sector_emoji", "📈"),
            "sector":        stock.get("sector", ""),
            "shares":        shares,
            "avg_cost":      avg_cost,
            "total_invested": invested,
            "current_price": cur_price,
            "market_value":  market_value,
            "pnl":           pnl,
            "pnl_pct":       pnl_pct,
            "change":        stock.get("change", 0),
            "change_pct":    stock.get("change_pct", 0.0),
            "purchased_at":  purchased_at or 0,
            "sellable_at":   sellable_at,
            "cooldown_remaining": cooldown_remaining,
            "can_sell":      can_sell,
        })

    # 5) Portfolio summary
    total_invested_sum = sum(h["total_invested"] for h in portfolio_list)
    total_mv_sum = sum(h["market_value"] for h in portfolio_list)
    total_pnl_sum = total_mv_sum - total_invested_sum
    total_pnl_pct_sum = round((total_pnl_sum / total_invested_sum) * 100, 2) if total_invested_sum > 0 else 0.0
    portfolio_summary = {
        "total_invested":    total_invested_sum,
        "total_market_value": total_mv_sum,
        "total_pnl":         total_pnl_sum,
        "total_pnl_pct":     total_pnl_pct_sum,
        "count":             len(portfolio_list),
    }

    # 6) Transactions gần đây
    txns = _get_txns()
    txns_sorted = sorted(txns, key=lambda t: t.get("timestamp", 0), reverse=True)[:50]

    # 7) Trading session info
    session_info = get_trading_session_info()

    return {
        "ok": True,
        "market":          market_array,
        "summary":         summary,
        "portfolio":       portfolio_list,
        "portfolio_summary": portfolio_summary,
        "transactions":    txns_sorted,
        "trading_session": session_info,
    }
