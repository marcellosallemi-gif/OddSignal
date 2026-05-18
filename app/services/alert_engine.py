from typing import Any, Dict, Optional


def evaluate_alert(
    variation_result: Dict[str, Any],
    min_percent: float = 8,
    max_percent: float = 15,
    critical_percent: float = 15,
) -> Optional[Dict[str, Any]]:
    if "absolute_variation_percent" not in variation_result:
        raise ValueError("absolute_variation_percent is required")
    if "direction" not in variation_result:
        raise ValueError("direction is required")

    if min_percent <= 0:
        raise ValueError("min_percent must be greater than 0")
    if max_percent < min_percent:
        raise ValueError("max_percent must be greater than or equal to min_percent")
    if critical_percent < max_percent:
        raise ValueError("critical_percent must be greater than or equal to max_percent")

    absolute_variation_percent = variation_result["absolute_variation_percent"]
    variation_percent = variation_result.get("variation_percent")
    direction = variation_result["direction"]

    if absolute_variation_percent < min_percent:
        return None

    if absolute_variation_percent <= max_percent:
        return {
            "alert_type": "standard_alert",
            "severity": "medium",
            "message": "Standard odds movement detected",
            "variation_percent": variation_percent,
            "absolute_variation_percent": absolute_variation_percent,
            "direction": direction,
        }

    if absolute_variation_percent > critical_percent:
        return {
            "alert_type": "critical_alert",
            "severity": "high",
            "message": "Critical odds movement detected",
            "variation_percent": variation_percent,
            "absolute_variation_percent": absolute_variation_percent,
            "direction": direction,
        }

    return {
        "alert_type": "critical_alert",
        "severity": "high",
        "message": "Critical odds movement detected",
        "variation_percent": variation_percent,
        "absolute_variation_percent": absolute_variation_percent,
        "direction": direction,
    }
