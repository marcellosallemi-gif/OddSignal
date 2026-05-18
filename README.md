# Calcolo Quote

Backend locale MVP per monitorare quote calcistiche a scopo informativo.

Questa base include una app FastAPI, configurazione SQLite locale, health check ed endpoint eventi.

## Installazione

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Avvio

```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Avvio server in background

```bash
nohup python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 > uvicorn.log 2>&1 & echo $! > uvicorn.pid
```

## Stop server

```bash
kill $(cat uvicorn.pid)
```

## Test

```bash
pytest
```

## URL

- http://127.0.0.1:8000/health
- http://127.0.0.1:8000/events
- http://127.0.0.1:8000/odds
- http://127.0.0.1:8000/alerts
- http://127.0.0.1:8000/docs

## Database

Il backend usa SQLite locale. Le tabelle MVP vengono create automaticamente all'avvio dell'app.

## Variation formula

La variazione percentuale delle quote decimali viene calcolata con:

```text
((current_odds - previous_odds) / previous_odds) * 100
```

Il valore con segno indica aumento o diminuzione; il valore assoluto serve per confrontare soglie future.

## Alert logic

Il motore alert puro restituisce `standard_alert` per variazioni assolute tra 8% e 15%, `critical_alert` sopra il 15% e nessun alert sotto l'8%.

## Real provider configuration - Odds-API.io

Il provider reale scelto è Odds-API.io.

- Sport configurato: `football`
- Modalità iniziale: pre-match, `status=pending`
- Bookmaker configurati: `Stake,Sbobet`
- Mercati target: `1X2`, `Goal/No Goal`, `Over/Under 2.5`

La chiave API reale deve essere inserita solo nel file `.env` locale. Il file `.env` non va committato.

`.env.example` contiene solo placeholder. `OddsApiIoProvider` è predisposto per costruire URL verso Odds-API.io, ma non sostituisce ancora `MockOddsProvider` e non esegue chiamate HTTP automatiche.

`ODDS_API_LEAGUES` resta vuoto finché non vengono validati gli slug delle competizioni.

Prossimo step: validare bookmaker e league slug con una singola chiamata controllata.

## Endpoint disponibili

### GET /health

Risposta:

```json
{
  "status": "ok",
  "service": "football-odds-monitor"
}
```

### GET /events

Restituisce gli eventi calcistici mock/seed locali del MVP.

Esempio risposta:

```json
[
  {
    "id": 1,
    "competition": "Serie A",
    "home_team": "Inter",
    "away_team": "Milan",
    "match": "Inter vs Milan",
    "start_time": "2026-08-15T18:30:00",
    "status": "scheduled"
  }
]
```

### GET /odds

Restituisce quote mock deterministiche per il solo MVP locale.

Esempio risposta:

```json
[
  {
    "id": 1,
    "event": "Inter vs Milan",
    "competition": "Serie A",
    "provider": "MockProvider A",
    "bookmaker": "MockBook A",
    "market": "Over/Under 2.5",
    "selection": "Over 2.5",
    "odds_decimal": 2.0,
    "captured_at": "2026-05-17T10:00:00"
  }
]
```

### GET /alerts

Restituisce gli alert salvati nel database locale. Gli alert saranno generati automaticamente nel prossimo step con `POST /poll`.

Esempio risposta:

```json
[
  {
    "id": 1,
    "event": "Inter vs Milan",
    "competition": "Serie A",
    "provider": "MockProvider A",
    "bookmaker": "MockBook A",
    "market": "Over/Under 2.5",
    "selection": "Over 2.5",
    "previous_odds": 1.8,
    "current_odds": 2.0,
    "variation_percent": 11.11,
    "direction": "increase",
    "alert_type": "standard_alert",
    "created_at": "2026-05-17T10:00:00"
  }
]
```
