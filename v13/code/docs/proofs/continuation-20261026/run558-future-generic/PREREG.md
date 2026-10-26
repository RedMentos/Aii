# Run558 prereg — source-only exact schedule executor for remaining STEP2 FUTURE_003..024

2026-10-26. Exact base Run557 PR #556 head `5cbf54f8c8ff2fe3fb8531a76a560493c7041296`. Run557 native FUTURE_002 is a separate active owner (Actions 40350723259) and **must not be touched, rerun or competed with**. Run558 runs no model, no native worker, no bootstrap, no training. Preregistered before source edits.

## Why

Frozen original Run491 ten-episode heldout cohort (75 stages/1050 rows) is split by immutable Run504 into 24 disjoint FUTURE batches. Run507 FUTURE_001 42 rows and Run557 FUTURE_002 42 rows use individually copied source executors. Copying that executor 22 more times risks stale stage/seed IDs, duplicate native work and large avoidable maintenance. Keep Run505/556 and all original frozen registrations unchanged, but provide one **strict schedule-derived** source-only executor for FUTURE_003 through FUTURE_024, selected only by an explicit typed `--batch` argument.

## Contract and tests

New `scripts/run558_future_batch.py` reads exact Run500 stage map and Run504 schedule from immutable workdir files; verifies they match freshly recomputed original registrations, SHA-bound fixture/model/runner IDs, exact stage IDs/pairs, row-key digest and no reserved/previously claimed FUTURE_001/002 keys. Only FUTURE_003..024 allowed; batch_003 has 42 keys, last batch_024 14. `--plan` writes exclusive one-shot batch plan; `--execute` requires that plan, actual SHA-verified installed model/runner/native libraries, no existing stage/result/progress, one process group at a time, bounded deadline and fail-stop on RED with append/fsync progress. No auto retries or deletion. Mixed arm/seed stages must be derived from frozen map, not assumed from the first stage.

Adversarial model-free tests: full remaining 22-batch partition with no overlap, reject reserved/invalid IDs, tampered map/schedule/plan, mixed seed and final 14-row batch, mock successful stage receipts, second-stage failure stops before third, malformed receipt or gate promotion refusal, no-rerun/partial evidence preservation and installed preflight not called for bad source. Pin original hashes, Canon, CI source tests, official privacy scan and SHA-close raw even RED.

## Claims and next

No native execution or utility gain in Run558. After Run557 native independently reviewed, a separately preregistered one-shot Run559 may execute FUTURE_003 only under the existing serialized native owner and raw/score audits. Keep original failed attempts and negative gates: `STEP2=UTILITY_FAIL`, `B3_L1=FAIL`, `Body_JEPA=UNAVAILABLE`, `jepa_weight=0`, `Redmi=UNMEASURED`, `V13=INCOMPLETE`. No Canon/model/seed/cohort/age/learning/approval changes.
