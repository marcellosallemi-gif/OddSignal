# AGENTS.md

## Project identity

This repository contains an MVP for a football odds monitoring system.

The software monitors football odds, stores odds snapshots, calculates percentage variations, and creates alerts when odds move within defined thresholds.

The project is informational only. It must not place bets, automate betting, bypass bookmaker limits, scrape unauthorized sources, or promise profits.

The project must be technically functional and intuitive for the final user.

## Core objective

Build a local MVP that can:

- manage football competitions, teams and events;
- simulate football odds through a deterministic mock provider;
- store odds snapshots;
- compare current odds with previous odds;
- calculate percentage variation;
- create standard alerts for variations between 8% and 15%;
- create separate critical alerts for variations above 15%;
- avoid duplicated alerts;
- expose clear REST APIs;
- include automated tests;
- document setup, usage, endpoints and limits.

## Development mode

Work in small, credit-efficient tasks.

Avoid large exploratory work.

Avoid broad refactors unless strictly necessary.

Inspect only files relevant to the requested task.

Modify only files needed for the task.

Do not implement future features unless explicitly requested.

Prefer small, verifiable changes over large rewrites.

At the end of each task, provide a concise report with:

- files changed;
- commands run;
- test result;
- remaining issues;
- next recommended step.

## Preferred stack

Use this stack unless the repository already uses a different one:

- Python 3.11+
- FastAPI
- SQLAlchemy
- SQLite for local development
- Pydantic
- Pytest
- Uvicorn

Keep the code compatible with a future migration to PostgreSQL.

Do not use real external odds APIs in the first MVP.

Use a deterministic mock odds provider.

## Non-negotiable constraints

Do not implement:

- automated betting;
- bookmaker scraping;
- hidden endpoint extraction;
- anti-bot bypass;
- VPN-based access strategies;
- account automation;
- login or payments in the MVP;
- SaaS billing in the MVP;
- complex frontend dashboard in the MVP;
- real Telegram, WhatsApp or payment integrations in the MVP;
- features that imply guaranteed betting profit.

The system must be positioned only as a data monitoring and alerting tool.

## Provider policy

Use only authorized, documented and legitimate data sources.

For the MVP, use only MockOddsProvider.

Do not integrate hga050.com or any similar website unless official API documentation and written authorization are provided.

Do not use browser network inspection to reuse private frontend APIs.

Do not scrape bookmaker pages.

Future real provider integrations must be implemented through a clean provider interface.

If a provider is not authorized, create only a non-operational placeholder with a comment such as:

Requires official API documentation and written authorization before implementation.

## Product and UX principles

Every feature must be understandable for the final user, not only technically correct.

Design API responses so they can later feed a clean dashboard without major restructuring.

Use clear field names.

Use predictable response formats.

Use meaningful status and error messages.

Avoid exposing unnecessary internal database complexity to the final user.

When returning events, odds or alerts, prefer readable labels such as:

- competition name;
- home team;
- away team;
- market;
- selection;
- bookmaker;
- current odds;
- previous odds;
- variation percent;
- direction;
- alert type.

Avoid raw technical-only outputs when the endpoint is user-facing.

When adding endpoints, update README with practical usage examples.

## Architecture rules

Keep the code modular.

Do not put business logic inside API routers.

Routers should only handle request/response orchestration.

Business logic must stay in services.

Separate these responsibilities:

- data provider;
- data normalization;
- odds storage;
- variation calculation;
- alert generation;
- polling orchestration;
- API endpoints;
- configuration.

Suggested structure for an empty or early-stage repository:

app/
  main.py
  database.py
  models.py
  schemas.py
  services/
    mock_odds_provider.py
    variation_engine.py
    alert_engine.py
    polling_service.py
  routers/
    health.py
    events.py
    odds.py
    alerts.py
tests/
  test_health.py
  test_events.py
  test_mock_odds_provider.py
  test_variation_engine.py
  test_alert_engine.py
README.md
requirements.txt
.env.example

If the repository already has a reasonable structure, preserve it where possible.

