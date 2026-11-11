# B1/B2 Body-JEPA im gemeinsamen Runtime-Lernpfad

Ausgangspunkt `01890c92de9e0b3638899b2e2ecf4c8a84d1fac2`, PR #1716. **Review-/Testkopie**, SourceHandoff-Produktivquellen unverändert. Neuer aktueller Builder: `scripts/integrated_body_role_candidate_20261111.py`, SHA-256 `41e08c932535bb450c0f031a2fdea5511f588d1d2be8abdcccd9c65044d6eef0`. Er erweitert dieselbe vorhandene World-/Resume-/Kontext-/Archiv-/Feedback-Kette.

## Tatsächlicher Pfad

`Runtime-Turn → ausdrückliche menschliche fact/preference-Korrektur mit learn → geprüfte F1/F5-/Feedback-/USER-Quellen → rollenbezogener AG6-Batch → SourceBoundBodyTrainer/BodyJepaTrainer → echte kleine Torch-/EMA-Schritte → privater Checkpoint/Adapter → Evaluation → gesonderte menschliche Freigabe → vorhandene rollenbezogene AdapterRegistry/Runner-Argumente`.

Die neue Auswahl ist standardmäßig aus und getrennt von den vorhandenen C3-Einstellungen gespeichert. Beispiele in der erzeugten Kopie:

```text
:learning shadow
:growth trainer body-jepa B1_DETAIL /path/to/b1-master
:growth trainer body-jepa B2_GIST /path/to/b2-master
:growth trainer cfg max_steps=2 checkpoint_resume=true
:growth consolidate
:growth trainer lora
```

Jede Rolle benötigt ihren eigenen gebundenen Master, die passende installierte GGUF-Datei und den vorhandenen Evaluationsrunner. Fehlende Abhängigkeiten/Architekturprüfung ergeben einen ehrlichen nicht bereiten Trainer. C3-Master und C3-Regler werden beim Body-Wechsel nicht überschrieben. Nach Neustart werden die gespeicherte Rolle und ihr bestehender Batch wieder installiert. Ein Wechsel zurück zu lora/sparse/auto/none deaktiviert die Body-Auswahl.

AG6 verwendet für B1 und B2 eigene Zustandskeys einschließlich Batchhistorie, Konsolidierungsmenge, Freigabejournal und Recovery. C3 behält seinen bisherigen Key. Rolle und Trainerbindung gehen in den Body-Dataset-Hash ein und werden vor Training geprüft. Gate und beide Freigabetransaktionen prüfen die Zielrolle erneut; die Freigabequittung bindet die Rollenfelder. Damit kann ein B1-Batch nicht durch Wechsel oder nachträgliche Änderung seiner Trainerrolle als B2 freigegeben werden.

## Quellen und Grenzen

Die Body-Route verwendet den bestehenden `Memory._verified_rows`-Prüfer mit begrenzten ereignisbezogenen Evidenzabfragen. Zusätzlich sind eine konsistente gespeicherte **learn**-Freigabe und die originale USER-Eingabe als Abhängigkeit notwendig. Nur gespeicherte record-Korrekturen werden nicht aufgenommen. Die erste angeschlossene Route verarbeitet direkte fact/preference-Ziele; implizite Ratings, SDFT-Ziele ohne Antwort und universelle Stilregeln werden hier nicht still umgedeutet. Diese weiteren Lernarten bleiben eigener offener Umfang.

Maximal 32 Items, ein Suchfenster von 256 passenden Erinnerungen, 128 Evidenzzeilen je Klasse und begrenzte Text-/JSON-Präfixe. Replay-Zulassung und die vorhandene AG12-Holdoutprüfung bleiben. Beim Training werden Modus, Trainingspause, Ressourcen, Warteschlange, Age, Rollenwahl und Quellen vor Modellladen, je Schritt und vor Veröffentlichung erneut geprüft. Der tatsächliche Scheduler-Consumer benötigt ein vorhandenes DISPATCHED-Consolidation-Ereignis; er täuscht keine menschliche Autorität vor und setzt Runtime.current nicht künstlich auf idle.

Der Startwert sind höchstens zwei Schritte; konfigurierbar bis acht, mit kooperativem 20-Sekunden-Budget. Modellladen/Datei-I/O lassen sich dadurch nicht hart unterbrechen. Während schwerer Fits wird keine dauernde SQLite-Schreibtransaktion gehalten. Widerruf/Abbruch kann einen privaten Zwischencheckpoint hinterlassen, aber kein TRAINED-Ergebnis veröffentlichen; eine weitere Nutzung muss die Quellen erneut prüfen. Sofortiges Unlernen und vollständige physische Bereinigung sind nicht nachgewiesen. Die alten allgemeinen C3-Kandidaten benötigen noch dieselbe vollständige learn-/F1/F5-Admission-Reconciliation; der neue globale train-Check verhindert bereits den Wechsel zu RECORD_ONLY nach dem Staging.

