import math
import pytest

from analyze.confidence_interval import (
    confidence_interval,
    classify_confidence_interval,
)


def test_confidence_interval_returns_expected_keys():
    result = confidence_interval([1, 2, 3, 4, 5])

    assert set(result.keys()) == {
        "estimate",
        "lower",
        "upper",
        "confidence",
        "n",
        "standard_error",
    }


def test_confidence_interval_mean():
    result = confidence_interval([1, 2, 3, 4, 5])

    assert result["estimate"] == pytest.approx(3.0)


def test_confidence_interval_n():
    result = confidence_interval([1, 2, 3, 4, 5])

    assert result["n"] == 5


def test_confidence_interval_standard_error():
    result = confidence_interval([1, 2, 3, 4, 5])

    expected_se = math.sqrt(2.5) / math.sqrt(5)

    assert result["standard_error"] == pytest.approx(expected_se)


def test_confidence_interval_bounds():
    result = confidence_interval([1, 2, 3, 4, 5])

    assert result["lower"] < result["estimate"]
    assert result["upper"] > result["estimate"]


def test_confidence_interval_is_symmetric():
    result = confidence_interval([1, 2, 3, 4, 5])

    lower_distance = result["estimate"] - result["lower"]
    upper_distance = result["upper"] - result["estimate"]

    assert lower_distance == pytest.approx(upper_distance)


def test_confidence_value_is_preserved():
    result = confidence_interval([1, 2, 3, 4, 5], confidence=0.99)

    assert result["confidence"] == 0.99


def test_higher_confidence_gives_wider_interval():
    result_95 = confidence_interval([1, 2, 3, 4, 5], confidence=0.95)
    result_99 = confidence_interval([1, 2, 3, 4, 5], confidence=0.99)

    assert result_99["lower"] < result_95["lower"]
    assert result_99["upper"] > result_95["upper"]


@pytest.mark.parametrize("confidence", [0, 1, -0.1, 1.1, 2])
def test_invalid_confidence_raises_error(confidence):
    with pytest.raises(ValueError, match="confidence must be between 0 and 1"):
        confidence_interval([1, 2, 3], confidence=confidence)


def test_less_than_two_values_returns_none():
    assert confidence_interval([]) is None
    assert confidence_interval([1]) is None


@pytest.mark.parametrize(
    "values",
    [
        [1, 2, float("nan")],
        [1, float("inf")],
        [float("-inf"), 2],
        [1, "2", 3],
        [1, None, 3],
    ],
)
def test_invalid_values_raise_error(values):
    with pytest.raises(ValueError, match="values must contain only finite numbers"):
        confidence_interval(values)


def test_accepts_generator():
    values = (x for x in [1, 2, 3, 4, 5])

    result = confidence_interval(values)

    assert result["estimate"] == pytest.approx(3.0)
    assert result["n"] == 5


def test_constant_values_have_zero_standard_error():
    result = confidence_interval([5, 5, 5, 5, 5])

    assert result["estimate"] == 5
    assert result["standard_error"] == 0
    assert result["lower"] == pytest.approx(5)
    assert result["upper"] == pytest.approx(5)

def test_confidence_interval_has_correct_95_percent_bounds():
    result = confidence_interval([1, 2, 3, 4, 5])

    assert result["estimate"] == pytest.approx(3.0)
    assert result["lower"] == pytest.approx(1.03675684)
    assert result["upper"] == pytest.approx(4.96324316)

def test_confidence_interval_99_percent_bounds():
    result = confidence_interval([1, 2, 3, 4, 5], confidence=0.99)

    assert result["estimate"] == pytest.approx(3.0)
    assert result["lower"] == pytest.approx(-0.2555867048)
    assert result["upper"] == pytest.approx(6.2555867048)

def test_confidence_interval_contains_sample_mean():
    result = confidence_interval([1, 2, 3, 4, 5])

    assert result["lower"] <= result["estimate"] <= result["upper"]


def test_confidence_interval_can_cross_zero():
    result = confidence_interval([-1, 0, 1])

    assert result["lower"] < 0
    assert result["upper"] > 0



def test_confidence_interval_classification_positive():
    result = confidence_interval([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])

    assert classify_confidence_interval(result) == "positive"


def test_confidence_interval_classification_inconclusive():
    result = confidence_interval([-1, 0, 1, -1, 0, 1, -1, 0, 1, 0])

    assert classify_confidence_interval(result) == "inconclusive"


def test_confidence_interval_classification_negative():
    result = confidence_interval([-10, -9, -8, -7, -6, -5, -4, -3, -2, -1])

    assert classify_confidence_interval(result) == "negative"


def test_confidence_interval_classification_insufficient_data():
    assert classify_confidence_interval(None) == "insufficient_data"
