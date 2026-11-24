# World-JEPA: fortgesetzter Trainingszustand in der gemeinsamen Runtime-Kopie

Stand 2026-11-11, Ausgangspunkt PR #1716 `c015f91c918cdda53fb460cf172947a4601d57d3`. **SHADOW / REVIEW ONLY**, keine Änderung eingefrorener produktiver Python-Dateien oder eines aktiven Modells.

## Problem und ausgeführter Pfad

Der bisherige `WorldJEPA.partial_fit()` führte Gewichte und EMA fort, erzeugte jedoch bei jedem Aufruf neue Adam-Momente, ein neues inverses Modell und neu gesetzte Zufallsfolgen. Der Checkpoint konnte diese verworfenen Werte folglich nicht wiederherstellen. Ein bloß zusätzliches Optimizerfeld im bisherigen Export hätte die tatsächliche Trainingsfortsetzung nicht repariert.

Der neue hashgebundene Builder `scripts/integrated_world_training_resume_candidate_20261111.py` erweitert die **bestehende** Kontext-/Archiv-/Feedback-/Body-/C3-/World-Kopie. Der einzige aktuelle Stager erzeugt jetzt diesen Stand. In der erzeugten `WorldJEPA.fit`-Implementierung werden vor Warm-start Modell und vollständiger Trainingszustand unter derselben Sperre getrennt kopiert. Fortgeführt werden:

- Gewichte des Encoders, des inversen Lernziels und sämtlicher Ensemble-Prädiktoren sowie das EMA-Ziel;
- Adam-Zähler und erste/zweite Momente des Hauptoptimizers und jedes Bootstrap-Optimizers;
- lokale PCG64-Zufallszustände für Haupttraining und Bootstrap;
- bestehende Kalibrierung, Schrittzähler und die bereits gebundenen Quellenquittungen.

Der tatsächliche Runtime-Pfad bleibt `:learning shadow → :growth jepa STEPS LIMIT → :growth jepa save → Runtime-Neustart → :growth jepa restore → weiterer Lernaufruf`. Updates verlangen weiterhin explizite menschliche Autorität, passenden Modus, keine Trainingspause, Leerlauf und überprüfte aktuelle sowie frühere Quellen. Beim Operator zeigen `optimizer_steps` und `optimizer_state_continued`, ob ein vorhandener Trainingszustand fortgesetzt wurde.

Alle neuen Arrays werden auf bekannte Schlüssel, exakte Shapes und float64, Endlichkeit sowie nichtnegative zweite Momente geprüft. Zähler sind echte begrenzte Integer, keine Booleans; ein Optimizer ohne Schritte darf keine Momente besitzen. Inverses Modell, Lernkonfiguration und PCG64-Zustände werden ebenfalls geprüft. Unbekannte Hooks/Objekttypen werden nicht kopiert. Validierung oder Gradient-/Commitfehler veröffentlichen keinen teilweise trainierten Zustand.

## Persistenz und Formatgrenzen

Die neuen numerischen Zustände liegen als zusätzliche Arrays und streng begrenzte JSON-Metadaten **im selben privaten NPZ-Artefakt** wie Modell und EMA. Der bestehende eine Generationszeiger bindet dessen Hash gemeinsam mit der vollständigen Quellenlineage. Quellen werden vor Speichern, Laden und weiterer Verwendung erneut geprüft. Die vorhandenen Quoten (128 MiB/128 Verzeichniseinträge, keine automatische Löschung) und active/previous-Generationen bleiben. `optimizer_state_persisted` ist bei dem neuen vollständigen Modell tatsächlich true.

Der Checkpointleser prüft Dateityp, maximale Größe und Dateiidentität mit einem begrenzten, nicht Symlinks folgenden Dateideskriptor. Vor `np.load(..., allow_pickle=False)` werden zusätzlich die deklarierten NPY-Shape-Allokationen mit den echten ZIP-Payloadgrößen verglichen. Ein kleiner Zip-Member darf keinen riesigen Tensorheader deklarieren. Gesamtgrenzen bleiben 32 MiB komprimiert/64 MiB dekomprimiert, maximal 512 bekannte numerische Mitglieder, Metadaten maximal 8192 Bytes. Das ist keine gemessene Redmi-RAM-Garantie.

Die World-Modellrevision heißt nun in der Testkopie `z12b-world-jepa-training-resume-v1`; der zusätzliche Zustand hat Schema `v13.world-jepa.training-state.v1`. Alte Gewichts-/Inference-Checkpoints werden nicht still zu vollständigen Resume-Checkpoints hochgestuft. Ihre alte Modellrevision wird zurückgewiesen, Dateien bleiben erhalten. Ein Modell ohne gebundenen Trainingszustand erhält beim Warm-start einen Fehler. Keine automatische Migration oder nachträglich erfundenen Momente. Diagnose-`history` wird beim Laden weiterhin nicht wiederhergestellt; der nächste echte Trainingsaufruf schreibt seine neuen Diagnosewerte.

Die bestehende Manifest-Veröffentlichung und deren Grenzen bleiben: Ein Fehler **nach** dem atomaren Publish kann bereits veröffentlicht haben, vorherige Auswahl lädt nur in den Speicher, vollständige Crash-/Verzeichnis- und Backup-Transaktionen beziehungsweise sofortiges Entlernen sind nicht nachgewiesen. Synchrone Quellenprüfung und Training halten die SQLite-Schreibsperre; Kosten und mobile Latenz sind offen.

