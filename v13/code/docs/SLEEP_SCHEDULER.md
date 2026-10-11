# WP-E Sleep/Replay + Event-Scheduler (§94, §15, §22.2.1, §37, §67, G8, G13)

Code: `v13/scheduler.py`, `v13/sleep.py`; Tests: `tests/test_sleep_scheduler.py` (21).
Hooks: `runtime.py` (SleepRuntime, Idle-Tick, Job `sleep`, Abbruch bei Nutzereingabe),
`operator.py` (`:sleep`, `:scheduler`), `store.py` (Telemetrie-Felder).

## Event-Scheduler (G13)
- Dauerhafte, begrenzte Queue (256) in `states['G13_EVENT_QUEUE']`, übersteht Neustart
  (DISPATCHED → wieder fällig, max. 3 Versuche).
- Priorität: USER_INPUT > TOOL_EVENT > RESOURCE_CHANGE > TIMER > GOAL_WAKE > REPLAY_DUE > IDLE.
- Hintergrund-Events nur wenn Runtime idle; RED (CRITICAL) = nichts, YELLOW (PRESSURE) = nur Sleep C;
  Quiet Hours blocken alles außer Nutzer-Events.
- SELF-Events (eigene Initiative) laufen über `age.py`-Rechte (`resume_open_goals`, `self_initiative`,
  `own_sleep_planning`); bei Age 0 bleiben sie `HELD_AGE`.

## Replay-Queue (§94.1)
- Baut auf der vorhandenen `replay`-Tabelle auf; Zusatzfelder (evidence_class, unresolved_errors,
  affected_paths, ttl, source_refs, max_authority) als `ReplayItem`-Pakete.
- Spaced Rehearsal (Intervall verdoppelt sich bei PASS), Mix nach §67: 50 % neu, 35 % geschützt alt,
  15 % Fehler, alt/neu verschränkt. Typ-Gains nach §67 (Age 0).

## Phasen
- Sleep A: echter Retention-Test pro Episode über `Memory.recall` + Provenienz; Fehler erhöhen
  Priorität; Regression-Flag wenn alte Retention < 0,95; Konsolidierung nur **staging** (Freigabe bleibt menschlich).
- Sleep B: Routen-Alternativen, Skill-Rekombination, Welt-Hypothesen. Nur Hypothesen
  (`DREAM_HYPOTHESIS`, `fact_write_authority=0`), nie in memories/Indexe. Autonom nur mit Age-Recht `short_dream`.
- Sleep C: Trace-Decay, TTL, homöostatische Gains (0,5–1,5× Basis), Plasticity-Reconcile, tmp-Cleanup,
  Index-Rebuild, Telemetrie-Prune, WAL-Checkpoint.
- Wake-Replay (§94.5): nach 20 s Idle nur hochpriore Episoden (max. 2).
- Volle Nacht: nach 600 s Idle, höchstens stündlich. Budget pro Lauf 10 min; Nutzereingabe bricht ab.

## Bedienung
```
:sleep                 Status
:sleep run full|a|b|c|wake
:sleep in 30 full      Timer
:sleep policy [Name Wert]   z. B. enabled off, quiet_hours 22-7, sleep_idle_s 900
:scheduler             Queue/Historie
```

## Grenzen (ehrlich)
- Retention-Test ist Abruf-Ebene, keine native Neubewertung (die bleibt `:replay`).
- Sleep B erzeugt strukturierte Hypothesen, keinen generierten Traumtext (der bleibt `:dream`).
- Keine Gewichts-Konsolidierung (Age 0: base_merge_authority = 0).
- Stale Deltas werden nur gezählt, nicht gelöscht (Rollback-Fenster).
- Redmi: Laufzeit/Thermik der Hintergrund-Ticks ist nicht gemessen.
