# Teil-Gegenprüfung BP5 / BP9a — 2026-11-06

Basis: Claude PR #1587, `claude/project-thread-ggf5qt`, Commit
`7f0158d223fefe5bb218ddccab6bf79dbbc44fb7`. Die Arbeit auf diesem
eigenen Prüfzweig ist **keine vollständige Prüfung oder Integration** aller
Änderungen des PR. Sie berührt keine laufende native Messung und aktiviert
keine Funktion für Nutzer. Der jüngste GPT-Zweig und dieser Claude-Zweig sind
auseinandergegangen; sie wurden nicht zusammengeführt.

## BP5: numerische Vorabprüfung

Am Original lieferte `b3pair.precheck` bei `NaN` für L1 oder L2, bei L1=1,5
und bei einem schlechteren oder gleichen L1 gegenüber SCALAR `GO`. Letzteres
widerspricht der Vorbedingung im BP5-Befund. Der bisherige Python-Pfad hat
keinen gefundenen Laufzeit- oder Skript-Aufrufer; ein aktiviertes produktives
Tor ist daraus nicht belegt.

Auf diesem Prüfzweig verweigert die Funktion fehlende, nichtnumerische,
nichtendliche und außerhalb von 0–1 liegende Genauigkeiten sowie ungültige
Zeilenzahlen. L1 muss auch den SCALAR-Punktwert übertreffen; das ist kein
statistischer Signifikanz- oder Replikationsnachweis. `GO` bleibt eine rein
numerische Vorabprüfung: Sie überprüft weder Manifest und Modellrevisionen noch die
Unabhängigkeit der Saaten, das L2-Tor oder die Freigabe für L3. Keine dieser
Voraussetzungen ist hiermit erfüllt.

Eine zweite Gegenprobe fand, dass `verify()` manipulierte `row_sha256`-Werte
nicht prüfte, obwohl `disjoint()` diese Werte vergleicht. `verify()` bindet
jetzt auch sie und die Manifest-Revision an den neu berechneten Inhalt. Der
Vergleich zweier verifizierter Manifeste schließt damit nur identische
Zustandspaare aus; er beweist weder verschiedene Texte noch unabhängige Saaten.

Die neuen Gegenproben in `code/tests/test_b3pair_review_gate.py` ergaben vor
der Korrektur 21 fehlgeschlagene und 15 fehlerhafte Teilfälle; danach:
`cd v13/code && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:tests python -m unittest discover -s tests -p 'test_b3pair*.py' -v`
→ 11 Tests bestanden. Das ist ausschließlich ein Softwaretest.

Vollständige Software-Suite nach der letzten Codeänderung:
`cd v13/code && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:tests V13_NO_AUTOSTART=1 NO_MODEL_DOWNLOADS=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 python -m unittest discover -s tests -p 'test_*.py'`
→ 1887 Tests, ein Fehler und 14 Skips. Der Fehler
`test_toolforecast.CheckpointTests.test_competence_check_scores_states_not_calls`
entsteht durch `PermissionError` beim Prüfen des hier nicht lesbaren Pfades
`/root/native/restore/round8-note-tool-raw`. Kein vollständiger Suite-PASS;
kein Modell- oder Redmi-Nachweis.

## BP9a: gemessene Werte nicht mit fehlenden Werten verwechseln

Die drei Originaldateien `bp9a-seed{1,2,3}.json` enthalten für den Arm
`no_own`, `recall_by_group.own_wrong`, jeweils `null`. Die dort weggelassene
Gruppe hat keinen ausgewiesenen Null-Recall. Der archivierte Bericht trägt
deshalb oben eine Korrektur; Tabelle und Schlussfolgerung sind entsprechend
präzisiert. Der ursprüngliche Text bleibt im Basiscommit erhalten; die Rohdaten
wurden nicht geändert. `BP9a_FAIL` bleibt unverändert; die spätere
Nah-Fehlgriff-Zahl ist kein vorregistrierter Nutzennachweis.

## Offen

Vollständigen Unterschied der beiden Entwicklungszweige und alle weiteren
Änderungen des Claude-PR separat prüfen. Historische Quellbindungen und
fehlgeschlagene oder nicht gemessene Gates nicht ändern. Keine neue Aussage
zu STEP2, B3-L3, Body-JEPA, Android oder kontinuierlichem Lernen.
