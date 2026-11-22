# WP-Z11d Befund: STEP4 Referenz-Lehrer, vierter Versuch — `STEP4_EXIT_PASS`

Vorregistriert in `PREREG.md` (vor dem Lauf committet und gepusht). Frischer Seed 31, Leck-Prüfung v3 auf Wort-Ebene.
Daten `v13/bench-results/z11d-reference-teacher-20261026/`.

T1 60/60, T2 0 Lecks, T3 60/60, T4 10/10, T5 20/20, T6 PASS → **`STEP4_EXIT_PASS`**.
Beschreibend: Self 38/60, Lehrer 41/60, Lehrer besser 11, schlechter 8; Lehrer 33 s, Self 10,5 s je Aufgabe.

Einordnung (ehrlich): Erst der vierte vorregistrierte Versuch ist grün. Z11, Z11b und Z11c bleiben FAIL. Was sich
zwischen den Versuchen geändert hat, war nie der Lehrer-Weg der Runtime, sondern (1) ein echter Fehler im
Fingerabdruck (behoben in `v13/memory.py`), (2) der Messaufbau (Auswahl erst nach allen Antworten) und (3) die
Leck-Prüfung, die zitierte eigene Sätze als Lehrer-Text zählte. Jeder Versuch lief auf frischen oder gleichen Aufgaben
mit vorher festgelegter Regel; keine Schwelle wurde gesenkt. Weil die Prüfung zwischen Z11b und Z11d geändert wurde,
ist dieses PASS ein Ergebnis für genau diese Prüfung auf Seed 31, kein Beweis für alle Aufgaben.
Der Lehrer ist als Referenz nur wenig besser als Self (+3 Aufgaben) und dreimal so langsam; STEP5 („Lehrer-besser-Fälle
verbessern später Self ohne Lehrer im Kontext“) ist nicht Teil dieses Pakets.
Grenzen: ein Seed, generierte englische Aufgaben, Regex-Prüfung, Cloud.
