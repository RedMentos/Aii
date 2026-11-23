# B3 explicit promotion legacy synthetic fixtures — preregistration (2026-10-27)

Review-only child of B3 explicit L1 promotion evidence branch at `e6e9acec3ecd39a87fed6621afd3faa985840ad5` (not main). Owner: GPT independent compatibility review. Scope limited to `v13/code/tests/test_b3calibration.py`, `v13/code/tests/test_b3order.py`, dedicated CI and coordination. Do not relax production `b3degrade.gate_passed`, `l1_report_valid`, Age0 or LATENT authority.

## Observed RED

Parent's full software Actions `40590933682` failed with **2 errors** among 1995 tests: old positive fixtures in `test_b3calibration.Ladder` and `test_b3order.Live` use `{'verdict':'PASS','criteria':{'receiver_ood':{'significant':True}}}`, which is intentionally rejected by the newly strict `GATE_L1`. The focused promotion review passed, so this is a cross-suite fixture regression. Preserve original failed raw artifact.

## Falsifiable fix

Change only the two legacy *positive* synthetic fixtures to use a complete seven-arm five-seed diagnostic from `b3bridge.l1_gate(tests.test_b3_l1_baseline_completeness_review.complete())`. The canonical positive fixture still has no native authority; the source scores/seed cohorts are synthetic and not a real B3 PASS. Keep negative geometry, low-pair, stale sender, incomplete-manifest and higher-rung controls intact. Focused old/new tests and full source-wide software CI must pass with privacy CLEAN and all raw exits0. No model download/native job, no production merge, no auto-merge. Original B3 L1 `FAIL`, STEP2 `UTILITY_FAIL`, LP1/LP2/BJ1 negatives, `jepa_weight=0` and Age0 unchanged.
