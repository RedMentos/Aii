# Kandidat: A3-Schüler-Gate mit kürzerem Fenster — **PASS**, übernommen (Thread L, 2026-10-12)

Skript `code/scripts/aplane_gate_candidate.py`, Vorregistrierung `preregistration.json` (Commit `ca732c3`, vor dem Lauf gepusht), Rohdaten `report.json`.
Änderung: Übereinstimmungs-Fenster 100 statt 400. Die Retention scheitert nur bei klarem Einbruch (letzte 25 unter .75) statt bei „letzte 25 um mehr als .05 schlechter als davor“. Schwelle .90 und n ≥ 50 bleiben.

| Welt | Kandidat | bisheriges Gate | immer Schüler | nie Schüler |
|---|---|---|---|---|
| Standard (2 kurze Einbrüche auf .50) | .820 | .702 | **.882** | .606 |
| Stress (3 lange Einbrüche auf .40, je 400 Runden) | **.721** | .635 | .699 | .614 |

- Kriterien: Standard besser als bisher 5/5, Stress besser als „immer Schüler“ 4/5, Stress nie unter „nie Schüler“ (0/5) → **PASS**.
- Übernommen in `v13/aplane.py` (`WINDOW=100`, `RETENTION=.15` als Abstand zur Schwelle) mit Test in `tests/test_aplane.py`. Freigabe bleibt Nutzerbefehl, Auto-Rückstufung bleibt.
- In der Standardwelt bleibt „immer Schüler“ besser. Das Gate ist eine Versicherung für lange Einbrüche und kostet bei kurzen etwas.
- Der Bericht `aplane-gate-20261012/report.json` stammt von der alten Regel.
- Grenze: synthetischer Übereinstimmungsprozess, Lehrer gilt als richtig.
