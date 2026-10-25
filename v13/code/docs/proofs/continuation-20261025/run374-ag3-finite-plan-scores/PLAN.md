# Run374 — AG3 long-horizon plan evaluator must fail closed on nonfinite scores (preregistered)

Parent: Run372/PR367 verified checkpoint `8d204939c62ba35ef6a457cebd469bafbb1d4f2d`. Independent software branch while Run373 pinned native diagnostic is serialized separately; no shared source ownership.

Owned: `v13/code/v13/agi/goals.py`, new `v13/code/tests/test_ag3_finite_plan_scores_run374.py`, new `.github/workflows/run374-ag3-finite-plan-scores.yml`, this proof directory. No change to Age rights, scheduler, model/cohort hashes, goal persistence revision or autonomous execution authority.

Observed hazard: `GoalStore.score_plans` converts evaluator outputs using `float(...)` and ranks by `value-risk`. An evaluator returning NaN, +/-Infinity, bool or a numeric string can produce an invalid/unbounded score; even individually finite extreme floats can overflow when subtracting. A bad plan can rank first or poison JEF's ordering, contrary to calibrated planning. No plan executes in this module, but its ranking is a decision input.

RED-first actual Runtime/SQLite tests: finite scores rank correctly and stably on ties; NaN, infinities, booleans, numeric strings, None and nonfinite margin must raise ValueError rather than returning a candidate ranking; after rejection, stored goal state and Age rights remain unchanged. Existing AG3 goal/wake tests must remain green.

GREEN: require exact int/float (excluding bool) and `math.isfinite` for both evaluator components and the derived margin, before sorting. Preserve return shape `{'plan','value','risk'}`, stable ties and no plan execution. This is a score integrity gate, not a learned planner or safety guarantee for finite but wrong evaluator predictions.

Evidence: source-bound RED/GREEN Actions, inherited AG3 tests, compileall/privacy, raw receipts with hashes and private Library byte comparisons. Negative STEP2/B3/Body-JEPA/jepa_weight/Redmi/whole V13 gates remain unchanged. Next independent package: inspect native Run373 evidence and resume separate Context OS/JEPA work.
