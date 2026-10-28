# STEP2 four-arm cross-arm B1 model identity preregistration — 2026-10-28

Review-only independent child of PR #826 head `0cc5e59fc1c91a71b0b232b42f70668c562d9d2b`; do not modify PR #826 or main.

## Problem and negative controls (registered before tests/source)
The four-arm diagnostic compares two-distinct TP/TC against shared-body SP/SC. Existing `validate` binds model identity within each arm across seeds, across pointer ON/OFF pairs, and C3 across all arms. It does **not** require the B1 weight to be identical between distinct-body and shared-body arms. Thus a synthetic twelve-report set can change B1 in both SP and SC for all three seeds, retain the same registration SHA and every existing cross-arm check, and still report `candidate_supported=True`. This confounds the claimed shared-body causal control. The same applies when both TC and TP change their B1 identity together.

## Acceptance
1. RED-first software tests create both counterexamples by changing model digests in the paired arms for all three seeds, with all other metadata intact. They must fail until the narrow source fix.
2. Reject both model-drift cases with a clear `ValueError` in `step2_longnote_fourarm_analysis.validate`; preserve all existing accepted synthetic fixtures.
3. Run focused stdlib unit tests and branch-only CI with raw exits, privacy and diff checks. This is a software-level contract, **not** native execution, a new model cohort or any gate promotion.
4. No changes to Canon, frozen Runtime, historical fixture/seed/model pins, collector, JEF, C3 or learning paths.

Evidence owner: GPT-6, this branch only. External dependencies: none for focused unit tests. Negative gates remain STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, Age0 RECORD_ONLY. Next after GREEN: independent review and a separate substantive package.
