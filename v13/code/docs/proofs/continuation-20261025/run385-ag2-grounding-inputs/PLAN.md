# Run385 / AG2 grounding input-boundary guard — preregistration (2026-10-25)

## Ownership and source
Independent owner: scheduled GPT continuation. New review branch `codex/ag2-grounding-modality-guard-run385-20261025`, parent exact Run384/PR379 head `83104a9364331f5c84db3a568b0558c3e0fb064b`. Only `v13/code/v13/agi/grounding.py`, new `tests/test_ag2_grounding_guard_run385.py`, a dedicated workflow and this proof directory may change. Do not edit Run384 AG9 or any frozen cohort/source/model/seed hashes.

## Existing defect and RED acceptance
The AG2 `set_modality(name,on)` API uses `bool(on)`: `"false"`, `"off"`, `1` accidentally enable a modality. A caller can also set screen/camera/audio/effector to True despite their STEP8 disabled-by-default gate, and `expect` checks the enabled flag only before the optimistic mutation (time-of-check/time-of-use race). `counterfactual(...,coverage_full)` accepts zero, negative, NaN, infinity and bool, producing division-by-zero or misleading confidence.

RED tests (real `Runtime`/SQLite, no model) require: (1) reject non-bool modality flags without any state change; (2) never enable STEP8-gated modalities through this AG2 API; (3) valid text/tool booleans remain functional, disabling text prevents `expect`; (4) a modality disabled between initial check and `StateBox.mutate` cannot admit a new expectation; (5) counterfactual coverage denominator must be finite, positive, exact int/float (not bool) and reject invalid inputs; (6) valid counterfactual stays SIMULATION_NOT_FACT, including unseen OOD and finite coverage cap.

Expected RED: tests 1,2,4,5 fail on the parent; inherited `tests.test_growth` and `tests.test_agi_live` should remain green. Fix only the boundary and transactional recheck; do not add a new activation path or change the predictive model. No claim of causal world learning.

## Evidence and stop gates
Source-only Linux CI with `numpy==2.3.5` and `prompt-toolkit==3.0.52` for actual Runtime imports, pinned actions, exact HEAD, compileall, raw unittest logs, privacy scan and artifact SHA256. Preserve both RED and GREEN results; no red retuning. Current STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA/jepa_weight=0, Age0 and Redmi missing remain unchanged. This package is not STEP8 activation or full V13 acceptance.
