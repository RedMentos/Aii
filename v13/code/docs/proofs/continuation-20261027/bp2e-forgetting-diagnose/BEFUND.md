# WP-BP2e Diagnose: wo das Vergessen im Q4-Tor herkommt (nur Auswertung vorhandener Läufe, kein neues Training)

Vorab-Überlegung (Regel „nicht dumm testen“): Ein neuer Trainer-Lauf lohnt nur, wenn klar ist, was er verbessern soll. Die 14 Läufe aus BP2c/BP2d (`bench-results/bp2c-ag6-wiring-20261027`, `bp2d-more-anchors-20261027`) enthalten die Liste der vergessenen Allgemeinfragen. Erst die auswerten, dann entscheiden.

| Befund | Wert |
|---|---|
| Läufe mit Vergessen > 0 | 7 von 14 |
| Vergessene Fragen insgesamt | nur 4 verschiedene (von 30): „gas plants absorb“ 4x, „thank you ins Deutsche“ 3x, „season after winter“ 2x, „largest ocean“ 2x |
| Alter Weg (`live`, LoraTrainer) | 1 von 4 Läufen mit Vergessen (.033) |
| Neuer Weg (`body0`/`gen`/`gen2`/`gen4`, BodyJepaTrainer) | 5 von 8 ohne minor-Arme: 4 mit Vergessen, aber im Mittel kleiner als eine Frage je Lauf |
| `gen_minor` (Subspace auf 350M) | 2 von 2 mit Vergessen, einmal .10 |

Schluss: Das Vergessen sitzt an wenigen **Grenzfragen**, die der Q4-Prüfer schon im Ausgangszustand knapp richtig beantwortet; Tor-Schwelle .02 heißt „keine einzige darf kippen“. Der neue Trainer ist nicht systematisch schlechter als der alte (kleine Zahlen, kein Beleg für einen Unterschied), und eine Einzelschritt-Schleife würde daran nichts erklärbar ändern. Die vier Fragen als Anker zu nehmen wäre Tor-Tricksen (Prüffragen im Training) und ist verboten; `minor` auf 350M schadet nachweislich.

Entscheidung: **kein BP2e-Trainingslauf jetzt**. Er hätte keinen messbaren Gewinn über dem Rauschen (bräuchte >= 6 Seeds je Arm) und keine benannte Ursache. Sinnvoll erst, wenn (a) der Q4-Prüfer die Grenzfragen mit mehr Proben/Sampling stabil bewertet (Messrauschen senken, Tor-Schwelle unverändert) oder (b) die Handy-Messung (Redmi) zeigt, ob das Muster dort überhaupt auftritt. Status BP2: Lecken gelöst (4/4 Seeds), Vergessen im Tor = Messrauschen an 4 Grenzfragen, Opt-in bleibt (`locality_gen=2`), Standard unverändert.
