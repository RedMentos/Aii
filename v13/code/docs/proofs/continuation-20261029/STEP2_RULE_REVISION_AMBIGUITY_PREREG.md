# STEP2 rule revision ambiguity guard — preregistration (2026-10-29)

## Immutable starting point
- Base: Run118 review PR #1022, `3531b6f20e8d0acffe246605bdfdf00ebfc62ecf`.
- This is an **isolated software candidate**, not production runtime, not native inference, not a new registered STEP2 cohort.
- Preserve Run109 six-fixture SHA256 `b8896bfba0c6c323ba1dafd12bc788e7f378bbf5d23c96e5074b3b1d058ef1d1`; no model, seed, runner, or frozen-source changes.
- Existing Run117/118 code, tests, canonical gates and CI are untouched.

## Predeclared failure hypothesis and counterexamples
Run118 verifies the historical source it selects, but does not inspect the **current** source for a newer rule change, and Run117 skips non-prefix project mentions in later history. Consequently an exact old rule may be transported even when a newer source introduces a conflicting or partial project rule.

1. Historical `Project Atlas. Budget 130 euros. Deadline 6 days. Local-only requirement: true.`, current `Project Atlas. Budget 50 euros. Deadline 2 days. Local-only requirement: false.` must **refuse** rather than advertise old rules as authoritative.
2. Later history `Meeting note: Project Atlas. Budget 50 euros. Deadline 2 days. Local-only requirement: false.` must **refuse** if old selector ignores the non-prefix record.
3. Later history `project Atlas revision: budget changed; details pending` must **refuse**.
4. Unrelated later `Project Zenith. Budget 50 euros...` must not poison Atlas; benign same-project notes without revision signals must not poison it.
5. Original six frozen Run109 cases must retain exact candidate coverage, immutable source refs, cap24 and no model/authority.
6. Tampered source SHA, duplicate IDs, bad project/cap remain fail closed.

## Planned implementation and verification
- New wrapper `v13/code/scripts/step2_rule_revision_ambiguity_candidate.py` around frozen Run118; source-ref validation precedes any inspection.
- New focused regression `v13/code/tests/test_step2_rule_revision_ambiguity_candidate.py`; explicit counterexample tests.
- Run focused unittest, source checks, full suite and privacy scan in isolated GitHub Actions on new branch; keep closed original raw and SHA256SUMS.
- Negative gates: Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 FAIL; Body-JEPA unavailable; LP3 FAIL; jepa_weight=0; Redmi unmeasured; whole-system incomplete.
- No native or paid runs. Do not promote any gate on software-only results.

## Acceptance
Focused negative counterexamples refuse; six original fixtures retain coverage; full suite and privacy scan clean. Any failing guard is RED and remains recorded. Software success does not prove semantic choice, learning, native utility or Android execution.
