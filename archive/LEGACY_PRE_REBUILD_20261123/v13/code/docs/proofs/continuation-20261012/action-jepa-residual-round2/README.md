# Action-JEPA Runde 2: Residuum über Mittelwert-Delta, Seeds 13/21/34

Stand 2026-10-12, Thread „Nächste offene Pakete F“ (Claude). Linux-Cloud, kein Redmi.
Vorregistrierung `preregistration.json` vor jedem Runde-2-Wert gepusht (Commit `de7f2c9`).

**Ergebnis: alle drei Seeds `candidate_gate_pass=false`.** Gleiche Gates wie Runde 1.

Änderung gegenüber Runde 1: Bias startet beim Mittelwert-Delta je Aktion (untrainiert = Kontrolle),
Schrittzahl 240 oder 960 nur über die Kalibrier-Partition gewählt.

| Seed | gewählt | Test Kandidat | Test Mittelwert-Delta | Test 960 Schritte | translate_de Test (Kandidat / Delta) |
|---|---|---|---|---|---|
| 13 | 240 | .179 | .180 | .442 | .277 / .319 |
| 21 | 240 | .193 | .194 | .486 | .303 / .344 |
| 34 | 240 | .169 | .176 | .403 | .267 / .310 |

- 960 Schritte überanpassen stark (Trainingsverlust sinkt, gehaltene Daten .38–.50).
- `translate_de` hat lernbare Kontextabhängigkeit: in allen Seeds und Partitionen unter Mittelwert-Delta, auf Kalibrierung/Test 12–20 % (Retention Seed 34 nur 3 %).
- `negate` und `question` werden schlechter als Mittelwert-Delta, `summarize` gemischt. Damit scheitern
  das Gate „jede Aktion > 2 % besser als alle Kontrollen“ und die Retention je Aktion.

Folgerung: Auf diesen Taps ist für drei von vier Aktionen ein fester Versatz die beste lineare Vorhersage;
nur Übersetzen hängt messbar vom Satz ab. Ein Action-JEPA mit Nutzen müsste nichtlinear sein oder
mehr Daten bekommen; der historische Testsatz ist exponiert, frische Testthemen wären nötig.

Dateien: `report.json`, `parts/` (geschlossenes ZIP `28b88fe2…` mit Checkpoints, rohen Metriken und
externen `predict`-Aufrufen für alle vier Aktionen). Keine Empfänger-, Lern- oder Runtime-Autorität.
