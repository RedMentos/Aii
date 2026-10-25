# Run366 — AG12 finite confidence before JEF ensemble/calibration (preregistered)

Parent: `codex/organ-checkpoint-path-safety-20261025` @ `554cbc46a8845284a55e504b5e28015ac5072b0a` (Run365 branch-scoped GREEN, not main).
Production blobs at parent: `v13/code/v13/agi/base.py`, `v13/code/v13/agi/solver.py` (read-only until RED).
Owned files: these two, new `tests/test_agi_solver_finite_run366.py`, isolated `.github/workflows/run366-ag12-finite-confidence.yml`, and this proof directory. No model downloads, native jobs, or writes to shared BUILD_STATE.

## Actual source-level risk
`agi.base.clamp01(x)` uses `max(0.,min(1.,float(x)))`; Python's comparisons with NaN make this produce a finite **1.0** for `NaN` and `+Infinity`. The AG12 native solver similarly clamps `token_confidence` without a finite check. `solver.combine` sums caller-provided confidence directly, so NaN/out-of-range values can determine a coalition vote. `GeneralityEval.run` persists `clamp01` into ECE/Brier, and AG9 metacognition reuses it. Invalid numerical measurements must not become high confidence or false calibration authority.

## RED-first checks
- `clamp01(NaN/+Inf)` returns 0, not 1; ordinary finite clamping unchanged.
- `solver.confidence` marks nonfinite numeric field as zero confidence (not a valid native probability).
- `solver.combine` must not let NaN or >1 confidence overpower two valid agreeing bodies.
- Actual `Runtime`/`GeneralityEval` persisted all-wrong synthetic run with NaN confidence has finite 0-confidence rows and ECE/Brier 0; no model or heldout training.
- Existing `test_agi_solver` and `test_agi_live` must remain passing. Tests committed before source patch; isolated Actions raw RED/GREEN with exact checkout, SHA, privacy scan and private checkpoint.

Only finite score normalization is in scope. Do not alter registered model/cohort/seed hashes, learning/age approvals, original negative gates or user-visible claims. If a nonfinite input arrives, fail closed at 0 confidence; missing metrics retain the existing 0.5 unknown baseline.
