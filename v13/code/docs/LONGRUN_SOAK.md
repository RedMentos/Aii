# G13 Langlauf-Harness (Canon G13, §22.2.1, §94; §102 `redmi_longrun_proof`)

Stand 2026-10-12, Thread „Nächste offene Pakete N“ (WP-N18). Skript `scripts/longrun_soak.py`, Tests `tests/test_longrun_soak.py` (3),
volle Suite 1310 grün. Beleg: `bench-results/longrun-soak-20261012/report.json` (7 Tage, 4 Turns/Tag, PASS).

## Was es tut

Simulierte Tage über den echten Laufpfad: jeder Tag startet die Runtime neu, Turns laufen durch die dauerhafte Turn-Queue und
den Worker, Wake-Events durch den echten G13-Scheduler, Schlaf durch den echten SleepRuntime-Job. Vorgestellt wird nur die
Wanduhr (Store-Zeitstempel + Scheduler/Sleep-Uhr gemeinsam, `SimulatedWall`); Turn-Fristen bleiben echt.

Prüfungen je Tag: Turns FINAL; Wake-Reihenfolge nach Priorität (TOOL > TIMER > GOAL > REPLAY > IDLE); ein zukünftiger TIMER wartet
und wird nach dem Neustart geweckt; Wach-Replays laufen ab; Nacht: voller Schlaf DONE; jeder gespeicherte Fakt bleibt abrufbar;
Store-Integrität; Age-Stufe stabil; keine `job_error`; Scheduler-Queue begrenzt; DB-Wachstum ≤ 8 MB/Tag (BOOT).

```
python scripts/longrun_soak.py --home /tmp/soak --days 7                         # Cloud, Fixture-Sprecher
python scripts/longrun_soak.py --home ~/v13soak --days 7 --native --models-from ~/v13   # Redmi (WP-R), nie im Nutzer-Home
```

## Befunde

1. **Behoben: Wach-Replays verdrängten den Nacht-Schlaf.** `REPLAY_DUE` (Priorität 20) schlägt `IDLE` (10). Jeder Wach-Replay
   bearbeitet unter dem Age-0-Budget nur einen Eintrag, also wurden sie hintereinander neu gepostet, bis das Burn-out-Budget
   (12 Hintergrund-Starts seit der letzten Nutzereingabe) verbraucht war; danach blieb `sleep_full` bis zur nächsten Eingabe liegen.
   Im Soak ab Tag 2 sichtbar. Fix in `SleepRuntime.tick`: höchstens ein Wach-Replay je Ruhephase (Meta `sleep_wake_replay_period`).
   Regressionstest schlägt ohne Fix fehl (3 statt 1).
2. **Offen (WARN): Replay-Rückstand wächst.** Fällige Einträge 4 → 24 in 7 Tagen bei 4 Fakten/Tag, weil autonomes Replay durch das
   Age-Budget `replay_items` (Age 0: 1 je Zyklus) gedeckelt ist. Einträge verfallen nach `ttl_days`. Ob das Budget mit der Reife
   steigen soll, ist eine Age-Policy-Frage, kein Fehler des Schedulers.
3. Neue Korrekturen sind für Wach-Replays erst nach dem nächsten Sleep-Lauf sichtbar (`queue.sync` läuft nur in `SleepCycle.run`).
   Unkritisch, weil der Nacht-Schlaf sie aufnimmt; dokumentiert.

## Grenzen

Fixture-Sprecher: keine Aussage zu Modellqualität, RSS, Thermik, Latenz. Gedächtnis-Gesundheit ist Abruf auf Retrieval-Ebene.
Drift gelernter Köpfe wird ohne `--native` nicht gemessen. Der echte Langlauf-Beweis (`redmi_longrun_proof`) ist der `--native`-Lauf am Redmi.
