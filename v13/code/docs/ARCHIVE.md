# WP-U4 Archiv-Politik für Quellen (§9.1 Archive, §9.5)

Kalte Quellen werden verlustfrei komprimiert: `data/blobs/<sha256>` wird zu `data/blobs/<sha256>.z` (zlib). Die Identität bleibt der sha256.

**Was als kalt gilt** (`archive.candidates`): Ein Blob ist kalt, wenn alle nicht gelöschten Quellen mit diesem Hash
- älter als 30 Tage sind (`ARCHIVE_DAYS`, BOOT),
- mindestens 512 Bytes groß sind,
- zu einer archivierbaren Art gehören:
  - rohe Nutzer-Turns (`USER`),
  - Retrieval-Sichten,
  - Ausgabe-Kontexte,
  - Body-Zustände,
  - abgebrochene Entwürfe,
  - `HUMAN_DECISION`, wenn alle Erinnerungen dazu inaktiv sind (überschrieben),
- und nicht Wert, Schlüssel oder Ereignis einer aktiven Erinnerung sind.

**Nie archiviert:** Bilder, feste Ausgaberegeln, Memory-Schlüssel, aktive menschliche Entscheidungen und unbekannte Arten.

**Lesen:** `Store.read_source` → `Store.blob_bytes` liest die normale Datei, sonst das Archiv. Das Archiv wird im Speicher entpackt (höchstens 64 MiB), danach wird der Hash geprüft. Ein kaputtes Archiv ergibt `ValueError`, und `:doctor` meldet „Source beschädigt“. Export, Backup (kopiert `data/blobs`) und `:forget` (löscht beide Formen) funktionieren unverändert.

**Wann:** Jede Sleep C archiviert bis zu 256 Blobs. Archiviert wird nur, wenn die Datei dadurch mindestens 10 % kleiner wird. Nach dem Schreiben wird das Archiv geprüft, erst dann wird das Original gelöscht.

**Befehle:** `:archive [status|run|restore <Quellen-ID>]`.
**Tests:** `tests/test_archive.py` (4).
**Grenze:** Die Schwellen sind BOOT-Werte und nicht gemessen. Es gibt keine Lese-Statistik; „kalt“ heißt alt und nicht mehr von aktiven Erinnerungen gebraucht.
