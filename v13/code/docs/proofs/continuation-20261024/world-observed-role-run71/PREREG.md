# Run71 prereg — World Model FINAL outcome role binding

2026-10-24. Base Run70 PR103 e89bd2fbee9c009c6fd177c3b886fb8767b99aae. Own only `world_model.transitions` role consistency and corresponding Run64/Run70 SQLite fixtures plus new tests/evidence. Do not alter original action producer, learning objective, model weights, JEF/Callosum, age or gates.

Hypothesis: FINAL actions currently enter the World Model even if actual outcome role contradicts the role in the forecast profile, or if either is absent. The canonical World.transition requires exact role agreement; the lightweight World Model should not silently learn from mismatched FINAL actions. RED synthetic SQLite: matching profile/actual admitted; mismatch/missing rejected; non-FINAL failures retained with no false success.

Fix: for FINAL only, require forecast.profile dict, actual.role str and exact equality. Do not infer or rewrite missing roles. Update synthetic test fixtures to mirror actual World.forecast and ActionOutcome schema. Native/Redmi and full checkout NOT RUN unless actually available. Gates unchanged.
