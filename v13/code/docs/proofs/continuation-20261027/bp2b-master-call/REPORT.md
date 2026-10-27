# BP2b batch real master-preflight call and identity — 2026-10-27

**Scope/owner:** GPT-6 review-only child of PR #715 exact `73f8d4446cca234628fced82f2fe1ab8d9de5a7a`, branch `codex/automation11-bp2b-master-call-20261027`. Software tests only; no model download or native training launched.

## Concrete blocker

The production default `bp2b_native_batch.execute(..., preflight=verify_master)` invoked `preflight(master_dir)`. But the imported real `bp2b_master_preflight.verify(master_dir, pin_path, metadata_only=False)` **requires `pin_path`**, so every genuine native batch would stop with `TypeError: missing a required argument: 'pin_path'` before any attempt. Existing fake preflight accepted one argument and concealed the mismatch. Separately, a forged receipt with `FULL_FILE_HASH_PASS` and `master_sha256_verified_locally=true` but wrong `master_expected_sha256` was accepted.

Repair: use a single-argument default adapter `_verified_master_preflight(master_dir)` calling `verify_master(master_dir, PIN_PATH, False)` with the exact registered pin from the native runner. Reject non-dict/missing/incorrect `master_expected_sha256` against the frozen `MASTER_SHA` before creating output. No changes to master/model bytes, metadata, seeds, arms, cohort, train parameters or native learning authority.

## RED/GREEN

- **RED** Actions `40509315923`, exact `eac466f8b247e6449d886873287bb466a14c3ae0`: 33 tests, **1 expected ERROR** (required pin_path) and **1 expected FAIL** (wrong SHA accepted). Original ZIP `12736182739`, SHA256 `ca4357c9806cead5b98e0aacadc3502edba03928822aa165e67e0191fe21a3b4`, CRC PASS, privacy CLEAN.
- **GREEN** Actions `40509359008`, exact `e30a3751ab824f9ecad4c4c61c54ed2256627c07`: **33/33 PASS**, dry-run no output writes, compile0, privacy CLEAN. Original ZIP `12736322065`, SHA256 `9eaa72753557265464931d6e175c2d4a9ca92c936b738cae4791c6574e6fe247`, CRC PASS.
- Original raw ZIPs privately saved under ChatGPT Library `/V13-Checkpoints/2026-10-27/BP2b-Master-Call/`, re-materialized and compared byte-exact with original downloads (PASS). Public repository contains only code, tests, state and report.

**Evidence class:** SOFTWARE_ONLY. Native BP2b learning effect, adapter utility, Q4/Redmi, STEP2/B3/BJ1/Body-JEPA and full V13 acceptance remain unproven; `jepa_weight=0`, `age_authority=0`, `full_acceptance=false`. Heavy seed41 owner Actions `40506115941` was still running at review time; no duplicate heavy run.

**Next command:** `cd v13/code && PYTHONPATH=. python -m unittest -v tests.test_bp2b_native_batch tests.test_bp2b_native_runner tests.test_bp2b_transfer_score`. After owner clears, independently inspect native seed41 evidence, determine if training/export/prediction really completed, and only then consider the next serialized preregistered arm. Another software integrity task is to hash-bind ATTEMPT/SCORE/prediction sidecars on batch resume, but this does not substitute for native utility.
