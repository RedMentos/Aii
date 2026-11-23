# §99-Ablation: F7 gemessene Plastizität (§16) — **SUPPORTED_SYNTHETIC**, kleine Abstände (Thread L, 2026-10-12)

Skript `code/scripts/ablation_f7_plasticity.py`, Vorregistrierung `preregistration.json` (Commit `49d8a07`, vor dem Lauf gepusht), Rohdaten `report.json`.
Echte `plasticity.Plasticity`: Jeder Versuch läuft durch das echte `budget()` (PlasticityBudget-Paket, effektive Lernrate) und das echte `observe()` (Manifest-, Checkpoint- und Hash-Prüfung, Gain-Update). Der Lerner drumherum ist ein Harness: lineare Regression, ein SGD-Durchgang je Versuch. Behalten wird ein Versuch nur, wenn Retention (alte 3 Aufgaben: MSE höchstens +.10) und Nutzen (aktuelle Aufgabe: MSE mindestens −2 %) bestehen; sonst Rollback. 240 Versuche, neue Aufgabe alle 8, ruhige und konfliktreiche Phasen im Wechsel.
Schrittweite ohne F7 kalibriert (Saaten 101–105): die Stufe, bei der „immer voll“ und „immer halb“ am nächsten beieinander liegen → .1.

| Arm | Fehler (niedriger besser) | behalten | Retention-Fehler | mittlerer Gain | F7 gewinnt |
|---|---|---|---|---|---|
| F7 (echter Gain) | **.776** | 168 | 70 | .63 | — |
| immer voll (Gain 1) | .810 | 138 | 96 | 1.0 | 5/5 |
| immer halb (Gain .5) | .825 | 180 | 60 | .5 | 5/5 |
| zufällig in [.5, 1] | .800 | 156 | 81 | .75 | 5/5 |

- Der gemessene Gain schlägt beide festen Budgets und zufälligen Gain in allen Saaten → SUPPORTED_SYNTHETIC. Die Abstände sind klein (≈ 3–6 %).
- F7 liegt zwischen den festen Budgets: weniger Retention-Fehler als „voll“, mehr Fortschritt als „halb“.
- Offen gelegt: Die Welt (Drift .10/.50, absolute Retention-Grenze wie `retention_max_delta`) wurde vor der Vorregistrierung auf Saat 999 so gewählt, dass Retention weder fast immer noch fast nie scheitert. Die Schrittweite legt die Kalibrierung ohne F7 fest.
- Grenze: synthetische lineare Aufgaben, Harness-Lerner, BOOT-Gates; keine native oder geteilte Interferenz-Messung.
