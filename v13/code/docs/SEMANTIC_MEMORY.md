# Semantisches Gedächtnis (WP-H + WP-S2, STEP3) — 2026-10-09

## Was es tut
Gespeicherte Korrekturen (`:feedback fact …`) werden jetzt auch gefunden, wenn die neue Frage anders formuliert ist.
Schlüssel ist ein Satzvektor von **EmbeddingGemma-300M** (Q8_0, gepinnt in `specs/models.json` → `embedding`),
Matryoshka auf 256 Dimensionen gekürzt. Der Vektor entscheidet nur, *welche* Korrektur passt; der Wert kommt immer
aus seiner Quelle (`source_ref`), der Entitäts-Wächter (`Projekt A` ≠ `Projekt B`) gilt weiter, und ein vom Menschen
gelabelter Cue-Kopf (`retrieval_worker`, `:retrieval … --learn`) hat das letzte Wort (admit/reject).

## Bedienung
- `:download embedding` lädt das Modell (334 MB, optional, nicht in `all`).
- `:semantic` zeigt Status; `:semantic off|shadow|on|auto` (Default `auto` = an, sobald installiert; `shadow` misst nur).
- Regler (`:knobs`): `memory_embed_dim` 256, `memory_embed_threshold` 0,84, `memory_embed_keep` 0 (Runner nach Abruf entladen).

## Code
- `v13/semantic_memory.py`: `EmbeddingEncoder` (eigener llama-server, `--embedding --no-repack`, Kontext 512),
  `SemanticKeys` (Vektor-Cache in `states`, Schlüssel enthält Quell-ID → `:forget` löscht mit, Revision/Dim/Prompt im Schlüssel),
  höchstens `retrieval_candidates` neue Schlüssel pro Runde, Rest folgt später.
- `v13/memory.py` `recall`: Score = max(lexikalisch, Kosinus falls ≥ Schwelle); `retrieval_channel` lexical|embedding|learned,
  `embedding_similarity` landet in den Turn-Metadaten. Jeder Fehler des Encoders → lexikalisch weiter, Telemetrie ohne Inhalt.
- `v13/runners.py`: Zweck `embed` + `embed()`; `v13/models.py`: optionale Rolle `M_EMBED` (nicht in `revisions()`).
- Tests `tests/test_semantic_memory.py` (8). Benchmark `scripts/semantic_recall_bench.py`, auch `cloud_bench.sh --semantic`.

## Messung Cloud (x86, 4 Threads, b10964) — `bench-results/semantic-recall-20261009/semantic_recall.json`
24 englische Erinnerungen, je 2 Umformulierungen (Kalibrier-/Testseite getrennt), 16 fremde Fragen; Deutsch als Transfer.

| | Treffer@1 Test EN | Fehlaufnahmen EN | Treffer@1 Test DE |
|---|---|---|---|
| lexikalisch (heute) | 25 % | 0 % | 0 % |
| EmbeddingGemma 256 Dim., Schwelle 0,84 | 96 % | 0 % | 75 % (768 Dim.: 88 %) |

Ende-zu-Ende über `Memory.recall`: EN 98 % Treffer@1, DE 88 %; die eine Fehlaufnahme (6 %) ist die lexikalische
(„How do I boil an egg?“ ↔ „How many hours of sleep…“ über Funktionswörter), nicht die semantische.
Server-RSS 433 MB (davon 354 MB gemapptes Modell; mit Repack 737 MB), Kaltstart ~1 s, ~35 ms pro Text, Abruf aus Cache ~40 ms.

## Offen
- RAM-Ziel < 200 MB aus WP-S2 ist mit dem Q8-Modell nicht erreichbar; Redmi-Messung (WP-R) entscheidet über `memory_embed_keep`
  und ob eine kleinere Quantisierung nötig ist.
- Schwelle ist auf Englisch kalibriert; Deutsch braucht eigene Kalibrierung, sobald es Lerntest wird.
- Lexikalischer Abruf lässt Funktionswörter („how“, „do“) zählen; eigener kleiner Fix, nicht Teil dieses Pakets.
- WP-N8 (Ereignis-Grenzen, Gedächtnisgraph) kann auf `SemanticKeys` aufbauen.
