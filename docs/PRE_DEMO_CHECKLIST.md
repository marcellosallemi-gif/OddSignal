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
   - verificare quali campionati sono mappati;
   - per i campionati non mappati usare “Salva mapping” solo con slug provider valido;
   - attivare solo campionati realmente monitorabili.
3. Mercati MVP.
4. Notifiche Telegram.
5. Alert recenti.
   - usare il filtro Solo cali notificabili per vedere cosa può partire su Telegram;
   - usare Aumenti non notificati per mostrare cosa resta solo nello storico;
   - usare Critici per isolare i cali oltre soglia critica.
6. Log notifiche.
7. Piano API provider.
   - verificare preset attivo: Free, 5000/h, Illimitato o Custom;
   - controllare la stima richieste/ora;
   - verificare che la configurazione non superi il limite impostato.
8. Automazione scheduler.

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
