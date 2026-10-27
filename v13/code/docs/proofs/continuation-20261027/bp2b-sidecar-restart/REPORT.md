# BP2b completed native sidecar integrity on restart — 2026-10-27

**Owner:** GPT-6 review-only child of PR #716 exact `e38d72a316b4aab57ff629cfe13300b4298cea25`, branch `codex/automation11-bp2b-sidecar-restart-20261027`. No model run or original cohort changes.

## Finding and fix

The batch operator previously resumed/skipped a completed native arm if only `RESULT.json` and raw subprocess log matched stored SHA256. Its original `ATTEMPT.json`, `SCORE.json` and `predictions.jsonl` could be removed or modified without detection, yet the batch would claim a verified completed arm. This breaks the evidence integrity needed for restart.

The new `_sidecar_hashes()` requires all three regular, non-symlink, nonempty and bounded (≤64 MiB each) sidecars; hashes their actual bytes before marking COMPLETED, records each SHA256 in the fsynced batch checkpoint, and re-verifies all three before skipping on resume. Missing, tampered or old unregistered sidecars fail closed; no silent overwrite. No change to frozen seeds/arms/model/pin/scorer or age gates.

## Evidence

- **RED** Actions `40509777121`, exact `1ce6c69c03dac9e41516ca177e9299468cf0d34d`: 35 tests, **3 expected failures** (missing SCORE sidecar accepted, altered ATTEMPT sidecar accepted, and unguarded next native call). Original ZIP `12735949252`, SHA256 `0b6020bfba89e79bfd5ec0d183b7353b26a203248049668dcaa192165178354d`, CRC PASS, privacy CLEAN.
- **GREEN** Actions `40509825442`, exact `03643fbffb434c05898c74d8a95e7d7b7374272f`: **35/35 PASS**, dry-run no writes, compile0, privacy CLEAN. Original ZIP `12736557509`, SHA256 `ca06c87a021fb73295f7a912c7e4e9118ca60b930fd84c6bf5b49222db0ebcb5`, CRC PASS.
- Both raw ZIPs privately uploaded to ChatGPT Library `/V13-Checkpoints/2026-10-27/BP2b-Sidecar-Restart/`, re-materialized and compared byte-exact with the original downloads (PASS).

**Claim limit:** SOFTWARE_FAKE_TEST orchestration only. Adapter GGUF/trainer manifest bytes are **not yet** re-hashed by this batch-level sidecar check (native one-arm runner verifies adapter at creation); a later independent package can close that gap. No native BP2b gain, Q4/Redmi, STEP2/B3/BJ1/Body-JEPA, age or whole-V13 promotion. `jepa_weight=0`, `age_authority=0`, `full_acceptance=false`.

**Next command:** `cd v13/code && PYTHONPATH=. python -m unittest -v tests.test_bp2b_native_batch tests.test_bp2b_native_runner tests.test_bp2b_transfer_score`. Before any new heavy run inspect separate seed41 owner Actions `40506115941` and its original closed raw evidence; do not duplicate or overlap that owner. Consider full software suite to check regressions across organs.
