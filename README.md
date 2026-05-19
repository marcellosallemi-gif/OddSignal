# Calcolo Quote

Software MVP locale per monitorare quote calcistiche a scopo informativo.

Il sistema usa Odds-API.io, salva storico quote, calcola variazioni, genera alert e consente configurazione da UI web minimale.

Non piazza scommesse, non automatizza betting, non usa scraping aggressivo e non interagisce con account bookmaker.

## Avvio

python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001

Aprire:

http://127.0.0.1:8001/

## Funzioni UI

- stato sistema
- stato scheduler
- selezione campionati
- configurazione soglie alert
- destinatari Telegram e telefono
- attivazione/disattivazione destinatari
- controllo quote manuale
- storico alert
- log notifiche

## Configurazione

Copiare .env.example in .env e impostare almeno:

ODDS_API_KEY=your_api_key
ODDS_API_SPORT=football
ODDS_API_BOOKMAKERS=Stake,Sbobet

Telegram:

TELEGRAM_BOT_TOKEN=

I destinatari Telegram vengono gestiti dalla UI. TELEGRAM_CHAT_ID resta solo fallback opzionale.

## Alert

Formula:

((quota_nuova - quota_precedente) / quota_precedente) * 100

Le soglie sono configurabili da UI/API:

- min_percent
- max_percent
- critical_percent
- deduplication_minutes

Default:

- min_percent = 8
- max_percent = 15
- critical_percent = 15
- deduplication_minutes = 30

## Campionati

L utente seleziona i campionati da monitorare dalla UI.

L ingestion usa solo i campionati attivi e, se disponibile, interroga Odds-API.io tramite provider_league_slug.

## Mercati MVP

Monitorati:

- ML
- Totals
- Both Teams To Score
- Spread

Esclusi:

- HT
- Team Total

## Endpoint principali

GET /
GET /health
GET /system/status
GET /configuration/available-competitions
GET /configuration/monitored-competitions
POST /configuration/monitored-competitions
GET /configuration/notification-recipients
POST /configuration/notification-recipients
GET /configuration/alert-settings
PUT /configuration/alert-settings
POST /api/odds-provider/ingest-sample?limit=1
GET /odds
GET /alerts
GET /notification-logs
GET /docs

## Migrazioni

Le migrazioni SQLite vengono eseguite automaticamente all avvio.

Script manuali disponibili:

python3 scripts/migrate_add_odds_snapshot_metadata.py
python3 scripts/migrate_create_notification_logs.py
python3 scripts/migrate_create_user_configuration.py
python3 scripts/migrate_add_competition_provider_slug.py
python3 scripts/migrate_create_alert_settings.py

## Test

pytest

Stato atteso attuale:

52 passed

## Note operative

- usare solo fonti dati legittime
- non committare .env
- lo scheduler e spento di default
- testare prima con il pulsante UI Esegui controllo quote ora
- il bookmaker va scritto Sbobet, non SBOBET
