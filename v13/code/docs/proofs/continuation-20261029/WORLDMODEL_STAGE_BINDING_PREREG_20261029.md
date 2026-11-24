# Preregister World-Model C5 selection stage binding (2026-10-29)

Review-only child of PR #1146 exact head `fa71bca01ad5a117b460015ac80d9bbc2ea56857`. Canon, model, source, seed and registered cohorts unchanged at preregistration.

## Defect
`v13/world_model.py::transitions` reads C5 `ActionSelection` rows without distinguishing `stage=PREDICTION` from `stage=COMMIT`. The actual producer in `v13/focal.py::select(predicted=...)` emits both. A prediction-only packet can therefore label a dispatched action as if C5 had committed it; conversely, one prediction plus one commit makes the current `len(sel)!=1` guard drop a valid observed transition.

## Frozen witness and acceptance
1. PREDICTION-only selection is not a training transition.
2. PREDICTION + COMMIT before dispatch admits exactly the COMMIT route.
3. Two COMMIT selections remain ambiguous and are rejected.
4. Legacy single selection with no stage remains supported for the existing recorded software cohort.
5. Unknown/invalid stage refuses training; excess packet rows refuse rather than silently truncating an ambiguity.
6. Original pre/post-dispatch, generation, real Store fit/restart and World-Model tests remain green.

Proposed minimal change: inspect a bounded number of same-event, same-generation, pre-dispatch selection packets, refuse truncated or invalid evidence, ignore explicitly provisional PREDICTION packets, require exactly one COMMIT or legacy selection. No fit objective, heldout split, model pin, learning authority or gate change.

Claim limits: Linux software/Store only; no native, Redmi or causal utility. Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight0, V13 INCOMPLETE.
