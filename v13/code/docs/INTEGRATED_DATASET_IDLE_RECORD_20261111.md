# Lokaler Dataset-Consumer mit eigener Quellenherkunft

Die gemeinsame Reviewkopie erweitert den Idle-Stand `7d66b22557baea7368611d38657224e84fe5ae60` über `scripts/integrated_dataset_idle_candidate_20261111.py` (SHA `8d18f9fcde0eac79442dceb16544e747b6baa4e7edc07436ef131b889d288282`). Frozen-Produktionsquellen bleiben unverändert. Dataset-Helper SHA `a460cd843a9f1fd05d6039f2743df44d13289684e938aff1d3c94b0cf08c1228`.

Ein tatsächlicher G13-/Sleep-Job nimmt eine bereits lokal vorbereitete Vorschauzeile aus dem vorhandenen gepinnten Katalog auf. Default OFF. Der Bediener wählt Repositoryansicht, konkrete Offsets, ein Textfeld und engere Quoten; diese Auswahl bindet Katalog, Revision, Split, Zeilen-/Feld-/Dateihash sowie lokale Dateiidentität. PROBE erlaubt hier nur die begrenzte Aufnahme einer Vorschau. HOLD, Test-/Eval-Ansichten, veränderte Auswahl oder Dateien erhalten keine stillschweigende Zulassung. Katalog-Lizenzmetadaten sind kein verifizierter Trainingslizenzbefund.

Der Consumer ruft ausschließlich `read_staged` auf. Er lädt keine Daten herunter und startet keinen Trainer. Die Quelle erhält `kind=EXTERNAL_DATASET`, einen echten vollständigen SourceRef und einen eigenen unveränderlich gebundenen Aufnahmebeleg. Er erzeugt keine USER-Ereignisse, Erinnerungen, Feedbackzeilen oder fingierten menschlichen Lernentscheidungen. Aufnahme bleibt PREVIEW_ONLY mit `training_authority=0`, auch in RECORD_ONLY und bei pausiertem Training. Globale Pause, Stop/Cancel, Vordergrund/Warteschlange, Ressourcen, Mindestleerlauf für SYSTEM-Jobs und vorhandene Schedulergrenzen bleiben bindend.

Pro Job höchstens eine kleine Zeile. Defaults: 8192 Byte pro Textfeld, acht reservierte Versuche/128 KiB pro UTC-Tag, insgesamt 64 Versuche/1 MiB sowie 300 Sekunden Abstand/Leerlauf. Harte Obergrenzen sind 16 KiB je Feld, 32 Tagesversuche, 256 Gesamtversuche, 8 MiB Gesamtbelastung, 16 ausgewählte Offsets pro Grant und 16 Grants. Versuch und Text-/Belegkosten werden vor Dateikonsum dauerhaft belastet; Fehler und spätere Widerrufe erstatten nichts. Eine globale Quotenerhöhung erweitert einen alten Grant nicht. Metadaten bleiben auf 256 KiB begrenzt.

Diese Kostenbilanz umfasst aufgenommenen Payload und Belege einschließlich gescheiterter Veröffentlichungsversuche. Bereits vorhandene Vorschauen, SQLite-/WAL-Seiten, Backups und andere Subsysteme sind kein Teil dieser Bilanz. Der Pfad ist kein Nachweis einer absoluten Gerätespeichergrenze.

Quellenzeile, Aufnahmebeleg und Cursor committen in derselben echten SQLite-Transaktion. Der schmale Store-Adapter benutzt die tatsächlich komponierte `Store.source`-Implementierung innerhalb der vorhandenen Transaktion, statt ein verschachteltes BEGIN zu starten oder die Source-Prüfer zu umgehen. Vorherige Quellen desselben Grants werden erneut geprüft. Ein Fehler vor Commit rollt Source-DB-Eintrag und Cursor gemeinsam zurück; ein möglicher begrenzter Blobrest bleibt belastet. Bei einem Fehler nach Commit ist der gespeicherte Aufnahmebeleg maßgeblich. Nach Neustart wird kein bereits abgeschlossener Offset erneut aufgenommen.

