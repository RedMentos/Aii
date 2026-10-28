# Native CLI noninteractive bounded output — preregistration 2026-10-28

Owner: Codex isolated review child of #839 (base 1d8c05b84b2b178d8ec0c1f5249c5fc36e171c9a); files owned for this candidate: `scripts/current_c3_native_linux_smoke_20261028.py`, `scripts/current_b1b2_native_linux_smoke_20261028.py`, new `scripts/native_smoke_io_20261028.py`, corresponding focused tests, and new branch-only CI. Do not modify the #838/#839 owner branches or frozen model/source catalog.

## Observed RED before code

GitHub Actions #838 run 40629227523, job 122621415577, artifact 12790289704 SHA256 b922aa4c9356e0f8d2be3b32c9d6eb14ab13c0c8d9cf9b516ae91e564d490525. The actual pinned C3 GGUF and runner hashes matched, native generated `Hello! How can I help you today?`, then default interactive `llama-cli` loop printed prompts until 180s timeout (exit 124). Closed raw stdout was **962086943 bytes**; evidence remains RED and must not be reclassified. Existing B1/B2 candidate shares the same interactive invocation defect. Pinned b10964 supports `--single-turn` according to official llama.cpp CLI docs and related issue #27214; no model/seed/catalog/hash changes authorized.

## Implementation and falsifiable checks

1. Add `--single-turn` to C3 and B1/B2 native CLI commands, retaining `Hello.`, 12 tokens, 2 threads, deterministic temperature, exact weights/runner.
2. Replace unbounded `capture_output` with Linux file-backed, **per-stream <=1 MiB** bounded subprocess raw capture. On overflow, signal, nonzero, or timeout, fail closed and preserve bounded raw prefix, explicit output-cap metadata, hashes, exit and elapsed. Do not mark truncated output as complete raw.
3. Require actual llama.cpp generation timing marker (not merely banners/prompt) for a PASS. Unit tests include synthetic real subprocess: one turn, timeout, >1MiB output, no-generation banner, and exact raw hashes. Do not claim native PASS from these software tests.
4. Branch-only GitHub Actions focused tests + compile + privacy scan + diff; after owner C3 job ended and no other heavy owner, one pinned C3 native rerun with closed raw and exact hashes, no model bytes uploaded. B1/B2 heavy job remains deferred until C3 finishes.
5. Negative gates preserved: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 heldout FAIL, jepa_weight=0, Age0 RECORD_ONLY. No C2/JEF/Redmi/whole-system claim.

## Next command

`cd v13/code && PYTHONPATH=.:tests python3 -m unittest -v tests.test_native_smoke_io_20261028 tests.test_current_c3_native_linux_smoke_20261028 tests.test_current_b1b2_native_linux_smoke_20261028`

After green, inspect remote CI raw and, if permitted, native C3 only. Remaining platform budget UNKNOWN.
