# WP-T8 for_event observed-state integrity preregistration

Date 2026-10-27 UTC. Owner GPT-6 continuation. Review-only child of PR #745 at exact parent `e8edc8a83bbf66624cda9482367daf7acabc3eee`. This is a distinct live Sleep B entrypoint, not a rerun of world_model.fit. Ownership: `v13/code/v13/world_model.py`, `v13/code/tests/test_world_model.py`, new isolated CI workflow, and this proof directory. Frozen runtime/model/cohorts untouched.

## Counterexample

`world_model.for_event(store,event_id,action)` selects an action's recorded forecast and directly decodes `expected`, then constructs a state from `input_chars`, `resource_state` and `created`. A malformed JSON payload raises; absent or invalid fields can be silently replaced by a fabricated zero-input state or propagate nonfinite numbers into a Sleep B route hypothesis. The ingestion fix in PR #745 protects `transitions` but not this direct consumer.

RED tests: malformed JSON, missing forecast/input, NaN/boolean/negative input, nonfinite created timestamp and invalid resource state must all yield an explicit `SIMULATION_UNCERTAIN` / `INVALID_OBSERVED_STATE` result with zero confidence and HYPOTHESIS authority, not crash or synthesize an observed state. A valid observed event still delegates to `counterfactual` (with no fit it returns NO_WORLD_MODEL). Missing action still returns NO_OBSERVED_STATE. No change to model coefficients, coverage formula, gates, or labels for valid data.

Verify RED focused, GREEN focused, full suite, compile, privacy and diff with exact raw artifacts, private byte-exact backup, independent review. LP1 NO_ATTRIBUTABLE_GAIN, LP2 ALIGNS_NO_GAIN, BJ1 NO_SIGNAL, STEP2 UTILITY_FAIL, B3 L1 FAIL, jepa_weight=0, Age authority 0, Redmi unmeasured, whole V13 incomplete. No main merge.