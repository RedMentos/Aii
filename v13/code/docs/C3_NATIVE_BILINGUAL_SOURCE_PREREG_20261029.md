# Current-catalog C3 native bilingual source/absence/revision pilot — preregistration

UTC 2026-10-29. Review-only child of PR #1135 at `32e6f4846ef03f3d8934f3824f809ff43763a70d`. Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` unchanged. The goal is new **real Linux-native** generation observations on source-grounded and unsupported questions, not to relabel a smoke as full C3 utility.

## Exact pinned public artifacts and claim limit

Reuse the current catalog C3 GGUF `LiquidAI/LFM2.5-350M-GGUF` revision `657e078c94084481950a2d555a941481f715536b`, model SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`, size 219312832, license `LFM Open License 1.0`; official pinned Linux llama.cpp b10964 tar SHA256 `9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443`, size 16825086. Reuse the existing source-pinned `current_c3_native_linux_smoke_20261028` catalog and safe tar extractor; do not change any pinned artifact or original registered cohort.

The new pilot is **C3-only**: no JEF/C2, B1/B2, JEPA, source-memory consumer, Redmi, learning authority, tool action or end-to-end gate. It does not imply correct semantic answers. Native generation marker, bounded stdout/stderr, nonzero/timeout/cap checks are prerequisites for calling an individual row `NATIVE_GENERATED`. The aggregate report must retain `utility_proven=false` and all negative gates. Raw fixed public prompts/outputs may be in Actions artifacts; model bytes, private data and weights must not be uploaded.

## Six preregistered fixed prompts

For English and German separately, ask about a fictional project budget in three conditions: source says 120 euros, no source (UNKNOWN/UNBEKANNT requested), and a later correction from 120 to 90 euros. Use deterministic `--temp 0`, 48 max generated tokens, 512 context, two CPU threads, `--single-turn`. Keep order fixed EN present/absent/revised, DE present/absent/revised. Each run has a distinct raw stdout/stderr pair and SHA256. Never score prompt echoes as answers; without a verified generated-only extraction the result remains **UNSCORED_NATIVE_OBSERVATION**. No success/utility gate may be inferred from token generation alone.

## Evidence and acceptance

Software prereg tests must validate the fixed six IDs, prompt uniqueness, absence of leaked numeric budget in unsupported conditions, exact 120→90 revision order, negative gates and official pinned hashes. Linux CI must verify official downloaded model and runner SHA256 before any generation, run each prompt in a bounded isolated subprocess, preserve failed attempts and full raw, and emit closed aggregate report with exact source and prompt digests. Failure of any row remains failure, not skipped success. An unavailable download or CI timeout is a bounded native blocker; continue other packages. Full independent software review on parent PR #1135 is a separate evidence track.

Owned files: `v13/code/scripts/current_c3_native_bilingual_source_probe_20261029.py`, `v13/code/tests/test_current_c3_native_bilingual_source_probe_20261029.py`, `.github/workflows/v13-current-c3-bilingual-native-20261029.yml`, this prereg, dedicated BUILD_STATE. No modification to runtime, models, corpus, licenses, native manager, original tests or existing pins.
