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

ODDS_PROVIDER=odds_api_io
ODDS_API_KEY=your_api_key
ODDS_API_BASE_URL=https://api.odds-api.io/v3
ODDS_API_SPORT=football
ODDS_API_STATUS=pending
ODDS_API_BOOKMAKERS=Stake,Sbobet
ODDS_API_EVENT_LIMIT=10

ALERT_MIN_PERCENT=8
ALERT_MAX_PERCENT=15
ALERT_DEDUPLICATION_MINUTES=30

ODDS_SCHEDULER_ENABLED=0
ODDS_POLL_INTERVAL_SECONDS=300
ODDS_SCHEDULER_EVENT_LIMIT=1

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

## Logica alert

Formula:

((quota_nuova - quota_precedente) / quota_precedente) * 100

Regole:

- sotto 8%: nessun alert
- da 8% a 15%: standard_alert
- oltre 15%: critical_alert

## Deduplicazione

Evita alert ripetuti entro ALERT_DEDUPLICATION_MINUTES sulla stessa combinazione:

- evento
- provider
- bookmaker
- mercato
- selezione
- tipo alert

La direzione non viene usata per deduplicare, così si evitano alert ping-pong.

## Test

Suite completa:

pytest

Test ingestion:

pytest tests/test_odds_ingestion_service.py

## Note

- Lo slug calcio è football.
- Il bookmaker asiatico va scritto Sbobet, non SBOBET.
- Il primo ciclo salva snapshot ma non crea alert.
- Gli alert possono nascere dal secondo ciclo.
- Prima di abilitare lo scheduler, testare sempre ingest-sample manualmente.
