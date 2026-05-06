# -*- coding: utf-8 -*-
"""Unit tests cho stock_market.py — helpers, constants, trading logic."""

from __future__ import annotations

import time
import math
import random
from datetime import datetime, timedelta

import pytest


class TestStockMaster:
    """STOCK_MASTER list integrity."""

    def test_has_15_symbols(self, fake_config):
        import anki_finance.stock_market as mod
        fake_config(mod, {})
        assert len(mod.STOCK_MASTER) == 15

    def test_all_symbols_uppercase(self, fake_config):
        import anki_finance.stock_market as mod
        fake_config(mod, {})
        for sym, *_ in mod.STOCK_MASTER:
            assert sym == sym.upper(), f"{sym} is not uppercase"

    def test_all_base_prices_positive(self, fake_config):
        import anki_finance.stock_market as mod
        fake_config(mod, {})
        for sym, name, short, sector, emoji, base, vol in mod.STOCK_MASTER:
            assert base > 0, f"{sym} base_price={base}"
            assert vol > 0, f"{sym} volatility={vol}"

    def test_all_have_unique_symbols(self, fake_config):
        import anki_finance.stock_market as mod
        fake_config(mod, {})
        symbols = [s[0] for s in mod.STOCK_MASTER]
        assert len(symbols) == len(set(symbols))


class TestIsWorkingDay:
    """_is_working_day kiểm tra T2-T6."""

    def test_monday_is_working(self, fake_config):
        import anki_finance.stock_market as mod
        fake_config(mod, {})
        d = datetime(2026, 5, 4)  # Monday
        assert mod._is_working_day(d) is True

    def test_friday_is_working(self, fake_config):
        import anki_finance.stock_market as mod
        fake_config(mod, {})
        d = datetime(2026, 5, 8)  # Friday
        assert mod._is_working_day(d) is True

    def test_saturday_not_working(self, fake_config):
        import anki_finance.stock_market as mod
        fake_config(mod, {})
        d = datetime(2026, 5, 9)  # Saturday
        assert mod._is_working_day(d) is False

    def test_sunday_not_working(self, fake_config):
        import anki_finance.stock_market as mod
        fake_config(mod, {})
        d = datetime(2026, 5, 10)  # Sunday
        assert mod._is_working_day(d) is False


class TestNextWorkingDay:
    """_next_working_day trả về ngày làm việc tiếp theo."""

    def test_friday_to_monday(self, fake_config):
        import anki_finance.stock_market as mod
        fake_config(mod, {})
        fri = datetime(2026, 5, 8)  # Friday
        nxt = mod._next_working_day(fri)
        assert nxt.weekday() < 5
        assert nxt > fri

    def test_monday_to_tuesday(self, fake_config):
        import anki_finance.stock_market as mod
        fake_config(mod, {})
        mon = datetime(2026, 5, 4)  # Monday
        nxt = mod._next_working_day(mon)
        assert nxt == datetime(2026, 5, 5)


class TestAddWorkingDays:
    """_add_working_days cộng n ngày làm việc."""

    def test_add_0_days(self, fake_config):
        import anki_finance.stock_market as mod
        fake_config(mod, {})
        d = datetime(2026, 5, 4)  # Monday
        result = mod._add_working_days(d, 0)
        assert result == d

    def test_add_2_working_days_skips_weekend(self, fake_config):
        import anki_finance.stock_market as mod
        fake_config(mod, {})
        thu = datetime(2026, 5, 7)  # Thursday
        result = mod._add_working_days(thu, 2)
        # Thu + 2 working days = Mon (skip Fri→Sat→Sun→Mon)
        assert result == datetime(2026, 5, 11)  # Monday


class TestSecondsFromMidnight:
    """_seconds_from_midnight tính giây từ 00:00."""

    def test_midnight_is_0(self, fake_config):
        import anki_finance.stock_market as mod
        fake_config(mod, {})
        d = datetime(2026, 5, 6, 0, 0, 0)
        assert mod._seconds_from_midnight(d) == 0

    def test_9am_is_32400(self, fake_config):
        import anki_finance.stock_market as mod
        fake_config(mod, {})
        d = datetime(2026, 5, 6, 9, 0, 0)
        assert mod._seconds_from_midnight(d) == 32400  # 9*3600


class TestComputeTplusRelease:
    """_compute_tplus_release tính T+2 release time."""

    def test_normal_t2_release(self, fake_config, monkeypatch):
        import anki_finance.stock_market as mod
        fake_config(mod, {})
        # Mua vào Monday 9h
        buy_dt = datetime(2026, 5, 4, 9, 0, 0)  # Monday
        buy_ts = buy_dt.timestamp()
        release_ts = mod._compute_tplus_release(buy_ts)
        release_dt = datetime.fromtimestamp(release_ts)
        # T+2 = Wednesday 9h
        assert release_dt.weekday() == 2  # Wednesday
        assert release_dt.hour == 9


class TestFmtTs:
    """_fmt_ts format timestamp đúng format."""

    def test_format_correct(self, fake_config):
        import anki_finance.stock_market as mod
        fake_config(mod, {})
        d = datetime(2026, 5, 6, 14, 30, 0)
        assert mod._fmt_ts(d.timestamp()) == "06/05/2026 14:30"


class TestRandomNormal:
    """_random_normal sử dụng Box-Muller."""

    def test_returns_float(self, fake_config):
        import anki_finance.stock_market as mod
        fake_config(mod, {})
        val = mod._random_normal(0, 1)
        assert isinstance(val, float)


class TestGetReviewsThreshold:
    """_get_reviews_threshold trả về số trong range 40-60."""

    def test_within_range(self, fake_config):
        import anki_finance.stock_market as mod
        fake_config(mod, {})
        for _ in range(100):
            t = mod._get_reviews_threshold()
            assert 40 <= t <= 60


