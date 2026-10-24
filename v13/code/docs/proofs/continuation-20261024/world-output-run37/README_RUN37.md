# V13 Run37 — World-Model impossible-outcome fail-closed candidate

Base PR #72 `003688c5f54fa87edae0f6496c4955484b981256`, original Run28 world-model candidate Git blob `682073e55ff2698edcf4d9d7dd9f8d3662868acf` (Run29 SQLite tests same source). **Isolated candidate only**, no production mutation or model calls.

## Finding

The original `counterfactual` uses ridge regression for `log1p(nonnegative duration)`, binary success and `log1p(nonnegative output chars)/8`. It checks finite values but not physical output domains. A supported in-distribution prediction can report **negative duration** or success >1. The Run37 synthetic negative control reproduces `SIMULATION_SUPPORTED` with duration -0.259 s and confidence >0.5. This is not a measured model failure rate, only a valid counterexample to the guard.

## Candidate

A single source-bound insertion after finite checks rejects mean log_duration <0, success outside [0,1] or mean log_chars <0 with `SIMULATION_UNCERTAIN`, confidence 0 and reason `IMPOSSIBLE_PREDICTED_OUTCOME`. No clipping, no invented outcome, no change to training, coverage, source, confidence threshold, model architecture or canonical gate. The complete Run28 source is copied to `scripts/world_model.py` with only this insertion. The original Run29 SQLite integration tests are copied byte-identically; eight additional candidate tests are included for full-checkout execution.

## Evidence

Local isolated NumPy seam replay: **10/10 software/synthetic tests PASS**, compileall PASS. Original impossible outcomes and guarded controls are recorded in `evidence/run37-original-vs-guarded.log`. The full candidate's eight tests and inherited seven SQLite tests were **NOT RUN locally** because the full source checkout is inaccessible through the current container network. The seam copies the relevant Run28 `counterfactual` and coverage math; it does not replace actual full-source execution.

Next: independent full-checkout test of all 15 candidate+SQLite tests and original suite, privacy scanner, then actual held-out action/outcome utility study. Preserve all original negative gates: STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; jepa_weight=0; Z6a FAIL; Z8 FAIL; full V13 INCOMPLETE. No Redmi or native model proof.
