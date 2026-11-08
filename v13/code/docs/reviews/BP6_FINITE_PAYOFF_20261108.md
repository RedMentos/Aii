# BP6: endliche aggregierte Nutzenwerte — 2026-11-08

Grundlage: PR #1593, exakter HEAD `27453db1b1fdce6561348762a763521fd790f4ca`. Eigener Review-Kandidat; nicht in `codex/resume-20261106` oder `main` integriert. Die Eltern #1589/#1592 bleiben eigenständige Abhängigkeiten.

## Befund und Änderung

Die bestehende Eingabeprüfung lässt große, aber endliche Kosten zu. Schon zwei Fehlantworten mit `wrong_cost=1e308` erzeugten `answer_all=-inf` und `gain=inf`. Auch die Abstentionssumme und die Differenz zweier endlicher Summen können überlaufen. `abstain_utility` weist jetzt nicht endliche Summen oder Differenzen mit `ValueError` ab. Wenn alle geprüften Zwischenwerte endlich bleiben, bleibt die bisherige Berechnung erhalten, auch für bewusst zugelassene vorzeichenbehaftete Kosten.

Ein Regressionstest prüft alle drei Überlaufstellen und einen großen, aber darstellbaren Kontrollwert. Auf der unveränderten Basis scheiterten alle drei Überlauffälle; nach der Änderung bestehen sie.

## Prüfung und Grenzen

Auf den exakt ausgecheckten Quelldateien: `PYTHONPATH=v13/code:v13/code/tests python -m unittest test_metaeff_abstain_guards test_metaeff_tie_invariance test_agi_metaeff test_bp6_metaeff_tie_reanalysis test_agi_live test_agi_solver test_growth` — 63 Tests bestanden. Das ersetzt die frühere Rekonstruktion aus PR #1593 nicht, sondern ergänzt sie um einen Test des echten Quellstands und der angrenzenden Konsumenten. `git diff --check` und Privacy-Scan gegen den Elternstand: CLEAN. Ein unabhängiger Review verglich 5.000 deterministische Fälle mit dem Elternstand; alle 3.353 akzeptierten Ergebnisse blieben gleich, 1.647 Überlauffälle wurden abgelehnt.

Softwareprüfung auf Linux; kein Modell-, Redmi-, Lern- oder Gate-Nachweis. Unabhängige Prüfung und Abgleich der abweichenden Branch-Abhängigkeiten vor einer Integration bleiben offen.
