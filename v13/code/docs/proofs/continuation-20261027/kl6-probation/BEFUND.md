# WP-KL6 Befund: Probezeit vor der Freigabe — `KL6_PROBATION_FAIL` (1 von 3 Seeds besteht alles)

Vorregistriert in `PREREG.md` (Commit bebbc685). Seeds 137, 139, 149. Daten `v13/bench-results/kl6-probation-20261027/`.
Gesamt-Testlauf mit Probezeit-Code: OK (5 übersprungen).

Kopf selbst, Hälfte-Fragen am Ende / gesamt / falsche Freigaben:

| Arm | Seed 137 | Seed 139 | Seed 149 |
|---|---|---|---|
| fixed (nur Needle) | 0,00 / 0,65 / 1 | 0,00 / 0,775 / 0 | 0,00 / 0,70 / 0 |
| fixed+lex+rec+cv+ov (KL3) | 0,375 / 0,875 / 0 | 1,00 / 0,975 / 0 | 1,00 / 1,00 / 0 |
| fixed+…+prob | **0,00** / 0,80 / 0 | 0,875 / 0,975 / 0 | 1,00 / 1,00 / 0 |
| adaptive+…+prob | 0,375 / 0,875 / 0 | 1,00 / 1,00 / 0 | 1,00 / 0,90 / **1** |

Seed 139 alle PASS; 137 P1+P6 FAIL; 149 P3 FAIL. Urteil **`KL6_PROBATION_FAIL`**.
Was passiert ist: Die Probezeit urteilt sauber auf neuen Korrekturen (z. B. 8 gegen 2, 8 gegen 6), aber 8 neue
Korrekturen sind wenig: In Seed 137 endete die einzige Probezeit nach der Verschiebung 4 gegen 4 (REJECT), danach
lehnte schon die Worker-Prüfung jeden Kandidaten ab — kein Lernen. In Seed 149 (adaptive) gab eine Probezeit mit 6
gegen 4 einen Kopf frei, der auf dem großen Prüfsatz kurz schlechter war (0,925 -> 0,95 gesamt, aber unveränderte
Fragen −5,6 Punkte); der nächste stellte 1,00 her.

Bilanz der KL-Reihe (15 Seeds, alle vorregistriert): Mit Wort-Kanal + Gewichtung neuerer Evidenz lernt der
Routen-Kopf eine geänderte menschliche Vorliebe selbst — mit der alten Prüfung in 4/4 Seeds, mit den neuen Prüfungen
meist (KL3-Prüfung 6/9 Seeds voll), die Needle-Kontrolle nie (0–25 %). Keine der vier Freigabe-Prüfungen erfüllt in
allen Seeds zugleich „übernimmt immer“ und „nie ein kurzer Rückschritt“. Bei 8 Korrekturen je Runde ist das eine
statistische Grenze, nicht ein fehlender Schwellwert: weitere Schwellen-Varianten auf diesem Strom sind nicht sinnvoll.
Empfehlung: Standard bleibt aus. Nächster Hebel ist nicht die Prüfung, sondern mehr Evidenz je Entscheidung (längere
Ströme, Schlaf-Wiederholung als Prüfsatz) und die Übertragung auf neue Wortlaute (KL4, half_novel meist ≤ 0,375).
Grenzen wie KL1.