class TestConstants:
    """Các hằng số trong stock_market."""

    def test_update_interval(self, fake_config):
        import anki_finance.stock_market as mod
        fake_config(mod, {})
        assert mod.UPDATE_INTERVAL_SECS == 4 * 3600

    def test_max_history_entries(self, fake_config):
        import anki_finance.stock_market as mod
        fake_config(mod, {})
        assert mod.MAX_HISTORY_ENTRIES == 50

    def test_t_plus_days(self, fake_config):
        import anki_finance.stock_market as mod
        fake_config(mod, {})
        assert mod.T_PLUS_DAYS == 2

    def test_div_chance(self, fake_config):
        import anki_finance.stock_market as mod
        fake_config(mod, {})
        assert 0 < mod.DIV_CHANCE < 1


class TestGetAllSymbols:
    """get_all_symbols trả về danh sách 15 mã."""

    def test_returns_list_of_dicts(self, fake_config):
        import anki_finance.stock_market as mod
        fake_config(mod, {})
        symbols = mod.get_all_symbols()
        assert len(symbols) == 15
        for s in symbols:
            assert "symbol" in s
            assert "base_price" in s
            assert "volatility" in s


class TestGetMarketSummary:
    """get_market_summary trả về dict với các keys cần."""

    def test_returns_required_fields(self, fake_config):
        import anki_finance.stock_market as mod
        store = fake_config(mod, {})
        # Need to seed market first - fake_config patches cfg_dict
        # Market is read from config, so we need to set it up
        summary = mod.get_market_summary()
        for key in ("vnindex", "up", "down", "flat", "total_volume", "last_updated"):
            assert key in summary, f"Missing key: {key}"

    def test_empty_market_returns_zero_counts(self, fake_config):
        import anki_finance.stock_market as mod
        store = fake_config(mod, {})

        class FakeMarket(dict):
            def items(self):
                return []

        fake_market = {}
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr(mod, "get_market_data", lambda: fake_market)
        try:
            summary = mod.get_market_summary()
            assert summary["up"] == 0
            assert summary["down"] == 0
            assert summary["flat"] == 0
            assert summary["total_volume"] == 0
        finally:
            monkeypatch.undo()


class TestGetTradingSessionInfo:
    """get_trading_session_info trả về thông tin phiên."""

    def test_has_required_keys(self, fake_config):
        import anki_finance.stock_market as mod
        fake_config(mod, {})
        info = mod.get_trading_session_info()
        for k in ("in_session", "session_name", "seconds_until_end", "seconds_until_next",
                  "session_start_str", "session_end_str", "source"):
            assert k in info, f"Missing key: {k}"

    def test_source_is_time_or_review(self, fake_config):
        import anki_finance.stock_market as mod
        fake_config(mod, {})
        info = mod.get_trading_session_info()
        assert info["source"] in ("time", "review")


class TestAddSharesDirectly:
    """_add_shares_directly thêm CP vào portfolio (từ bond)."""

    def _seed_market(self, store, mod):
        """Seed market data để VCB tồn tại."""
        store[mod._KEY_MARKET] = {
            "VCB": {
                "current_price": 50000,
                "company_name": "Vietcombank",
                "sector_emoji": "🏦",
                "sector": "Ngân hàng",
            }
        }

    def test_adds_shares_to_portfolio(self, fake_config):
        import anki_finance.stock_market as mod
        store = fake_config(mod, {})
        self._seed_market(store, mod)
        result = mod._add_shares_directly("VCB", 100, 5_000_000)
        assert result["ok"] is True
        portfolio = mod.get_portfolio()
        assert len(portfolio) == 1
        assert portfolio[0]["symbol"] == "VCB"
        assert portfolio[0]["shares"] == 100

    def test_accumulates_existing_holding(self, fake_config):
        import anki_finance.stock_market as mod
        store = fake_config(mod, {})
        self._seed_market(store, mod)
        mod._add_shares_directly("VCB", 100, 5_000_000)
        mod._add_shares_directly("VCB", 50, 2_500_000)
        portfolio = mod.get_portfolio()
        vcb = next(h for h in portfolio if h["symbol"] == "VCB")
        assert vcb["shares"] == 150
        assert vcb["total_invested"] == 7_500_000


class TestGetPortfolio:
    """get_portfolio trả về danh sách holdings."""

    def test_empty_portfolio(self, fake_config):
        import anki_finance.stock_market as mod
        store = fake_config(mod, {})
        portfolio = mod.get_portfolio()
        assert portfolio == []


class TestGetStockTransactions:
    """get_stock_transactions lọc và sắp xếp giao dịch."""

    def test_empty_returns_empty_list(self, fake_config):
        import anki_finance.stock_market as mod
        store = fake_config(mod, {})
        txns = mod.get_stock_transactions()
        assert txns == []

    def test_filter_by_symbol(self, fake_config):
        import anki_finance.stock_market as mod
        store = fake_config(mod, {})
        # Cần ghi txn trực tiếp vào store
        mod._save_txns([
            {"symbol": "VCB", "type": "buy", "timestamp": 1000},
            {"symbol": "FPT", "type": "buy", "timestamp": 1001},
        ])
        vcb_txns = mod.get_stock_transactions("VCB")
        assert len(vcb_txns) == 1
        assert vcb_txns[0]["symbol"] == "VCB"


class TestGetPortfolioSummary:
    """get_portfolio_summary trả về tổng quan."""

    def test_empty_portfolio_returns_zeros(self, fake_config):
        import anki_finance.stock_market as mod
        store = fake_config(mod, {})
        summary = mod.get_portfolio_summary()
        assert summary["total_invested"] == 0
        assert summary["total_market_value"] == 0
        assert summary["count"] == 0
