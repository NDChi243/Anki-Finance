# -*- coding: utf-8 -*-
"""
test_streak_system.py — Unit tests cho streak_system.py

Coverage:
  A. get_multiplier()         — bảng nhân streak → multiplier
  B. record_card_reviewed()   — logic cập nhật streak ngày liên tiếp / bỏ ngày
  C. check_streak_broken()    — phát hiện streak bị mất khi mở Anki
  D. get_streak_status()      — trả về dict trạng thái đầy đủ
"""
from __future__ import annotations

import pytest

import anki_finance.streak_system as ss

# Config keys (copy từ module để test không phụ thuộc vào tên biến nội bộ)
_KEY_STREAK      = "anki_tycoon_streak"
_KEY_STREAK_DATE = "anki_tycoon_streak_date"
_KEY_BEST_STREAK = "anki_tycoon_best_streak"
_KEY_TODAY_CARDS = "anki_tycoon_streak_today_cards"
_KEY_TODAY_DATE  = "anki_tycoon_streak_today_date"

TODAY     = "2026-05-01"
YESTERDAY = "2026-04-30"
TWO_DAYS  = "2026-04-29"


@pytest.fixture(autouse=True)
def patch_dates(monkeypatch):
    """Cố định ngày hôm nay và hôm qua để test không phụ thuộc ngày thật."""
    monkeypatch.setattr(ss, "_today",     lambda: TODAY)
    monkeypatch.setattr(ss, "_yesterday", lambda: YESTERDAY)


# ═══════════════════════════════════════════════════════════════
# A. get_multiplier
# ═══════════════════════════════════════════════════════════════

class TestGetMultiplier:
    """Tra bảng STREAK_MULTIPLIERS."""

    @pytest.mark.parametrize("streak,expected", [
        (0,   1.0),
        (1,   1.1),
        (2,   1.1),
        (3,   1.2),
        (6,   1.2),
        (7,   1.5),
        (13,  1.5),
        (14,  1.8),
        (29,  1.8),
        (30,  2.0),
        (59,  2.0),
        (60,  2.5),
        (99,  2.5),
        (100, 3.0),
        (200, 3.0),
        (365, 3.0),
    ])
    def test_multiplier_values(self, streak, expected):
        assert ss.get_multiplier(streak) == pytest.approx(expected), \
            f"streak={streak}: expected {expected}"

    def test_multiplier_increases_with_streak(self):
        """Multiplier phải không giảm khi streak tăng."""
        prev = ss.get_multiplier(0)
        for s in range(1, 101):
            curr = ss.get_multiplier(s)
            assert curr >= prev, f"streak {s}: {curr} < {prev} (giảm!)"
            prev = curr

    def test_max_multiplier_is_3(self):
        assert ss.get_multiplier(1000) == pytest.approx(3.0)

    def test_milestone_set(self):
        """Các mốc streak quan trọng."""
        assert ss.STREAK_MILESTONES == {3, 7, 14, 30, 60, 100, 200, 365}


# ═══════════════════════════════════════════════════════════════
# B. record_card_reviewed
# ═══════════════════════════════════════════════════════════════