Widerruf betrifft nur SourceRefs dieses Grants und Kindes, bewahrt Datei-/Zählerstände und blockiert weitere Aufnahme. Er behauptet kein physisches Löschen oder Unlernen. Externe Texte erreichen weder den ausschließlich USER-basierten Kontextabruf noch C3-/Body-Trainingsbatches über erfundene F1/F5-Rechte. Für tatsächliches Datasettraining ist ein eigener expliziter Trainingsvertrag mit geeigneten Items und Holdouts weiterhin erforderlich.

Eine Vorschau kann separat mit der bereits bestehenden expliziten Ein-Zeilen-CLI vorbereitet werden. `list` bleibt offline; nur `stage` fordert den benannten Download an. Diese CLI wird vom Idle-Consumer niemals aufgerufen.

```bash
python -m v13.dataset_probe_candidate list
python -m v13.dataset_probe_candidate stage cosmo_small --offset 0 --out-dir /lokaler/vorschauordner --quota-bytes 8388608
python -m v13.dataset_probe_candidate read cosmo_small --offset 0 --out-dir /lokaler/vorschauordner
```

```text
:dataset status
:dataset admit cosmo_small /lokaler/vorschauordner offsets=0,1 field=text
:dataset cfg daily_rows=8 daily_bytes=131072 total_bytes=1048576
:dataset on
:dataset step
:dataset off
:dataset revoke AUFNAHME_ID
```

Beide neuen Hintergrundpfade verlangen jetzt zusätzlich `threading.current_thread() is runtime.worker`. Der vorherige World-Idle-Scope band seinen Besitzer an einen Thread, prüfte beim erstmaligen Eintritt aber nur laufendes Sleep/DISPATCHED-Ereignis. Ein anderer Thread konnte den Scope vor dem tatsächlichen Worker beanspruchen und dessen Versuch reservieren. Die Dataset-Komposition korrigiert dies am erzeugten World-Helfer und bindet dessen neuen Hash im Guard erneut; der ursprüngliche 38c6879-Builder und Helper bleiben bytegleich als überprüfbarer Vorgänger erhalten. Ein eigener gepinnter alter Gegenbeispiellauf und neue negative Fälle prüfen die Übergabe.

Erste geschlossene Prüfung: **29 Dataset-Laufzeitfälle PASS**, äußerer Stage-Test PASS. Tatsächlicher Operator → Scheduler → externe Quelle → lesen → Runtime-Neustart → zweiter Offset → keine Duplikate; manipulierter Katalog/Zeile/Symlink, HOLD, Widerruf, Fehler nach Source-Anlage, persistente Quoten, tatsächliche Workeridentität und Deadline geprüft. Netzwerk- und Traineraufrufe sind in diesen Fällen verbotene Spies. Geschlossen auf derselben Stage: **592 PASS / 3 CUDA SKIP / 70 Untertests PASS**. Gesonderte Auswahl: **29 Dataset- und 77 Idle-/Legacy-/Schedulerfälle PASS**, vier äußere Tests PASS. Zusätzlich **14 äußere Staging-/Runtime-Tests PASS** einschließlich des gepinnten ursprünglichen Worker-Gegenbeispiels. Ungekürzte Protokolle wurden vor verlustfreier Kompression geprüft; `proofs/dataset-idle-record-20261111/` bindet Quellen und Rohbytes. Die neue Remote-CI folgt erst nach Push.

Der zugrunde liegende Idle-Code `7d66b225…` hat unabhängig davon bestätigte CI: exakter Push `43070919414` und PR-Merge `43070928053`/`9341be4`, beide Jobs SUCCESS mit 562 gemeinsamen PASS/70 Untertests und 15 äußeren Minimaltests. Nicht als CI des neueren Dataset-Codes ausgeben. `proofs/idle-world-runtime-20261111/CI_RESULT.json`.

Nächster Schritt läuft disjunkt: alte FINAL-USER-Nachrichten nur mit gültigem bestehenden komprimierten Source-Archiv verdichten und alle betroffenen Leser ausdrücklich hydratisieren. Assistant-/Teacher-Texte bleiben wegen T8-/C5-Hashes geschützt. Danach eigene Dataset-Trainingsadmission und unabhängige Retention; langer lokaler Kontext und tatsächliche Cross-Organ-Selbstoptimierung bleiben verbindlich offen. SourceHandoff, Age, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE und beide false-Gesamtflags bleiben unverändert.
