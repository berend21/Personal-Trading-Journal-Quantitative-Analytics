from datetime import datetime

import pytest

from analytics import (
    _calculate_drawdown,
    _calculate_streaks,
    _date_range,
    _percentage,
    _safe_float,
)


class TestSafeFloat:

    def test_none_uses_default(self):
        assert _safe_float(None) == 0.0

    def test_none_can_use_custom_default(self):
        assert _safe_float(None, 99.0) == 99.0

    def test_numeric_string(self):
        assert _safe_float("12.5") == 12.5

    def test_invalid_string_uses_default(self):
        assert _safe_float("abc") == 0.0


class TestPercentage:

    def test_percentage(self):
        assert _percentage(25, 100) == 25.0

    def test_percentage_rounding(self):
        assert _percentage(1, 3) == 33.3

    def test_zero_denominator(self):
        assert _percentage(10, 0) == 0.0


class TestStreaks:

    def test_win_streak(self):
        wins, losses = _calculate_streaks(
            [1, 2, -1, 3, 4, 5, -1]
        )

        assert wins == 3
        assert losses == 1

    def test_loss_streak(self):
        wins, losses = _calculate_streaks(
            [1, -1, -2, -3, 2]
        )

        assert wins == 1
        assert losses == 3

    def test_breakeven_breaks_streaks(self):
        wins, losses = _calculate_streaks(
            [1, 2, 0, 3, -1, 0, -2]
        )

        assert wins == 2
        assert losses == 1

    def test_empty_sequence(self):
        assert _calculate_streaks([]) == (0, 0)


class TestDrawdown:

    def test_drawdown_after_peak(self):
        result = _calculate_drawdown(
            [1, 1, -1, -2, 1]
        )

        max_drawdown, max_drawdown_pct, equity, drawdown = result

        assert max_drawdown == -3.0
        assert equity == [1.0, 2.0, 1.0, -1.0, 0.0]
        assert drawdown == [0.0, 0.0, -1.0, -3.0, -2.0]

    def test_no_drawdown(self):
        result = _calculate_drawdown(
            [1, 2, 3]
        )

        max_drawdown, max_drawdown_pct, equity, drawdown = result

        assert max_drawdown == 0.0
        assert max_drawdown_pct == 0.0

    def test_empty_sequence(self):
        result = _calculate_drawdown([])

        assert result == (0.0, 0.0, [], [])


class TestDateRange:

    def test_monthly_range(self):
        now = datetime(2026, 8, 15, 14, 30)

        start, end = _date_range("monthly", now)

        assert start == datetime(2026, 8, 1, 0, 0, 0)
        assert end == datetime(2026, 8, 31, 23, 59, 59)

    def test_last_month_range(self):
        now = datetime(2026, 8, 15, 14, 30)

        start, end = _date_range("last_month", now)

        assert start == datetime(2026, 7, 1, 0, 0, 0)
        assert end == datetime(2026, 7, 31, 23, 59, 59)

    def test_yearly_range(self):
        now = datetime(2026, 8, 15, 14, 30)

        start, end = _date_range("yearly", now)

        assert start == datetime(2026, 1, 1, 0, 0, 0)
        assert end == datetime(2026, 12, 31, 23, 59, 59, 999999)

    def test_all_returns_no_range(self):
        now = datetime(2026, 8, 15)

        assert _date_range("all", now) == (None, None)
