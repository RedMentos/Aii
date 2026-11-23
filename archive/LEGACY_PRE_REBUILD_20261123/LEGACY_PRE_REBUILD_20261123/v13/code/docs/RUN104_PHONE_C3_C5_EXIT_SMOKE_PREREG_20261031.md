# Run104 optional bounded Age0 phone C3→JEF/C5/C6 + STEP2_EXIT smoke — prereg 2026-10-31

Owner GPT-6 automation11. Review-only child of verified PR #1474 exact parent `70dc2e169465e948c24514ca5aebe33a4ca8fea0`, which integrates donor #1472 native-negative STEP2_EXIT with phone/C3 #1473. No edits to any parent/other owner's branch.

## Fixed scope, before code

Add a **new optional** `run104_c3_c5_exit` 21-case exact model-free bounded installer cohort to `scripts/install_selftest.py`; preserve original `legacy_run97` and `run102_c3` case names, order, SHA256 and default. Do not change `setup.sh`'s existing `run102_c3` selection. Existing 18 Run102 cases plus exactly these three in order:

1. `test_jef_c3_c5_c6_operator_cli.JefC3C5C6OperatorCliTests.test_six_source_bound_local_drafts_survive_restart` — real Store, six synthetic callback cases across two modes, C5/C6 SHADOW DRAFT, restart invalidates uncommitted draft, no live output.
2. `test_jef_c3_c5_c6_operator_cli.JefC3C5C6OperatorCliTests.test_native_missing_pinned_model_refuses_before_human_records` — native-missing refusal, no model invocation or memory side effects.
3. `test_step2_exit_gate_split_20261031.Step2ExitGate.test_exit_is_explicitly_red_and_all_graph_deps_remain_known` — original Z2b/Z2c native utility still FAIL, dependent gates not GREEN.

New 21-case JSON-compact tuple digest SHA256 `d745f4a1df7d54f7b1c1024e7d3aa24603d007070a694a6611d50ba958b96d70`. Original `legacy_run97` digest `31b7d96ed740139b07b3b9dcf820aa04fafa13f5dfdcc4645e1df8e8df933f55`; `run102_c3` digest `218303e408fab72d705dc3daa2f63dab63e0e34a7ab7ecc31f4954c585a563f5`. All immutable.

## Acceptance and evidence

- New unit tests assert all three exact digests, case order, nonduplication, fail-closed unknown cohort and actual `run_bounded(120,'run104_c3_c5_exit')` success; original 5/5 installer and 5/5 Run102 cohort contract must remain GREEN.
- Run 21-case worker **from actual extracted current phone source ZIP**, plus independent JEF/C5/C6 CLI tests and original STEP2_EXIT suite. Verify ZIP CRC, all source manifest hashes, C3 Context OS tests, and `STEP2_EXIT=EVIDENCE_NOT_PASSING`.
- Isolated Linux software only; no native model, Redmi, learning or output authority. Capture exact HEAD, stdout/stderr, exits, SHA256SUMS, privacy/diff, source ZIP and original failures if any. Preserve artifacts in private Library if available. No promotion, merge or force-push.
- If new cohort fails, keep original failed attempt and fix only this child; never silently edit old registered cohort or original negative results.
