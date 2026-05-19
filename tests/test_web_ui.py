from fastapi.testclient import TestClient

from app.main import app


def test_web_home_returns_html_page():
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Calcolo Quote - MVP" in response.text
    assert "Riepilogo dashboard" in response.text
    assert "dashboard-summary" in response.text
    assert "Events count" in response.text
    assert "Notification logs count" in response.text
    assert "Scheduler automatico" in response.text
    assert "JSON tecnico sistema" in response.text
    assert "Controllo quote manuale" in response.text
    assert "Esegui controllo quote ora" in response.text
    assert "Impostazioni alert" in response.text
    assert "Salva impostazioni alert" in response.text
    assert "Campionati disponibili" in response.text
    assert "Mercati monitorati" in response.text
    assert "loadMonitoredMarkets" in response.text
    assert "toggleMonitoredMarket" in response.text
    assert "Destinatari notifiche" in response.text
    assert "Log notifiche" in response.text
    assert "toggleRecipient" in response.text
