from typing import Any, Dict, Optional


def evaluate_alert(variation_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if "absolute_variation_percent" not in variation_result:
        raise ValueError("absolute_variation_percent is required")
    if "direction" not in variation_result:
        raise ValueError("direction is required")

    absolute_variation_percent = variation_result["absolute_variation_percent"]
    variation_percent = variation_result.get("variation_percent")
    direction = variation_result["direction"]

    if absolute_variation_percent < 8:
        return None

    if absolute_variation_percent <= 15:
        return {
            "alert_type": "standard_alert",
            "severity": "medium",
            "message": "Standard odds movement detected",
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
