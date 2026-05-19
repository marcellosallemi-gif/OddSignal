# Calcolo Quote

Software MVP locale per monitorare quote calcistiche a scopo informativo.

Il sistema acquisisce quote calcio da Odds-API.io, salva storico quote, calcola variazioni percentuali, genera alert e invia notifiche Telegram. La configurazione principale avviene da dashboard web.

Non piazza scommesse, non automatizza betting, non usa scraping aggressivo e non interagisce con account bookmaker.

## Avvio locale

python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001

Aprire:

http://127.0.0.1:8001/

## Funzioni UI

- stato sistema
- configurazione controllo automatico
- selezione campionati
- configurazione soglie alert
- rilevamento account Telegram tramite bot
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

Flusso Telegram:

1. aprire il bot Telegram configurato;
2. inviare /start o un messaggio;
3. dalla dashboard cliccare “Rileva account Telegram”;
4. il sistema salva internamente l’ID tecnico della chat.

Il canale telefono/SMS/WhatsApp non è incluso nell’MVP.

Gli account Telegram vengono rilevati dalla dashboard dopo che l’utente ha avviato il bot. TELEGRAM_CHAT_ID resta solo fallback opzionale.

## Alert

Telegram notifica solo i cali quota. Gli aumenti restano nello storico alert ma non vengono inviati via Telegram.

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

## Mapping manuale campionati

I campionati senza `provider_league_slug` risultano non monitorabili perché il software non può interrogare il provider in modo mirato.

Dalla dashboard, nella sezione “Campionati da monitorare”, è possibile inserire manualmente lo slug provider e cliccare “Salva mapping”.

Dopo il salvataggio:

- il campionato diventa monitorabile;
- può essere attivato/disattivato dalla dashboard;
- viene incluso nei controlli quote se attivo;
- la stima del Piano API viene aggiornata.

Non inserire slug inventati: usare solo slug validi recuperati da Odds-API.io o da documentazione/provider.

## Campionati

L’utente seleziona i campionati da monitorare dalla dashboard.

L ingestion usa solo i campionati attivi e, se disponibile, interroga Odds-API.io tramite provider_league_slug.

## Mercati MVP

Monitorati:

- 1X2 (provider: ML)
- Over/Under (provider: Totals)
- Goal/No Goal (provider: Both Teams To Score)
- Handicap (provider: Spread)

Esclusi:

- HT
- Team Total


## Piano API provider

La dashboard include una sezione “Piano API provider” per configurare i limiti operativi del piano Odds-API.io senza modificare il codice.

Preset disponibili:

- Free: 100 richieste/ora, 2 bookmaker
- 5000/h: 5000 richieste/ora
- Illimitato: nessun blocco interno richieste/ora lato software
- Custom: valori manuali

Il software calcola una stima prudenziale delle richieste orarie usando:

- campionati attivi mappati;
- frequenza scheduler;
- eventi per ciclo.

La stima serve per capire se la configurazione è compatibile con il piano API impostato.

Esempio prudente per piano Free:

- 1 campionato mappato attivo;
- 1 evento per ciclo;
- refresh ogni 300 secondi;
- stima circa 24 richieste/ora.

Il limite del piano provider non va aggirato: va configurato correttamente in base al piano acquistato.

## Scheduler automatico

Lo scheduler è configurabile da dashboard e API.

Endpoint:

GET /configuration/scheduler-settings
PUT /configuration/scheduler-settings

Valori consigliati:

- 3 secondi: solo test locale
- 30 secondi: test reale controllato
- 60 secondi: frequente
- 300 secondi: consigliato/prudente
- 900 secondi: conservativo

Per uso commerciale non usare 3 secondi come default: può consumare molte chiamate API e generare rumore.

## Endpoint principali

GET /
GET /health
GET /system/status
GET /configuration/available-competitions
GET /configuration/monitored-competitions
POST /configuration/monitored-competitions
GET /configuration/notification-recipients
POST /configuration/telegram-recipients/sync
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

Script manuali disponibili:

python3 scripts/migrate_add_odds_snapshot_metadata.py
python3 scripts/migrate_create_notification_logs.py
python3 scripts/migrate_create_user_configuration.py
python3 scripts/migrate_add_competition_provider_slug.py
python3 scripts/migrate_create_alert_settings.py

## Test

pytest

Stato atteso attuale:

67 passed

## Note operative

- usare solo fonti dati legittime
- non committare .env
- lo scheduler è configurabile da dashboard/API
- testare prima con il pulsante UI Esegui controllo quote ora
- il bookmaker va scritto Sbobet, non SBOBET
