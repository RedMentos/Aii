# Run11 bilingual half parser: second-number ambiguity review prereg — 2026-10-28

Owner: GPT-6 independent review child of PR #851, base commit `42daf68da2d0a5dac986f6744fa0cc9ef363b72a`; do not change the parent owner branch. Only `v13/code/v13/toolstep.py`, `v13/code/tests/test_toolstep.py`, this prereg, scoped handoff and test workflow are owned by this review. Frozen model/source/seed cohorts and all other files remain unchanged.

## Observed source-level bug and falsifier

The existing `propose_half` enumerates only matches to `HALF_INTEGER`. A second number written in an excluded notation (signed, decimal, thousands separator, scientific notation, Unicode digit) can escape enumeration, leaving one recognized integer and incorrectly proposing `calc(<first>/2)`. The parent contract explicitly says any second numeric value is ambiguous and must abstain. This review is a **source inspection hypothesis** before the counterexample run; no native or Redmi evidence is claimed.

Predeclared negative controls:
- `Halbiere 120 und -5.`
- `Halbiere 120 und 1,5.`
- `Halbiere 120 und 1.200.`
- `Halbiere 120 und 2e3.`
- `Halbiere 120 und ١٢.`
- `Calculate half of 120 and -5.`

Positive controls: `Budget 120 Euro. Berechne die Hälfte.` -> `120/2`, `What is half of 80?` -> `80/2`, and `Halbiere 8.` -> `8/2`.

## Narrow candidate and gates

Reject if **any digit** lies outside the single exact integer match, including Unicode digits, before emitting the half proposal. This adds a fail-closed check only; it does not change the generic arithmetic parser, policy, tool registry, C5, runtime, prompts, source handoff or models. Run regression for `tests.test_toolstep` and existing calc ablations; ideally full Linux software suite on a clean branch. Existing Age0 `RECORD_ONLY` and tool shadow-only behavior must remain, with no user-visible calculator bypass. A parser unit PASS is software evidence only, not native semantic utility.

Preserve STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 heldout FAIL, jepa_weight=0, phone_measured=false and all canonical requirements. This branch is review-only; never merge directly into main without independent integration and frozen source gate checks.
