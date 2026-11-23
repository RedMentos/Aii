# WP-N7-Rest: native Cache-Primitiven (§8.5, §8.6, G6B) — 2026-10-12

Thread „Nächste offene Pakete I“ (Claude). Isolierter Kandidat: **keine** Änderung an eingefrorenen `v13/*.py`
(SourceHandoff-Kohorte). Evidenzstufe: **Linux-nativ in der Cloud** (4 vCPU Xeon, llama.cpp b10964, gepinnte GGUFs),
kein Redmi-Nachweis, kein Lernnutzen.

## Dateien
- `scripts/native_cache_primitives.py` — Log-Parser (llama-server `-lv 4`), Fähigkeits-Manifest im BodyPort-Stil,
  G6B-Auswahl-Policy `select_mechanism`, Flag-Vorschlag `runner_flags` für ein RAM-Budget. Kein Modellcode.
- `scripts/native_cache_bench.py` — startet eigene llama-server mit denselben Basisflags wie `v13/runners.py`
  (`-c 2048 -np 1 -t 4 -b/-ub 128 -ngl 0 --no-warmup`, Template mit `enable_thinking=false`) und misst 6 Primitive.
- `tests/test_native_cache_primitives.py` — 8 Tests ohne Modell.
- Belege: `bench-results/native-cache-20261012/report.json` (SHA256 `63997f53…656d`), je Body alle Server-Logs.
  `dev-run1-thinking-on/` ist der verworfene Vorlauf (B2 mit Thinking an, ungleich Runtime), erhalten statt gelöscht.
- Hashes im Report: Runner `79e31218…5d39` (Binärdatei `llama-server`), Modelle, beide Skripte.

## Methode
Jedes Experiment wird gegen eine kalte Referenz verglichen (Prompt-Cache aus, keine Checkpoints,
`cache_prompt=false`), greedy, 24 Tokens, gewählte-Token-Logprobs. **Rauschboden:** dieselben Prompts kalt mit
anderem Batch-Split (`-b/-ub 64`). Klassen: EXACT (gleiche Tokens, |Δlogp| ≤ 1e-3), NUMERIC_CLOSE (gleiche Tokens,
≤ max(0,05; 2 × Split-Drift)), DIVERGENT, BASELINE_SPLIT_UNSTABLE (schon der kalte Prompt kippt mit dem Batch-Split
→ nicht entscheidbar → Manifest UNMEASURED). Die Toleranzregel wurde nach einem Entwicklungslauf auf C3 festgelegt,
vor Lauf 2. Gleicher Server, gleicher Prompt zweimal: in allen 21 Fällen bitgleich.

## Ergebnisse (Lauf 2, 2 Wiederholungen)

| | C3 LFM2.5-350M | B1 LFM2.5-1.2B | B2 Qwen3.5-0.8B |
|---|---|---|---|
| Architektur | lfm2, 16 Schichten, 6 mit KV | lfm2, 16 / 6 KV | qwen35, 24 / 6 KV (Gated DeltaNet) |
| Rekurrenter Zustand = Checkpoint-Größe | 0,08 MiB | 0,16 MiB | **19,3 MiB** |
| KV f16 bei 2048 Zellen | 24 MiB | 24 MiB | 24 MiB |
| Präfix-Reuse letzter Turn (kalt → warm) | 1488 → 169 ms | 4740 → 463 ms | 3932 → 366 ms |
| Turn früher ändern (Checkpoint je Turn) | 472 Tok. wieder, 1606 → 406 ms | 479 wieder, 4744 → 1283 ms | 520 wieder, 3982 → 1092 ms |
| Ganze Historie auf einmal, dann ändern | 0 wieder (auch mit `-cms 64`) | 0 | 0 |
| Gespräch A → B → A (Host-Prompt-Cache) | 1360 → 85 ms | 4332 → 210 ms | 3696 → 277 ms |
| Slot speichern → Neustart → laden | **4 ms Laden + 73 ms** statt 1540 ms, 6,5 MiB Datei | 4 + 239 ms statt 4465, 6,5 MiB | **nicht nutzbar** (0 wieder), 26 MiB Datei |
| `--cache-reuse` (KV-Shift) | nicht nutzbar | nicht nutzbar | vom Server abgeschaltet |
| KV q8_0 statt f16 | 24 → 12,75 MiB, HWM −11 MiB | dito, **Tokens kippen** | dito, NUMERIC_CLOSE |

