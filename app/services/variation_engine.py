def calculate_variation(previous_odds: float, current_odds: float) -> dict:
    if previous_odds <= 0:
        raise ValueError("previous_odds must be greater than 0")
    if current_odds <= 0:
        raise ValueError("current_odds must be greater than 0")

    variation_percent = ((current_odds - previous_odds) / previous_odds) * 100

    if current_odds > previous_odds:
        direction = "increase"
    elif current_odds < previous_odds:
        direction = "decrease"
    else:
        direction = "unchanged"

    rounded_variation = round(variation_percent, 2)

    return {
        "previous_odds": previous_odds,
        "current_odds": current_odds,
        "variation_percent": rounded_variation,
        "absolute_variation_percent": abs(rounded_variation),
        "direction": direction,
    }
