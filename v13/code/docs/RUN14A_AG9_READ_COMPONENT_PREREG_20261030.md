# Run14A prereg — AG9 invalid read-side component containment (2026-10-30)

Owner: GPT-6 scheduled continuation, isolated review-only child of Run13Z PR #1317 at `7e7d57e1db88642f4fcd447eda2c012c1e625bfb`. File ownership for this package: `v13/code/v13/agi/metacog.py`, new `tests/test_ag9_read_component_run14a.py`, new isolated Actions workflow, scoped BUILD_STATE. No other owner files changed.

## Exact observed source issue
`Metacognition.record` validates component with `_component_name`, but `calibrated` and `decide` do not. An unhashable component (list/dict) reaches `components.get(component)` and raises TypeError; malformed hashable components such as None, bool, whitespace or control characters return `UNCALIBRATED` with `second_attempt=True` rather than fail-closed. Read-side invalid components must not trigger extra model compute, crash the request or mutate Store.

## Frozen candidate acceptance
Test-first focused in-memory Store; compare original exact source vs candidate. For invalid components (None, bool, list, dict, empty, whitespace, control, >64 chars), `calibrated` returns None, `decide` returns exactly `{calibrated: None, second_attempt: False, abstain: True, reason: INVALID_COMPONENT}`, without Store writes or read-side TypeError. For valid unknown components, retain `UNCALIBRATED` second_attempt=True; valid supported components preserve calibration. `record` remains unchanged. Invalid confidence continues to return `INVALID_CONFIDENCE` and abstain; validate component before confidence in `decide`. Existing Run13Y/Z focused tests remain passing. Fail closed, no extra Store mutation. No changes to stored schema, BINS, WINDOW, cohort/model/seed hashes, AG9 age_metric, thresholds or authority.

Software-only proof via isolated GitHub Actions pinned to exact source, test-first RED and candidate GREEN, privacy scan, source blob pin checks, compile and raw SHA256SUMS. Original failures are retained. This does not authorize AG9 age metric, STEP2, B3, Body-JEPA, jepa_weight, native/Redmi or whole-system promotion. Full-suite historical RED remains and is not waived.

Next command: create test-first regression and isolated workflow on this branch, collect original RED artifact, then patch only read-side validation, collect candidate GREEN artifact, independently verify raw/remote bytes, checkpoint and proceed to another canonical package.