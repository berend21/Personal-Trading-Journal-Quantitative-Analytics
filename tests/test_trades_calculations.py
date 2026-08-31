import pytest

from trades import (
    calculate_r_multiple,
    calculate_parent_rr_with_partials,
    parse_float,
    parse_time,
)


class TestCalculateRMultiple:

    def test_long_winning_trade(self):
        result = calculate_r_multiple(
            "LONG",
            100,
            110,
            95,
        )

        assert result == pytest.approx(2.0)

    def test_long_losing_trade(self):
        result = calculate_r_multiple(
            "LONG",
            100,
            95,
            95,
        )

        assert result == pytest.approx(-1.0)

    def test_long_breakeven(self):
        result = calculate_r_multiple(
            "LONG",
            100,
            100,
            95,
        )

        assert result == pytest.approx(0.0)

    def test_short_winning_trade(self):
        # Entry 100, SL 105 => 1R = 5
        # Exit 90 => +10 => +2R
        result = calculate_r_multiple(
            "SHORT",
            100,
            90,
            105,
        )

        assert result == pytest.approx(2.0)

    def test_short_losing_trade(self):
        result = calculate_r_multiple(
            "SHORT",
            100,
            105,
            105,
        )

        assert result == pytest.approx(-1.0)

    def test_short_breakeven(self):
        result = calculate_r_multiple(
            "SHORT",
            100,
            100,
            105,
        )

        assert result == pytest.approx(0.0)

    @pytest.mark.parametrize(
        "sort,open_price,close_price,stop_loss",
        [
            ("LONG", None, 110, 95),
            ("LONG", 100, None, 95),
            ("LONG", 100, 110, None),
            ("SHORT", None, 90, 105),
        ],
    )
    def test_missing_values_return_none(
        self,
        sort,
        open_price,
        close_price,
        stop_loss,
    ):
        assert (
            calculate_r_multiple(
                sort,
                open_price,
                close_price,
                stop_loss,
            )
            is None
        )

    def test_invalid_direction_returns_none(self):
        assert (
            calculate_r_multiple(
                "SIDEWAYS",
                100,
                110,
                95,
            )
            is None
        )

    def test_invalid_long_stop_returns_none(self):
        # LONG requires SL < entry.
        assert (
            calculate_r_multiple(
                "LONG",
                100,
                110,
                105,
            )
            is None
        )

    def test_invalid_short_stop_returns_none(self):
        # SHORT requires SL > entry.
        assert (
            calculate_r_multiple(
                "SHORT",
                100,
                90,
                95,
            )
            is None
        )

    def test_direction_is_case_insensitive(self):
        result = calculate_r_multiple(
            "long",
            100,
            110,
            95,
        )

        assert result == pytest.approx(2.0)

    def test_numeric_strings_are_supported(self):
        result = calculate_r_multiple(
            "LONG",
            "100",
            "110",
            "95",
        )

        assert result == pytest.approx(2.0)


class TestPartialRCalculation:

    def test_weighted_partial_rr(self):
        parent = {}

        partials = [
            {
                "risk_action": "CLOSE",
                "risk": 1.0,
                "RR": 2.0,
            },
            {
                "risk_action": "CLOSE",
                "risk": 1.0,
                "RR": 0.0,
            },
        ]

        result = calculate_parent_rr_with_partials(
            parent,
            partials,
        )

        assert result == pytest.approx(1.0)

    def test_weighted_partial_rr_respects_risk_size(self):
        partials = [
            {
                "risk_action": "CLOSE",
                "risk": 3.0,
                "RR": 2.0,
            },
            {
                "risk_action": "CLOSE",
                "risk": 1.0,
                "RR": -1.0,
            },
        ]

        result = calculate_parent_rr_with_partials(
            {},
            partials,
        )

        # (3 * 2 + 1 * -1) / 4 = 1.25
        assert result == pytest.approx(1.25)

    def test_open_partials_are_ignored(self):
        partials = [
            {
                "risk_action": "OPEN",
                "risk": 2.0,
                "RR": 5.0,
            },
            {
                "risk_action": "CLOSE",
                "risk": 1.0,
                "RR": 2.0,
            },
        ]

        result = calculate_parent_rr_with_partials(
            {},
            partials,
        )

        assert result == pytest.approx(2.0)

    def test_missing_rr_is_ignored(self):
        partials = [
            {
                "risk_action": "CLOSE",
                "risk": 1.0,
                "RR": None,
            },
            {
                "risk_action": "CLOSE",
                "risk": 1.0,
                "RR": 2.0,
            },
        ]

        result = calculate_parent_rr_with_partials(
            {},
            partials,
        )

        assert result == pytest.approx(2.0)

    def test_missing_risk_is_ignored(self):
        partials = [
            {
                "risk_action": "CLOSE",
                "risk": None,
                "RR": 2.0,
            },
            {
                "risk_action": "CLOSE",
                "risk": 1.0,
                "RR": 2.0,
            },
        ]

        result = calculate_parent_rr_with_partials(
            {},
            partials,
        )

        assert result == pytest.approx(2.0)

    def test_non_positive_risk_is_ignored(self):
        partials = [
            {
                "risk_action": "CLOSE",
                "risk": 0,
                "RR": 100,
            },
            {
                "risk_action": "CLOSE",
                "risk": -1,
                "RR": 100,
            },
            {
                "risk_action": "CLOSE",
                "risk": 1,
                "RR": 2,
            },
        ]

        result = calculate_parent_rr_with_partials(
            {},
            partials,
        )

        assert result == pytest.approx(2.0)

    def test_no_valid_partial_closes_returns_zero(self):
        result = calculate_parent_rr_with_partials(
            {},
            [],
        )

        assert result == pytest.approx(0.0)


class TestParsing:

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("100", 100.0),
            (" 100.5 ", 100.5),
            (100, 100.0),
            (None, None),
            ("", None),
            ("   ", None),
        ],
    )
    def test_parse_float(self, value, expected):
        assert parse_float(value, "Risk") == expected

    def test_parse_float_invalid_value(self):
        with pytest.raises(ValueError, match="Risk must be a valid number"):
            parse_float("abc", "Risk")

    @pytest.mark.parametrize(
        "value",
        [
            "2026-08-31 12:30",
            "2026-08-31 12:30:45",
            "2026-08-31T12:30",
            "2026-08-31T12:30:45",
        ],
    )
    def test_parse_time_accepts_supported_formats(self, value):
        assert parse_time(value) is not None

    def test_parse_time_empty_returns_none(self):
        assert parse_time("") is None

    def test_parse_time_none_returns_none(self):
        assert parse_time(None) is None

    def test_parse_time_invalid_returns_none(self):
        assert parse_time("not-a-date") is None
