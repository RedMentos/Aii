# Befund WP-Z2f: Körper-Frage fest aus der aktuellen Nachricht (2026-10-26)

Vorregistriert in `0b14fd6`. Seeds 26/27/28, Arme C (keine Frage), CL (spezifische Frage), CD (abgeleitete Frage).
Daten `bench-results/step2-z2f-derived-20261026/`.

## Urteil: **NOT_SUPPORTED** (Arm CD nicht auswertbar)
Zwei von drei CD-Läufen haben strukturelle Fehler. Der eingefrorene Werkzeug-Replay lehnt sie ab („Input report has
structural failures“). Die Entscheidungsregel lässt sich deshalb nicht prüfen. Ich zähle das als NOT_SUPPORTED und
werte nicht nachträglich um.
- CD Seed 27: Vorbereitung von Episode Nimbus brach ab, weil ein Körper-Angebot kein gültiges JSON war
  („Unterminated string“). Dadurch fehlen 7 Zeilen.
- CD Seed 28: 1 Zeile (Tycho, both_none) mit ungültigem Körper-JSON („Expecting ',' delimiter“).
- C und CL: 0 solche Fehler in 6 Läufen. Der Fehler hängt also wahrscheinlich an der längeren abgeleiteten Frage
  (längere Zitat-Antworten, abgeschnitten).

## Beschreibend (nicht Teil des Urteils)
| Seed | C both_exact | CL both_exact | CD both_exact | B1-Optionszitate C / CL / CD (both_exact) |
|---|---|---|---|---|
| 26 (Werkzeug-Replay) | .325 | .550 | .450 | 3 / 8 / 4 |
| 27 | .275 | .550 | (.400 ohne Werkzeug) | – |
| 28 | .442 | .508 | (.450 ohne Werkzeug) | – |
0 falsch festgelegte Werkzeug-Zeilen in allen auswertbaren Läufen.

## Was das heißt
Auf dem einzigen auswertbaren Seed liegt die abgeleitete Frage zwischen keiner und der spezifischen Frage. Sie nennt
„Option A/B“, aber nicht *welche* Werte (Kosten, Dauer, lokal). B1 zitiert deshalb seltener die Optionswerte.
Außerdem macht sie die Körper-Ausgabe brüchig. Bevor der Schalter wieder gemessen wird, müssen ungültige Körper-Angebote
abgefangen werden (gekürzte Zitate oder ein Schema-Limit). Und die Frage muss die gebrauchten Merkmale benennen. Die
stehen nicht in der Nachricht, wohl aber im Werkzeug-Schema (das eligibility-Werkzeug kennt cost/days/local).

## Folge
Schalter `body_question_mode` bleibt aus. Nächster Ansatz: Die Frage aus dem Werkzeug ableiten, das die Nachricht
auslöst (`eligibility.question()` → benötigte Felder), und ungültiges Körper-JSON robust behandeln.
