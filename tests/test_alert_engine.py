import pytest

from app.services.alert_engine import evaluate_alert


def variation_result(absolute_variation_percent, direction="increase"):
    variation_percent = absolute_variation_percent
    if direction == "decrease":
        variation_percent = -absolute_variation_percent

    return {
        "previous_odds": 1.80,
        "current_odds": 2.00,
        "variation_percent": variation_percent,
        "absolute_variation_percent": absolute_variation_percent,
        "direction": direction,
    }


def test_no_alert_below_eight_percent():
    assert evaluate_alert(variation_result(7.99)) is None


def test_standard_alert_at_eight_percent():
    alert = evaluate_alert(variation_result(8.00))

    assert alert["alert_type"] == "standard_alert"
    assert alert["severity"] == "medium"
    assert alert["message"] == "Standard odds movement detected"


def test_standard_alert_at_eleven_percent():
    alert = evaluate_alert(variation_result(11.11))

    assert alert["alert_type"] == "standard_alert"
    assert alert["absolute_variation_percent"] == 11.11


def test_standard_alert_at_fifteen_percent():
    alert = evaluate_alert(variation_result(15.00))

    assert alert["alert_type"] == "standard_alert"


def test_critical_alert_above_fifteen_percent():
    alert = evaluate_alert(variation_result(15.01))

    assert alert["alert_type"] == "critical_alert"
    assert alert["severity"] == "high"
    assert alert["message"] == "Critical odds movement detected"


def test_critical_alert_at_twenty_percent():
    alert = evaluate_alert(variation_result(20.00))

    assert alert["alert_type"] == "critical_alert"
    assert alert["absolute_variation_percent"] == 20.00


def test_preserves_increase_direction():
    alert = evaluate_alert(variation_result(11.11, direction="increase"))

    assert alert["direction"] == "increase"
    assert alert["variation_percent"] == 11.11


def test_preserves_decrease_direction():
    alert = evaluate_alert(variation_result(11.11, direction="decrease"))

    assert alert["direction"] == "decrease"
    assert alert["variation_percent"] == -11.11


def test_missing_absolute_variation_percent_raises_value_error():
    data = variation_result(11.11)
    del data["absolute_variation_percent"]

    with pytest.raises(ValueError, match="absolute_variation_percent is required"):
        evaluate_alert(data)


def test_missing_direction_raises_value_error():
    data = variation_result(11.11)
    del data["direction"]

    with pytest.raises(ValueError, match="direction is required"):
        evaluate_alert(data)
