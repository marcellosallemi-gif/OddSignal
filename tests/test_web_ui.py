from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


AUTH = ("admin", "change-me")


def test_web_home_without_auth_returns_401():
    with TestClient(app) as client:
        response = client.get("/", auth=None)

    assert response.status_code == 401


def test_web_home_with_wrong_auth_returns_401():
    with TestClient(app) as client:
        response = client.get("/", auth=("wrong", "wrong"))

    assert response.status_code == 401


def test_web_home_returns_html_page():
    with TestClient(app) as client:
        response = client.get("/", auth=AUTH)

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "OddSignal" in response.text
    assert "Benvenuto in OddSignal" in response.text
    assert "Consumo API locale" in response.text
    assert "Il dato può differire dal pannello ufficiale Odds-API.io" in response.text
    assert "Cancella alert recenti" in response.text
    assert "Mercati MVP supportati" not in response.text
    assert "Mercati futuri / da integrare" not in response.text
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
    assert "data-page=\"readiness\" onclick=\"showPage('readiness', event)\">Sistema</button>" in response.text
    assert "Alert" in response.text
    assert "Bookmaker" in response.text
    assert "Storico / Log" in response.text
    assert "Area tecnica" in response.text
    assert "Consumo API provider" not in response.text
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
    assert "Come funziona" in response.text
    assert "eventi per ciclo" in response.text
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
    assert "Dedup minuti" in response.text
    assert "evita di generare alert duplicati" in response.text
    assert "Cancella alert recenti" in response.text
    assert "Campionati" in response.text
    assert "competition-search" in response.text
    assert "Cerca campionati" in response.text
    assert "Campionati rilevati dagli eventi disponibili ora" in response.text
    assert "Aggiorna leghe/slug dal provider" in response.text
    assert "Aggiorna campionati da eventi" in response.text
    assert "refreshProviderCompetitions" in response.text
    assert "Mercati MVP supportati" not in response.text
    assert "Mercati futuri / da integrare" not in response.text
    assert "Carica mercati suggeriti" in response.text
    assert "Doppia chance" in response.text
    assert "loadMonitoredMarkets" in response.text
    assert "toggleMonitoredMarket" in response.text
    assert "Rileva account Telegram" in response.text
    assert "Alert recenti" in response.text
    assert "notification-logs-section" in response.text
    assert "toggleRecipient" in response.text


def test_static_logo_is_accessible_without_auth_if_file_exists():
    logo_path = Path("app/static/brand/oddsignal-horizontal.png")
    if not logo_path.exists():
        return

    with TestClient(app) as client:
        response = client.get(
            "/static/brand/oddsignal-horizontal.png",
            auth=None,
        )

    assert response.status_code == 200


def test_system_readiness_requires_auth_and_accepts_valid_auth():
    with TestClient(app) as client:
        unauthenticated_response = client.get("/system/readiness", auth=None)
        authenticated_response = client.get("/system/readiness", auth=AUTH)

    assert unauthenticated_response.status_code == 401
    assert authenticated_response.status_code == 200
