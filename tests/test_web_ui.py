from fastapi.testclient import TestClient

from app.main import app


def test_web_home_returns_html_page():
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "OddSignal" in response.text
    assert "Benvenuto in OddSignal" in response.text
    assert "/static/brand/oddsignal-horizontal.png" in response.text
    assert "Software informativo per monitorare variazioni significative delle quote calcio" in response.text
    assert "cooldown_active" in response.text
    assert "cooldown_until" in response.text
    assert "cooldown_reason" in response.text
    assert "Cooldown provider attivo" in response.text
    assert "Navigazione dashboard" in response.text
    assert "app-shell" in response.text
    assert "sidebar-nav" in response.text
    assert "sidebar-link" in response.text
    assert "data-page" in response.text
    assert "Home" in response.text
    assert "Prontezza sistema" in response.text
    assert "Alert" in response.text
    assert "Bookmaker" in response.text
    assert "Storico / Log" in response.text
    assert "Area tecnica" in response.text
    assert "Consumo API provider" in response.text
    assert "checks.provider_usage" in response.text
    assert "readiness-summary" in response.text
    assert "loadReadiness" in response.text
    assert "showPage" in response.text
    assert ".page-section" in response.text
    assert ".page-section.active" in response.text
    assert "/system/readiness" in response.text
    assert "/system/provider-usage" in response.text
    assert "dashboard-summary" in response.text
    assert "Sistema" in response.text
    assert "Monitoraggio" in response.text
    assert "Consumo API" in response.text
    assert "Campionati attivi" in response.text
    assert "Mercati attivi" in response.text
    assert "Telegram" in response.text
    assert "Automazione" in response.text
    assert "Frequenza controllo" in response.text
    assert "Cooldown notifiche" in response.text
    assert "Salva automazione" in response.text
    assert "Frequenza controllo" in response.text
    assert "3 secondi - test locale" in response.text
    assert "Definisce ogni quanto controllare le quote" in response.text
    assert "Dettagli tecnici sistema" in response.text
    assert "Controllo quote manuale" in response.text
    assert "Esegui controllo quote ora" in response.text
    assert "Soglie alert" in response.text
    assert "Salva soglie" in response.text
    assert "Campionati" in response.text
    assert "Campionati rilevati dagli eventi disponibili ora" in response.text
    assert "Aggiorna leghe/slug dal provider" in response.text
    assert "Aggiorna campionati da eventi" in response.text
    assert "refreshProviderCompetitions" in response.text
    assert "Mercati MVP supportati" in response.text
    assert "Mercati futuri / da integrare" in response.text
    assert "loadMonitoredMarkets" in response.text
    assert "toggleMonitoredMarket" in response.text
    assert "Rileva account Telegram" in response.text
    assert "Alert recenti" in response.text
    assert "notification-logs-section" in response.text
    assert "toggleRecipient" in response.text
