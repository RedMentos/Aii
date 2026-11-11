# Alte USER-Texte ohne zusätzliches SQLite-Klartextduplikat

Die gemeinsame Reviewkopie ergänzt Dataset-Stand `8d601e684917b692e004c00e464d806c19103016` durch `scripts/integrated_user_compaction_candidate_20261111.py`, SHA `516d9a18e033987a759716885617cee600c009725a5a5d54adf9783a060962a7`. Wiring SHA `622ef73418fe0698b549df95564458ecd8a357e03365c2c27cb197690bb27069`, ursprünglicher Helperinput SHA `3208fabfd73daa7ecdf16bf2ff981fcc7ddadb5e71d7e9f6bcfea05846b1c8e6`. Der Stager bleibt der einzige Erzeugungspfad; produktive eingefrorene Runtime-Dateien bleiben unangetastet.

## Tatsächliche Speicherung und Abruf

Ein ausdrücklich aktivierter bestehender G13-/Sleep-Job verarbeitet höchstens eine alte FINAL-USER-Nachricht. Voraussetzung sind ein bereits vorhandenes ausschließlich komprimiertes `.z`-Archiv, vollständige Hash-/UTF8-/Größen-/Dateiidentitätsprüfung sowie unveränderte Event-/Session-/Generation-/SourceRef-Bindungen in Ereignis und Nachrichtenmetadaten. Es wird kein neuer Blob erzeugt und keine Quelle gelöscht. Plain-Blob, fehlendes oder beschädigtes Archiv, aktive Erinnerung, aktuelle Historie, falsche Metadaten oder zwischenzeitliche Änderung schließen die Zeile aus.

Der Job schreibt einen kleinen Referenzeintrag mit gebundenem Textdigest und komprimiertem Suchpräfix und setzt ausschließlich `messages.text` dieser USER-Zeile leer. Beide Schritte liegen in einer eigenen rollbackfähigen SQLite-Transaktion und einem abschließenden CAS. Fremde äußere Transaktionen werden für diese Mutation abgelehnt. Reader dürfen ihre bestehende Transaktion dagegen mitbenutzen; sie starten kein verschachteltes BEGIN.

IDs, Nachrichtenanzahl, Metadaten, Ereignisse, Quellen und sämtliche Assistant-/Teacher-Texte bleiben erhalten. Letztere sind unter anderem durch T8-/C5-Hashprüfungen gebunden und werden hier ausdrücklich nicht verdichtet. Ein Fehler nach möglicherweise erfolgtem Commit meldet einen unbekannten I/O-Ausgang mit `compacted=null`, keine behauptete sichere Nichtveröffentlichung.

Betroffene USER-Leser werden ausdrücklich an Quellenhydrierung angeschlossen: `Store.history`/UI, `native_history` einschließlich Forward-Cursor, Context-Recall-Präfixsuche, AG6-Rating-Prompts, Drift-SDFT, Duplex und die Query-Echo-/Collapse-Paare. Native-History-Tails verwenden bereits hydrierte Store-Historie, statt dieselben Archive doppelt zu laden. Experience/Export lesen den Nutzerinput schon aus dem Event-SourceRef; diese Voraussetzung wird im Wiring geprüft. Keine SQL-Umschreibung, globale Row-Factory oder erfundene USER-Quelle.

Hydrierte Texte werden nie zurück nach `messages.text` geschrieben. Markierte Zeilen kommen nur aus ihrer weiterhin gültigen Quelle. Ein gemeinsames kooperatives 0,25-s-Budget begrenzt neue Batch-Hydrierung; ein abgebrochener oder ungültiger Abruf erhält `text_unavailable`, nicht den alten Inhalt. Der Suchpräfix dient nur zur Kandidatensuche; vor Modellverbrauch wird die echte Quelle weiter geprüft. Quellenwiderruf entfernt den abgeleiteten Präfix und verhindert Hydrierung/Recall.

## Grenzen und Bedienung

Default OFF. Standardmäßig mindestens 30 Tage alt, 300 Sekunden Abstand/Leerlauf und acht vorab reservierte Versuche pro UTC-Tag. Die geschützte jüngste Historie ist mindestens `history_turns+2`; Streaming, aktuelle/pending Daten und aktive Erinnerungen bleiben ausgeschlossen. Pro Job maximal 16 Kandidaten und 64 KiB pro Quelle, mit kooperativem 0,5-s-Budget. Metadatenbudget standardmäßig 2 MiB, höchstens 16 MiB beziehungsweise 8192 Einträge. Fehlversuche verbrauchen Reservierung und Abstand; ein Rollback erstattet kein Budget. Tatsächlicher Runtime.worker, DISPATCHED-Ereignis, unveränderte Policy, Queue/Pause/Trainingpause/Cancel/Ressourcen und SYSTEM-Leerlauf werden geprüft.

```text
:archive compact status
:archive compact cfg min_age_s=2592000 daily_attempts=8 ref_bytes=2097152
:archive compact on
:archive compact step
:archive compact off
```

