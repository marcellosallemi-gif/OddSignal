import pytest

from app.services.variation_engine import calculate_variation


def test_calculate_positive_variation():
    result = calculate_variation(previous_odds=1.80, current_odds=2.00)

    assert result["previous_odds"] == 1.80
    assert result["current_odds"] == 2.00
    assert result["variation_percent"] == 11.11
    assert result["absolute_variation_percent"] == 11.11
    assert result["direction"] == "increase"


def test_calculate_negative_variation():
    result = calculate_variation(previous_odds=2.00, current_odds=1.78)

    assert result["variation_percent"] == -11.00
    assert result["absolute_variation_percent"] == 11.00
    assert result["direction"] == "decrease"


def test_calculate_unchanged_variation():
    result = calculate_variation(previous_odds=2.00, current_odds=2.00)

    assert result["variation_percent"] == 0.00
    assert result["absolute_variation_percent"] == 0.00
    assert result["direction"] == "unchanged"


def test_previous_odds_must_be_positive():
    with pytest.raises(ValueError, match="previous_odds must be greater than 0"):
        calculate_variation(previous_odds=0, current_odds=2.00)


def test_current_odds_must_be_positive():
    with pytest.raises(ValueError, match="current_odds must be greater than 0"):
        calculate_variation(previous_odds=2.00, current_odds=0)
