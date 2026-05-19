# Odds-API.io MVP Integration

## Stato attuale

Provider: Odds-API.io
Sport: football
Bookmaker configurati: Stake, Sbobet
Scheduler: configurabile da dashboard/API
Polling consigliato MVP: 300 secondi
Eventi per ciclo scheduler: configurabili, default 1

Il sistema usa Odds-API.io solo come fonte dati. Non piazza scommesse, non usa scraping e non interagisce con account bookmaker.

## UI operativa

La dashboard operativa è disponibile su:

http://127.0.0.1:8001/

Dalla UI puoi:

- vedere stato sistema;
- configurare il controllo automatico;
- selezionare campionati;
- configurare soglie alert;
- rilevare account Telegram tramite bot;
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

TELEGRAM_CHAT_ID è solo fallback opzionale. Gli account Telegram reali vengono rilevati dalla dashboard dopo che l’utente ha avviato il bot.

## Campionati

I campionati selezionati dall utente sono salvati in monitored_competitions.

L ingestion usa solo i campionati attivi.

Se disponibile, provider_league_slug viene usato per interrogare direttamente Odds-API.io sul campionato selezionato.

## Mercati MVP

Monitorati:

- 1X2 (provider: ML)
- Over/Under (provider: Totals)
- Goal/No Goal (provider: Both Teams To Score)
- Handicap (provider: Spread)

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

Flusso utente:

1. l’utente apre il bot Telegram;
2. invia /start o un messaggio;
3. dalla dashboard clicca “Rileva account Telegram”;
4. il sistema chiama getUpdates;
5. salva/aggiorna il destinatario in notification_recipients.

Endpoint:

POST /configuration/telegram-recipients/sync

Il sistema deduplica gli update Telegram per chat_id, quindi lo stesso account non viene ritornato più volte anche se ha scritto più messaggi al bot.


Se Telegram non è configurato o non ci sono destinatari attivi, il sistema crea log skipped e non va in errore.

Stati log:

- sent
- skipped
- failed

Il canale telefono/SMS/WhatsApp non è incluso nell’MVP.

## Notifiche aggregate

Telegram notifica solo i cali quota. Gli aumenti restano nello storico alert ma non vengono inviati via Telegram.

Gli alert creati nello stesso ciclo vengono aggregati in un singolo messaggio Telegram.

Esempio operativo:

5 alert nel ciclo = 1 messaggio Telegram con 5 dettagli.

Questo evita spam e rende il sistema più adatto a uso commerciale.

Nota tecnica: oggi il log aggregato viene collegato al primo alert del gruppo. In futuro può essere introdotto un concetto dedicato di notification batch.

## Scheduler

Lo scheduler è configurabile da dashboard e API.

Endpoint:

GET /configuration/scheduler-settings
PUT /configuration/scheduler-settings

Esempio:

curl -X PUT "http://127.0.0.1:8001/configuration/scheduler-settings" \
  -H "Content-Type: application/json" \
  -d '{"enabled":false,"poll_interval_seconds":30,"event_limit":1}'

Valori consigliati:

- 3 secondi: solo test locale
- 30 secondi: test reale controllato
- 60 secondi: frequente
- 300 secondi: prudente/consigliato
- 900 secondi: conservativo

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
POST /configuration/telegram-recipients/sync
PATCH /configuration/notification-recipients/{recipient_id}/toggle

GET /configuration/alert-settings
PUT /configuration/alert-settings

GET /configuration/scheduler-settings
PUT /configuration/scheduler-settings

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

67 passed

## Note operative

- Lo slug calcio è football.
- Il bookmaker asiatico va scritto Sbobet, non SBOBET.
- Il primo ciclo salva snapshot ma non crea alert.
- Gli alert possono nascere dal secondo ciclo utile.
- Non committare .env.
