# WP-T8 world-model finite-data / finite-confidence review preregistration

Date 2026-10-27 UTC. Owner GPT-6 continuation. Review-only child of PR #744 at exact parent `55314b3e2d97d3d7b4ce2513e54ccd36486d07c8`. File ownership: `v13/code/v13/world_model.py`, `v13/code/tests/test_world_model.py`, new isolated workflow and this proof directory. No frozen `runtime.py`, model weights, registered cohorts, seeds, canonical blueprint, or shared BUILD_STATE changes.

## Counterexamples to test BEFORE changing source

1. The persisted actions table can contain malformed/legacy forecast/outcome JSON and nonfinite, boolean, negative duration or output-character values. Current `transitions` calls `json.loads`, `math.log1p` and `state_vec` without rejecting them; one bad row can crash fit or poison a fitted state. Expected: skip invalid observations, retain valid ones and their original ordering; invalid latent vectors become unavailable rather than learned evidence.
2. `counterfactual(store, s, a, st=...)` accepts nonfinite state vectors and externally supplied corrupted fit matrices/support. Python `min/max` on NaN can turn nonfinite confidence into 1.0. Expected: never emit SIMULATION_SUPPORTED or positive confidence for invalid query state, fit, or numerical prediction; return SIMULATION_UNCERTAIN, reason INVALID_NUMERIC_EVIDENCE, authority HYPOTHESIS. Valid state and fit preserve the existing formula, split, model coefficients and confidence thresholds.
3. A malformed stored fit loaded by `load` must be rejected on use; a valid fit remains usable. A held-out-only action stays unsupported as in PR #740.

Verification: focused RED with exact source blob/exit logs; GREEN focused, full software suite, compile, privacy scan, diff check; raw artifacts, hashes, no evidence promotion. No native/Redmi run. LP1 NO_ATTRIBUTABLE_GAIN; LP2 ALIGNS_NO_GAIN; BJ1 NO_SIGNAL; STEP2 UTILITY_FAIL; B3 L1 FAIL; jepa_weight=0; Age authority=0; V13 incomplete.

Do not silently modify or delete any historical failed run. No model retraining, cohort edits or main merge.