Das entfernt logische Textduplikate und macht SQLite-Seiten wiederverwendbar. DB-Datei, WAL, Backups und die gesamten Systemdaten werden dadurch nicht nachweislich kleiner. Kein VACUUM, keine sofortige sichere Löschung, kein Unlernen und kein fertiges unbegrenztes Gedächtnis. Weitere Duplikate, Gesamtquoten, langfristige Index-/Lineage-Konsolidierung und gemessene Handy-Latenz bleiben offen.

## Tatsächliches Lernen nach der Verdichtung

Zusätzliche echte Tiny-C3-/Body-Läufe und ein numerischer World-Lauf verwenden denselben verdichteten USER-SourceRef. F1/F5-learn-Korrektur → Stage → tatsächlicher Torch-/Adam-/EMA-Schritt beziehungsweise World-Update → privater Save → Runtime-Neustart bleiben möglich, ohne SQL-Klartext wieder anzulegen. Keine native GGUF-Ausgabe oder Qualitätsverbesserung wird daraus abgeleitet.

Dabei wurde ein echter alter Body-Grenzfehler gefunden: lange Kontext-/Zielansichten überschritten trotz `max_tokens=64` das 96-Positionsfenster des Tiny-Modells. Beide lokalen JEPA-Ansichten werden nun auf das konfigurierte Fenster begrenzt. `TAIL_MAX_TOKENS_V1` ist Teil des Body-Checkpoint-Quellvertrags und der Telemetrie. Alte Checkpoints werden nicht still unter geändertem View-Verhalten fortgesetzt; ihre Dateien bleiben erhalten. Eine abgeschnittene Ansicht beweist keine vollständige semantische Aufnahme eines langen Dokuments. Übrige allgemeine C3-Prompt-/Teacherbudgets werden im nächsten getrennten Paket weiter geprüft.

Der ausführbaren Stage fehlte außerdem die vom bestehenden Completion-Registry tatsächlich geprüfte Canon-Datei. Der Stager nimmt jetzt genau diese öffentliche Datei mit festem SHA und passendem Component-Contract auf. Falscher Canon/Symlink scheitert vor Veröffentlichung; keine Gate-Evidenz oder Canon-Inhalte wurden geändert.

## Geschlossene Prüfungen

- **636 gemeinsame PASS / 3 CUDA SKIP / 70 Untertests PASS** in einer Stage einschließlich alter Organ-, Source-/Approval-/Rollback-, History-/Guards-/Drift-/Duplex-Tests und neuer Verdichtung-/Trainingsfälle.
- **11 Verdichtungsfälle PASS** und **3 echte nachfolgende Trainings-/Restartfälle PASS**; **15 äußere Staging-/Runtime-Tests PASS** auf dem finalen Source-Stand.
- Vor zusätzlicher Absicherung **2 FAIL / 8 PASS** für äußere Mutationstransaktion und abgebrochene Hydrierung; nach Reparatur 11 PASS. Tatsächlicher Trainingspfad zuerst **1 FAIL / 2 PASS** wegen unbeschränkter Body-Views, danach 3 PASS.
- Erster erweiterter gemeinsamer Lauf **3 FAIL / 632 PASS**: eine alte Ratingfixture fügte die bereits bestehende USER-Zeile erneut hinzu; der alte Drift-Mock erfand ein Feedbackereignis; der Stage fehlte die erforderliche Canon-Datei. Fixtures verwenden jetzt eindeutige echte Nutzereingaben/learn-Feedback, ein zusätzlicher Negativfall verweigert doppelte USER-Prompts. Keine Quellen-/Retentions-/Gateprüfung abgeschwächt.
- Acht vollständige Originalprotokolle samt fehlgeschlagenen Versuchen werden vor verlustfreier Kompression geprüft und hashgebunden unter `proofs/user-message-compaction-20261111/` abgelegt. Remote-CI für den neuen Code erst nach abgeschlossenem Push werten.

Vorgänger `8d601e68…`: exakter Push `43073688604` und PR-Merge `43073701241`/`047d306` mit beiden Jobs SUCCESS, 592 gemeinsame PASS und 17 äußere Minimaltests; dekodierte Original-CI-Logs sind gesichert. Das ist separat von der neueren Verdichtungsprüfung.

Nächste Arbeit läuft ohne Checkpoint-Pause: generelle C3-Prompt-/Label-/Teacherbudgets mit eigener Encoding-/Resume-Bindung. Externe Corpus-Lernadmission und generationsübergreifende C3-Fortsetzung bleiben zusätzliche offene Verträge; `DATASET_CONTINUATION_CONTRACT_GAPS_20261111.md`. Vollständiger Kontext-/Organ-/Cross-Organ-Selbstoptimierungsumfang bleibt verbindlich. SourceHandoff/Age, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE und beide false-Gesamtflags bleiben bestehen.
