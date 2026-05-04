# -*- coding: utf-8 -*-
"""
digital_assets.py — Thị trường Tài sản số (Crypto) Anki Finance.

- 15 loại crypto thực tế: BTC, ETH, BNB, SOL, XRP, ADA, AVAX, DOT, MATIC, LINK, UNI, LTC, DOGE, SHIB, USDT
- Giá mô phỏng offline (random walk seeded) với volatility cao hơn cổ phiếu nhiều
- Mua theo số tiền VND, bán theo % danh mục, không T+2
- Staking: khóa 7 ngày, nhận yield theo APY
- Bull/bear market gắn với streak học tập
- Rug pull mechanic cho meme coins
- Pump/dump event theo mốc review
"""

import time
import math
import random
import uuid
from datetime import datetime
from ._safe_config import col_ready, cfg_int, cfg_dict, cfg_list, cfg_set
from .logger import get_logger

logger = get_logger(__name__)

# ── Config keys ──────────────────────────────────────────────
_KEY_MARKET       = "anki_tycoon_crypto_market"         # dict{symbol: asset_data}
_KEY_PORTFOLIO    = "anki_tycoon_crypto_portfolio"      # list[holding]
_KEY_LAST_UPDATE  = "anki_tycoon_crypto_last_update"    # float timestamp
_KEY_HISTORY      = "anki_tycoon_crypto_price_history"  # dict{symbol: [[ts,price],...]}
_KEY_TXNS         = "anki_tycoon_crypto_transactions"   # list[txn]
_KEY_REVIEW_COUNT = "anki_tycoon_crypto_review_count"   # int
_KEY_STAKING      = "anki_tycoon_crypto_staking"        # list[stake]
_KEY_MARKET_CYCLE = "anki_tycoon_crypto_market_cycle"   # dict{mode, ...}

UPDATE_INTERVAL_SECS = 4 * 3600   # 4 giờ dự phòng
MAX_HISTORY_ENTRIES  = 50
REVIEWS_PER_UPDATE   = 50         # Cứ 50 thẻ ôn → cập nhật giá
STAKE_LOCK_DAYS      = 7          # Lock 7 ngày khi stake
TRADING_FEE          = 0.001      # 0.1% phí giao dịch (base, có thể giảm qua passive effect)


def _get_effective_trading_fee() -> float:
    """
    Đọc crypto_cooldown_reduction từ passive effects để giảm phí giao dịch.
    Trả về tỷ lệ phí hiệu dụng (mặc định 0.001 = 0.1%).
    Ví dụ: reduction = 0.5 (50%) → phí = 0.001 * (1 - 0.5) = 0.0005 (0.05%)
    """
    try:
        from .item_effects import get_all_passive_effects
        passive = get_all_passive_effects()
        reduction = float(passive.get("crypto_cooldown_reduction", 0.0))
        reduction = min(max(reduction, 0.0), 0.9)  # cap 0%–90%
        if reduction > 0:
            return TRADING_FEE * (1.0 - reduction)
    except Exception as e:
        logger.debug("_get_effective_trading_fee: %s", e)
    return TRADING_FEE


# ── Master list 15 crypto assets ─────────────────────────────
# (symbol, name, name_vi, category, emoji, exchange, base_price_vnd, volatility, staking_apy, rug_pull_risk, is_stablecoin)
CRYPTO_MASTER = [
    ("BTC",  "Bitcoin",        "Bitcoin",        "Layer 1",        "🟠", "Binance",       1_700_000_000, 0.05,  0.0,   0.0,   False),
    ("ETH",  "Ethereum",       "Ethereum",       "Layer 1",        "🔷", "Binance",          90_000_000, 0.06,  0.04,  0.0,   False),
    ("BNB",  "BNB Chain",      "BNB",            "Exchange Token", "🟡", "Binance",          15_000_000, 0.07,  0.02,  0.0,   False),
    ("SOL",  "Solana",         "Solana",         "Layer 1",        "🟣", "OKX",               4_000_000, 0.09,  0.065, 0.0,   False),
    ("XRP",  "XRP",            "Ripple",         "Payment",        "🔵", "Remitano",            600_000, 0.08,  0.0,   0.0,   False),
    ("ADA",  "Cardano",        "Cardano",        "Layer 1",        "💙", "Bybit",               20_000,  0.08,  0.03,  0.0,   False),
    ("AVAX", "Avalanche",      "Avalanche",      "Layer 1",        "🔴", "Binance",             900_000, 0.10,  0.05,  0.0,   False),
    ("DOT",  "Polkadot",       "Polkadot",       "Parachain",      "⚫", "OKX",                 200_000, 0.09,  0.12,  0.0,   False),
    ("MATIC","Polygon",        "Polygon",        "Layer 2",        "🟣", "Binance",              15_000,  0.10,  0.04,  0.0,   False),
    ("LINK", "Chainlink",      "Chainlink",      "Oracle",         "🔗", "Coinbase",            350_000, 0.09,  0.0,   0.0,   False),
    ("UNI",  "Uniswap",        "Uniswap",        "DeFi",           "🦄", "Uniswap DEX",         300_000, 0.10,  0.0,   0.0,   False),
    ("LTC",  "Litecoin",       "Litecoin",       "Payment",        "🩶", "BitcoinVN",         2_300_000, 0.07,  0.0,   0.0,   False),
    ("DOGE", "Dogecoin",       "Dogecoin",       "Meme",           "🐶", "VNDC",                  5_000, 0.12,  0.0,   0.02,  False),
    ("SHIB", "Shiba Inu (1M)", "Shiba Inu",      "Meme",           "🦊", "Binance",              70_000,  0.15,  0.0,   0.05,  False),
    ("USDT", "Tether USD",     "Tether",         "Stablecoin",     "💵", "Remitano",             25_500,  0.002, 0.05,  0.0,   True),
]
# SHIB price = giá của 1.000.000 SHIB (đơn vị mua bán là 1M SHIB)

