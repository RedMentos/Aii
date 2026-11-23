# Action-JEPA Runde 5: echte Werkzeug-Aktionen (Zähler-Welt mit `calc`)

Stand 2026-10-12, Thread „Nächste offene Pakete F“ (Claude). Linux-Cloud, kein Redmi.

**Ergebnis: alle 24 Läufe (4 Taps × 2 Arme × Seeds 13/21/34) bestehen das Gate nicht.**

- Welt: 400 Startwerte („The counter shows N.“), je vier echte `calc`-Aufrufe (verdoppeln, +15, /4, −7) über
  `ToolRegistry` mit IH-H29-Politik und IH-H14-Transaktion in einem Wegwerf-Sandbox-Store: 1600 ausgeführte
  Transaktionen, jede als Quelle ihrer Zeile gebunden. Ergebnistext aus dem Werkzeug-Resultat, nicht vom Modell.
- v1 (`1ba1d95`) war undurchführbar: Ergebnistexte glichen Starttexten anderer Partitionen, der feste Ausschluss
  ließ 32/400 Episoden. Kein Training, kein Wert. Gesichert in `v1-failed-parts/`, `v1-outcome.json`.
  v2 (`434b4ab`) ändert nur den Ergebnistext („After doubling, the counter shows 74.“); 0 Episoden ausgeschlossen.
- Taps wie Runde 4 (`l_out-11`/`l_out-23`, letzter Token/Mittel), 2000 Texte.

| Tap | Mittelwert-Delta Test-MSE | Residuum-Arm Test-MSE | Runde-1-Arm Test-MSE |
|---|---|---|---|
| l_out-11 letzter Token | .060–.068 | .35–.43 | .52–.88 |
| l_out-11 Mittel | .017–.018 | .050–.053 | .48–.58 |
| l_out-23 letzter Token | .019–.025 | .10–.23 | .41–.93 |
| l_out-23 Mittel | .004–.005 | .041–.046 | .21–.45 |

Befund: Hier ist Mittelwert-Delta je Aktion eine sehr starke Kontrolle. Jeder gelernte Prädiktor ist 2- bis
128-mal schlechter. Der Residuum-Arm **startet exakt bei Mittelwert-Delta** und wird durch das Training schlechter:
Die Zielfunktion selbst (Varianz-Untergrenze auf z, Projektor-Anker, EMA-Ziel) passt nicht zu fast konstanten
Handlungsfolgen, deren Kontextanteil nur ein paar Ziffern sind. Das ist ein Befund über das Objective, nicht nur über die Daten.

Dateien: `report.json`, `raw-parts/` (ZIP `82a48d42…`: Welt, Transaktionen, Sandbox-DB, rohe Taps),
`results-parts/` (ZIP `0e5cc010…`). Keine Änderung an `code/v13/*.py`, keine Autorität.
