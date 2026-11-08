# AG4-Gegenprüfung: Bewertungen und Fertigkeitszähler

Review-Kind von #1611, Basis `a9753b8edd2db7bae6cecacc0778754bae468932`. Der ursprüngliche #1611-Actions-Lauf `42483315056` bleibt **RED**: neun Tests, sechs Fehler. Der Test-Store verlangte bei `expected=None` fälschlich einen CAS-Vergleich; außerdem war der Patchpfad für `agi.maturity` falsch. Der Test verwendet nun den echten Runtime-/SQLite-Store und prüft einen tatsächlichen Neustart.

## Gegenbeispiele und Korrektur

Fünf neue Tests liefen auf der ursprünglichen Quelle zunächst **5/5 FAIL**, danach nach den Änderungen grün:

1. Ein `IMPLICIT_CHAT`-Heuristikwert wurde in AG4 wie eine ausdrückliche Note angerechnet. Der Aufrufer übergibt die Herkunft; nur `EXPLICIT_NOTE` fließt in den neuen menschlichen AG4-Ratingpfad. AG9 behält seinen bestehenden Herkunftspfad und benötigt dort weitere Arbeit.
2. Nach `reopen()` oder einer Beförderung konnte die Korrektur eines früheren positiven Belegs den auf null gesetzten Erfolgszähler des neuen Abschnitts auf -1 setzen. Jeder Abschnitt erhält eine eigene Zählerepoche; Korrekturen ändern nur einen Zähler derselben Epoche.
3. Nach Stilllegung und Neuerstellung einer gleichnamigen Fertigkeit konnte ein alter Beleg deren Zähler ändern. Die beim Routing gespeicherte Bindung unterscheidet die konkrete Fertigkeitsinstanz.
4. Ein Fehler der AG9-Metakognition übersprang die AG4-Ratingverarbeitung. Beide Teilpfade laufen getrennt; das gilt auch für die AG9-Behandlung bei einer Faktkorrektur.

Die Bindung aus Fertigkeitsinstanz und Zählerepoche wird beim normalen wie automatischen Routing im Ereigniszustand gesichert, nicht erst bei der späteren Bewertung geraten. Eine erste verspätete Bewertung nach einem Reset wird zwar einmal im Ledger erfasst, zählt aber nicht als Erfolg des neuen Abschnitts. Fehlende Ereignisbindungen, alte Ledgerbelege ohne Bindung und Bindungen an eine andere Instanz werden für den neuen AG4-Pfad abgewiesen; die gespeicherte Note bleibt erhalten. Eine echte Runtime mit synthetischer C3-Ausgabe prüft Routing, FINAL ohne Erfolgsanrechnung, ausdrückliche Note, Doppelzustellung, Neustart und spätere Korrektur.

97 gezielte und angrenzende Tests bestanden lokal: `PYTHONPATH=.:tests python -m unittest test_ag4_human_outcome_review_20261108 test_agi_live_human_skill_outcome_20261108 test_agi_live test_inputs test_skilllive test_skilllive_crossskill_conflict_20261029 test_skilllive_multistep_route_review_20261029 test_skilllive_jef_route_correction_20261030 test_growth test_agi_solver test_agi_trainers`. Dies ist keine vollständige Suite und kein nativer Modelllauf.

## Grenzen und nächste Schritte

- Die bisherigen AG4-Zähler können bereits durch technische FINAL-Zustände verunreinigt sein; aus den vorhandenen Aggregaten lässt sich die Historie nicht zuverlässig rekonstruieren. Zähler und bisherige Stufen brauchen eine quellengebundene Migration/Quarantäne und Überprüfung. Alte Belege ohne die neue Bindung dürfen nicht still umgedeutet werden.
- `skilllive.after_turn` vergibt im separaten Shadow-Parity-Pfad weiterhin `record(..., True, parity=...)` auf FINAL. Routenparität ist kein semantischer Qualitätsnachweis; deren getrennte Erfassung und Beförderungswirkung sind vor Integration zu überprüfen. Der vorliegende Fix betrifft die direkt geroutete Fertigkeit.
- Die Ratingzustellung und die spätere AG4-StateBox-Änderung sind nicht eine Transaktion; ein Crash kann einen Zustellversuch auslassen. Herkunft, Rating und F5-Quellen werden beim Update noch nicht atomar erneut geprüft, eine Widerruf-/Retention-Strategie fehlt. Fact-Korrektur und spätere Bewertung können sich zudem widersprechen; ihre Priorität und Replay-Reihenfolge brauchen eine beleggebundene Regel. `memory.feedback` übergibt bisher seine `learning_permission` nicht an `agi.live.on_feedback`.
- Die AG9-Receipt-Deduplizierung ist begrenzt und kann eine korrigierte Note nicht zurücknehmen; sie ersetzt keine quellengebundene Kalibrierhistorie. Ein Fehlerlog darf nicht als Zustellbeleg gelten.
- #1612 ist ein **separater** Feedback-/Gedächtniszweig. Dessen `inputs.record_rating` hat eine andere Fanout-Implementierung; die Herkunftsweitergabe und Transaktions-/Zustellsemantik müssen bei einer späteren Zusammenführung geprüft werden. Kein fremder Branch wurde überschrieben.
- Die AGI-/Skill-/Input-Dateien werden nur in diesem Review-Zweig geändert. Vor Nutzung für eingefrorene SourceHandoff-Kohorten braucht es einen passenden quellhashgebundenen Kandidaten sowie die vorhandenen Gates. Kein natives Modell, Redmi, Modellgewicht oder nachgewiesener Antwortnutzen; STEP2/B3/JEPA- und Full-Suite-Status bleiben unverändert.
