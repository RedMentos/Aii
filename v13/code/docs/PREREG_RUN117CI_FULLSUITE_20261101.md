# Run117CI prereg — unfiltered current-chain full software regression after Run117CH

2026-11-01 UTC. Owner: Run117CI branch. Exact parent Run117CH PR #1561 head `594143dc778e4317f0b011b862a7b94232567488`. No source/model/cohort/Canon edits; Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7`.

## Purpose and frozen protocol

The prior original Run117CC full unfiltered software Actions `41255783737` was RED (5,326 tests, 5 failures, 75 errors, 28 skips). Its raw ZIP SHA256 `22a0e72b12beccd8a624c7ca6eca56754e8f24f302a5147cdbd59bc6ba7d8ced` was independently CRC/25-hash checked. Run117CH corrected **one synthetic test-only model-cache prerequisite**, with 6/6 focused software tests; it does not cure the other frozen-source or missing-original-native-artifact errors.

Run117CI repeats the **same unfiltered** `python -m unittest discover -s tests -p 'test_*.py'` under pinned isolated Linux Python/torch/transformers/peft dependencies and no model downloads. Preserve full raw and all failed tests. Do not skip, xfail, filter, edit, rescore or weaken any test; do not claim full suite GREEN unless FULL_EXIT=0. Expected likely RED due source-handoff frozen controls and unavailable historical native artifacts. Report exact test/failure/error/skip counts, raw artifact CRC/hashes and source/runner scope. A reduced failure count is only a diagnostic, not a gate.

## Pins and limits

- `v13/code/v13/history.py` blob `867d06c230ed3860f12cb7d256579c07cb214e91`.
- `v13/code/v13/sleep_offline.py` blob `dcaaf645d303fc4a4b18414fab4e3fa22957b41f`.
- `v13/code/tests/test_run83_native_driver_fake_c3.py` blob `883f5ea8a34cfd68aa46ce338cf4b68288e1d3b1`.
- `v13/code/docs/canon/V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md` blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7`.
- Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; World-JEPA SHADOW; `jepa_weight=0`. No native model, Redmi, learning, tool/output authority, or whole-system completion.

Next: launch pinned workflow, independently audit terminal original ZIP, preserve RED as RED, triage remaining failures by immutable source and missing artifacts. Remaining platform budget UNKNOWN.