## Database rules

Use SQLite for local MVP development.

Create tables automatically at app startup only for MVP purposes.

Keep the structure simple and easy to migrate later.

Avoid complex migrations unless explicitly requested.

Do not over-engineer relationships before the feature requires them.

## Minimum data model

Use tables or equivalent models for:

- competitions;
- teams;
- events;
- providers;
- bookmakers;
- markets;
- selections;
- odds_snapshots;
- alerts.

Minimum fields for competitions:

- id;
- name;
- country.

Minimum fields for teams:

- id;
- name.

Minimum fields for events:

- id;
- competition_id;
- home_team_id;
- away_team_id;
- start_time;
- status.

Minimum fields for odds_snapshots:

- id;
- event_id;
- provider;
- bookmaker;
- market;
- selection;
- odds_decimal;
- captured_at.

Minimum fields for alerts:

- id;
- event_id;
- provider;
- bookmaker;
- market;
- selection;
- previous_odds;
- current_odds;
- variation_percent;
- direction;
- alert_type;
- created_at.

## MVP markets

Use only these football markets in the MVP:

- 1X2;
- Over/Under 2.5;
- Goal/No Goal;
- Main Handicap.

Do not add extra markets unless explicitly requested.

## Mock data requirements

The mock provider must generate deterministic data for tests and local development.

Include at least:

- 3 football matches;
- 2 simulated bookmakers or providers;
- multiple markets per match;
- one case with variation between 8% and 15%;
- one case with variation above 15%;
- one case with no alert.

Mock data must be stable enough for automated tests.

Seed data must avoid duplicates when the app restarts or endpoints are called multiple times.

## Variation formula

Use decimal odds variation as the default calculation:

variation_percent = ((current_odds - previous_odds) / previous_odds) * 100

Use the absolute value to check alert thresholds.

Keep the original sign in stored data and API responses.

Direction must be:

- increase: when current odds are higher than previous odds;
- decrease: when current odds are lower than previous odds;
- unchanged: only if needed for non-alert cases.

Handle invalid previous odds safely.

If previous odds are zero, missing or invalid, do not calculate variation and do not create an alert.

## Alert rules

Create a standard alert when all conditions are true:

- previous comparable odds exist;
- current odds differ from previous odds;
- absolute variation is greater than or equal to 8%;
- absolute variation is less than or equal to 15%;
- no duplicate alert already exists for the same key.

Create a critical alert when:

abs(variation_percent) > 15

Use these alert types:

- standard_alert;
- critical_alert.

Do not mix standard alerts and critical alerts.

Do not create alerts for variations below 8%.

## Alert deduplication

Avoid duplicated alerts using this key:

- event_id;
- provider;
- bookmaker;
- market;
- selection;
- alert_type.

If an identical alert already exists, do not create another one.

If a future cooldown window is added, document it clearly.

## Required API endpoints

Implement at least:

- GET /health
- POST /poll
- GET /events
- GET /odds
- GET /alerts

Endpoint behavior:

GET /health

Returns service status.

Expected response:

{
  "status": "ok",
  "service": "football-odds-monitor"
}

POST /poll

Runs mock polling, stores odds, compares snapshots and generates alerts.

GET /events

Returns football events in a user-readable format.

GET /odds

Returns odds snapshots in a user-readable format.

GET /alerts

Returns generated alerts in a user-readable format.

## API response UX

Responses must be clear and practical.

For events, prefer output like:

{
  "id": 1,
  "competition": "Serie A",
  "home_team": "Milan",
  "away_team": "Inter",
  "start_time": "2026-05-20T20:45:00",
  "status": "scheduled"
}

For odds, prefer output like:

{
  "event": "Milan vs Inter",
  "competition": "Serie A",
  "bookmaker": "MockBook A",
  "market": "Over/Under 2.5",
  "selection": "Over 2.5",
  "odds_decimal": 2.00,
  "captured_at": "2026-05-17T10:00:00"
}

For alerts, prefer output like:

