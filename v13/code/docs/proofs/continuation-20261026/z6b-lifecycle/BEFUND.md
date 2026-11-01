# WP-Z6b Befund: §24.32 Lern-Lebenszyklus — `Z6B_LIFECYCLE_ADAPTIVE_FAIL`

Vorregistriert in `PREREG.md` (vor dem Lauf committet und gepusht). Daten `v13/bench-results/z6b-lifecycle-20261026/`.
Echter Routen-Kopf-Lerner, Seed 71, 48 + 32 Korrekturen, Held-out 40 Fragen.

| | none | fixed | adaptive |
|---|---|---|---|
| Shadow-Jobs | 0 | 10 | 8 |
| unnötige Updates | 0 | 3 | 3 |
| Freigaben (= Freigabe-Last) | 0 | 5 | 3 |
| falsche Freigaben | 0 | 1 | 0 |
| Held-out Ende Phase 1 | 0,35 | 0,85 | 0,85 |
| Held-out Ende | 0,55 | 0,65 | 0,65 |
| Hälfte-Fragen nach Verschiebung | 1,00 | 0,00 | 0,00 |
| record-only Updates | 0 | 0 | 0 |

Kriterien: **C1 FAIL** (adaptive 3 unnötige Updates = fixed 3), C2 PASS, C3 PASS (0 vs. 1), **C4 nicht gemessen**
(Fehler der Bench: ein Kommentar hat die Zuweisung des Rücknahme-Ergebnisses verschluckt; die Rücknahme lief, ihr
Ergebnis wurde nicht festgehalten, die Prüfung hat das leer als bestanden gezählt; behoben im Skript für spätere Läufe),
C5 PASS, C6 PASS. Urteil **`Z6B_LIFECYCLE_ADAPTIVE_FAIL`**.

Wichtigster Befund: **Der Lerner kann neue menschliche Evidenz nicht übernehmen (L11 Wiederöffnen bleibt stecken).**
Nach der Verschiebung (Nutzer will „Hälfte von X“ jetzt als `simple`) scheiterten in beiden lernenden Armen alle
4 Kandidaten an der eingebauten Prüfung (EVALUATED_FAIL); die Hälfte-Fragen blieben bei 0 %. Ursache im Worker
(`v13/learning_worker.py`): Training und Prüf-Split enthalten die alten Labels (Hälfte → detail) und die neuen
(Hälfte → simple) gleichzeitig; die Behalten-Prüfung je Klasse verbietet jede Verschlechterung der alten Klasse. Es
gibt keinen Weg, mit dem neuere Korrekturen ältere widersprechende ersetzen. Ironie: das starre Gerüst ohne Lernen
(`none`) routet die Hälfte-Fragen richtig.
Weitere Befunde: adaptive spart 2 Shadow-Jobs und 2 Freigaben, aber nicht die unnötigen; die eine falsche Freigabe
von fixed vermeidet adaptive. Keiner erreicht in Phase 1 90 % (höchstens 85 %).

Nächster Schritt (neu vorregistrieren): „Ersetzen“ für Korrekturen (neuere menschliche Korrektur zum gleichen Muster
ersetzt ältere im Trainings- und Prüfsatz, mit Herkunft und Rücknahme) und Rücknahme-Messung (C4) im selben Lauf.
Grenzen: nur Routen-Kopf, generierte deutsche Umschreibungen, ein Seed, Mensch durch Regel ersetzt, Cloud.

Nachtrag (Diagnose nach dem Lauf, Dev-Seed 3, ändert das Urteil nicht): Ein automatisches „Ersetzen nach Ähnlichkeit“
geht mit den Needle-Embeddings nicht. Roh-Kosinus liegt zwischen allen Fragearten bei 0,95–0,98 (Hälfte↔Hälfte Median
0,965, Hälfte↔detail bis 0,984); auch zentriert trennt er nicht (Hälfte↔Hälfte Median 0,03, Hälfte↔detail bis 0,51).
Ersetzen muss deshalb ausdrücklich vom Menschen kommen (z. B. „gilt ab jetzt für alle Hälfte-Fragen“, fest gelesen wie
die Nutzer-Regeln) oder über Aktualität (neuere Korrekturen schwerer, alte widersprechende aus dem Prüfsatz), nicht
über Embedding-Nähe.
