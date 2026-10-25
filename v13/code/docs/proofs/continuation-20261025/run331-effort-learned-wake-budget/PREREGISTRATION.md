# Run331 preregistration — learned wake cannot exceed actual effort band

UTC 2026-10-25. Independent owner: **only** `v13/code/v13/effort.py`, new `v13/code/tests/test_run331_effort_learned_wake_budget.py`, new source-only CI and this proof directory. Parent Run330 source `c847c4244ccb34f950e5be05acaa8078dfbbde49` / PR327; native Run330 model job is separate and must not be interrupted. No edits to native C++/training, Canon, model/seed/cohort, runtime interaction contracts, Age or approval rights.

## Observed policy bug, not yet native evidence

Existing `effort.plan_for()` maps BOOT `DIRECT_C_NATIVE` (<0.2) to **zero bodies**, `C_NATIVE_ONE_BODY` (0.2..0.5) to **at most one body**, and higher focal bands to up to both. Existing `constrain()` writes `plan['wake_ceiling']` as a hard resource/deadline ceiling (often `both`) without folding in the effort band's compute budget. Existing `resolve_wake()` applies a learned wake only to `plan['wake_ceiling']`; therefore adaptive mode with DIRECT_C_NATIVE or ONE_BODY band can be overridden by a learned `both` action and execute unbudgeted B1+B2 wake. This is a source-observed gap; no claim of observed real learned action or Redmi cost. Original test `tests.test_effort` covers resource deadline and forced mode, not this band leak.

## Frozen correction and acceptance

Within `resolve_wake()` only, intersect the learned action with **both** the band maximum (`DIRECT_C_NATIVE→none`, `C_NATIVE_ONE_BODY→one`, `FOCAL_TARGETED/DEEP_FOCAL→both`) and the existing hard resource/deadline/observer ceiling. Preserve `one_body` preference, existing hard cap, user-forced modes, Age constraints, plan creation, telemetry packet shape and BOOT values. Unknown band/action fail closed. Do not let learned policy increase autonomous Age/effort or bypass `observers=False`, RED resource, deadlines or exact-output direct. No new rights, models, learned weights or activation.

Red-first synthetic tests: all four bands, learned `none|detail|gist|both`, zero body direct, at most one body in one-body band, hard resource/deadline cap, user-fixed mode unaffected, unknown action/band fail closed; run original `tests.test_effort` and privacy. Dedicated source-only CI, no model/Redmi claim. Original negative gates: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, Redmi MISSING, V13 INCOMPLETE.

**Next command:** source-only tests and privacy; inspect Run330 native job independently; if tests pass, checkpoint raw hashes and continue another canonical package. No production integration claim from a review branch.
