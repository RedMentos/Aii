# Action-JEPA Runde 4: Mittelschicht- und Letzter-Token-Taps

Stand 2026-10-12, Thread „Nächste offene Pakete F“ (Claude). Linux-Cloud, kein Redmi.
Vorregistriert vor der Erfassung (GitHub `19c37f5`). Gleiche Zeilen und Partitionen wie Runde 3 (Test = 5 frische Themen).

**Ergebnis: alle 24 Läufe (4 Taps × 2 Arme × Seeds 13/21/34) bestehen das Gate nicht.**

Neues Lesewerkzeug `scripts/native_layer_taps.cpp` (cb_eval kopiert `l_out-L`, ändert nichts), gebaut gegen das
vendorte llama.cpp aus dem PyPI-sdist llama-cpp-python 0.3.36 (GitHub-Quellarchiv in dieser Sitzung gesperrt).
Erfassung 2475 Texte × Schichten 11 und 23 in 4 min, Exit 0.

Verhältnis Test-MSE zu Mittelwert-Delta je Aktion, Residuum-Arm (Seeds 13/21/34):

| Tap | negate | question | summarize | translate_de |
|---|---|---|---|---|
| l_out-11 letzter Token (primär) | 0.98–1.14 | **0.79–0.88** | 0.90–0.96 | 1.10–1.41 |
| l_out-11 Mittel | 1.14–1.41 | 0.93–1.11 | 0.94–0.96 | 0.91–1.05 |
| l_out-23 letzter Token | 1.37–1.82 | 0.73–0.99 | 0.95–0.97 | 0.92–0.97 |
| l_out-23 Mittel | 1.29–1.41 | 1.06–1.15 | 0.98–1.01 | **0.81–0.97** |

- Welche Aktion lernbar ist, hängt vom Tap ab: die Mittelschicht trägt Information für `question`/`summarize`,
  die letzte Schicht für `translate_de`. `negate` ist auf keinem Tap besser als ein fester Versatz.
- Der Runde-1-Arm ist überall schlechter als Mittelwert-Delta.
- Kein Tap schlägt die Kontrolle für alle vier Aktionen; das Gate verlangt das. §99 „JEPA hilft“ für
  Text-Handlungsfolgen bleibt **nicht belegt**. Lineare Köpfe sind damit über Schicht, Pooling und Testdaten ausgeschöpft.

Dateien: `report.json` (alle 24 Läufe), `raw-taps-parts/` (ZIP `dab0df1b…`, rohe float32-Taps),
`results-parts/` (ZIP `43b3b3de…`, Datensätze ohne Arrays, Metriken, Checkpoints). Keine Autorität.
