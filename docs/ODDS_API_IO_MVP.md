# Odds-API.io MVP Integration

## Stato attuale

Provider: Odds-API.io
Sport: football
Bookmaker configurati: Stake, Sbobet
Scheduler: disattivato di default
Polling consigliato MVP: 300 secondi
Eventi per ciclo scheduler: 1

Il sistema usa Odds-API.io solo come fonte dati. Non piazza scommesse, non usa scraping e non interagisce con account bookmaker.

## UI operativa

La UI minimale è disponibile su:

http://127.0.0.1:8001/

Dalla UI puoi:

- vedere stato sistema;
- vedere stato scheduler;
- selezionare campionati;
- configurare soglie alert;
- inserire destinatari Telegram o telefono;
- attivare/disattivare destinatari;
- eseguire controllo quote manuale;
- vedere alert;
- vedere log notifiche.

## Variabili .env principali

DATABASE_URL=sqlite:///./football_odds_monitor.db

ODDS_PROVIDER=odds_api_io
ODDS_API_KEY=your_api_key
ODDS_API_BASE_URL=https://api.odds-api.io/v3
ODDS_API_SPORT=football
ODDS_API_STATUS=pending
ODDS_API_BOOKMAKERS=Stake,Sbobet
ODDS_API_EVENT_LIMIT=10

ODDS_SCHEDULER_ENABLED=0
ODDS_POLL_INTERVAL_SECONDS=300
ODDS_SCHEDULER_EVENT_LIMIT=1

TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

TELEGRAM_CHAT_ID è solo fallback opzionale. I destinatari Telegram reali vengono gestiti da UI/API.

## Campionati

I campionati selezionati dall utente sono salvati in monitored_competitions.

L ingestion usa solo i campionati attivi.

Se disponibile, provider_league_slug viene usato per interrogare direttamente Odds-API.io sul campionato selezionato.

## Mercati MVP

Monitorati:

- ML
- Totals
- Both Teams To Score
- Spread

Esclusi:

- HT
- Team Total

## Logica alert

Formula:

((quota_nuova - quota_precedente) / quota_precedente) * 100

Le soglie sono persistenti nel database e modificabili da UI/API.

Default:

min_percent = 8
max_percent = 15
critical_percent = 15
deduplication_minutes = 30

## Deduplicazione

Evita alert ripetuti nella finestra deduplication_minutes sulla stessa combinazione:

- evento
- provider
- bookmaker
- mercato
- selezione
- tipo alert

La direzione non viene usata per deduplicare, così si evitano alert ping-pong.

## Telegram

TELEGRAM_BOT_TOKEN resta in .env.

I destinatari Telegram sono salvati in notification_recipients.

Se Telegram non è configurato o non ci sono destinatari attivi, il sistema crea log skipped e non va in errore.

Stati log:

- sent
- skipped
- failed

I numeri telefono sono salvati per integrazioni future SMS/WhatsApp ufficiali. L MVP non invia ancora SMS o WhatsApp.

## Scheduler

Lo scheduler è spento di default:

ODDS_SCHEDULER_ENABLED=0

Per abilitarlo:

ODDS_SCHEDULER_ENABLED=1

Per piano gratuito o test controllati:

ODDS_POLL_INTERVAL_SECONDS=300
ODDS_SCHEDULER_EVENT_LIMIT=1

Prima di abilitarlo, testare sempre il controllo manuale dalla UI.

## Endpoint utili

GET /
GET /health
GET /system/status

GET /configuration/available-competitions
GET /configuration/monitored-competitions
POST /configuration/monitored-competitions
PATCH /configuration/monitored-competitions/{competition_id}/toggle

GET /configuration/notification-recipients
POST /configuration/notification-recipients
PATCH /configuration/notification-recipients/{recipient_id}/toggle

GET /configuration/alert-settings
PUT /configuration/alert-settings

POST /api/odds-provider/ingest-sample?limit=1

GET /odds
GET /alerts
GET /notification-logs
GET /docs

## Migrazioni

Le migrazioni SQLite vengono eseguite automaticamente all avvio.

Script manuali idempotenti:

python3 scripts/migrate_add_odds_snapshot_metadata.py
python3 scripts/migrate_create_notification_logs.py
python3 scripts/migrate_create_user_configuration.py
python3 scripts/migrate_add_competition_provider_slug.py
python3 scripts/migrate_create_alert_settings.py

## Test

Suite completa:

pytest

Stato atteso attuale:

52 passed

## Note operative

- Lo slug calcio è football.
- Il bookmaker asiatico va scritto Sbobet, non SBOBET.
- Il primo ciclo salva snapshot ma non crea alert.
- Gli alert possono nascere dal secondo ciclo utile.
- Non committare .env.
