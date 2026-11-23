# WP-T14 FINAL latency boundary completeness — independent review prereg 2026-10-28

Review-only child of #831 at `28320b825d789ecc4d505a2b86279bcb2fc89927`. Owner GPT-6 independent control-fabric review; #829 source remains untouched. Prereg before RED tests or fix.

## Counterexample and expected contract
Existing `durations` accepts sparse stage marks by design, but also accepts a FINAL record missing **ingress** or **finished**. A FINAL without finished is an open interval: assigning the last observed timestamp to the previous stage may produce a deceptively low control P95 and configured `PASS`. Missing ingress similarly has no measured start. A synthetic FINAL with one valid complete mark set and one boundary-incomplete mark set must report `invalid_stage_marks >= 1` and `INCOMPLETE_EVIDENCE` under a configured control limit, never PASS. Preserve legitimate sparse interior-stage historical fixtures and the existing no-limits behavior.

Test RED first on current source, then narrow change to require `ingress` and `finished` in `durations` before accepting any per-turn latency. No runtime, Canon, existing cohort, model, seed, threshold or age authority changes.

Run focused control-budget suites in branch-only Linux software CI with raw exits, compile, privacy scan and diff check. This is **not** WP-T14 hardware calibration or Redmi measurement. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 heldout FAIL, jepa_weight=0, Age0 RECORD_ONLY; no whole-system or gate promotion.
