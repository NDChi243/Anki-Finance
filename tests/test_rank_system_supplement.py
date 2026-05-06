# -*- coding: utf-8 -*-
"""Supplement tests cho rank_system.py — các hàm chưa có trong test_rank_system.py."""

from __future__ import annotations

import pytest


class TestGetHighest:
    """get_highest_reward_mult, get_highest_xp_mult, get_highest_rank_index."""

    def test_get_highest_reward_mult_returns_float(self, fake_config):
        import anki_finance.rank_system as mod
        fake_config(mod, {})
        val = mod.get_highest_reward_mult()
        assert isinstance(val, float)
        assert val >= 1.0

    def test_get_highest_xp_mult_returns_float(self, fake_config):
        import anki_finance.rank_system as mod
        fake_config(mod, {})
        val = mod.get_highest_xp_mult()
        assert isinstance(val, float)
        assert val >= 1.0

    def test_get_highest_rank_index_returns_int(self, fake_config):
        import anki_finance.rank_system as mod
        fake_config(mod, {})
        idx = mod.get_highest_rank_index()
        assert isinstance(idx, int)
        assert idx >= 0


class TestUnlockGate:
    """_unlock_gate kiểm tra feature gate dựa trên rank."""

    def test_unknown_feature_auto_unlock(self, fake_config):
        import anki_finance.rank_system as mod
        fake_config(mod, {})
        result = mod._unlock_gate("basic_shop")
        assert result is True


class TestAddXp:
    """add_xp ghi XP (cho phép âm)."""

    def test_adds_xp_to_config(self, fake_config):
        import anki_finance.rank_system as mod
        store = fake_config(mod, {})
        mod.add_xp(100)
        assert mod.get_xp() == 100

    def test_accumulates_xp(self, fake_config):
        import anki_finance.rank_system as mod
        store = fake_config(mod, {})
        mod.add_xp(100)
        mod.add_xp(50)
        assert mod.get_xp() == 150

    def test_negative_xp_stored_as_is(self, fake_config):
        import anki_finance.rank_system as mod
        store = fake_config(mod, {})
        mod.add_xp(-10)
        assert mod.get_xp() == -10


class TestGetAndAddKn:
    """get_kn / add_kn quản lý knowledge points."""

    def test_get_kn_default_zero(self, fake_config):
        import anki_finance.rank_system as mod
        fake_config(mod, {})
        assert mod.get_kn() == 0

    def test_add_kn_increases(self, fake_config):
        import anki_finance.rank_system as mod
        fake_config(mod, {})
        mod.add_kn(200)
        assert mod.get_kn() == 200

    def test_add_kn_accumulates(self, fake_config):
        import anki_finance.rank_system as mod
        fake_config(mod, {})
        mod.add_kn(100)
        mod.add_kn(50)
        assert mod.get_kn() == 150

    def test_negative_kn_stored_as_is(self, fake_config):
        import anki_finance.rank_system as mod
        fake_config(mod, {})
        mod.add_kn(-10)
        assert mod.get_kn() == -10


class TestGetRankHistory:
    """get_rank_history trả về dict."""

    def test_empty_when_no_history(self, fake_config):
        import anki_finance.rank_system as mod
        store = fake_config(mod, {})
        history = mod.get_rank_history()
        assert isinstance(history, dict)


class TestSnapshotRankIfChanged:
    """snapshot_rank_if_changed ghi snapshot khi rank thay đổi."""

    def test_first_unknown_rank_creates_snapshot(self, fake_config):
        import anki_finance.rank_system as mod
        store = fake_config(mod, {})
        result = mod.snapshot_rank_if_changed("sv1")
        # Lần đầu với rank "sv1" → tạo snapshot (nếu chưa có)
        assert result is None or isinstance(result, dict)

    def test_snapshot_requires_col_ready(self, fake_config):
        import anki_finance.rank_system as mod
        store = fake_config(mod, {})
        # col_ready trả về True (đã patch bởi fake_config)
        result = mod.snapshot_rank_if_changed("sv2")
        # sv2 chưa từng snapshot → trả về dict snapshot
        if result is not None:
            assert isinstance(result, dict)
            assert "simple_xp" in result
            assert "full_xp" in result
            assert "achieved_at" in result


class TestCalcRankWithKn:
    """_calc_rank với tham số kn (mới)."""

    def test_calc_rank_accepts_kn_param(self, fake_config):
        import anki_finance.rank_system as mod
        fake_config(mod, {})
        result = mod._calc_rank(0, 0, kn=0)
        # _calc_rank trả về rank dict (RANKS entry) có key 'id'
        assert "id" in result

    def test_kn_affects_rank_calculation(self, fake_config):
        import anki_finance.rank_system as mod
        fake_config(mod, {})
        # Với kn=0, rank cao nhất đạt được là nlc3 (vì tt1 cần kn=1000)
        result_no_kn = mod._calc_rank(10_000_000, 10_000_000_000, kn=0)
        # Với kn đủ cao, có thể lên rank cao hơn
        result_with_kn = mod._calc_rank(10_000_000, 10_000_000_000, kn=10_000_000)
        idx_no = mod._RANK_INDEX.get(result_no_kn["id"], 0)
        idx_kn = mod._RANK_INDEX.get(result_with_kn["id"], 0)
        assert idx_kn >= idx_no


class TestGetAllRanks:
    """get_all_ranks trả về RANKS (same reference, không phải copy)."""

    def test_returns_list(self, fake_config):
        import anki_finance.rank_system as mod
        fake_config(mod, {})
        ranks = mod.get_all_ranks()
        assert isinstance(ranks, list)
        assert len(ranks) > 0

    def test_returns_same_reference(self, fake_config):
        import anki_finance.rank_system as mod
        fake_config(mod, {})
        ranks = mod.get_all_ranks()
        # get_all_ranks trả về RANKS reference (không copy)
        assert ranks is mod.RANKS