class TestRecordCardReviewed:
    """Logic cập nhật streak + đếm thẻ hàng ngày."""

    MIN = ss.MIN_CARDS_FOR_STREAK  # 5

    def test_below_min_cards_no_streak_update(self, fake_config):
        store = fake_config(ss, {
            _KEY_TODAY_DATE:  TODAY,
            _KEY_TODAY_CARDS: 0,
            _KEY_STREAK:      5,
            _KEY_STREAK_DATE: YESTERDAY,
        })
        result = ss.record_card_reviewed()
        assert result["streak_updated"] is False
        # Streak không thay đổi
        assert store[_KEY_STREAK] == 5

    def test_today_cards_increments_each_call(self, fake_config):
        store = fake_config(ss, {
            _KEY_TODAY_DATE:  TODAY,
            _KEY_TODAY_CARDS: 0,
        })
        ss.record_card_reviewed()
        assert store[_KEY_TODAY_CARDS] == 1
        ss.record_card_reviewed()
        assert store[_KEY_TODAY_CARDS] == 2

    def test_reaching_min_cards_updates_streak_consecutive(self, fake_config, monkeypatch):
        """Thẻ thứ MIN_CARDS trong ngày → streak tăng nếu hôm qua đã review."""
        monkeypatch.setattr(ss, "check_and_unlock", lambda *a: None, raising=False)
        store = fake_config(ss, {
            _KEY_TODAY_DATE:  TODAY,
            _KEY_TODAY_CARDS: self.MIN - 1,  # Còn thiếu 1 thẻ
            _KEY_STREAK:      7,
            _KEY_STREAK_DATE: YESTERDAY,     # Hôm qua đã review → liên tiếp
        })
        result = ss.record_card_reviewed()
        assert result["streak_updated"] is True
        assert result["streak"] == 8
        assert store[_KEY_STREAK] == 8

    def test_missed_day_resets_streak_to_1(self, fake_config, monkeypatch):
        """Bỏ ngày (streak_date < hôm qua) → streak reset = 1."""
        monkeypatch.setattr(ss, "check_and_unlock", lambda *a: None, raising=False)
        store = fake_config(ss, {
            _KEY_TODAY_DATE:  TODAY,
            _KEY_TODAY_CARDS: self.MIN - 1,
            _KEY_STREAK:      15,
            _KEY_STREAK_DATE: TWO_DAYS,  # 2 ngày trước → bỏ ngày
        })
        result = ss.record_card_reviewed()
        assert result["streak"] == 1
        assert store[_KEY_STREAK] == 1

    def test_first_time_ever_streak_starts_at_1(self, fake_config, monkeypatch):
        """Chưa có streak_date → khởi tạo streak = 1."""
        monkeypatch.setattr(ss, "check_and_unlock", lambda *a: None, raising=False)
        store = fake_config(ss, {
            _KEY_TODAY_DATE:  TODAY,
            _KEY_TODAY_CARDS: self.MIN - 1,
            _KEY_STREAK:      0,
            _KEY_STREAK_DATE: "",          # Chưa từng review
        })
        result = ss.record_card_reviewed()
        assert result["streak"] == 1

    def test_same_day_no_double_update(self, fake_config):
        """Đã cập nhật hôm nay rồi → không tăng thêm."""
        store = fake_config(ss, {
            _KEY_TODAY_DATE:  TODAY,
            _KEY_TODAY_CARDS: self.MIN + 5,  # Đã đủ
            _KEY_STREAK:      10,
            _KEY_STREAK_DATE: TODAY,         # Đã update hôm nay
        })
        result = ss.record_card_reviewed()
        assert result["streak_updated"] is False
        assert store[_KEY_STREAK] == 10  # Không thay đổi

    def test_new_day_resets_today_cards(self, fake_config):
        """Sang ngày mới → bộ đếm today_cards phải reset về 0 trước khi đếm."""
        store = fake_config(ss, {
            _KEY_TODAY_DATE:  "2026-04-30",  # Ngày CŨ
            _KEY_TODAY_CARDS: 999,
            _KEY_STREAK:      5,
            _KEY_STREAK_DATE: TWO_DAYS,
        })
        ss.record_card_reviewed()
        # today_cards phải là 1 (reset → +1 thẻ vừa review)
        assert store[_KEY_TODAY_CARDS] == 1

    def test_best_streak_updated_when_exceeded(self, fake_config, monkeypatch):
        """best_streak phải tăng khi streak vượt kỷ lục cũ."""
        monkeypatch.setattr(ss, "check_and_unlock", lambda *a: None, raising=False)
        store = fake_config(ss, {
            _KEY_TODAY_DATE:  TODAY,
            _KEY_TODAY_CARDS: self.MIN - 1,
            _KEY_STREAK:      10,
            _KEY_BEST_STREAK: 10,
            _KEY_STREAK_DATE: YESTERDAY,
        })
        ss.record_card_reviewed()
        assert store[_KEY_BEST_STREAK] == 11

    def test_milestone_detected_correctly(self, fake_config, monkeypatch):
        """Khi streak đạt milestone (vd: 7), milestone_hit = True."""
        monkeypatch.setattr(ss, "check_and_unlock", lambda *a: None, raising=False)
        store = fake_config(ss, {
            _KEY_TODAY_DATE:  TODAY,
            _KEY_TODAY_CARDS: self.MIN - 1,
            _KEY_STREAK:      6,             # Sắp đạt 7
            _KEY_STREAK_DATE: YESTERDAY,
        })
        result = ss.record_card_reviewed()
        assert result["milestone_hit"] is True
        assert result["milestone_val"] == 7

    def test_non_milestone_streak_no_hit(self, fake_config, monkeypatch):
        monkeypatch.setattr(ss, "check_and_unlock", lambda *a: None, raising=False)
        store = fake_config(ss, {
            _KEY_TODAY_DATE:  TODAY,
            _KEY_TODAY_CARDS: self.MIN - 1,
            _KEY_STREAK:      4,             # 5 không phải milestone
            _KEY_STREAK_DATE: YESTERDAY,
        })
        result = ss.record_card_reviewed()
        assert result["milestone_hit"] is False


# ═══════════════════════════════════════════════════════════════
# C. check_streak_broken
# ═══════════════════════════════════════════════════════════════

