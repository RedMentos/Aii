# B3-H3 L1 baseline completeness and finite paired gate — prereg (2026-10-27)

Review-only child of current C1 + World-JEPA two-parent integration `87dd02f82abdcc3762029dac3ea8170c9db30e7c` (not main). Owner independent B3 review, files only `v13/code/v13/b3bridge.py`, new `tests/test_b3_l1_baseline_completeness_review.py`, existing `tests/test_b3bridge.py` positive fixture correction, dedicated CI/coordination. Do not change the frozen original B3 L1 failed evidence, any model, cohort, source hash, age or learning authority.

## Falsifiable defect

`b3bridge.l1_gate` reports missing `CONTROL`, `LATENT_RANDOM` or `LATENT_SHUFFLED` but excludes them from the all-significant predicate. Existing `test_b3bridge.py` even treats a five-seed record with missing CONTROL and LATENT_RANDOM as a `PASS`. This contradicts the canonical requirement that L1 beat **NO_MESSAGE, EXACT, CONTROL, SYMBOLIC, LATENT_SHUFFLED and LATENT_RANDOM** with matched paired observations. `paired` silently truncates unequal arrays via `zip`, and malformed/nonfinite arms or nonboolean reload flags can undermine a proof.

## RED cases (before implementation)

1. An otherwise strong complete five-seed record passes only if all six required arms are present, same length, finite, with finite nonnegative bytes and typed retention/OOD/reload flags.
2. Remove each of EXACT, CONTROL, SYMBOLIC, LATENT_SHUFFLED, LATENT_RANDOM: `verdict=FAIL`, missing arm named, never L2 shadow.
3. Truncated paired arms, empty arrays, NaN/Inf, invalid/negative bytes and truthy string reload cannot return `PASS`.
4. Preserve actual negative control where cheap EXACT beats LATENT on utility and role-drop violation.
5. Keep old test coverage but correct the old incomplete-positive fixture to include CONTROL and LATENT_RANDOM; no historical evidence is erased.

## GREEN contract

`l1_gate` returns a fail-closed verdict for missing/malformed arms and only allows L2 shadow when all preregistered comparisons and safety gates pass. No LATENT runtime authority, no native receiver injection, no source or model changes, no new baseline weights. Focused RED/GREEN and full source-wide software CI with raw exits/privacy/diff, private byte-verified backups. Keep B3 L1 original `FAIL`, STEP2 `UTILITY_FAIL`, LP1/LP2/BJ1 negatives, `jepa_weight=0`, `age_authority=0`; whole V13 incomplete. Independent review, no auto-merge.
