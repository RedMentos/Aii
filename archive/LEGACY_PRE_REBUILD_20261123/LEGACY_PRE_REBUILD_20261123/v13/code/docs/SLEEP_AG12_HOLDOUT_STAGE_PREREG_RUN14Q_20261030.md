# Run14Q — Sleep TTT candidate staging respects registered AG12 holdouts (preregistered)

2026-10-30 UTC, GPT-6 scheduled continuation, review-only child of Run14P PR #1332 exact `49e7eb3edbee83a7717a4d4356df086406a2a817`. Own `v13/code/v13/agi/generality.py`, `v13/code/v13/sleep_offline.py`, `v13/code/tests/test_sleep_ag12_holdout_run14q.py` and scoped docs/workflows. Do not change canonical seeds, model pins, output authority, original raw evidence, active owner branches or Age gates.

## Concrete cross-organ gap

AG12 `GeneralityEval.guard_training` now protects both registered EN/DE historical unseen prompts, but `sleep_offline.stage_ttt` stages source-valid FINAL turns into `exports/sleep-ttt-candidates.jsonl` without checking those registered holdouts. A user-visible holdout prompt can therefore appear as a `CANDIDATE_NOT_TRAINED` input or context. Staging is not training authorization, but the leakage is preventable before candidates are created.

## Frozen test-first expectations

1. Real Runtime/SQLite, actual source-bound FINAL messages generated via test seam (not native model). Register AG12 EN seed13 and DE seed13. After digest and staging, exclude any candidate whose input/target or source-valid context messages equal a registered unseen prompt; ordinary source-valid context-conditioned candidate survives. Test both languages.
2. Rotate a language suite (seed17) and restart. Historical seed13 unseen prompts remain excluded in Sleep staging; no new AG12 suite registration from Sleep itself.
3. Missing AG12 StateBoxes: normal Sleep TTT staging unchanged; no EN/DE AG12 StateBox written as side effect.
4. Corrupted/unknown-history AG12 registry: fail closed before publishing a new candidate export. Existing export, if any, remains explicitly untrusted and requires consumer-time validation; do not claim a training gate.
5. Preserve existing `test_sleep_offline`, Sleep/Context source revocation, AG12 Run14P/Run14M/Run14F/H/I and AG9 feedback regressions. No actual model or learning weights are changed.

Implementation direction: expose a bounded read-only registry union helper in AG12 and reuse it for `guard_training` and Sleep staging; do not instantiate a GeneralityEval merely to query exclusions. Use original source-valid `native_history` messages for comparisons, not only compressed digest snippets. Treat absent state as unregistered; malformed existing state fails closed. No auto-promotion.

Original source pins: Canon `218464b12a2d27d92524c751922fa8e1c3fb0ea7`, Run14P `generality.py` `43831251af47dbdd718fa9ee3289955fc7f84a87`, `sleep_offline.py` `e51766478fee915824853da7c8e73785b12e91b3`, `test_sleep_offline.py` `bdf3d5bca1444c69fcd986b3eca0a7cb5929a721`.

Negative gates unchanged: Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, jepa_weight0, Redmi unmeasured, V13 incomplete. Historical unfiltered suite RED remains unwaived. Exact-prompt staging filter is not a guarantee against paraphrases, future unregistered suites, or stale exports consumed without revalidation.
