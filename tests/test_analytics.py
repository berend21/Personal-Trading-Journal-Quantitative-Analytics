from datetime import datetime
from analytics import _date_range
from analyze.statistics import (
    calculate_drawdown,
    calculate_streaks,
    percentage,
    safe_float,
)


class TestSafeFloat:

    def test_none_uses_default(self):
        assert safe_float(None) == 0.0

    def test_none_can_use_custom_default(self):
        assert safe_float(None, 99.0) == 99.0

    def test_numeric_string(self):
        assert safe_float("12.5") == 12.5

    def test_invalid_string_uses_default(self):
        assert safe_float("abc") == 0.0


class TestPercentage:

    def test_percentage(self):
        assert percentage(25, 100) == 25.0

    def test_percentage_rounding(self):
        assert percentage(1, 3) == 33.3

    def test_zero_denominator(self):
        assert percentage(10, 0) == 0.0


class TestStreaks:

    def test_win_streak(self):
        wins, losses = calculate_streaks(
            [1, 2, -1, 3, 4, 5, -1]
        )

        assert wins == 3
        assert losses == 1

    def test_loss_streak(self):
        wins, losses = calculate_streaks(
            [1, -1, -2, -3, 2]
        )

        assert wins == 1
        assert losses == 3

    def test_breakeven_breaks_streaks(self):
        wins, losses = calculate_streaks(
            [1, 2, 0, 3, -1, 0, -2]
        )

        assert wins == 2
        assert losses == 1

    def test_empty_sequence(self):
        assert calculate_streaks([]) == (0, 0)


class TestDrawdown:

    def test_drawdown_after_peak(self):
        result = calculate_drawdown(
            [1, 1, -1, -2, 1]
        )

        assert result["max_drawdown"] == -3.0
        assert result["equity_curve"] == [
            1.0,
            2.0,
            1.0,
            -1.0,
            0.0,
        ]
        assert result["drawdown_curve"] == [
            0.0,
            0.0,
            -1.0,
            -3.0,
            -2.0,
        ]

    def test_no_drawdown(self):
        result = calculate_drawdown(
            [1, 2, 3]
        )

        assert result["max_drawdown"] == 0.0
        assert result["current_drawdown"] == 0.0
        assert result["equity_curve"] == [
            1.0,
            3.0,
            6.0,
        ]
        assert result["drawdown_curve"] == [
            0.0,
            0.0,
            0.0,
        ]

    def test_empty_sequence(self):
        result = calculate_drawdown([])

        assert result["max_drawdown"] == 0.0
        assert result["current_drawdown"] == 0.0
        assert result["max_drawdown_duration"] == 0
        assert result["recovery_trades"] is None
        assert result["equity_curve"] == []
        assert result["drawdown_curve"] == []


class TestDateRange:

    def test_monthly_range(self):
        now = datetime(2026, 8, 15, 14, 30)

        start, end = _date_range("monthly", now)

        assert start == datetime(2026, 8, 1, 0, 0, 0)
        assert end == datetime(2026, 8, 15, 23, 59, 59, 999999)

    def test_last_month_range(self):
        now = datetime(2026, 8, 15, 14, 30)

        start, end = _date_range("last_month", now)

        assert start == datetime(2026, 7, 1, 0, 0, 0)
        assert end == datetime(2026, 7, 31, 23, 59, 59, 999999)

    def test_ytd_range(self):
        now = datetime(2026, 8, 15, 14, 30)

        start, end = _date_range("ytd", now)

        assert start == datetime(2026, 1, 1, 0, 0, 0)
        assert end == datetime(2026, 8, 15, 23, 59, 59, 999999)


    def test_all_returns_no_range(self):
        now = datetime(2026, 8, 15)

        assert _date_range("all", now) == (None, None)

    def test_last_month_range_handles_leap_year(self):
        now = datetime(2024, 3, 15, 14, 30)

        start, end = _date_range("last_month", now)

        assert start == datetime(2024, 2, 1, 0, 0, 0)
        assert end == datetime(2024, 2, 29, 23, 59, 59, 999999)

    def test_last_month_range_across_year_boundary(self):
        now = datetime(2026, 1, 15, 14, 30)

        start, end = _date_range("last_month", now)

        assert start == datetime(2025, 12, 1, 0, 0, 0)
        assert end == datetime(2025, 12, 31, 23, 59, 59, 999999)