Der abgeleitete Body-Trainer führt jetzt den übergebenen Evaluator tatsächlich aus, schließt ihn und liefert dessen Report an AG6. Ohne Evaluator bleibt ein Ergebnis TRAINED, ohne Adapteraktivierung. Master-/Config-Dateien und der zum Trainieren/Evaluieren gewählte Modellhash sind gebunden. Reale native B1/B2-Qualität, rollenbezogene unabhängige Retention und adapterabhängige Bridge-Rekalibrierung bleiben offen. Der normale rollenbezogene Registry-/Runnerpfad wird wiederverwendet; kein neuer Shadow-Serving-Mechanismus.

## Geschlossene lokale Evidenz

- **15 neue Body-Fälle PASS**, ein äußerer Stage-Test PASS. Tatsächliche SQLite-Runtime-Turns/F5-Korrekturen, Operatorwahl, getrennte B1-/B2-Torch-Updates mit gemessenem Parameterdelta und EMA, echter Scheduler-Job, Wiederöffnung der Runtime und anschließendes Trainieren, Record-only/Pause/Cancel, erneute Quellenprüfung, Widerruf nach einem echten Schritt, gespeicherte C3-Konfiguration, Zielrollentausch, explizite Freigabe und Rückrolle.
- **473 PASS / 3 CUDA SKIP / 58 Untertests PASS** in derselben Stage, einschließlich zusätzlicher bestehender AG6-Approval-/Widerrufs-/Rollback-/Sparse-Tests. Vor der letzten Erweiterung 430 PASS; Rohlogs bleiben getrennt.
- Echter Stager-/Manifest-/Compile-Smoke: **9 PASS**.
- Testmaster/GGUF-Dateien und Export sind ausdrücklich synthetische Marker; `_load` nutzt einen tatsächlichen kleinen GPT-2/PEFT-Trainingslauf. Native Modellverfügbarkeit/Architektur werden nur im Test ersetzt. Die Freigabe-/Serving-Prüfung nutzt einen klar gekennzeichneten synthetischen Evaluator und prüft Registry/Runner-Argumente, keine echten nativen Tokenausgaben. Daraus folgt kein Native-/Redmi-/Utility-Beweis.

Die ersten beiden fehlgeschlagenen Testanläufe verwendeten einen unvollständigen Fake-ModelManager, der M_EMBED mit KeyError statt der normalen Unavailable-Semantik beantwortete. Ein späterer Builderlauf scheiterte vor Ausführung an einem nicht-ASCII-Bytesliteral. Fehler wurden repariert; Original-Logs werden vor Kompression auf Privacy geprüft und unverändert erhalten. Quellen, Rohlogs, Manifest und SHA-256 stehen unter `proofs/body-role-runtime-20261111/`. Remote-CI auf Code-HEAD `bb1a94ca4d5b123640dff4574095f1d047f94846` abgeschlossen: exakter Push `43015808657` und PR-Merge `43015814118` (Checkout `8d5b19a`), jeweils beide Jobs SUCCESS; 473 PASS / 3 SKIP / 58 Untertests und 13 äußere Minimal-Stack-Prüfungen. Original-Joblogs und CI_RESULT.json sind SHA-gebunden gespeichert.

```bash
cd v13/code
python -m pytest -q -s tests/test_body_role_runtime_stage_20261111.py
python -m pytest -q -s tests/test_staged_integrated_regression_20261111.py
```

Lokale erzeugte Kopie: `/workspace/shared/v13-body-role-current-review-20261111`, 327 anfängliche Dateihashes. SourceHandoff, Age, STEP2 UTILITY_FAIL, B3 L1 FAIL und Body-JEPA UNAVAILABLE sowie beide Gesamtflags bleiben unverändert. Nächste Arbeit: vollständige C3-Consent-Admission und den vorhandenen Idle-/Sleep-Datenverbrauch schließen, feste Holdout-/Retention-Ziele und Ressourcen nachweisen; der Selbstoptimierungs-/Cross-Organ-Nachtrag bleibt verbindlich offen. Ein Git-Zwischenstand beendet diese Arbeit nicht.
