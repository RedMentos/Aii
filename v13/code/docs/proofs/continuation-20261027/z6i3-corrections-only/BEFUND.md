# WP-Z6i3 Befund: geänderte Vorliebe nur aus Korrekturen — `Z6I3_FAIL`

Vorregistriert in `PREREG.md` (dba98725, vor dem Lauf gepusht). Frische Seeds 151/157/163, Daten
`v13/bench-results/z6i3-corrections-only-20261027/seed*.json` (+ `run_seed*.log`; Vorläufe unter `dev/`).

| Seed | fixed+rec Hälfte / Behalten / falsch | adaptive+rec Hälfte / Behalten / falsch | Kontrolle ohne Gewichtung Hälfte |
|---|---|---|---|
| 151 | 0,125 / 1,00 / 0 | 0,75 / 1,03 / 0 | 0,00 |
| 157 | 1,00 / 0,875 / 2 | 1,00 / 0,87 / 2 | 0,25 |
| 163 | 0,00 / 1,00 / 0 | 0,875 / 1,10 / 0 | 0,25 |

Rücknahme in allen Armen exakt. Urteil **`Z6I3_FAIL`** (R1 in 151 und 163, R2+R3 in 157).

Bedeutung: Ohne Hinweis des Menschen gibt es nur zwei Möglichkeiten. Der Kopf bleibt beim Alten (alte Labels sind nicht
sicher als überstimmt erkennbar, Seeds 151/163 fixed), oder er übernimmt die neue Vorliebe und reißt dabei ähnliche
andere Rechenfragen mit (157: zwei falsche Freigaben). Der Grund: ohne genannten Geltungsbereich gibt es keine Anker und
keine Grenze, welche Fragen gemeint sind. „Lernt bei Bedarf“ kommt am nächsten (0,75–1,00 in allen Seeds), aber nicht
sauber. Der Schalter `route_recency_half_life` bleibt 0 (aus).

Der verlässliche Weg bleibt der aus Z6i2: Der Mensch nennt den Bereich einmal (`:ersetze … --sofort --lehre`), dann
lernt der Kopf ihn sauber (3/3 frische Seeds, 0 falsche Freigaben). Nur aus Korrekturen lernen bleibt offen. Daran arbeitet
die KL-Reihe (Branch uvt813) mit einer anderen Prüfung (k-fach außerhalb der Stichprobe).
Grenzen wie Z6i.
