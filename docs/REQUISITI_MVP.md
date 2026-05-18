# Requisiti MVP

## Obiettivo

Monitorare quote calcistiche pre-match da provider dati legittimi e generare alert Telegram quando la variazione percentuale rispetto alla quota di apertura rientra tra 8% e 15%.

## Mercati iniziali

- 1X2
- Goal/No Goal
- Over/Under 2.5

## Competizioni iniziali

Da confermare in modo definitivo, ma la prima ipotesi operativa è:

- Premier League
- Championship
- Serie A
- Serie B
- LaLiga
- Segunda División
- Bundesliga
- 2. Bundesliga
- Ligue 1
- Ligue 2

## Formula

Variazione percentuale:

((quota_attuale - quota_apertura) / quota_apertura) * 100

Per la soglia si usa il valore assoluto della variazione.
Nella notifica si conserva il segno.

## Alert standard

Genera alert se:

- esiste una quota di apertura
- esiste una quota attuale confrontabile
- la quota attuale è diversa dalla quota di apertura
- la variazione assoluta è >= 8%
- la variazione assoluta è <= 15%
- non esiste alert duplicato recente
- evento, mercato e provider sono attivi

## Alert critici

Le variazioni superiori al 15% saranno gestite come alert critici separati.

## Compliance

Il software deve usare solo fonti dati legittime e non deve effettuare scraping non autorizzato, aggirare sistemi anti-bot o piazzare scommesse.
