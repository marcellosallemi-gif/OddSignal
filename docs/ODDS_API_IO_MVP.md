# Odds-API.io MVP Integration

## Stato attuale

Provider demo: Odds-API.io
Sport: football
Bookmaker: Stake, Sbobet
Scheduler: disattivato di default
Polling consigliato: 300 secondi
Eventi per ciclo scheduler: 1

Il sistema usa Odds-API.io solo come fonte dati. Non piazza scommesse, non usa scraping e non interagisce con account bookmaker.

## Variabili .env

APP_NAME=Calcolo Quote
APP_ENV=local
APP_DEBUG=true

DATABASE_URL=sqlite:///./football_odds_monitor.db

ODDS_PROVIDER=odds_api_io
ODDS_API_KEY=your_api_key
ODDS_API_BASE_URL=https://api.odds-api.io/v3
ODDS_API_SPORT=football
ODDS_API_STATUS=pending
ODDS_API_BOOKMAKERS=Stake,Sbobet
ODDS_API_EVENT_LIMIT=10
ODDS_API_LEAGUES=
ODDS_API_MARKETS=1X2,Goal/No Goal,Over/Under 2.5

ALERT_MIN_PERCENT=8
ALERT_MAX_PERCENT=15
ALERT_DEDUPLICATION_MINUTES=30

ODDS_SCHEDULER_ENABLED=0
ODDS_POLL_INTERVAL_SECONDS=300
ODDS_SCHEDULER_EVENT_LIMIT=1

TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

## Migrazioni locali

Se il database esiste gia, eseguire:

python3 scripts/migrate_add_odds_snapshot_metadata.py
python3 scripts/migrate_create_notification_logs.py

Le migrazioni sono idempotenti.

## Endpoint utili

Health:

curl "http://127.0.0.1:8001/health"

Sample live:

curl "http://127.0.0.1:8001/api/odds-provider/sample?limit=1"

Ingestion manuale:

curl -X POST "http://127.0.0.1:8001/api/odds-provider/ingest-sample?limit=1"

Quote salvate:

curl "http://127.0.0.1:8001/odds?provider=odds_api_io&limit=20"

Quote Stake:

curl "http://127.0.0.1:8001/odds?provider=odds_api_io&bookmaker=Stake&limit=20"

Alert:

curl "http://127.0.0.1:8001/alerts?provider=odds_api_io&limit=20"

Alert critici:

curl "http://127.0.0.1:8001/alerts?provider=odds_api_io&alert_type=critical_alert&limit=20"

Log notifiche:

curl "http://127.0.0.1:8001/notification-logs?limit=20"

## Logica alert

Formula:

((quota_nuova - quota_precedente) / quota_precedente) * 100

Regole:

- sotto 8%: nessun alert
- da 8% a 15%: standard_alert
- oltre 15%: critical_alert

## Deduplicazione

La deduplicazione evita alert ripetuti entro ALERT_DEDUPLICATION_MINUTES sulla stessa combinazione:

- evento
- provider
- bookmaker
- mercato
- selezione
- tipo alert

La direzione non viene usata per deduplicare, cosi si evitano alert ping-pong.

## Telegram

Se TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID non sono configurati, il sistema non invia notifiche e salva un log skipped.

Se Telegram e configurato correttamente, salva status=sent.
In caso di errore HTTP o rete, salva status=failed.

## Scheduler

Lo scheduler e spento di default:

ODDS_SCHEDULER_ENABLED=0

Per abilitarlo:

ODDS_SCHEDULER_ENABLED=1

Per il piano gratuito non scendere sotto:

ODDS_POLL_INTERVAL_SECONDS=300
ODDS_SCHEDULER_EVENT_LIMIT=1

## Test

Suite completa:

pytest

Test ingestion:

pytest tests/test_odds_ingestion_service.py

Test Telegram:

pytest tests/test_telegram_notifier.py

## Note operative

- Lo slug calcio e football.
- Il bookmaker asiatico va scritto Sbobet, non SBOBET.
- Il primo ciclo salva snapshot ma non crea alert.
- Gli alert possono nascere dal secondo ciclo.
- Prima di abilitare lo scheduler, testare sempre ingest-sample manualmente.
