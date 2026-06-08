from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def test_web_home_returns_html_page():
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "OddSignal" in response.text
    assert "Benvenuto in OddSignal" in response.text
    assert "Consumo API locale" in response.text
    assert "Il dato può differire dal pannello ufficiale Odds-API.io" in response.text
    assert "I dati della dashboard si aggiornano automaticamente ogni 5 minuti quando la pagina è aperta." in response.text
    assert "Ricarica consumo API locale" in response.text
    assert "DASHBOARD_AUTO_REFRESH_INTERVAL_MS = 300000" in response.text
    assert "PROVIDER_USAGE_AUTO_REFRESH_INTERVAL_MS = 300000" in response.text
    assert 'timeZone: "Europe/Rome"' in response.text
    assert "hour12: false" in response.text
    assert "Usate ora corrente" in response.text
    assert "Reset finestra" in response.text
    assert "startDashboardAutoRefresh" in response.text
    assert "Automazioni automatiche" in response.text
    assert "Provider competitions auto refresh" in response.text
    assert "Ultimo aggiornamento" in response.text
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
    assert "Esci" in response.text
    assert "/logout" in response.text
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
    assert "Calcio attivo" in response.text
    assert "Tennis attivo" in response.text
    assert "Mercati attivi" in response.text
    assert "Telegram" in response.text
    assert "Automazione" in response.text
    assert "Come funziona" in response.text
    assert "eventi per ciclo" in response.text
    assert "Frequenza controllo" in response.text
    assert "Cooldown notifiche" in response.text
    assert "Salva automazione" in response.text
    assert "Frequenza controllo" in response.text
    assert "3 secondi" in response.text
    assert "Definisce ogni quanto controllare le quote" in response.text
    assert "Dettagli tecnici sistema" in response.text
    assert "Controllo quote manuale" in response.text
    assert "Esegui controllo quote ora" in response.text
    assert "Ultimo controllo eseguito" in response.text
    assert "Servizio temporaneamente non disponibile o timeout durante il controllo quote. Codice:" in response.text
    assert "Richiesta non completata. Codice:" in response.text
    assert "Controlla i log Render" in response.text
    assert "http_status" in response.text
    assert "message = text" not in response.text
    assert '"Errore controllo quote: " + error.message' not in response.text
    assert "Quote ricevute" in response.text
    assert "Quote processate" in response.text
    assert "Quote escluse per mercati non ancora supportati" in response.text
    assert "Snapshot inseriti" in response.text
    assert "Quote invariate" in response.text
    assert "Alert generati" in response.text
    assert "Notifiche Telegram create" in response.text
    assert "Duplicati alert evitati" in response.text
    assert "Le quote escluse non sono errori" in response.text
    assert "Mercati esclusi principali" in response.text
    assert "Soglie alert" in response.text
    assert "Salva soglie" in response.text
    assert "Dedup minuti" in response.text
    assert "evita di generare alert duplicati" in response.text
    assert "Cancella alert recenti" in response.text
    assert "data-page=\"competitions\" onclick=\"showPage('competitions', event)\">Calcio</button>" in response.text
    assert "data-page=\"tennis\" onclick=\"showPage('tennis', event)\">Tennis</button>" in response.text
    assert "Tornei tennis" in response.text
    assert "Aggiorna tornei tennis" in response.text
    assert "Torneo attivo" in response.text
    assert "In attesa di attivazione" in response.text
    assert "competition-search" in response.text
    assert "Cerca campionati" in response.text
    assert "rilevati dagli eventi disponibili ora" in response.text
    assert "Aggiorna leghe/slug dal provider" in response.text
    assert "Aggiorna campionati da eventi" in response.text
    assert "refreshProviderCompetitions" in response.text
    assert "Mercati MVP supportati" not in response.text
    assert "Mercati futuri / da integrare" not in response.text
    assert "Carica mercati suggeriti" in response.text
    assert "Doppia chance" in response.text
    assert "Pareggio escluso" in response.text
    assert "Handicap principale" not in response.text
    assert "Nome provider" not in response.text
    assert "Handicap europeo" in response.text
    assert "activeSuggestedFootballMarkets" in response.text
    assert "loadMonitoredMarkets" in response.text
    assert "toggleMonitoredMarket" in response.text
    assert "Rileva account Telegram" in response.text
    assert "Test Telegram non inviato" in response.text
    assert "Test Telegram inviato correttamente" in response.text
    assert "/configuration/telegram-test-message" in response.text
    assert "loadRecipients()" in response.text
    assert "loadRecipients(syncedRecipients)" not in response.text
    assert "Nessun nuovo account Telegram rilevato. I profili già configurati sono stati sincronizzati con i dati Telegram più recenti." in response.text
    assert "Nuovi account Telegram rilevati" in response.text
    assert "Invia test Telegram" in response.text
    assert "sendTelegramTestMessage" in response.text
    assert "recipients-last-updated" in response.text
    assert "Alert recenti" in response.text
    assert "Aggiornamento alert in corso" in response.text
    assert "Alert aggiornati alle" in response.text
    assert "Alert non aggiornati" in response.text
    assert "Nessun alert presente. Ultimo controllo" in response.text
    assert "ALERTS_AUTO_LOAD_COOLDOWN_MS" in response.text
    assert "loadAlerts({ifStale: true})" in response.text
    assert "Quota prec." in response.text
    assert "Quota att." in response.text
    assert "Data creazione" in response.text
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
