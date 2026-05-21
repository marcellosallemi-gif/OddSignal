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

APP_USERNAME=admin
APP_PASSWORD=change-me
APP_SESSION_SECRET=change-me-random-secret
ODDS_API_KEY=
ODDS_API_SPORT=football
ODDS_API_BOOKMAKERS=Stake,Sbobet
PROVIDER_COMPETITIONS_AUTO_REFRESH_ENABLED=0
PROVIDER_COMPETITIONS_AUTO_REFRESH_INTERVAL_SECONDS=300

Telegram:

TELEGRAM_BOT_TOKEN=
TELEGRAM_AUTO_SYNC_ENABLED=0
TELEGRAM_AUTO_SYNC_INTERVAL_SECONDS=300

Flusso Telegram:

1. aprire il bot Telegram configurato;
2. inviare /start o un messaggio;
3. dalla dashboard cliccare “Rileva account Telegram”;
4. il sistema salva internamente l’ID tecnico della chat.

Il canale telefono/SMS/WhatsApp non è incluso nell’MVP.

Gli account Telegram vengono rilevati dalla dashboard dopo che l’utente ha avviato il bot. TELEGRAM_CHAT_ID resta solo fallback opzionale.

Con `TELEGRAM_AUTO_SYNC_ENABLED=1`, il backend sincronizza i destinatari Telegram ogni `TELEGRAM_AUTO_SYNC_INTERVAL_SECONDS` secondi. Se il token manca, il sync viene saltato senza bloccare l’app.

Con `PROVIDER_COMPETITIONS_AUTO_REFRESH_ENABLED=1`, il backend può aggiornare automaticamente i metadati campionati provider ogni `PROVIDER_COMPETITIONS_AUTO_REFRESH_INTERVAL_SECONDS` secondi. Questa automazione non esegue controlli quote e non crea snapshot o alert.

## Autenticazione

Con `APP_AUTH_ENABLED=1`, dashboard ed endpoint operativi richiedono login con `APP_USERNAME` e `APP_PASSWORD`.

Il login imposta un cookie di sessione HttpOnly persistente. `APP_SESSION_SECRET` firma il cookie; se manca, per l’MVP viene usato un fallback derivato da `APP_PASSWORD`.

Restano pubblici solo:

- `GET /login`
- `GET /health`
- `/static/*`

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

Il flusso principale è usare il pulsante “Aggiorna leghe/slug dal provider”, che recupera dal catalogo Odds-API.io gli slug ufficiali disponibili.

Il pulsante “Aggiorna campionati da eventi” aggiorna invece le competizioni partendo dagli eventi attualmente disponibili dal provider.

Dalla dashboard, nella sezione “Campionati da monitorare”, è comunque possibile inserire manualmente lo slug provider e cliccare “Salva mapping”. Questa funzione è un fallback amministrativo, non il flusso principale.

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

- Free Plan: 100 richieste/ora, 2 bookmaker
- Starter: 5.000 richieste/ora, 5 bookmaker
- Growth: 5.000 richieste/ora, 10 bookmaker
- Pro: 5.000 richieste/ora, 15 bookmaker
- Enterprise: richieste illimitate lato software, bookmaker configurabili


Il software calcola una stima prudenziale delle richieste orarie usando:

- campionati attivi mappati;
- frequenza scheduler;
- eventi per ciclo.

La stima serve per capire se la configurazione è compatibile con il piano API impostato.

Se lo scheduler viene attivato con una configurazione stimata sopra il limite richieste/ora del Piano API, il backend blocca il salvataggio e restituisce errore. Con piano Illimitato il blocco interno richieste/ora non viene applicato.

Esempio prudente per piano Free:

- 1 campionato mappato attivo;
- 1 evento per ciclo;
- refresh ogni 300 secondi;
- stima circa 24 richieste/ora.

Il limite del piano provider non va aggirato: va configurato correttamente in base al piano acquistato.

## Controllo consumo API provider

Il software registra localmente le chiamate reali verso Odds-API.io nella tabella `provider_api_request_logs`.

La dashboard espone una sezione “Consumo API provider” che mostra:

- richieste usate nell’ultima ora;
- limite richieste/ora del Piano API;
- richieste residue;
- stato OK o limite raggiunto;
- messaggio operativo.

Prima di ogni chiamata reale a Odds-API.io, il backend controlla il consumo locale dell’ultima ora. Se il limite locale è già raggiunto, la chiamata viene bloccata prima di contattare il provider.

Questo evita di continuare a generare richieste quando il piano API è esaurito.

Nota: se Odds-API.io segnala comunque rate limit o richieste perse, evitare refresh manuali e controlli quote finché il provider non resetta la finestra oraria. In caso di consumo anomalo con server spento, verificare processi esterni o rigenerare la API key.

### Cooldown rate limit provider

Se Odds-API.io restituisce errore `429`, il software attiva un cooldown locale per il provider.

Durante il cooldown:

- le nuove chiamate a Odds-API.io vengono bloccate prima di contattare il provider;
- la dashboard mostra `cooldown_active`, `cooldown_until` e `cooldown_reason`;
- non bisogna usare refresh manuali, controllo quote o scheduler fino al reset;
- il blocco protegge il piano API da ulteriori tentativi inutili durante una finestra già limitata.

Questo cooldown è diverso dal conteggio locale richieste/ora: il conteggio locale previene il superamento del limite stimato; il cooldown reagisce invece a un rate limit effettivamente restituito dal provider.

## Bookmaker provider

La dashboard include una sezione “Bookmaker provider” per configurare i bookmaker selezionati su Odds-API.io senza modificare file `.env` o codice.

Esempio:

- `Stake,Sbobet`

Il software normalizza automaticamente l’elenco:

- rimuove spazi inutili;
- elimina duplicati;
- conserva l’ordine inserito;
- valida il numero di bookmaker rispetto al Piano API attivo.

Se il Piano API consente massimo 2 bookmaker, il salvataggio di 3 o più bookmaker viene bloccato con errore. Per aumentare il numero di bookmaker è necessario selezionare un piano coerente, ad esempio Starter, Growth, Pro o Enterprise.

Il file `.env` resta solo come fallback iniziale: dopo il salvataggio dalla dashboard, il provider usa i bookmaker persistiti nel database.

Se i bookmaker configurati superano il limite del Piano API attivo, il backend blocca l’attivazione dello scheduler. Esempio: con Free Plan sono ammessi massimo 2 bookmaker; se sono configurati Stake,Sbobet,Bet365, lo scheduler non può essere acceso finché non riduci l’elenco bookmaker o selezioni un piano superiore.

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
