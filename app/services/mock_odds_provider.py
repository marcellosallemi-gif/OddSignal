from datetime import datetime


class MockOddsProvider:
    captured_at = datetime(2026, 5, 17, 10, 0)

    def get_odds(self, events):
        odds = []
        sources = [
            ("MockProvider A", "MockBook A"),
            ("MockProvider B", "MockBook B"),
        ]
        markets = [
            ("1X2", [("Home", 1.80), ("Draw", 3.20), ("Away", 4.10)]),
            ("Over/Under 2.5", [("Over 2.5", 2.00), ("Under 2.5", 1.85)]),
            ("Goal/No Goal", [("Goal", 1.75), ("No Goal", 2.05)]),
            ("Main Handicap", [("Home -1", 2.40), ("Away +1", 1.55)]),
        ]

        for event_index, event in enumerate(events):
            for source_index, (provider, bookmaker) in enumerate(sources):
                adjustment = (event_index * 0.03) + (source_index * 0.04)
                for market, selections in markets:
                    for selection, base_odds in selections:
                        odds.append(
                            {
                                "event_id": event.id,
                                "provider": provider,
                                "bookmaker": bookmaker,
                                "market": market,
                                "selection": selection,
                                "odds_decimal": round(base_odds + adjustment, 2),
                                "captured_at": self.captured_at,
                            }
                        )

        return odds
