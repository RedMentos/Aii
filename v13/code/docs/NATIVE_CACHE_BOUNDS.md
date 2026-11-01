# Native-Cache-RAM begrenzt (G6B-Runtime-Anschluss) — 2026-10-12 (Claude, Thread G)

Befund von Thread I (`docs/NATIVE_CACHE.md` auf Branch `claude/project-thread-uu86x1`): `v13/runners.py` setzte weder
`--cache-ram` (b10964-Standard 8192 MiB Host-Prompt-Cache) noch `--ctx-checkpoints` (Standard 32 je Slot).

## Änderung
- Neue Knobs `native_cache_ram_mb` (BOOT 128, 0 = Host-Cache aus) und `native_ctx_checkpoints` (BOOT 6) in `v13/config.py`.
- `v13/runners.native_cache_args` hängt beide Flags an jeden llama-server-Start (generate, tap, embed).
- Teil der integrierten Kette in `scripts/integrated_candidates.py` (`native_cache_bounds`), damit die Kandidaten-Lader exakt bleiben.
- Tests `tests/test_native_cache_bounds.py` (echter Kindprozess auf Loopback-Fixture, kein Modell).

## Messung (Linux-nativ, b10964-Release, gepinnte GGUFs, 4 Threads)
Skript `scripts/native_cache_bounds_bench.py`, gleiche Basisflags wie die Runtime, greedy, 48 Antwort-Tokens.

| Body / Muster | Standard: RSS-Zuwachs | Begrenzt: RSS-Zuwachs | Prompt-Zeit gesamt Std → begr. | Antworten gleich |
|---|---|---|---|---|
| B2 Qwen3.5-0.8B, ein Gespräch 24 Turns (Runtime-Muster) | +665 MiB | +164 MiB | 24,6 s → 17,4 s | 24/24 |
| B2, drei verschränkte Gespräche × 8 | **+1317 MiB** (Ende 2,26 GB) | +206 MiB | 14,7 s → 49,1 s | 8/24 |
| B2 verschränkt, 320 MiB Cache | | +453 MiB | 14,7 s → 37,1 s | 11/24 |
| C3 LFM2.5-350M verschränkt | +29 MiB | +29 MiB | 2,3 s → 2,4 s | 24/24 |
| B1 LFM2.5-1.2B verschränkt | +40 MiB | +32 MiB | 7,8 s → 7,6 s | 24/24 |

Die Wiederholung des verschränkten B2-Laufs reproduziert die RAM-Zahlen exakt (+1317,4 / +205,5 MiB).

Lesart: Nur B2 ist betroffen; ein B2-Cache-Eintrag ist etwa 100 MiB (rekurrenter Zustand und Checkpoints). Mit
Standardflags wächst B2 bei einem einzigen Gespräch schon um 0,65 GB, beim Wechsel zwischen Gesprächen um 1,3 GB, auf
einem 6-GB-Handy mit drei Bodies ein OOM-Risiko. Begrenzt bleibt der Zuwachs bei rund 0,2 GB. Im Ein-Gespräch-Muster
kostet das nichts (gleiche Antworten, gleiche Cache-Treffer, sogar schneller). Beim Wechsel zwischen Gesprächen passt
kein B2-Eintrag mehr in 128 MiB, B2 rechnet den Prompt dann neu (Prompt-Zeit ×3,3, Wanduhr +20 bis +34 % in zwei Läufen). 320 MiB sind kein
guter Mittelweg. Abweichende Antworten sind numerische Pfadunterschiede (Thread I: kein Cache-Pfad ist bitgleich),
kein Qualitätsbefund.

Belege `docs/proofs/continuation-20261012/native-cache-bounds/`. Redmi-RSS/Zeit offen (WP-R); `phone_measured=false`.
