# Checklist pre-demo

## Prima di mostrare il software

- Avviare il server su http://127.0.0.1:8001/
- Verificare che Telegram sia configurato.
- Verificare che lo scheduler sia spento prima della demo.
- Usare i dati reali già presenti nel database.
- Non cancellare alert, log o snapshot prima della demo.

## Controlli rapidi

```bash
git status --short
pytest
curl "http://127.0.0.1:8001/system/status"
```

## Sequenza demo consigliata

1. Stato operativo.
2. Campionati da monitorare.
   - usare prima “Aggiorna leghe/slug dal provider” per recuperare gli slug ufficiali;
   - usare “Aggiorna campionati da eventi” per aggiornare le competizioni presenti negli eventi disponibili;
   - verificare quali campionati sono mappati;
   - usare “Salva mapping” solo come fallback amministrativo con slug provider valido;
   - attivare solo campionati realmente monitorabili.
3. Mercati MVP.
4. Notifiche Telegram.
5. Alert recenti.
   - usare il filtro Solo cali notificabili per vedere cosa può partire su Telegram;
   - usare Aumenti non notificati per mostrare cosa resta solo nello storico;
   - usare Critici per isolare i cali oltre soglia critica.
6. Log notifiche.
7. Piano API provider.
   - verificare preset attivo: Free Plan, Starter, Growth, Pro o Enterprise;
   - controllare la stima richieste/ora;
   - verificare che la configurazione non superi il limite impostato;
   - se la stima supera il limite, lo scheduler non può essere attivato.
8. Consumo API provider.
   - verificare richieste usate nell’ultima ora;
   - verificare richieste residue;
   - se il limite è raggiunto, non fare refresh provider o controllo quote;
   - se Odds-API.io segnala rate limit, attendere il reset orario prima di test reali.
9. Bookmaker provider.
   - verificare i bookmaker configurati;
   - verificare che il numero bookmaker non superi il limite del Piano API;
   - per Free Plan usare massimo 2 bookmaker, ad esempio Stake,Sbobet;
   - se i bookmaker superano il limite del piano, lo scheduler non deve potersi attivare.
9. Automazione scheduler.

## Regole demo

- Non promettere profitti.
- Non promettere scommesse automatiche.
- Non promettere WhatsApp/SMS.
- Non usare 3 secondi come frequenza commerciale.
- Spegnere lo scheduler a fine demo.

## Spegnimento scheduler

```bash
curl -X PUT "http://127.0.0.1:8001/configuration/scheduler-settings" \
  -H "Content-Type: application/json" \
  -d '{"enabled":false,"poll_interval_seconds":30,"event_limit":1}'
```
