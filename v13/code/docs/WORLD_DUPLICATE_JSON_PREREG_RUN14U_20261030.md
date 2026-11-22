# Run14U — World F4 duplicate JSON key rejection (2026-10-30)

Parent: independent ContextOS Run14S PR #1336, exact head `3c7ffab524dbb346d115e81067e5f5729dc5057a`. Owner: GPT-6. Scope: `v13/code/v13/world.py`, new `v13/code/tests/test_world_duplicate_json_run14u.py`, workflows/checkpoint only. No model/seed/registered cohort/canon modifications.

## Observed gap

`_strict_json_object` rejects nonfinite JSON but `json.loads` silently accepts duplicate object keys (last key wins). SQLite JSON1 `json_extract` may select the first occurrence, and `_VALID_RECEIPT_SQL` currently checks `json_valid` only. A persisted `PredictionOutcome` with duplicate `observation.scored` or action outcome with repeated `role` can be treated as source-bound observation despite ambiguous bytes; the materialized `observed_action_count` is computed by SQL independently of Python receipt verification. This is a data integrity issue, not semantic learning.

## Test-first frozen expectations

1. Python strict World parser refuses duplicate keys at top level and nested levels while accepting normal finite objects; no auto-repair.
2. A real SQLite action with duplicate keys in its persisted outcome is not observed or scored; original bytes remain untouched.
3. A previously valid World receipt modified to contain duplicate nested `scored` is not counted in `_refresh` or trusted on restart. `recover` can append a *new* valid receipt from the intact authoritative action without deleting the invalid raw packet.
4. Existing World timing, multi-action recovery, receipt binding, valid-recent-window, modulator atomicity and F4/World-JEPA software tests remain passing. Preserve original RED and candidate attempts.

Proposed mechanism: Python `object_pairs_hook` rejects duplicate keys; SQL `json_tree` duplicate parent/key check on both packet and action outcome inside existing `CASE json_valid` envelope. No DB migration or source rewrite; performance and SQLite JSON1 availability must be checked in real Runtime tests. If SQL expression fails or is costly, preserve RED and seek a bounded fail-closed alternative.

Claim limits: software/real SQLite only; no native inference, model learning, Redmi or end-to-end utility. Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; jepa_weight=0; V13 incomplete; historical full-suite RED unwaived.
