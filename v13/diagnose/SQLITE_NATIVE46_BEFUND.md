# SQLite-Fehler im 46er-Lauf: Befund (2026-10-09)

Nur gelesen, nichts repariert, keine native Inferenz. Verglichen wurden Kopien von
`checkpoint65-first8.sqlite3` (Stand nach 8 Zeilen) und `native46-failed-db-preserved/brain.sqlite3`
(Stand nach Zeile 9). Werkzeug: `pagediff.py`, Ausgabe in `pagediff-first8-vs-failed9.txt`.

## Was belegt ist
- Stand nach 8 Zeilen: 251 Seiten, Header-Zähler 17, Integrity OK.
- Kaputter Stand: Datei und Header sagen 261 Seiten, Zähler 18. 35 Seiten haben sich geändert, 252–261 sind neu.
- Die Wurzeln der Tabellen `messages` (Seite 13) und `telemetry` (Seite 31) zeigen als jüngstes Kind auf
  Seite 272 bzw. 276. Diese Seiten existieren in der Datei nicht. Alles andere (packets, events, states) ist lesbar.
- Daten der neunten Runde (Event `evt_5b9ae5d2…`) stehen in den Seiten 252–261 und in mehreren älteren Seiten.
  Die fehlenden Seiten 262–276 enthielten also die neuesten messages-/telemetry-Blätter dieser Runde.
- Der Zähler stieg seit dem 8er-Stand nur um 1. Seite 1 wurde also nur einmal geschrieben,
  und zwar mit einer Größe von 261 Seiten, obwohl der Baum schon bis 276 reichte.

## Einordnung (gefolgert, nicht bewiesen)
Eine einzelne, normal arbeitende SQLite-Verbindung erzeugt so ein Bild nicht: Ein Schreiber hat mit einer
veralteten Sicht auf die Datenbankgröße committet, und der anschließende Checkpoint hat die Datei auf 261 Seiten
gekürzt. Das passiert typischerweise, wenn
1. zwei Verbindungen gleichzeitig schreiben und Sperren/Shared-Memory (-shm) nicht wirken, oder
2. die Datei bzw. die -wal-Datei außerhalb von SQLite kopiert, ersetzt, gelöscht oder per Snapshot
   zurückgesetzt wurde (z. B. bei einem Abbruch/Restore der damaligen Cloud-Arbeitsumgebung).

Im V13-Code öffnet nur `Store` die Datenbank. `Store` hält eine exklusive flock-Sperre, setzt WAL und
synchronous=FULL und macht beim Schließen `wal_checkpoint(TRUNCATE)`. Der Sammel-Ablauf schließt die Runtime,
bevor Export und Prüfung eigene Stores öffnen. Es gibt keinen fork und keinen zweiten Direktzugriff.
Ein Fehler im V13-Code ist damit nicht gefunden; die Umgebung ist der wahrscheinlichere Verursacher.

## Nebenbefunde
- `PRAGMA wal_checkpoint(TRUNCATE)` in `Store.close()` meldet „busy“ als Ergebnis-Zeile, nicht als Ausnahme;
  das Ergebnis wird nicht geprüft.
- Der Sammler prüft die Integrität erst beim nächsten Öffnen. Ein `PRAGMA quick_check` nach jedem
  Schließen und das Sichern von -wal/-shm beim ersten Fehler würden die Grenze genau zeigen.

## Basislauf hier
398 Unit-Tests (`tests/test_*.py`) in dieser Umgebung: OK (Python 3.13, SQLite 3.45.1, ohne native Modelle).

## Absicherung (eingebaut 2026-10-09)
- `v13/store.py`: `Store.close()` merkt sich das Ergebnis von `wal_checkpoint(TRUNCATE)` in `last_checkpoint` (busy, log, checkpointed).
  Neu: `audit_closed(home)` (nur lesend: Dateigröße, WAL/SHM-Größe, page_count, `quick_check`) und
  `preserve_sqlite(home, ziel)` (kopiert DB + -wal + -shm byte-genau, mit SHA256).
- `tests/integration_causal_output_lifecycle.py`: Der Sammler prüft nach jedem Schließen
  (`runtime-close`, `tokenizer-close`, `export-close`) und hält beim ersten Fehler an. Dann liegt der unveränderte
  Zustand in `sqlite-boundary-failure-row-<n>-<grenze>/`. Die Messwerte stehen pro Zeile in `sqlite_boundaries`.
- Neuer Test `tests/test_sqlite_close_audit.py` (3 Fälle). `audit_closed` erkennt die echte kaputte DB von Zeile 9
  (malformed) und lässt den 8er-Stand durch.
- Alle 401 Tests grün (`unit-tests-after-guard-20261009.log`).
- Achtung: Der Sammler hat damit neue Quell-Hashes. Der alte 46er-Versuch bleibt abgeschlossen (terminal);
  ein neuer Versuch braucht einen neuen Quell-Checkpoint.

## Nachspielen ohne Modell (2026-10-09)
`replay_native46.py` startet von einer Kopie von `checkpoint65-first8.sqlite3` mit der echten isolierten Konfiguration
und spielt die Zeilen 9 bis 46 mit denselben Schreibwegen nach: Runtime öffnen, Event, Kontext, gestreamte Antwort
(echter Text und Metadaten von Zeile 9), Telemetrie, `output_feedback(learn)`, Runtime schließen; dann Export-Store mit
`persist_export_decision` (echte `observed.json` von Zeile 9) schließen; dann Prüf-Store öffnen/schließen.
Nach jeder der 115 Schließ-Grenzen lief `audit_closed`.

Ergebnis: alle 115 Grenzen OK, Datenbank am Ende 752 Seiten, `quick_check` ok (`replay-native46-log.json`).
Der V13-Schreibablauf erzeugt den Schaden hier also nicht. Das stützt die Vermutung, dass die damalige Umgebung
(Dateisystem/Snapshot/Abbruch) die Ursache war.

Grenzen: Hier läuft SQLite 3.45.1, damals 3.53.1. Native Läufe, Tokenizer und echte Modell-Wartezeiten fehlen,
und blobs/Modelle sind nicht vorhanden. Bewiesen ist die Ursache damit nicht.
