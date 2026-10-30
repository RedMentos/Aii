# Run11c current-chain full unfiltered software regression — verified RED (2026-10-30)

Review-only branch `assistant/v13-fullsuite-currentchain-de-20261030-run11c` from #1225 `852f2c6ccef375cb03a0ad8318fec851f3b191ad`. Prereg `1e11d3a0f35cb67f789c5d44257239ada46b83fe` before workflow. No source changes or waived tests.

GitHub Actions `41018761078` **RED**, exact HEAD `df51911c13cd04fd345016ce842058724d76b4a7`, artifact `12960931826`, ZIP SHA256 `33de529daf0f1b3dfe55e5b5cbced8c4432180647ddcb25bb37dcc79234bf277`, 9,799 bytes, CRC clean, **30/30 SHA256SUMS** verified. Isolated Ubuntu 24.04: CPU torch 2.5.1+cpu, numpy 2.2.6, transformers 4.44.2, peft 0.13.2 installed/imported, pip check0, Canon check0, compile0, privacy CLEAN, diff clean. Full suite actual exit **1**, **3,635 tests, 3 errors, 14 skips**, 392.129 seconds. No filtering/waivers.

## Exact three errors
- Frozen historical `test_run34_c3_native_quote_intervention_pilot`: `native_source_or_catalog_changed`. **Preserve** original source pin.
- Frozen historical `test_run37_c3_rule_use_native_pilot`: same historical `native_source_or_catalog_changed` via Run34. **Preserve** original source pin.
- `test_step2_expression_diagnostic_20261030.ExpressionSensitivityTests.test_original_zip_bound_posthoc_only`: **FileNotFoundError** for `v13/code/tests/NATIVE_40996792157.zip` in fresh runner. This is a missing original artifact prerequisite, **not** a code assertion failure. The original GitHub Actions `40996792157` artifact `12951963045` was retrieved, CRC clean, 54 entries, HEAD `5e802d235c9501879a3aff07e5134c1455e1769b`, exact ZIP SHA256 `98a61f622b64b792f38d766da3ef50e9101571b7e616f2c587d6e89ab5e31c46` (297,655 bytes), matching the frozen diagnostic's `ORIGINAL_SHA256`.

## Next package
On a **child review branch**, change only the *test workflow prerequisite setup* to fetch original artifact `12951963045`, verify SHA256 `98a61f...`, copy to the test's existing expected path, then rerun the **same unfiltered** command. Never modify/skip `test_step2_expression_diagnostic_20261030.py`, original raw, scoring, or historical Run34/Run37 source pins. Expected (not guaranteed): 3,635 tests, only the two original historical RED errors. Capture raw/ZIP hashes and report any new failures honestly. No native inference or Redmi.

Private Library backup at `/V13-Checkpoints/2026-10-30/Run11-FullSuite/`: original unfiltered RED artifact and original native v3 ZIP. Gates unchanged: Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA unavailable; jepa_weight=0; Redmi UNMEASURED; V13 INCOMPLETE. Platform budget UNKNOWN.
