# -*- coding: utf-8 -*-
"""
test_rank_system.py — Unit tests cho rank_system.py

Coverage:
  A. get_xp_for_ease()  — XP theo ease button
  B. _calc_rank()       — tính rank từ XP + balance
  C. _next_rank()       — rank kế tiếp
  D. get_rank_status()  — dict trạng thái đầy đủ + progress %
  E. Bảng RANKS         — tính toàn vẹn của bảng định nghĩa
"""
from __future__ import annotations

import pytest

import anki_finance.rank_system as rs

_KEY_XP   = "anki_tycoon_xp"
_KEY_KN   = "anki_tycoon_kn_points"
_KEY_RANK = "anki_tycoon_rank"


# ═══════════════════════════════════════════════════════════════
# A. get_xp_for_ease
# ═══════════════════════════════════════════════════════════════

class TestGetXpForEase:
    """XP_PER_EASE = {1:2, 2:8, 3:15, 4:25}"""

    @pytest.mark.parametrize("ease,expected", [
        (1, 2),   # Again
        (2, 8),   # Hard
        (3, 15),  # Good
        (4, 25),  # Easy
    ])
    def test_known_ease(self, ease, expected):
        assert rs.get_xp_for_ease(ease) == expected

    def test_unknown_ease_returns_0(self):
        assert rs.get_xp_for_ease(0)  == 0
        assert rs.get_xp_for_ease(5)  == 0
        assert rs.get_xp_for_ease(-1) == 0

    def test_easy_gives_most_xp(self):
        assert rs.get_xp_for_ease(4) > rs.get_xp_for_ease(3) \
               > rs.get_xp_for_ease(2) > rs.get_xp_for_ease(1)


# ═══════════════════════════════════════════════════════════════
# B. _calc_rank (hàm thuần túy)
# ═══════════════════════════════════════════════════════════════

class TestCalcRank:
    """
    Điều kiện lên rank: ĐỦ CẢ HAI xp >= xp_required VÀ balance >= bal_required.
    """

    def test_new_player_gets_sv1(self):
        rank = rs._calc_rank(xp=0, balance=0)
        assert rank["id"] == "sv1"

    def test_sv1_label_correct(self):
        rank = rs._calc_rank(0, 0)
        # Rank đầu tiên thuộc nhóm "Học giả" (đã đổi tên từ Sinh viên)
        assert "Học giả" in rank["label"] or rank["group"] == "Học giả"

    def test_enough_xp_and_balance_advances_rank(self):
        # sv2: xp=200, bal=10M
        rank = rs._calc_rank(xp=200, balance=10_000_000)
        assert rank["id"] == "sv2"

    def test_enough_xp_not_enough_balance_stays_lower(self):
        # sv2: xp=200, bal=10M; nếu balance < 10M → ở sv1
        rank = rs._calc_rank(xp=200, balance=9_999_999)
        assert rank["id"] == "sv1"

    def test_enough_balance_not_enough_xp_stays_lower(self):
        rank = rs._calc_rank(xp=199, balance=10_000_000)
        assert rank["id"] == "sv1"

    def test_nlc1_requires_both_conditions(self):
        # nlc1: xp=1000, bal=50M
        assert rs._calc_rank(1000, 50_000_000)["id"] == "nlc1"
        assert rs._calc_rank(999,  50_000_000)["id"] != "nlc1"
        assert rs._calc_rank(1000, 49_999_999)["id"] != "nlc1"

    def test_returns_highest_qualified_rank(self):
        # Đủ điều kiện sv1+sv2+sv3 → trả về sv3 (cao nhất)
        # sv3: xp=500, bal=20M
        rank = rs._calc_rank(xp=500, balance=20_000_000)
        assert rank["id"] == "sv3"

    def test_very_high_stats_max_rank(self):
        rank = rs._calc_rank(xp=99_999_999, balance=999_999_999_999_999, kn=99_999_999)
        assert rank["id"] == rs.RANKS[-1]["id"]  # Rank cao nhất

    def test_rank_has_required_fields(self):
        rank = rs._calc_rank(0, 0)
        for field in ("id", "label", "xp", "bal", "emoji", "color", "group"):
            assert field in rank, f"Thiếu field: {field}"


# ═══════════════════════════════════════════════════════════════
# C. _next_rank
# ═══════════════════════════════════════════════════════════════

class TestNextRank:
    def test_sv1_next_is_sv2(self):
        nxt = rs._next_rank("sv1")
        assert nxt is not None
        assert nxt["id"] == "sv2"

    def test_sv2_next_is_sv3(self):
        nxt = rs._next_rank("sv2")
        assert nxt["id"] == "sv3"

    def test_max_rank_returns_none(self):
        # Rank cuối cùng
        last_rank = rs.RANKS[-1]
        assert rs._next_rank(last_rank["id"]) is None

    def test_invalid_id_returns_none(self):
        assert rs._next_rank("not_a_real_rank") is None

    def test_all_except_last_have_next(self):
        for rank in rs.RANKS[:-1]:
            assert rs._next_rank(rank["id"]) is not None, \
                f"{rank['id']} không có rank tiếp theo"

    def test_chain_is_complete(self):
        """Duyệt toàn bộ chuỗi rank từ đầu đến cuối."""
        visited = []
        current = rs.RANKS[0]
        while current is not None:
            visited.append(current["id"])
            current = rs._next_rank(current["id"])
        assert len(visited) == len(rs.RANKS)