# ── Helpers ──────────────────────────────────────────────────

def _now() -> float:
    return time.time()


def _fmt_ts(ts: float = None) -> str:
    dt = datetime.fromtimestamp(ts if ts is not None else _now())
    return dt.strftime("%d/%m/%Y %H:%M")


def _cfg_get_raw(key: str, default=None):
    if not col_ready():
        return default
    try:
        from aqt import mw
        if mw is None or mw.col is None:
            return default
        return mw.col.get_config(key, default)
    except Exception as e:
        logger.debug("_cfg_get_raw: %s", e)
        return default


# ── Seeded PRNG ──────────────────────────────────────────────
_SEEDED_RNG = None


def _init_seeded_rng(seed: int):
    global _SEEDED_RNG
    _SEEDED_RNG = random.Random(seed)


def _seeded_random() -> float:
    global _SEEDED_RNG
    if _SEEDED_RNG is None:
        _SEEDED_RNG = random.Random(int(_now()))
    return _SEEDED_RNG.random()


def _seeded_normal(mu: float = 0.0, sigma: float = 1.0) -> float:
    u1 = max(_seeded_random(), 1e-10)
    u2 = _seeded_random()
    return mu + sigma * math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)


def _seed_rng_for_simulation():
    now = _now()
    interval_seed = int(now // UPDATE_INTERVAL_SECS) if UPDATE_INTERVAL_SECS > 0 else int(now)
    _init_seeded_rng(interval_seed)


# ── Storage helpers ──────────────────────────────────────────

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


def _get_staking() -> list:
    return cfg_list(_KEY_STAKING, [])


def _save_staking(s: list):
    cfg_set(_KEY_STAKING, s)


def _get_cycle() -> dict:
    return cfg_dict(_KEY_MARKET_CYCLE, {"mode": "neutral", "streak_days": 0})


def _save_cycle(c: dict):
    cfg_set(_KEY_MARKET_CYCLE, c)


# ── Market Initialization ────────────────────────────────────

def _seed_market_if_empty(market: dict) -> dict:
    if market and any(
        isinstance(v, dict) and v.get("current_price", 0) > 0 for v in market.values()
    ):
        return market

    now = _now()
    seeded = {}
    for sym, name, name_vi, cat, emoji, exchange, base, vol, apy, rug_risk, is_stable in CRYPTO_MASTER:
        seeded[sym] = {
            "symbol":         sym,
            "name":           name,
            "name_vi":        name_vi,
            "category":       cat,
            "emoji":          emoji,
            "exchange":       exchange,
            "base_price":     base,
            "current_price":  base,
            "previous_close": base,
            "high_24h":       base,
            "low_24h":        base,
            "change":         0,
            "change_pct":     0.0,
            "volatility":     vol,
            "staking_apy":    apy,
            "rug_pull_risk":  rug_risk,
            "is_stablecoin":  is_stable,
            "rug_pulled":     False,
            "rug_pull_event": "",
            "event_next_update": "",
            "last_updated":   now,
        }
    return seeded


# ── Price Simulation ─────────────────────────────────────────

def _simulate_price_changes(market: dict, streak_days: int = 0) -> dict:
    now = _now()

    # Bull/bear modifier từ streak học
    if streak_days >= 7:
        streak_bias = 0.002 * min(streak_days / 7, 3.0)
    elif streak_days == 0:
        streak_bias = -0.003
    else:
        streak_bias = 0.0

    updated = {}
    for sym, asset in market.items():
        if not isinstance(asset, dict):
            continue

        base       = float(asset.get("base_price", 25000))
        prev_close = float(asset.get("previous_close", base))
        cur        = float(asset.get("current_price", base))
        vol        = float(asset.get("volatility", 0.05))
        is_stable  = bool(asset.get("is_stablecoin", False))
        is_rugged  = bool(asset.get("rug_pulled", False))

        if is_rugged:
            # Giá đã sập, chỉ dao động nhỏ quanh mức thấp
            new_price = max(cur * (1 + _seeded_normal(0.0, 0.01)), base * 0.005)
            new_price = round(new_price)
            updated[sym] = {
                **asset,
                "previous_close": int(prev_close),
                "current_price":  int(new_price),
                "high_24h":       int(new_price),
                "low_24h":        int(new_price),
                "change":         int(new_price - prev_close),
                "change_pct":     round((new_price - prev_close) / prev_close * 100, 2) if prev_close > 0 else 0.0,
                "last_updated":   now,
                "event_next_update": "",
            }
            continue

        if is_stable:
            # Stablecoin: drift rất nhỏ
            drift = _seeded_normal(0.0, 0.001)
            new_price = base * (1 + drift)
            new_price = max(base * 0.97, min(new_price, base * 1.03))
            new_price = round(new_price)
        else:
            # Random walk với mean reversion
            daily_return = _seeded_normal(0.0, vol)
            mean_rev = 0.02 * (base - cur) / base
            event = asset.get("event_next_update", "")
            if event == "pump":
                daily_return += _seeded_normal(0.08, 0.03)
            elif event == "dump":
                daily_return += _seeded_normal(-0.10, 0.03)

            daily_return += streak_bias

            change_pct = daily_return + mean_rev
            new_price = cur * (1.0 + change_pct)

            # Rug pull check (chỉ 1 lần)
            rug_risk = float(asset.get("rug_pull_risk", 0))
            if rug_risk > 0 and _seeded_random() < rug_risk * 0.005:
                new_price = base * (_seeded_random() * 0.04 + 0.01)
                asset = {**asset, "rug_pulled": True, "rug_pull_event": _fmt_ts()}

            min_price = base * 0.001
            max_price = base * 10.0
            new_price = max(min_price, min(new_price, max_price))
            new_price = round(new_price)

        high = max(prev_close, new_price, float(asset.get("high_24h", new_price))) * (1 + _seeded_random() * 0.005)
        low  = min(prev_close, new_price, float(asset.get("low_24h",  new_price))) * (1 - _seeded_random() * 0.005)
        change     = int(new_price - prev_close)
        change_pct = round((change / prev_close) * 100, 2) if prev_close > 0 else 0.0

        updated[sym] = {
            **asset,
            "previous_close": int(prev_close),
            "current_price":  int(new_price),
            "high_24h":       int(high),
            "low_24h":        int(low),
            "change":         change,
            "change_pct":     change_pct,
            "last_updated":   now,
            "event_next_update": "",
        }

    return updated


def _append_history(market: dict):
    hist = _get_history()
    for sym, asset in market.items():
        if not isinstance(asset, dict):
            continue
        price = asset.get("current_price", 0)
        ts    = asset.get("last_updated", _now())
        if sym not in hist or not isinstance(hist[sym], list):
            hist[sym] = []
        hist[sym].append([ts, price])
        if len(hist[sym]) > MAX_HISTORY_ENTRIES:
            hist[sym] = hist[sym][-MAX_HISTORY_ENTRIES:]
    _save_history(hist)


# ── Market Cycle ─────────────────────────────────────────────

def _update_market_cycle(streak_days: int):
    cycle = _get_cycle()
    if streak_days >= 7:
        mode = "bull"
    elif streak_days == 0:
        mode = "bear"
    else:
        mode = "neutral"
    cycle["mode"] = mode
    cycle["streak_days"] = streak_days
    _save_cycle(cycle)


def _get_streak_days() -> int:
    try:
        from .streak_system import get_streak_status
        status = get_streak_status()
        return int(status.get("current_streak", 0))
    except Exception as e:
        logger.debug("_get_streak_days: %s", e)
        return 0


# ── Public: Update Prices ────────────────────────────────────

def update_prices_if_needed() -> bool:
    if not col_ready():
        return False

    market = _get_market()
    now    = _now()
    last   = _cfg_get_raw(_KEY_LAST_UPDATE, 0.0)
    last_ts = float(last) if isinstance(last, (int, float)) else 0.0
    streak  = _get_streak_days()

    if not market:
        market = _seed_market_if_empty(market)
        _save_market(market)
        _seed_rng_for_simulation()
        market = _simulate_price_changes(market, streak)
        _save_market(market)
        _append_history(market)
        cfg_set(_KEY_LAST_UPDATE, now)
        _update_market_cycle(streak)
        return True

    elapsed = now - last_ts
    if elapsed >= UPDATE_INTERVAL_SECS:
        for sym, asset in market.items():
            if isinstance(asset, dict):
                asset["previous_close"] = asset.get("current_price", asset.get("base_price", 0))
        _seed_rng_for_simulation()
        market = _simulate_price_changes(market, streak)
        _save_market(market)
        _append_history(market)
        cfg_set(_KEY_LAST_UPDATE, now)
        _update_market_cycle(streak)
        return True

    return False


def _force_update_prices():
    market = _get_market()
    if not market:
        return
    streak = _get_streak_days()
    now    = _now()
    for sym, asset in market.items():
        if isinstance(asset, dict):
            asset["previous_close"] = asset.get("current_price", asset.get("base_price", 0))
    _seed_rng_for_simulation()
    market = _simulate_price_changes(market, streak)
    _save_market(market)
    _append_history(market)
    cfg_set(_KEY_LAST_UPDATE, now)
    _update_market_cycle(streak)


def record_review(count: int = 1):
    try:
        current = cfg_int(_KEY_REVIEW_COUNT, 0)
        current += count
        if current >= REVIEWS_PER_UPDATE:
            # Pump/dump event ngẫu nhiên ở các mốc
            _maybe_trigger_event(current)
            _force_update_prices()
            cfg_set(_KEY_REVIEW_COUNT, 0)
        else:
            cfg_set(_KEY_REVIEW_COUNT, current)
    except Exception as e:
        logger.warning("record_review: %s", e)


def _maybe_trigger_event(total_reviews: int):
    """30% xác suất pump/dump cho 1 coin ngẫu nhiên tại mốc review."""
    milestones = {100, 200, 500, 1000}
    if total_reviews not in milestones:
        return
    if random.random() > 0.30:
        return
    market = _get_market()
    candidates = [sym for sym, a in market.items()
                  if isinstance(a, dict) and not a.get("is_stablecoin") and not a.get("rug_pulled")]
    if not candidates:
        return
    target = random.choice(candidates)
    event  = "pump" if random.random() > 0.4 else "dump"
    market[target]["event_next_update"] = event
    _save_market(market)


# ── Buy / Sell ────────────────────────────────────────────────

def buy_crypto(symbol: str, amount_vnd: int) -> dict:
    if not col_ready():
        return {"ok": False, "error": "Chưa sẵn sàng."}

    symbol = symbol.upper()
    market = _get_market()
    if not market:
        market = _seed_market_if_empty({})
        _save_market(market)

    asset = market.get(symbol)
    if not asset:
        return {"ok": False, "error": f"Không tìm thấy coin {symbol}."}

    from .balance import get_balance, set_balance_and_log
    balance = get_balance()

    if amount_vnd <= 0:
        return {"ok": False, "error": "Số tiền phải lớn hơn 0."}
    if amount_vnd > balance:
        return {"ok": False, "error": f"Không đủ tiền! Số dư hiện tại: {balance:,}đ.".replace(",", ".")}

    current_price = float(asset.get("current_price", asset.get("base_price", 1)))
    eff_fee_rate  = _get_effective_trading_fee()
    fee           = int(amount_vnd * eff_fee_rate)
    net_vnd       = amount_vnd - fee
    quantity      = net_vnd / current_price

    # Cập nhật portfolio
    portfolio = _get_portfolio()
    holding = next((h for h in portfolio if h.get("symbol") == symbol), None)
    if holding:
        # Tính avg cost mới
        old_qty  = float(holding.get("quantity", 0))
        old_cost = float(holding.get("avg_cost_per_unit", current_price))
        new_qty  = old_qty + quantity
        new_avg  = (old_qty * old_cost + quantity * current_price) / new_qty if new_qty > 0 else current_price
        holding["quantity"]         = new_qty
        holding["avg_cost_per_unit"] = new_avg
        holding["total_invested"]   = holding.get("total_invested", 0) + amount_vnd
    else:
        slot_id = f"crypto_{symbol}_{str(uuid.uuid4())[:8]}"
        portfolio.append({
            "slot_id":          slot_id,
            "symbol":           symbol,
            "quantity":         quantity,
            "avg_cost_per_unit": current_price,
            "total_invested":   amount_vnd,
            "purchased_at":     _fmt_ts(),
            "staked_amount":    0.0,
        })
    _save_portfolio(portfolio)

    # Trừ tiền
    new_balance = balance - amount_vnd
    set_balance_and_log(new_balance, "purchase", -amount_vnd,
                        f"Mua {quantity:.6f} {symbol} trên {asset.get('exchange','')}")

    # Ghi transaction
    _add_txn("buy", symbol, quantity, current_price, amount_vnd, asset.get("emoji", "🪙"), asset.get("exchange", ""))

    return {
        "ok":          True,
        "symbol":      symbol,
        "quantity":    quantity,
        "price":       int(current_price),
        "fee":         fee,
        "total_vnd":   amount_vnd,
        "new_balance": new_balance,
    }


def sell_crypto(symbol: str, sell_pct: float) -> dict:
    if not col_ready():
        return {"ok": False, "error": "Chưa sẵn sàng."}

    symbol   = symbol.upper()
    sell_pct = max(0.01, min(sell_pct, 1.0))
    market   = _get_market()
    asset    = market.get(symbol)
    if not asset:
        return {"ok": False, "error": f"Không tìm thấy coin {symbol}."}

    portfolio = _get_portfolio()
    holding   = next((h for h in portfolio if h.get("symbol") == symbol), None)
    if not holding:
        return {"ok": False, "error": f"Bạn không có {symbol} trong danh mục."}

    total_qty  = float(holding.get("quantity", 0))
    staked_qty = float(holding.get("staked_amount", 0))
    avail_qty  = total_qty - staked_qty
    sell_qty   = avail_qty * sell_pct

    if sell_qty <= 0:
        return {"ok": False, "error": f"Không có {symbol} khả dụng để bán (đang stake)."}

    current_price = float(asset.get("current_price", asset.get("base_price", 1)))
    gross_vnd     = sell_qty * current_price
    eff_fee_rate  = _get_effective_trading_fee()
    fee           = int(gross_vnd * eff_fee_rate)
    net_vnd       = int(gross_vnd - fee)

    avg_cost  = float(holding.get("avg_cost_per_unit", current_price))
    cost_basis = sell_qty * avg_cost
    pnl        = net_vnd - int(cost_basis)

    # Cập nhật holding
    new_qty = total_qty - sell_qty
    if new_qty < 1e-10:
        portfolio = [h for h in portfolio if h.get("symbol") != symbol]
    else:
        holding["quantity"] = new_qty
        invested_ratio = 1.0 - sell_pct * (avail_qty / total_qty)
        holding["total_invested"] = int(holding.get("total_invested", 0) * max(0.0, invested_ratio))
    _save_portfolio(portfolio)

    # Cộng tiền
    from .balance import get_balance, set_balance_and_log
    balance     = get_balance()
    new_balance = balance + net_vnd
    set_balance_and_log(new_balance, "income", net_vnd,
                        f"Bán {sell_qty:.6f} {symbol} ({sell_pct*100:.0f}%) — PnL: {pnl:+,}đ".replace(",", "."))

    _add_txn("sell", symbol, sell_qty, current_price, net_vnd, asset.get("emoji", "🪙"), asset.get("exchange", ""))

    return {
        "ok":          True,
        "symbol":      symbol,
        "quantity":    sell_qty,
        "price":       int(current_price),
        "fee":         fee,
        "net_vnd":     net_vnd,
        "pnl":         pnl,
        "new_balance": new_balance,
    }


# ── Staking ──────────────────────────────────────────────────

def stake_crypto(symbol: str, stake_pct: float) -> dict:
    if not col_ready():
        return {"ok": False, "error": "Chưa sẵn sàng."}

    symbol    = symbol.upper()
    stake_pct = max(0.01, min(stake_pct, 1.0))
    market    = _get_market()
    asset     = market.get(symbol)
    if not asset:
        return {"ok": False, "error": f"Không tìm thấy coin {symbol}."}

    apy = float(asset.get("staking_apy", 0))
    if apy <= 0:
        return {"ok": False, "error": f"{symbol} không hỗ trợ staking."}

    portfolio = _get_portfolio()
    holding   = next((h for h in portfolio if h.get("symbol") == symbol), None)
    if not holding:
        return {"ok": False, "error": f"Bạn không có {symbol} để stake."}

    total_qty  = float(holding.get("quantity", 0))
    staked_qty = float(holding.get("staked_amount", 0))
    avail_qty  = total_qty - staked_qty
    stake_qty  = avail_qty * stake_pct

    if stake_qty <= 1e-10:
        return {"ok": False, "error": "Không có đủ số lượng khả dụng để stake."}

    now = _now()
    stake_id = f"stake_{symbol}_{str(uuid.uuid4())[:8]}"
    staking  = _get_staking()
    staking.append({
        "stake_id":        stake_id,
        "symbol":          symbol,
        "staked_amount":   stake_qty,
        "staking_apy":     apy,
        "staked_at":       now,
        "last_yield_ts":   now,
        "total_yield":     0.0,
        "unlock_at":       now + STAKE_LOCK_DAYS * 86400,
    })
    _save_staking(staking)

    holding["staked_amount"] = staked_qty + stake_qty
    _save_portfolio(portfolio)

    _add_txn("stake", symbol, stake_qty, float(asset.get("current_price", 0)), 0,
             asset.get("emoji", "🪙"), "", note=f"APY {apy*100:.1f}%")

    return {
        "ok":        True,
        "stake_id":  stake_id,
        "symbol":    symbol,
        "amount":    stake_qty,
        "apy":       apy,
        "unlock_at": now + STAKE_LOCK_DAYS * 86400,
    }


def unstake_crypto(stake_id: str) -> dict:
    if not col_ready():
        return {"ok": False, "error": "Chưa sẵn sàng."}

    staking = _get_staking()
    pos     = next((s for s in staking if s.get("stake_id") == stake_id), None)
    if not pos:
        return {"ok": False, "error": "Không tìm thấy vị thế staking."}

    now       = _now()
    unlock_at = float(pos.get("unlock_at", 0))
    if now < unlock_at:
        days_left = round((unlock_at - now) / 86400, 1)
        return {"ok": False, "error": f"Còn {days_left} ngày nữa mới được rút."}

    symbol   = pos.get("symbol", "")
    amount   = float(pos.get("staked_amount", 0))
    apy      = float(pos.get("staking_apy", 0))
    staked_at = float(pos.get("staked_at", now))
    elapsed_days = (now - staked_at) / 86400
    yield_amount  = amount * apy * (elapsed_days / 365)

    # Trả về portfolio
    portfolio = _get_portfolio()
    holding   = next((h for h in portfolio if h.get("symbol") == symbol), None)
    if holding:
        holding["quantity"]      = float(holding.get("quantity", 0)) + yield_amount
        holding["staked_amount"] = max(0.0, float(holding.get("staked_amount", 0)) - amount)
    else:
        # Edge case: holding bị xóa, thêm lại
        portfolio.append({
            "slot_id":          f"crypto_{symbol}_{str(uuid.uuid4())[:8]}",
            "symbol":           symbol,
            "quantity":         amount + yield_amount,
            "avg_cost_per_unit": 0.0,
            "total_invested":   0,
            "purchased_at":     _fmt_ts(),
            "staked_amount":    0.0,
        })
    _save_portfolio(portfolio)

    # Xóa staking position
    staking = [s for s in staking if s.get("stake_id") != stake_id]
    _save_staking(staking)

    market = _get_market()
    asset  = market.get(symbol, {})
    _add_txn("unstake", symbol, amount + yield_amount, float(asset.get("current_price", 0)), 0,
             asset.get("emoji", "🪙"), "", note=f"Yield: +{yield_amount:.6f} {symbol}")

    return {
        "ok":          True,
        "symbol":      symbol,
        "returned":    amount,
        "yield_units": yield_amount,
        "elapsed_days": round(elapsed_days, 1),
    }


def collect_staking_yield() -> dict:
    """Thu yield staking mà không unlock principal. Gọi khi mở app."""
    if not col_ready():
        return {"ok": True, "yield_vnd": 0}

    staking  = _get_staking()
    market   = _get_market()
    portfolio = _get_portfolio()
    now      = _now()
    total_yield_vnd = 0

    changed_staking   = False
    changed_portfolio = False

    for pos in staking:
        last_ts  = float(pos.get("last_yield_ts", pos.get("staked_at", now)))
        elapsed  = (now - last_ts) / 86400  # ngày
        if elapsed < 0.5:
            continue

        symbol     = pos.get("symbol", "")
        amount     = float(pos.get("staked_amount", 0))
        apy        = float(pos.get("staking_apy", 0))
        yield_units = amount * apy * (elapsed / 365)

        if yield_units <= 0:
            continue

        asset         = market.get(symbol, {})
        price         = float(asset.get("current_price", 0))
        yield_vnd     = int(yield_units * price)
        total_yield_vnd += yield_vnd

        holding = next((h for h in portfolio if h.get("symbol") == symbol), None)
        if holding:
            holding["quantity"] = float(holding.get("quantity", 0)) + yield_units
            changed_portfolio = True
        # Cập nhật last_yield_ts
        pos["last_yield_ts"]  = now
        pos["total_yield"]    = float(pos.get("total_yield", 0)) + yield_units
        changed_staking = True

    if changed_portfolio:
        _save_portfolio(portfolio)
    if changed_staking:
        _save_staking(staking)

    return {"ok": True, "yield_vnd": total_yield_vnd}


# ── Portfolio helpers ────────────────────────────────────────

def get_portfolio() -> list:
    """Trả về portfolio đã enrich với giá hiện tại."""
    market    = _get_market()
    portfolio = _get_portfolio()
    staking   = _get_staking()

    staked_map: dict = {}
    for s in staking:
        sym = s.get("symbol", "")
        staked_map[sym] = staked_map.get(sym, 0.0) + float(s.get("staked_amount", 0))

    result = []
    for h in portfolio:
        sym   = h.get("symbol", "")
        asset = market.get(sym, {})
        qty   = float(h.get("quantity", 0))
        avg   = float(h.get("avg_cost_per_unit", 0))
        price = float(asset.get("current_price", avg))

        staked  = float(h.get("staked_amount", staked_map.get(sym, 0.0)))
        avail   = max(0.0, qty - staked)
        mkt_val = int(qty * price)
        cost    = int(qty * avg) if avg > 0 else h.get("total_invested", 0)
        pnl     = mkt_val - cost
        pnl_pct = round(pnl / cost * 100, 2) if cost > 0 else 0.0

        result.append({
            **h,
            "name":          asset.get("name", sym),
            "emoji":         asset.get("emoji", "🪙"),
            "exchange":      asset.get("exchange", ""),
            "staking_apy":   asset.get("staking_apy", 0),
            "current_price": int(price),
            "market_value":  mkt_val,
            "cost_basis":    cost,
            "pnl":           pnl,
            "pnl_pct":       pnl_pct,
            "staked_amount": staked,
            "avail_qty":     avail,
            "change_pct":    asset.get("change_pct", 0.0),
        })
    return result


def get_portfolio_summary() -> dict:
    holdings = get_portfolio()
    total_invested = sum(h.get("total_invested", 0) for h in holdings)
    total_mkt_val  = sum(h.get("market_value", 0)   for h in holdings)
    total_staked   = sum(h.get("staked_amount", 0) * h.get("current_price", 0) for h in holdings)
    pnl            = total_mkt_val - total_invested

    btc_h = next((h for h in holdings if h.get("symbol") == "BTC"), None)
    btc_val = btc_h.get("market_value", 0) if btc_h else 0
    btc_dom = round(btc_val / total_mkt_val * 100, 1) if total_mkt_val > 0 else 0.0

    return {
        "total_invested":    total_invested,
        "total_market_value": total_mkt_val,
        "total_pnl":         pnl,
        "total_pnl_pct":     round(pnl / total_invested * 100, 2) if total_invested > 0 else 0.0,
        "total_staking_vnd": int(total_staked),
        "btc_dominance_pct": btc_dom,
        "count":             len(holdings),
    }


def get_crypto_portfolio_value() -> int:
    """Tổng giá trị VND của crypto portfolio — dùng cho tax_system."""
    return get_portfolio_summary().get("total_market_value", 0)


def get_staking_positions() -> list:
    staking = _get_staking()
    market  = _get_market()
    now     = _now()
    result  = []
    for s in staking:
        sym      = s.get("symbol", "")
        asset    = market.get(sym, {})
        unlock_at = float(s.get("unlock_at", 0))
        locked    = now < unlock_at
        days_left = max(0.0, round((unlock_at - now) / 86400, 1)) if locked else 0.0
        price     = float(asset.get("current_price", 0))
        staked_vnd = int(float(s.get("staked_amount", 0)) * price)
        result.append({
            **s,
            "emoji":       asset.get("emoji", "🪙"),
            "exchange":    asset.get("exchange", ""),
            "locked":      locked,
            "days_left":   days_left,
            "staked_vnd":  staked_vnd,
        })
    return result


def get_market_cycle_info() -> dict:
    cycle   = _get_cycle()
    streak  = _get_streak_days()
    mode    = cycle.get("mode", "neutral")
    if mode == "bull":
        label = "🐂 Thị trường BÒ — Streak học tập đang kéo giá tăng!"
        color = "bull"
    elif mode == "bear":
        label = "🐻 Thị trường GẤU — Cần ôn bài để phục hồi!"
        color = "bear"
    else:
        label = "⚖️ Thị trường TRUNG LẬP"
        color = "neutral"
    return {
        "mode":        mode,
        "label":       label,
        "color":       color,
        "streak_days": streak,
    }


def get_crypto_history(symbol: str, limit: int = 50) -> list:
    hist = _get_history()
    entries = hist.get(symbol.upper(), [])
    return entries[-limit:]


# ── Combined data loader ─────────────────────────────────────

def get_all_crypto_data() -> dict:
    update_prices_if_needed()
    market = _get_market()
    if not market:
        market = _seed_market_if_empty({})
        _save_market(market)

    market_array = []
    for sym, asset in market.items():
        if isinstance(asset, dict):
            market_array.append({
                "symbol":        sym,
                "name":          asset.get("name", sym),
                "name_vi":       asset.get("name_vi", sym),
                "category":      asset.get("category", ""),
                "emoji":         asset.get("emoji", "🪙"),
                "exchange":      asset.get("exchange", ""),
                "price":         asset.get("current_price", 0),
                "previous_close": asset.get("previous_close", 0),
                "high_24h":      asset.get("high_24h", 0),
                "low_24h":       asset.get("low_24h", 0),
                "change":        asset.get("change", 0),
                "change_pct":    asset.get("change_pct", 0.0),
                "staking_apy":   asset.get("staking_apy", 0.0),
                "is_stablecoin": asset.get("is_stablecoin", False),
                "rug_pulled":    asset.get("rug_pulled", False),
                "rug_pull_event": asset.get("rug_pull_event", ""),
            })

    txns = _get_txns()
    return {
        "ok":               True,
        "market":           market_array,
        "portfolio":        get_portfolio(),
        "portfolio_summary": get_portfolio_summary(),
        "staking":          get_staking_positions(),
        "transactions":     txns[-50:],
        "market_cycle":     get_market_cycle_info(),
    }


# ── Transaction logger ───────────────────────────────────────

def _add_txn(txn_type: str, symbol: str, quantity: float, price: float,
             total_vnd: int, emoji: str, exchange: str, note: str = ""):
    """Ghi giao dịch crypto vào cả hệ thống riêng và hệ thống chung."""
    txns = _get_txns()
    entry = {
        "type":      txn_type,
        "symbol":    symbol,
        "emoji":     emoji,
        "quantity":  quantity,
        "price":     int(price),
        "total_vnd": total_vnd,
        "exchange":  exchange,
        "note":      note,
        "timestamp": _now(),
        "date":      _fmt_ts(),
    }
    txns.append(entry)
    if len(txns) > 200:
        txns = txns[-200:]
    _save_txns(txns)

    # Ghi vào hệ thống giao dịch chung
    type_map = {
        "buy":     "crypto_buy",
        "sell":    "crypto_sell",
        "stake":   "crypto_stake",
        "unstake": "crypto_unstake",
    }
    main_type = type_map.get(txn_type, "crypto_buy" if txn_type == "buy" else txn_type)
    description = {
        "buy":     f"Mua {quantity:.6f} {symbol} trên {exchange}",
        "sell":    f"Bán {quantity:.6f} {symbol} ({note})" if note else f"Bán {quantity:.6f} {symbol}",
        "stake":   f"Stake {quantity:.6f} {symbol} ({note})" if note else f"Stake {quantity:.6f} {symbol}",
        "unstake": f"Unstake {quantity:.6f} {symbol} ({note})" if note else f"Unstake {quantity:.6f} {symbol}",
    }.get(txn_type, f"{txn_type} {quantity:.6f} {symbol}")

    try:
        from .transactions import add_transaction
        add_transaction(main_type, abs(total_vnd) if total_vnd else int(price * quantity),
                        f"{emoji} {description}",
                        {"symbol": symbol, "quantity": quantity, "price": int(price)})
    except Exception as e:
        logger.warning("_record_txn: %s", e)


# ── Shop integration ─────────────────────────────────────────

def add_digital_asset(item_id: str, item_data: dict) -> dict:
    """Gọi từ web_bridge.buyItem() khi mua crypto từ shop."""
    symbol     = item_data.get("crypto_symbol", "").upper()
    amount_vnd = int(item_data.get("crypto_amount_vnd", item_data.get("price", 0)))
    if not symbol or amount_vnd <= 0:
        return {"ok": False, "error": "Dữ liệu sản phẩm không hợp lệ."}
    return buy_crypto(symbol, amount_vnd)
