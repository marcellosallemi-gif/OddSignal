from fastapi.testclient import TestClient

from app.main import app


def test_get_odds_returns_readable_odds():
    with TestClient(app) as client:
        response = client.get("/odds")

    assert response.status_code == 200

    odds = response.json()
    assert len(odds) >= 1

    for odds_snapshot in odds:
        assert "event" in odds_snapshot
        assert "competition" in odds_snapshot
        assert "provider" in odds_snapshot
        assert "bookmaker" in odds_snapshot
        assert "market" in odds_snapshot
        assert "selection" in odds_snapshot
        assert "odds_decimal" in odds_snapshot
        assert "captured_at" in odds_snapshot
