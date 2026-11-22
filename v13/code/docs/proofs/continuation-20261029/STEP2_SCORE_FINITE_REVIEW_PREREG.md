# STEP2 paired utility score-integrity review — preregistration (2026-10-29)

## Exact scope and ownership
Review-only child of PR #1090, base `1aa13abec66eccd2df24942479e1194e826caa5e`.
Own only `v13/code/v13/utility.py`, `v13/code/tests/test_step2_score_finite_review_20261029.py`, this preregistration and an isolated software CI workflow. No changes to frozen cohorts, models, prompts, seeds, gates, source hashes or other owners' branches.

## Observed source issue, before tests
`paired_utility` reads `score.utility` with no numeric type/range/finite validation. A NaN can enter reported means; a string may cause TypeError during aggregation; a null `score` raises AttributeError. It also does not explicitly reject duplicate preregistered fixture IDs. This is a scoring-integrity and availability guard, NOT a new result on B1/B2 complementarity.

## Precommitted counterexamples
1. Replace one otherwise valid `score.utility` with NaN, positive/negative infinity, boolean, string, negative or >1 value: reject the affected variant and forbid `scoped_utility_gate_pass`, never emit nonfinite means.
2. Replace `score` with null (failed inference) or omit it: score exactly zero, never silently drop the row or crash.
3. Duplicate a preregistered fixture ID: reject cohort completeness and forbid promotion.
4. Retain the historical two-fixture valid complementary example as passing, and the single-body noncomplementary example as failing.

## Implementation and verification
Commit test-only RED first; then narrow fix preserving `score_decision` and existing report keys. Run `python -m unittest -v tests.test_step2_utility tests.test_step2_score_finite_review_20261029`, full `unittest discover`, compile, privacy scan and diff check on the exact head using isolated GitHub Actions. Archive raw logs with SHA256SUMS. This package has **software-only** claim scope and must not promote STEP2, B3, JEPA, Redmi, age or complete V13. Negative gates remain unchanged. No native/model job.
