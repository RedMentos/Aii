# WP-T6 trusted cross-skill route conflict — prospective review (2026-10-29)

## Base, evidence and file ownership
- Independent review-only child of PR #1097 at exact head `ecbf73384b23814f17255c9bc617e31477f9a6fa`. Parent already rejects conflicting **steps within one** trusted skill, but `skilllive.automatic` still picks the first of **multiple** matching TRUSTED/INTERNALISED skills without checking agreement across skills.
- Owner: `codex/v13-skilllive-crossskill-conflict-20261029`. Owned source `v13/code/v13/skilllive.py`, new focused tests `v13/code/tests/test_skilllive_crossskill_conflict_20261029.py`, own prereg/CI/handoff. Do not modify #1097 branch or frozen source/seed/model cohorts.
- Exact pre-fix source blob: `a10bb733308b7d20c21f1aa83028435522a3ea22`. Reproduction uses real Runtime and Store-backed two TRUSTED route-only skills, not merely a mocked selector.

## Hypothesis and expected RED
If two individually valid live skills match the same user request but choose different routes (e.g. `detail` and `gist`), the old `automatic` silently selects one by trigger length/name and returns `TRUSTED_SKILL_AUTOMATIC`, skipping C2. This is a fail-open executive authority bypass. A RED-first test must prove old code fails to fall back.

## Narrow fix and acceptance
- Automatic bypass is allowed **only when every matching TRUSTED/INTERNALISED route-only skill agrees on one valid route**. If routes disagree, return None and run the full C_fast path; record an allowlisted count/routes ambiguity event without exposing prompt text.
- One trusted skill, or multiple agreeing trusted skills, must retain existing automatic behavior. SHADOW skills and mixed tool procedures cannot veto a valid trusted skill. Existing within-skill ambiguity guard remains intact.
- Real Runtime test must assert `_route` called exactly once and resulting route source is `BOOT_SCAFFOLD` when two conflicting trusted skills match. Same-route control must still skip `_route`. Unit tests also exercise trigger priority, invalid steps, and stage separation.
- Do not promote any procedural-learning, C2 native, STEP2, B3, JEPA or age gate. Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, Redmi unmeasured, V13 incomplete.

## Evidence plan
Commit this prereg before test/source. Run source-pinned RED test on original code and retain raw. Apply minimal source fix, rerun focused `test_skilllive`, `test_skilllive_multistep_route_review_20261029` and new tests, compile/privacy/diff; verify exact remote head and original ZIP SHA256/CRC/SHA256SUMS. Full suite separately where feasible; preserve historical source identity failures instead of rewriting pins. No native model calls.
