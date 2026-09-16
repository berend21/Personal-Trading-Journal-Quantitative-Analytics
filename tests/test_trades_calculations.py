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

    @pytest.mark.parametrize(
        "entry,stop_distance,price_distance",
        [
            (100, 5, 10),
            (100, 5, -5),
            (100, 5, 0),
            (250, 25, 37.5),
            (50, 2.5, -7.5),
            (1000, 100, 250),
        ],
    )
    def test_long_short_symmetry(
        self,
        entry,
        stop_distance,
        price_distance,
    ):
        long_stop = entry - stop_distance
        long_exit = entry + price_distance

        short_stop = entry + stop_distance
        short_exit = entry - price_distance

        long_r = calculate_r_multiple(
            "LONG",
            entry,
            long_exit,
            long_stop,
        )

        short_r = calculate_r_multiple(
            "SHORT",
            entry,
            short_exit,
            short_stop,
        )

        assert long_r == pytest.approx(short_r)

    @pytest.mark.parametrize(
        "scale",
        [0.1, 0.5, 2, 10, 100],
    )
    def test_r_multiple_is_scale_invariant(self, scale):
        entry = 100
        exit_price = 110
        stop_loss = 95

        result = calculate_r_multiple(
            "LONG",
            entry * scale,
            exit_price * scale,
            stop_loss * scale,
        )

        assert result == pytest.approx(2.0)




class TestPartialRCalculation:

    def test_weighted_partial_rr(self):
        parent = {
            "initial_risk": 2.0,
        }

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
        parent = {
            "initial_risk": 4.0,
        }

        result = calculate_parent_rr_with_partials(
            parent,
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
        parent = {
                    "initial_risk": 1.0,
                }

        result = calculate_parent_rr_with_partials(
            parent,
            partials,
        )

        assert result == pytest.approx(2 / 3)

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
        parent = {
            "initial_risk": 2.0,
        }

        result = calculate_parent_rr_with_partials(
            parent,
            partials,
        )

        assert result == pytest.approx(1.0)

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
        parent = {
            "initial_risk": 2.0,
        }

        result = calculate_parent_rr_with_partials(
            parent,
            partials,
        )

        assert result == pytest.approx(1.0)

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
        parent = {
            "initial_risk": 2.0,
        }

        result = calculate_parent_rr_with_partials(
            parent,
            partials,
        )

        assert result == pytest.approx(1.0)

    def test_no_valid_partial_closes_returns_zero(self):
        result = calculate_parent_rr_with_partials(
            {},
            [],
        )

        assert result == pytest.approx(0.0)

    def test_weighted_partial_rr_is_average_not_total(self):
        partials = [
            {
                "risk_action": "CLOSE",
                "risk": 2.0,
                "RR": 3.0,
            },
            {
                "risk_action": "CLOSE",
                "risk": 1.0,
                "RR": 0.0,
            },
        ]
        parent = {
            "initial_risk": 3.0,
        }

        result = calculate_parent_rr_with_partials(
            parent,
            partials,
        )

        # Weighted average:
        # (2 * 3 + 1 * 0) / 3 = 2

        assert result == pytest.approx(2.0)

    def test_partial_rr_is_order_independent(self):
        partials = [
            {
                "risk_action": "CLOSE",
                "risk": 1.0,
                "RR": 2.0,
            },
            {
                "risk_action": "CLOSE",
                "risk": 3.0,
                "RR": -1.0,
            },
            {
                "risk_action": "OPEN",
                "risk": 2.0,
                "RR": 99.0,
            },
        ]
        parent = {
            "initial_risk": 4.0,
        }

        reversed_partials = list(reversed(partials))

        result = calculate_parent_rr_with_partials(
            parent,
            partials,
        )

        reversed_result = calculate_parent_rr_with_partials(
            parent,
            reversed_partials,
        )

        assert result == pytest.approx(reversed_result)




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
