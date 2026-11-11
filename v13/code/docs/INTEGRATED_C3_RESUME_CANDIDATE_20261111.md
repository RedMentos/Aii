# C3-LoRA: gebundene, fehlersichere Wiederaufnahme — 2026-11-11

## Ausgangsfehler und Kandidat

Auf #1663 `95aea15a046e73acf82c67ccf934cebda651ef87` akzeptiert die bestehende Metadatenprüfung auch ein leeres oder nichtfinites Optimizer-Dictionary. Bei einem Fehler in `optimizer.load_state_dict` wurden Adaptergewichte bereits geladen; ein nichtfiniter Adam-Moment vergiftete den nächsten Schritt. Das ursprüngliche Gegenbeispiel `review_integrated_learning_modes_20261110.py` bleibt unverändert.

`scripts/integrated_c3_resume_candidate_20261110.py` ergänzt in der gemeinsamen, hashgebundenen Body-/World-Testkopie den C3-Eintritt `LoraTrainer.fit`. `lora_resume_atomic_candidate.py` prüft vor einer Mutation:

- Bindung an vollständigen Master-Gewichts-SHA, Basisgeneration, sämtliche übergebenen Items einschließlich Gewicht, Anker, Probes und Konfiguration. Fehlende Bindung, alter ungebundener Checkpoint und veränderte Daten werden abgelehnt und die bestehende Datei nicht gelöscht.
- Namen/Reihenfolge der trainierbaren Adapterparameter und AdamW-Gruppen; gültige IDs, Shapes, Dtypes, endliche Momente und nichtnegative zweite Momente sowie Schrittzähler. Adaptergewichte und Verlauf werden ebenfalls geprüft.
- Sowohl den separaten Shuffle-Generator als auch den CPU-Torch-Zufallszustand vor ihrer Wiederherstellung. Bei anschließend injiziertem Ladefehler werden Adapter, Optimizer und Torch-Zustand zurückgesetzt; scheitert das Zurücksetzen, wird der Optimizer als unbenutzbar markiert.

Der Master-SHA ist im regulären `_load` an `model.safetensors` gebunden; der Checkpoint-Hash beweist weder ein aktuelles SourceRef-Recht noch die Unveränderlichkeit aller Tokenizer-/Konfigurationsdateien. Der Kandidat ist ausdrücklich auf den CPU-Torch-Pfad beschränkt. Der globale Torch-RNG ist pro Prozess geteilt: Exakt reproduzierbare Fortsetzung setzt voraus, dass andere Threads nicht gleichzeitig denselben RNG verändern. Kein tatsächlicher Nutzerinhalt wird im Beleg gespeichert.

## Test und Einordnung

`/tmp/v13-online-review-venv/bin/python -m pytest -q -s v13/code/tests/test_integrated_c3_resume_candidate_20261110.py`: **2 äußere Tests PASS, 162 Tests PASS und 3 CUDA SKIP** auf einer gemeinsamen C3-/Body-/World-Testkopie. Die Mock-Grenzen der älteren World-Synthetiktests bleiben wie in `INTEGRATED_PREDICTOR_HISTORY_GUARD_20261110.md` offengelegt.

Mit einem winzigen synthetischen Torch-/PEFT-GPT2 wurde ein tatsächlicher C3-LoRA-Lauf nach einem von zwei Schritten unterbrochen und anschließend fortgesetzt; Adapterparameter und Loss-Verlauf stimmen exakt mit dem ununterbrochenen Lauf überein. Manipulierte Momente, Form, IDs, Gruppen, RNG, Herkunft, Gewicht und Generation werden abgewiesen; injizierte Ladefehler lassen Adapter/Optimizer unverändert bzw. markieren fehlgeschlagene Recovery. Ein weiterer Test nutzt den echten SQLite-`WeightConsolidation.stage`-/`train_and_gate`-Weg, der einen winzigen synthetischen C3-Trainer aufruft und den Kandidaten ohne Evaluator im Status `TRAINED` belässt; keine Aktivierung. Das GGUF im Test ist ein Platzhalter.

Der erste Tiny-C3-Restartvergleich war **11 PASS / 1 FAIL**: bei nur gespeichertem Shuffle-RNG wich der zweite Loss vom ununterbrochenen Lauf ab. Dieser negative Befund führte zur zusätzlichen Speicherung des CPU-Torch-RNG; erst der oben genannte erneute Test bestand. Keine Aussage zu echten C3-Mastergewichten, Redmi, Native, Lernqualität, Vergessen oder abgeschlossenem Nutzerziel.

Die bestehende C3-Speicherung nutzt weiterhin `torch.save` auf einer temporären Datei mit anschließendem `os.replace`; Größenbegrenzung vor `torch.load`, vollständige Crash-/fsync-Dauerhaftigkeit, gleichzeitige nichtkooperierende Dateischreiber, aktuelle Source-Widerrufsrechte und Finitheitschecks **während** jedes Trainingsschritts sind offen. Legacy-Checkpoints werden in dieser Testkopie nicht automatisch migriert. Für Body-JEPA fehlt weiter der reguläre Organ-Auswahlpfad; Memory-/Archiv-/Idle-Integration folgt. Original-Runtime und SourceHandoff bleiben unverändert; #1663-Vollsuite ist weiterhin RED, STEP2 `UTILITY_FAIL` und B3 L1 `FAIL` bleiben.