Exaktheit: **kein** Cache-Pfad ist bitgleich zur kalten Referenz; alle nutzbaren liegen im Rauschboden des
Re-Prefills selbst (anderer Batch-Split ändert die Floats genauso). Folge für die Policy: Exact-Restore-Anfragen
(§8.4) bekommen immer den Baseline-Pfad „volles Re-Prefill aus exakter Quelle“; native Pfade nur, wo Näherung erlaubt ist.

## Befunde
1. **§8.6.4 ist da, §8.6.1/8.6.3/8.6.5 nicht.** Alle drei Bodies sind Hybride aus kompaktem rekurrentem Zustand und
   dichter (nicht sparsamer) globaler Attention in 6 Schichten. Encoder/Decoder-Split, geteilte/gepoolte Indexer und
   Block-Sparse-Attention fehlen in den Architekturen und werden als `ABSENT_IN_ARCHITECTURE` deklariert, nicht gefälscht.
2. **§8.6.2 Bounded Replay gibt es nativ** (llama.cpp PR #16382, Kontext-Checkpoints für Hybrid/Rekurrent): Rückrollen
   geht nur bis zu einem gespeicherten Checkpoint, danach wird ab dort neu gerechnet. b10964 legt Checkpoints nur am
   Ende einer Anfrage an; `--checkpoint-min-step 64` erzeugt **keine** zusätzlichen innerhalb eines langen Prompts.
   Granularität = Turn-Grenzen. Wer Historie auf einmal schickt (Neustart, Kontextumbau), hat danach kein Rückrollen.
3. **RAM-Risiko am Handy:** b10964-Standard ist `--cache-ram 8192` und 32 Checkpoints je Slot; `v13/runners.py` setzt
   beides nicht. Für B2 sind 32 × 19,3 MiB ≈ 616 MiB möglich, gemessen schon nach 7 Turns HWM +116 MiB (1000 → 1116).
   Vorschlag bei 256 MiB Budget je Body (`runner_flags`): C3/B1 `--cache-ram 255 --ctx-checkpoints 8`,
   B2 `--cache-ram 140 --ctx-checkpoints 6`. Nur Vorschlag; Redmi-Messung und Nutzerfreigabe nötig.
4. **B2 kann nach Neustart nicht vom gespeicherten Slot weiterlaufen:** das Qwen3.5-Template schreibt beim
   Generierungs-Prompt `<think>\n\n</think>\n\n`, lässt den leeren Block in der Historie aber weg (geprüft per
   `/apply-template`). Der gespeicherte Zustand weicht also direkt nach `assistant\n` ab; nach dem Laden gibt es keinen
   Checkpoint → volles Re-Prefill („forcing full prompt re-processing“ im Log). Bei C3/B1 (LFM) klappt es.
5. KV-Quantisierung spart nur 11 MiB (nur 6 KV-Schichten) und kippt bei B1 Tokens → kein lohnender Hebel.

## Offen
- Integration in Runtime (Flags in `runners.py`, Policy-Aufruf in `context_os.py`) erst nach Freigabe der
  eingefrorenen Quellen; dann SHADOW zuerst.
- Redmi: RSS/Zeit mit begrenzten Flags messen (WP-R); B2-Template-Abweichung ggf. durch Speichern nach dem
  Re-Render statt nach der Generierung umgehen (eigene Messung).
- Quellen (Zugriff 2026-10-12, Status aktuell): llama.cpp PR #15293 (SWA-Checkpoints, gemergt 2025-08-14),
  #16382 (Checkpoints für Hybrid/Rekurrent, ~2025-10-03), #16391 (Host-Prompt-Cache `--cache-ram`, 2025-10-09);
  Flags/Defaults aus `llama-server --help` der gepinnten b10964-Binärdatei.
