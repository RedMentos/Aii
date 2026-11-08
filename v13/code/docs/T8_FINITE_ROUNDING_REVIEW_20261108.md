# T8: finite World-Model-Metriken beim Runden — 2026-11-08

Isolierter Kandidat auf PR #1601, Parent `2bc5cdef158b3831c1c1bc002c3c05d10b4835dd`. Die T8-Abhängigkeiten liegen auf dieser Review-Kette und werden nicht als bereits in `codex/resume-20261106` integriert ausgegeben.

NumPy kann einen endlichen sehr großen Wert beim Runden auf vier Nachkommastellen in Unendlich umwandeln oder unter strenger Fehlerbehandlung eine Exception werfen. Damit wurden zuvor gültig geprüfte R²- und Fehlerwerte nach der Prüfung nicht mehr endlich. Der Kandidat erhält das NumPy-Ergebnis für gewöhnliche Werte und verwendet beim Skalierungsüberlauf den ursprünglichen endlichen Float; nicht endliche Eingaben werden weiterhin abgelehnt. Training, Daten, Gates und Modellgewichte bleiben unverändert.

Die neuen Gegenfälle scheiterten auf dem Parent mit zwei FAIL und einem ERROR. Auf dem Kandidaten bestanden fünf neue und 54 bestehende gezielte und angrenzende Tests, darunter strikte NumPy-Fehlerbehandlung und JSON-Ausgabe ohne NaN/Infinity. Ein zusätzlicher unabhängiger Lauf der neuen, der Routing- und der Strict-FP-Tests ergab 9/9 PASS. Privacy-Scan gegen `5e9641465`: CLEAN.

Dies ist eine Softwareprüfung, kein Full-Suite-, Modell-, Redmi- oder Gate-Nachweis.
