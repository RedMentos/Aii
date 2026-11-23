# Run14Y — World-model observed-transition JSON source admission (2026-10-30)

Parent: Run14X PR #1339 at exact `3aad48000d9b1fe543b7d84b0aef342be2a8258e`; inherits Run14W integration and Run14V effort, all review-only. Owner GPT-6. Scope `v13/code/v13/world_model.py`, one new test module, review workflow and checkpoint. Canon, cohorts, frozen model/seed hashes and negative gates unchanged.

## Observed gap and rationale

Run14U World F4 enforces duplicate-key rejection on action/outcome receipts, including escaped JSON aliases, yet `world_model.transitions()` and `world_model.for_event()` still use ordinary `json.loads` on stored action expected/outcome and C5 ActionSelection packets. Python silently uses the last duplicate key. This admits ambiguous historical action evidence to the separate T8 forward/inverse world-model fit and to counterfactual forecasts. Reuse the already-implemented strict World object parser; do not redefine a different policy.

## Frozen test-first contract

1. A valid action with unique forecast, outcome and unique committed C5 selection remains an observed transition.
2. Duplicate nested forecast key, duplicate action-outcome key, or duplicate C5 ActionSelection route key — including escaped aliases — must exclude the entire transition without altering raw stored rows.
3. A duplicate forecast key in `for_event` returns `SIMULATION_UNCERTAIN`, `INVALID_OBSERVED_STATE`, zero confidence and HYPOTHESIS authority; no fabricated state.
4. Ordinary finite/numeric, train-only support, World F4 receipt and existing T8 tests remain green. No change to fit formula, registered data, labels or runtime permissions.
5. Test-first original failure and candidate result must be separately recorded. Evidence is software/SQLite only; no Linux-native model, Redmi, STEP2/B3/Body-JEPA/age promotion.

Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; jepa_weight=0; V13 incomplete.