class TestCheckStreakBroken:
    """Phát hiện streak bị mất khi mở Anki sáng hôm nay."""

    def test_no_last_date_not_broken(self, fake_config):
        fake_config(ss, {_KEY_STREAK_DATE: "", _KEY_STREAK: 0})
        assert ss.check_streak_broken() is False

    def test_streak_zero_not_broken(self, fake_config):
        fake_config(ss, {_KEY_STREAK_DATE: TWO_DAYS, _KEY_STREAK: 0})
        assert ss.check_streak_broken() is False

    def test_yesterday_date_not_broken(self, fake_config):
        """Review hôm qua → streak vẫn nguyên."""
        fake_config(ss, {_KEY_STREAK_DATE: YESTERDAY, _KEY_STREAK: 5})
        assert ss.check_streak_broken() is False

    def test_today_date_not_broken(self, fake_config):
        """Review hôm nay → streak vẫn nguyên."""
        fake_config(ss, {_KEY_STREAK_DATE: TODAY, _KEY_STREAK: 5})
        assert ss.check_streak_broken() is False

    def test_two_days_ago_broken(self, fake_config):
        """Bỏ hôm qua → streak bị reset về 0."""
        store = fake_config(ss, {_KEY_STREAK_DATE: TWO_DAYS, _KEY_STREAK: 10})
        broken = ss.check_streak_broken()
        assert broken is True
        assert store[_KEY_STREAK] == 0  # Đã reset

    def test_long_ago_broken(self, fake_config):
        fake_config(ss, {_KEY_STREAK_DATE: "2025-01-01", _KEY_STREAK: 365})
        assert ss.check_streak_broken() is True


# ═══════════════════════════════════════════════════════════════
# D. get_streak_status
# ═══════════════════════════════════════════════════════════════

class TestGetStreakStatus:
    """Dict trả về phải có đủ field và giá trị đúng."""

    def test_required_fields_present(self, fake_config):
        fake_config(ss, {
            _KEY_STREAK: 7,
            _KEY_BEST_STREAK: 10,
            _KEY_TODAY_DATE: TODAY,
            _KEY_TODAY_CARDS: 3,
            _KEY_STREAK_DATE: TODAY,
        })
        status = ss.get_streak_status()
        for field in ("streak", "best", "multiplier", "today_cards",
                      "cards_needed", "min_cards", "streak_active"):
            assert field in status, f"Thiếu field: {field}"

    def test_streak_value_correct(self, fake_config):
        fake_config(ss, {
            _KEY_STREAK: 14,
            _KEY_STREAK_DATE: TODAY,
            _KEY_TODAY_DATE: TODAY,
            _KEY_TODAY_CARDS: 10,
            _KEY_BEST_STREAK: 14,
        })
        status = ss.get_streak_status()
        assert status["streak"] == 14
        assert status["multiplier"] == pytest.approx(1.8)

    def test_cards_needed_correct(self, fake_config):
        fake_config(ss, {
            _KEY_TODAY_DATE: TODAY,
            _KEY_TODAY_CARDS: 2,
            _KEY_STREAK: 3,
            _KEY_STREAK_DATE: TODAY,
            _KEY_BEST_STREAK: 3,
        })
        status = ss.get_streak_status()
        assert status["today_cards"] == 2
        assert status["cards_needed"] == ss.MIN_CARDS_FOR_STREAK - 2

    def test_cards_needed_zero_when_enough(self, fake_config):
        fake_config(ss, {
            _KEY_TODAY_DATE: TODAY,
            _KEY_TODAY_CARDS: 10,  # > MIN_CARDS=5
            _KEY_STREAK: 5,
            _KEY_STREAK_DATE: TODAY,
            _KEY_BEST_STREAK: 5,
        })
        status = ss.get_streak_status()
        assert status["cards_needed"] == 0

    def test_streak_active_when_recent(self, fake_config):
        fake_config(ss, {
            _KEY_STREAK_DATE: YESTERDAY,
            _KEY_STREAK: 5,
            _KEY_TODAY_DATE: TODAY,
            _KEY_TODAY_CARDS: 0,
            _KEY_BEST_STREAK: 5,
        })
        status = ss.get_streak_status()
        assert status["streak_active"] is True

    def test_streak_not_active_when_missed(self, fake_config):
        fake_config(ss, {
            _KEY_STREAK_DATE: TWO_DAYS,
            _KEY_STREAK: 0,  # broken đã reset
            _KEY_TODAY_DATE: TODAY,
            _KEY_TODAY_CARDS: 0,
            _KEY_BEST_STREAK: 5,
        })
        status = ss.get_streak_status()
        assert status["streak_active"] is False
