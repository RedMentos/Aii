# Befund WP-Z2e: allgemeine Körper-Frage (2026-10-22, ausgewertet 2026-10-26)

Vorregistriert in `b2876f5` (vor dem Lauf gepusht). Seeds 23/24/25, 10 Z2-Episoden, 3 Arme, 630 Zeilen + Werkzeug-Replay.
Lauf 1 brach nach 8 von 9 Läufen am Zeitlimit ab; der fehlende Lauf CG/25 lief unverändert von vorn (`run2_resume.log`).
Daten `bench-results/step2-z2e-general-20261022/`.

## Urteil: **NOT_SUPPORTED**
| Arm | b1_only | b2_only | both_exact |
|---|---|---|---|
| C (keine Frage) | .367 | .236 | .328 |
| CL (spezifische STEP2-Frage) | .578 | .194 | **.661** |
| CG (allgemeine Frage) | .358 | .194 | .361 |

- Kriterium 1 ✗: CG − C = +.03, 95-%-KI [−.07, +.15].
- Kriterium 2 ✗: CG − CL = −.30, KI [−.44, −.18].
- Kriterium 3 ✓: 0 falsch festgelegte Werkzeug-Zeilen in allen Armen.
- Nebenbefund: Der Effekt der spezifischen Frage repliziert auf frischen Seeds: CL − C = +.33, KI [+.18, +.50].

## Was das heißt
Mit der allgemeinen Frage zitiert B1 die Optionswerte kaum öfter als ohne Frage (z. B. b1_only, Seed 23: 3 gegen 10 mit der
spezifischen Frage). Der Gewinn kommt also daher, dass die Frage benennt, *welche* Werte gebraucht werden, nicht daher,
dass überhaupt gefragt wird. Die Frage muss also für jede Aufgabe gebildet werden. Ein Kandidat dafür ist JEF:
Es leitet aus der aktuellen Nachricht ab, was fehlt („Optionswerte A/B“), und stellt die Rückfrage gezielt.

## Folge
Allgemeine Frage nicht übernehmen, Schalter bleibt aus. Nächstes Paket (neu vorregistrieren): JEF formuliert die Körper-
Frage aus der aktuellen Nachricht (fest, nicht generativ: Schlüsselwörter/Entitäten der Nachricht einsetzen) und wird gegen
die spezifische Frage auf frischen Seeds gemessen.

## Grenzen
Nur STEP2-Episoden, Linux-Cloud, kein Handy.