{
  "event": "Milan vs Inter",
  "competition": "Serie A",
  "bookmaker": "MockBook A",
  "market": "Over/Under 2.5",
  "selection": "Over 2.5",
  "previous_odds": 1.80,
  "current_odds": 2.00,
  "variation_percent": 11.11,
  "direction": "increase",
  "alert_type": "standard_alert"
}

## Testing requirements

Add tests only relevant to the current task.

Do not run unnecessary heavy checks.

Use pytest.

Minimum test coverage over time should include:

- health endpoint;
- events endpoint;
- mock provider returns deterministic data;
- positive variation calculation;
- negative variation calculation;
- no alert below 8%;
- standard alert between 8% and 15%;
- critical alert above 15%;
- duplicate alert prevention.

Tests must run with:

pytest

If only a subset of tests is relevant to the current task, run that subset and explain it.

If a test cannot be added immediately, explain why and document the gap.

## Local run commands

Use these commands unless the repository defines better ones.

Install dependencies:

python -m pip install -r requirements.txt

Run tests:

pytest

Start server:

python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

Start server in background when explicitly requested:

nohup python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 > uvicorn.log 2>&1 & echo $! > uvicorn.pid

Stop background server:

kill $(cat uvicorn.pid)

Local URLs:

http://127.0.0.1:8000/health

http://127.0.0.1:8000/docs

## README requirements

Create or update README.md whenever project behavior changes.

Keep README practical and useful for a non-developer product owner.

README must include:

- project description;
- MVP scope;
- what the software does not do;
- local setup;
- install command;
- run command;
- test command;
- available endpoints;
- example responses where useful;
- alert logic;
- MVP limits;
- next recommended steps.

Avoid long theory in README.

## Security and configuration

Never commit real API keys.

Use .env.example for environment variables.

Do not hardcode secrets.

Do not store credentials in the repository.

Do not include real bookmaker credentials or tokens.

Future real provider integrations must respect provider terms of service, usage limits and costs.

## Compliance rules

Always preserve these constraints:

- use only legitimate data sources;
- respect provider terms of service;
- avoid unauthorized scraping;
- do not automate betting;
- do not provide betting advice;
- do not promise profit;
- keep the system informational;
- document provider limitations clearly.

If a requested feature creates legal, contractual or operational risk, flag it clearly and suggest a safer alternative.

## Development workflow

When working on this repository:

1. Read this AGENTS.md first.
2. Inspect only relevant files.
3. Identify the current project state.
4. Make the smallest coherent change.
5. Keep business logic in services.
6. Keep routers thin.
7. Keep outputs user-readable.
8. Run relevant tests.
9. Update README only if behavior changes.
10. Avoid unrelated cleanup.
11. Avoid broad refactors.
12. Report what changed.

## Credit-saving behavior

Minimize token and compute usage.

Do not print large file contents unless necessary.

Do not perform broad repository scans unless needed.

Do not regenerate files that only need small edits.

Do not add dependencies unless necessary.

Do not implement multiple future phases in one task.

Do not run long commands unless needed.

Prefer targeted commands such as:

pytest tests/test_health.py

instead of full test runs when only one module changed.

If a full test run is necessary, explain why.

## Definition of done

A task is complete only when:

- the requested code is implemented;
- relevant tests pass or failures are clearly explained;
- README is updated if behavior changed;
- no prohibited betting, scraping or bypass functionality is introduced;
- API responses remain clear for the final user;
- final response includes:
  - files changed;
  - commands run;
  - test result;
  - any remaining limitations;
  - next recommended step.

## Current MVP direction

Build the backend first.

Do not build a frontend dashboard until backend events, odds, polling and alerts are working.

Recommended sequence:

1. Health endpoint and app startup.
2. Competitions, teams and events.
3. Events endpoint with readable output.
4. Mock odds provider.
5. Odds snapshots and GET /odds.
6. Variation engine.
7. Alert engine.
8. Polling service and POST /poll.
9. GET /alerts with readable output.
10. Basic documentation and examples.
11. Only later: dashboard or external provider integration.