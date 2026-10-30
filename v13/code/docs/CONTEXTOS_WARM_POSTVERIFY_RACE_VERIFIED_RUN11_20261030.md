# Context OS warm source-loss race after F5 verification — verified 2026-10-30

Review-only child of #1235 exact parent `75daa272237a5800e8577e59d9eca834cc878918`. Real Runtime/Store/SQLite with synthetic human feedback; injected source disappearance between successful F1/F5 validation and final warm delivery. **Not** an observed real concurrent deletion, model/native run or Redmi measurement. Owner GPT-6; only `v13/code/v13/context_os.py`, new test, branch-specific CI and scoped docs changed. Memory/F5 authority, registered source/model hashes, learning, approvals and age rights unchanged.

## Reproduced original RED

`ContextOS.warm` uses `Memory._verified_rows` for F1/F5 provenance, then `Store.read_source` before adding an item to the active warm view. Its late read caught only `ValueError`; `Store.blob_bytes` raises `FileNotFoundError` when the source blob vanishes. In a deterministic injected race after verification, this exception escaped instead of failing closed on the candidate.

Prereg committed `c9de4eecd3234b265031f79e026bdc4cb2039d5a` before tests. **Actions 41024672714 RED** at exact HEAD `230dbd532eaf01e21d10fa8123c79e77629ff917`: **53 tests, 1 expected error**, traceback `ContextOS.warm -> Store.read_source -> Store.blob_bytes -> FileNotFoundError`; normal live human-source positive control passed. Artifact **12962669238**, ZIP SHA256 **`eb2d7e2c95586031b17493efcc35a1b405d1f9a6494a699b62f0a2658798573b`**, CRC clean, **13/13 inner hashes**, VENV/DEPS/COMPILE/PRIVACY/DIFF exit0 and TEST exit1. Original RED privately backed and byte-identical on re-materialization.

## Minimal fix and verified GREEN

Late delivery now catches `(ValueError, OSError)` and **skips the warm candidate**. It does not bypass the earlier F1/F5 validator or permit stale source text; the injected ACTIVE-mode path returns zero items/ids. No authority or learning change. Source commit `b20aa4e1bf3017cd9a386689c409726eabab8b43`, source blob `e2d1049dc65a5eeb7ebbadab7013da1d756911b2`.

**Actions 41024777713 GREEN** at exact HEAD `b20aa4e1bf3017cd9a386689c409726eabab8b43`: **53/53 PASS**, including Context OS warm F5 authority, FINAL-only warm activation, quote/code exact pinning, Context OS plans/cache and synthetic race. All six VENV/DEPS/TEST/COMPILE/PRIVACY/DIFF exit0, privacy CLEAN, artifact **12963181183**, ZIP SHA256 **`8737ba060f1a48bb27c3951deec0f0b97e5ea3d5a550fc68a47e55bb0c8beef2`**, CRC clean, 13/13 inner hashes. Both original ZIPs privately backed at `/V13-Checkpoints/2026-10-30/Run11-ContextOS-WarmRace/` and re-materialized SHA256 byte-identical.

## Claim limits and next

**SOFTWARE_REAL_STORE_INJECTED_RACE_ONLY.** No real concurrent deletion, Linux-native model, Android/Redmi or end-to-end utility demonstrated. Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA unavailable, jepa_weight=0, V13 incomplete. No full unfiltered suite. Review-only draft; no auto-merge.

Next: independent review of late source-read failure containment, then run a current-chain combined integration check (C3 deterministic + JEF human report + Context OS warm) and resume full blueprint packages. Exact focused rerun: `cd v13/code && PYTHONPATH=.:tests:scripts python -m unittest -v tests.test_context_warm_postverify_race_run11 tests.test_context_warm_authority_run271 tests.test_context_warm_final_20261029 tests.test_context_os_singlequote_exact_20261029 tests.test_context_os_unclosed_code_20261029 tests.test_context_os`. CI workflow `.github/workflows/v13-contextos-warm-race-run11.yml` preserves raw receipts.

Checkpoint is intermediate; remaining platform budget UNKNOWN.