## Geprüfter Vergleich und Reproduktion

Der neue Test erzeugt echte synthetische Runtime-Turns in SQLite, lernt zwei Schritte, speichert, lernt zwei weitere Schritte ohne Neustart und hält den vollständigen Stand fest. Anschließend startet er dieselbe Runtime neu, stellt den vorherigen Checkpoint wieder her und führt **denselben zweiten Zwei-Schritte-Aufruf** aus. Encoder, EMA, alle Prädiktoren, inverses Modell, Momente, Zähler, RNG, Kalibrierung und abschließende Diagnosewerte stimmen exakt; Quellenlineage ebenso. Er prüft außerdem, dass Encoder und inverse Parameter tatsächlich verändert wurden.

Das vergleicht dieselbe Folge von Aufrufen mit und ohne Neustart. Ein einzelner Vier-Schritte-Aufruf hat durch die bestehende Bootstrap-/Kalibrierungsreihenfolge eine andere Semantik als zwei Zwei-Schritte-Aufrufe; deren Gleichheit wird nicht behauptet. Der inverse Optimizer bleibt jetzt über Aufrufe bestehen, wodurch sich der Warm-start gegenüber dem alten Verfahren absichtlich ändert.

```bash
python v13/code/scripts/stage_integrated_candidate.py --output /tmp/v13-resume-review-new
cd v13/code
python -m pytest -q -s tests/test_world_jepa_training_resume_stage_20261111.py
python -m pytest -q -s tests/test_staged_integrated_regression_20261111.py
```

Builder-SHA-256: `82e2fd27712d17a489ce5fd2f75d749f3f0e08dcc9d7fcc8852bbe6f738e8e18`. Erzeugte lokale Reviewkopie `/workspace/shared/v13-world-training-resume-review-20261111`, 326 anfängliche Dateihashes. `world_jepa.py` und `world_jepa_shadow_checkpoint.py` werden ausschließlich dort ersetzt, zusammen mit explizit neu gebundenen Guard-Pins.

Geschlossene lokale Prüfung: Vorher **10 FAIL / 1 PASS** im neuen inneren Resume-Testpaket auf dem alten Stager; danach **11 PASS**. Der abschließende gezielte Lauf aller sechs Staging-/Runtime-Dateien besteht mit **13 äußeren Tests**, darin 15 Kontextfälle und 11 Resume-Fälle. Rohlogs einschließlich des roten Ausgangs werden unverändert mit SHA-256 unter `proofs/world-training-resume-20261111/` gesichert. Das rote Rohlog ist vor verlustfreier Kompression Privacy CLEAN geprüft (`before.log.gz`, entpackter SHA-256 `e1220bead55762a8e2278b01de3b00d251fb82084e850dc5fbde6d92a73368ee`). Der abschließende gemeinsame Auswahl-Lauf einschließlich vorhandener World-Kerntests ist mit **415 PASS / 3 CUDA SKIP / 58 Untertests PASS** geschlossen (ein äußerer Test PASS). Davor 385 PASS / 3 SKIP / 35 Untertests ohne diese Ergänzung. Die Remote-CI wird erst nach tatsächlichem Abschluss eingetragen.

Die zwei alten Tests für Save-/Restore-Metadaten prüfen nun abhängig vom tatsächlich vorhandenen Trainingszustand den entsprechenden Persistenzstatus; alte Builder ohne diesen Zustand müssen weiterhin false liefern. Zusätzlich prüfen die neuen Fälle reale Arrays über Neustart, Mutationsfreiheit bei ungültigen Momenten/Zählern/RNG/Objective, echte Gradientenfehler und Ablehnung eines gefälschten riesigen NPY-Headers **vor** dem NumPy-Lader. Die vorhandene atomare Fit-Prüfung vergleicht jetzt auch verschachtelte Array-Dictionaries vollständig und rekursiv. Gradienten-/Lerneffektkontrolle, Fit-Input-/Stale-Fit-/Read-Snapshot- und bestehende Checkpoint-/Incremental-/Online-Experimente sind im abschließenden gemeinsamen Lauf enthalten. Keine Fehlerschranke entfernt.

## Noch offene Arbeit

Feste unabhängige Holdout-Ziele, Retention, Replay-off/No-signal-Kontrollen und mehrere Seeds für Lernnutzen bleiben offen. Der übernommene #1737-Holdoutwert vergleicht noch ein mitbewegtes EMA-Ziel und verlangt keine Verbesserung. Exakte Original-Vollsuiten #1737/#1742 bleiben RED; ausgewählte Softwaretests ändern diese Befunde nicht.

Als Nächstes reguläre Body-JEPA-Trainerauswahl und tatsächlichen Organ-Consumer verbinden, dann Replay/Sleep und langsamen Dataset-/Gesprächs-Idle-Pfad unter Ressourcen- und Quellenregeln. Der Selbstoptimierungs-/Cross-Organ-Nachtrag bleibt zusätzlicher offener Umfang; dieser Schritt weist die Fortsetzung des eigenen kleinen World-Modells nach, keine organübergreifenden Updates oder strukturelle Selbständerung. Langer effizienter Speicher bleibt wegen SQLite-Textduplikaten und fehlender Gesamtkonsolidierung offen. Kein Native-/Redmi-/AGI-/Utility-Nachweis. SourceHandoff-Freeze, Age und alle negativen Gates sowie beide Gesamtflags bleiben unverändert.
