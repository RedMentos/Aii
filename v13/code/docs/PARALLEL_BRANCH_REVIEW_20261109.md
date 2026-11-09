# Parallele Projektstände geprüft — 2026-11-09

Der Nutzer möchte die Arbeit aus anderen Chats mitlesen und erhalten. Die folgenden Arbeitszweige wurden als eigene, noch nicht zusammengeführte Stände gelesen; kein fremder Branch wurde überschrieben. CI-Status und HEADs sind Momentaufnahmen. Dies ist keine Freigabe ihrer unveränderten Übernahme und kein Ersatz für eine volle Gegenprüfung bei späterer Integration.

| PR / Head | Gelesener Inhalt und unabhängige Beobachtung |
| --- | --- |
| #1645 `00314306ff172e6d6d5c20a0e2e80a5269b2b9d7` → #1647 `3e2adca6690ac6e8e17b59a43696e0b6105d972b` → #1648 `638eed0443aadf12d8af0f988541b69ccf951781` | T8-Checkpoint-Zähler, atomare Einzelbeobachtung, RNG-Vorprüfung. Gemeinsamer Fokustest auf #1648: **35 PASS**, CI grün. Mit #1631 noch bezüglich `RECORD_ONLY`, expliziter Lern- und Quellberechtigung, Cursor und Widerruf zusammenführen; diese Tests beweisen keine vollständige Lernfreigabe. |
| #1646 `60efb035a6c9e0b3b2175e8cd8c131e52efa242b` | Int64-Grenze für Body-JEPA-Token und Padding; **5 Tests PASS** mit echtem Torch gegen die isoliert geladene PR-Datei, CI grün. Änderungen mit dem separaten Atomizitätskandidaten #1643 vergleichen. |
| #1649 `6f4e3178b3d314f89f0683bc7d5a2b030a7f7120` → #1650 `ee598db967e87528b08e9cb99b4defecdc038264` | Direkte Änderungen an `store.py`: Archivlesegrenze 128 MiB, anschließend quellengeprüfte UTF-8-Spannen. #1649-CI grün; für den geprüften #1650-HEAD waren keine CI-Checks gemeldet. Auf #1650 **80 fokussierte Tests und 16 Untertests PASS**, Privacy-Scan gegenüber #1649 CLEAN. Die bereits im Bestand vorhandene SourceRef-Widerrufslücke bleibt nachstellbar. #1650 und #1651 bearbeiten denselben Pfad auf unterschiedlichen Grundlagen; nichts automatisch ersetzen. |
| #1652 `3cff4930158e2431de51c472303c27fdbdc65df6` | Replay-Arbeit; beim Prüfen CI **RED: 3 FAIL / 5 PASS**, Privacy-Scan gegen seine Basis CLEAN. Der Testgenerator erzeugt falsche Arrayformen. Nach rein temporärer Fixture-Korrektur weiterhin **1 FAIL / 7 PASS**: `replay_update` verwendet Tupellänge statt Zeilenzahl und wählt nur einen Teil verfügbarer Trainingszeilen. Bei fehlgeschlagenem Postcheck kann ein zuvor mutiertes Modell verändert bleiben. Separater Korrektur-/Full-Suite-Review wurde gestartet; dieser Befund ist keine Rücknahme des Original-RED. |

## Reproduzierbare synthetische Gegenproben

`code/scripts/compare_context_stream_memory_20261109.py`, SHA-256 `0aaf155bcdf755af8f7171672f670fab5db3c2542d2cb4cd7f5f09f340246a4d`, vergleicht dieselbe auf 65.239 Bytes komprimierte, synthetische 64-MiB-Quelle und dieselben acht Zeichen. Mit exakt #1650 und #1651 jeweils per `PYTHONPATH` gewähltem Source-Checkout und Python `tracemalloc` ergaben eigene Läufe **148.320.794 Bytes** (#1650) bzw. **371.857 Bytes** (#1651) Peak zusätzlicher Python-Allokationen. Beispiel:

```sh
PYTHONPATH=/PFAD/ZU/EXAKT_PR1650/v13/code python compare_context_stream_memory_20261109.py 1650
PYTHONPATH=/PFAD/ZU/EXAKT_PR1651/v13/code python compare_context_stream_memory_20261109.py 1651
```

Das ist ein konkreter synthetischer Allokationsvergleich der Methoden, **keine** Messung von Gesamt-RSS, Laufzeit, Akkunutzung oder Redmi. #1651 ist ein isolierter Kandidat und nicht schon der aktive Runtime-Leser.

`code/scripts/review_jepa_replay_counterexample_20261109.py`, SHA-256 `cda3e1a2b75d8383a431fb99d7396d2c84e0535e1a96dfe47b1285cef9dcae15`, ist gegen den exakten #1652-HEAD auszuführen. Von je 12 synthetischen neuen/Replay-Zeilen verwendete der Ausgangspfad 3 neue und 2 Replay-Zeilen (`[0,1,2,100,102]`); nach einer absichtlich nichtendlichen Nachprüfung blieb das künstlich mutierte Modellgewicht bei `7`. Diese Probe diagnostiziert Kontrollfluss/Zeilenauswahl und belegt keinen echten Modellnutzen.

Die exakten HEADs und noch offenen Gates sind bei jeder zukünftigen Integration erneut zu prüfen. Die bereits dokumentierten STEP2-/B3-Fehlschläge, SourceHandoff-Freeze, Age-, JEPA- und Redmi-Grenzen bleiben bestehen.
