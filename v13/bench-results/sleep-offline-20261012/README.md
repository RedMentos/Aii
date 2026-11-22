# §99-Ablation: Schlaf-Replay des Fast-Forward-Prädiktors (WP-S7 Schritt 2) — **SUPPORTED_SYNTHETIC** (Thread L, 2026-10-12)

Skript `code/scripts/ablation_sleep_offline.py`, Vorregistrierung `preregistration.json` (Commit `4aa892c`, vor dem Lauf gepusht), Rohdaten `report.json`.
Echter `fastforward.FastForward` (Online-NLMS, Replay-Puffer, `consolidate` mit Held-out-Schutz) auf frischem SQLite-Store. 10 Tage × 60 Runden, Schlaf nach jedem Tag, 5 Saaten; verborgene lineare Ziele (Dauer, Erfolg, Zeichen) mit Rauschen.
Primärmaß: summierter absoluter Vorhersagefehler vor jedem Online-Update, Tage 2–10.

| Strom | Schlaf (mit Schutz) | kein Schlaf | Replay mit vertauschten Ergebnissen | Schlaf ohne Schutz | Schlaf gewinnt (kein / vertauscht / ohne Schutz) |
|---|---|---|---|---|---|
| stationär | .950 (3/10 Nächte behalten) | 1.033 | 1.688 (10/10 behalten) | **.922** | 5 / 5 / 0 |
| Drift (neue Ziele ab Tag 6) | **1.225** (3.6/10) | 1.288 | 1.742 (10/10) | 1.326 | 5 / 5 / 5 |

- Schlaf-Replay senkt den Fehler am nächsten Tag um ≈ 8 % → SUPPORTED_SYNTHETIC.
- Der Held-out-Schutz ist bei stabiler Welt zu vorsichtig (ohne Schutz besser, 0/5), schützt aber bei Drift (5/5).
- Schwäche: Der Schutz prüft gegen denselben Puffer. Sind die gespeicherten Ergebnisse vertauscht/verdorben, besteht jede Nacht den Schutz (10/10) und der Fehler steigt stark (1.69 statt 1.03). Der Schutz erkennt also Überanpassung, keine kaputten Daten.
- Grenze: synthetischer linearer Ergebnisprozess, BOOT-Lernrate/Epochen/Held-out; Tages-Digest und TTT-Staging (Schritte 1 und 3) nicht getestet.
