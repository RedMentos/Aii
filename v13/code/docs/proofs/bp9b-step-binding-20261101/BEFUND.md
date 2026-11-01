# WP-BP9b BEFUND: `BP9b_NO_SIGNAL` (uniform_sgd divergiert, Lernrate aus der Kalibrierung trug nicht)

Vorregistrierung `PREREG.md`. Roh: `bench-results/bp9b-step-binding-20261101/` (Pilot Seed 91, Seed 1 teilweise). Seeds 2 und 3 nicht gelaufen (Abbruch nach Seed 1, weil derselbe Ausfall zu erwarten war und Rechenzeit ohne möglichen Gewinn).

Seed 1, SGD lr 0,05 (kleinste Rate der Kalibrierung mit Treffer >= 0,9 auf 8 Fakten):
| Arm | Mensch | Ergebnis | Eigen richtig | Eigen FALSCH übernommen | Allgemeinfragen |
|---|---|---|---|---|---|
| uniform_sgd | 0,0 | 0,0 | 0,0 | 0,0 | 0,0 |
| typed_sgd | 1,0 | 1,0 | 0,75 | 0,5 | 1,0 |

Der Arm uniform_sgd ist **zerstört** (alle Werte 0, auch Allgemeinfragen 0): Die Rate, die auf 8 Fakten stabil war, divergiert auf dem vollen 16er-Batch mit Gewicht 1 (zweifache Gradientensumme in der Schrittrichtung, Momentum 0,9). Regel der Vorregistrierung: Mensch+Ergebnis in uniform_sgd < 0,8 -> `BP9b_NO_SIGNAL`. Ein Vergleich typed gegen uniform ist damit nicht gültig.
Nebenbeobachtung (nicht gewertet, weil ohne gültiges uniform): typed_sgd lernt Mensch und Ergebnis voll, aber Eigen-Fakten nur noch teilweise (richtig .75, falsch .50); bei AdamW war es richtig 1,0 / falsch .83. Das Gewicht bindet mit SGD also stärker, nur ist der Schutz noch nicht klar getrennt von "falsch" und "richtig".
## Lehre
Die Kalibrierung musste auf dem tatsächlichen Batch laufen, nicht auf einer Teilmenge. Das ist ein Fehler im Aufbau, kein Befund zum Modell. Neu: WP-BP9c mit Kalibrierung auf dem vollen Batch (`--pilot-all`) und eigener Vorregistrierung.
