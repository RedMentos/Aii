# B3 L1 persisted report revalidation — prereg (2026-10-27)

Review-only child of B3 L1 baseline completeness review at exact parent `80e2dfc1d39256153df6bc6ff316349c705dc65a`; ultimately C1+World integration `87dd02f82abdcc3762029dac3ea8170c9db30e7c`, NOT main. Owner independent B3 review, files `v13/code/v13/b3bridge.py`, new `tests/test_b3_l1_report_revalidation_review.py`, existing `tests/test_b3_completion.py` synthetic fixture, CI/coordination only. Frozen native failures, model/seed/cohort/source hashes and age/learning authority unchanged.

## Falsifiable defect

Even after strict `l1_gate`, persisted B3 manifests can contain an arbitrary `l1_gate.verdict='PASS'` with missing comparator criteria. `doctor_fields` currently labels this `L1_PASSED_L2_SHADOW_ALLOWED`; `completion_gate` can label `L1_shadow` or `active` based on the same unvalidated verdict and synthetic row flags. The original `test_b3_completion.py` creates a PASS manifest with no shuffled/random or role-retention evidence. Reporting a partial/fabricated L1 PASS contradicts canonical negative gates even though latent runtime authority stays 0.

## RED

1. Persisted PASS without every required `l1_gate` criterion (NO_MESSAGE, LATENT_SHUFFLED, LATENT_RANDOM, EXACT, CONTROL, SYMBOLIC, role retention, receiver OOD, restart) must not grant doctor L1 shadow or completion L1_shadow/active.
2. Any missing baseline, invalid-evidence marker, or `significant` false/absent in a required criterion must fail closed.
3. Positive synthetic full criteria remain eligible for **report-only** L1 shadow (never LATENT authority); stale receiver revision must invalidate.
4. Correct the historical synthetic PASS fixture to include all required criteria, empty missing/invalid lists. Preserve original failing B3 evidence; do not invent native proof.

## GREEN

Revalidate persisted gate completeness at each doctor/completion read. `B3_LATENT_IMPLEMENTED` requires this gate in addition to existing completion booleans; no new native receiver or production authority. The row-level hardware proof ID is still only a report field, not a cryptographic native proof; keep this residual limitation explicit. Focused RED/GREEN and full software raw evidence, private backups. No STEP2/B3/LP1/LP2/BJ1/Age/jepa_weight promotion; independent review, no auto-merge.
