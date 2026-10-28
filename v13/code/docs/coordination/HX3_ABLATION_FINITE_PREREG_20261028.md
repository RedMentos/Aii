# HX3 ablation score integrity — preregistration, 2026-10-28

Parent review-only head: `e621be4869da2b6d87ff1e0b3317f887dd82cbe2` (PR #804), which includes the approved-origin read-side HX3 fix. This branch does not merge production and does not alter Canon, model, seed, registered cohorts, or age/learning gates.

## Observed code gap / proposed counterexample

`v13/code/v13/agi/experience.py:ablation()` documents a solver score in [0,1], but unconditionally calls `float()` without rejecting NaN, +/-infinity, negative, above-one, bool or numeric text. An invalid score can be averaged and reported as HX3 evidence (NaN can also defeat comparisons). This is software-evaluation integrity, not a measured utility result.

## Registered test contract (before source edit)

- Valid numeric endpoints 0 and 1 and normal 0.8/0.5 remain supported with the existing output structure, mean delta and worse counts.
- For **both** solver arms, reject nonfinite, out-of-range, bool and numeric-string scores with ValueError; no invalid row may be returned as utility evidence.
- Preserve empty-task behavior and the disabled-library ablation arm.
- Run the new focused tests first on unchanged parent source (expected RED), preserve the raw exit/log; then make the narrow change to `ablation` and run focused and full Linux software suites on exact Git blobs. Never claim a green full suite from a focused pass.
- Independently inspect the unrelated existing `test_b3degrade.Live.test_promotion_needs_human_and_evidence_then_resource_mode_demotes` failure in PR #804 full CI 40608236483 (2098 tests, 1 fail); do not silently erase or reinterpret it.

No native inference, real Redmi test, online learning, AGI or B3 promotion is in scope. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, Age0 gates unchanged. Owner: GPT-6 independent HX3 ablation review branch only. Exact next command after test commit: GitHub Actions focused run on this branch, inspect raw logs and source hashes before any production edit.
