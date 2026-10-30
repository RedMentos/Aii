# Run15 — restore unfiltered full-suite execution after exact-pin typo (2026-10-30)

Parent review PR #1341 exact head `5e264d6b7e32e926aa188246fa958709d6f1d6df`. New review-only branch `codex/v13-run15-fullsuite-pin-recovery-20261030`; owner GPT-6 automation. No runtime, model, Canon, cohort, seed or production changes.

## Original failure retained
Original Run14Z unfiltered Actions 41129115843 at `ad653af688341110fc3c9f03815aae9fd7e85815` ended FAILURE, but **did not run the suite**. The PINS file specified non-existent `v13/code/tests/test_run14z_context_world_effort_integration.py`; actual immutable Run14W witness path is `v13/code/tests/test_run14w_context_world_effort_integration.py`, blob `597d6ca7528a496c34d1178a6f6156993b457ebb`. PINS_EXIT=1, FULL_EXIT=99, FULL_RAW=SKIPPED_DEPS_RED. The 26-file original ZIP artifact 13012152679 SHA256 `f9ff915930fabbf7c8a33524ead601fcd5265c52875c3ffa506c6f9aa8901ed9` has clean CRC. Do not call it a test regression.

## Authorized recovery
Create an independent new Actions workflow on this child branch, copying the Run14Z full-suite runner and changing only the workflow name, branch/path trigger, and the mistaken Run14W test filename. Retain all original hashes, dependency pins, original negative gates, unfiltered discovery, and fail-on-nonzero behavior. Save original raw ZIP, verify CRC/inner SHA256SUMS, report real test totals/errors without waiver. Keep parent original workflow and failed run immutable.

Expected historical baseline: Run14W 4154 tests, 4 failures, 66 errors, 16 skipped. A full-suite RED after actual execution is useful evidence, not permission to mark full V13 complete. No native/Redmi proof. Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, jepa_weight=0.
