from fastapi.testclient import TestClient

from app.main import app


def test_get_events_returns_at_least_three_events():
    with TestClient(app) as client:
        response = client.get("/events")

    assert response.status_code == 200

    events = response.json()
    assert len(events) >= 3

    for event in events:
        assert "competition" in event
        assert "home_team" in event
        assert "away_team" in event
        assert "match" in event
        assert "start_time" in event
        assert "status" in event