# ═══════════════════════════════════════════════════════════════
# D. get_rank_status
# ═══════════════════════════════════════════════════════════════

class TestGetRankStatus:
    """Dict đầy đủ với progress percentage."""

    def test_required_fields(self, fake_config):
        fake_config(rs, {_KEY_XP: 0})
        status = rs.get_rank_status(balance=0)
        for field in ("xp", "rank_id", "rank_label", "rank_emoji",
                      "next_rank", "xp_pct", "bal_pct", "overall_pct",
                      "xp_needed", "bal_needed", "is_max"):
            assert field in status, f"Thiếu field: {field}"

    def test_new_player_status(self, fake_config):
        fake_config(rs, {_KEY_XP: 0})
        status = rs.get_rank_status(balance=0)
        assert status["rank_id"] == "sv1"
        assert status["is_max"] is False

    def test_xp_pct_correct(self, fake_config):
        # sv2 cần xp=200, bal=10M; ta có xp=100 → xp_pct = 50%
        fake_config(rs, {_KEY_XP: 100})
        status = rs.get_rank_status(balance=0)
        # Đang ở sv1, next là sv2 (xp=200) → xp_pct = min(100, 100/200*100) = 50
        assert status["xp_pct"] == pytest.approx(50.0)

    def test_bal_pct_correct(self, fake_config):
        # Đang ở sv1, next sv2 cần 10M; ta có 5M → bal_pct = 50%
        fake_config(rs, {_KEY_XP: 0})
        status = rs.get_rank_status(balance=5_000_000)
        assert status["bal_pct"] == pytest.approx(50.0)

    def test_overall_pct_is_min_of_xp_bal(self, fake_config):
        # xp_pct=80%, bal_pct=30% → overall=30%
        sv2_xp = 200
        sv2_bal = 10_000_000
        fake_config(rs, {_KEY_XP: int(sv2_xp * 0.8)})  # 80% XP
        status = rs.get_rank_status(balance=int(sv2_bal * 0.3))  # 30% bal
        assert status["overall_pct"] == pytest.approx(30.0, abs=0.5)

    def test_xp_needed_decreases_as_xp_grows(self, fake_config):
        fake_config(rs, {_KEY_XP: 50})
        s1 = rs.get_rank_status(balance=0)
        fake_config(rs, {_KEY_XP: 150})
        s2 = rs.get_rank_status(balance=0)
        assert s2["xp_needed"] < s1["xp_needed"]

    def test_max_rank_status(self, fake_config):
        fake_config(rs, {_KEY_XP: 99_999_999, _KEY_KN: 99_999_999})
        status = rs.get_rank_status(balance=999_999_999_999_999)
        assert status["is_max"] is True
        assert status["next_rank"] is None
        assert status["xp_needed"] == 0
        assert status["bal_needed"] == 0
        assert status["overall_pct"] == pytest.approx(100.0)

    def test_uses_get_balance_when_no_arg(self, fake_config, monkeypatch):
        """Khi không truyền balance, phải lấy từ get_balance()."""
        fake_config(rs, {_KEY_XP: 0})
        monkeypatch.setattr("anki_finance.balance.get_balance", lambda: 5_000_000)
        status = rs.get_rank_status()  # Không truyền balance → gọi get_balance()
        assert status["rank_id"] == "sv1"  # 5M < 10M (sv2 cần)


# ═══════════════════════════════════════════════════════════════
# E. Bảng RANKS — tính toàn vẹn
# ═══════════════════════════════════════════════════════════════

class TestRanksTable:
    def test_ranks_not_empty(self):
        assert len(rs.RANKS) > 0

    def test_first_rank_starts_from_zero(self):
        assert rs.RANKS[0]["xp"]  == 0
        assert rs.RANKS[0]["bal"] == 0

    def test_xp_requirements_non_decreasing(self):
        xps = [r["xp"] for r in rs.RANKS]
        for i in range(1, len(xps)):
            assert xps[i] >= xps[i - 1], \
                f"rank {rs.RANKS[i]['id']}: xp {xps[i]} < xps[{i-1}]={xps[i-1]}"

    def test_bal_requirements_non_decreasing(self):
        bals = [r["bal"] for r in rs.RANKS]
        for i in range(1, len(bals)):
            assert bals[i] >= bals[i - 1]

    def test_all_ranks_have_required_fields(self):
        for rank in rs.RANKS:
            for field in ("id", "label", "xp", "bal", "emoji", "color", "group"):
                assert field in rank, f"Rank {rank.get('id')!r} thiếu field {field!r}"

    def test_all_ids_unique(self):
        ids = [r["id"] for r in rs.RANKS]
        assert len(ids) == len(set(ids)), "Có ID rank trùng nhau"

    def test_ranks_count_reasonable(self):
        """Số lượng rank tối thiểu >= 20."""
        assert len(rs.RANKS) >= 20

    def test_last_rank_has_highest_requirements(self):
        last = rs.RANKS[-1]
        assert last["xp"] == max(r["xp"] for r in rs.RANKS)
        assert last["bal"] == max(r["bal"] for r in rs.RANKS)
        assert last.get("kn", 0) == max(r.get("kn", 0) for r in rs.RANKS)

    def test_get_all_ranks_returns_copy(self):
        all_r = rs.get_all_ranks()
        assert len(all_r) == len(rs.RANKS)
        assert all_r is not rs.RANKS or all_r == rs.RANKS
