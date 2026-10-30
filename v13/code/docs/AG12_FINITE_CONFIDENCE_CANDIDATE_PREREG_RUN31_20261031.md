# Run31 prereg — AG12 native token-confidence finite candidate (SHADOW)

Owner GPT-6 scheduled continuation, 2026-10-31 UTC. Review-only child of Run30 at exact `709899cf7832b753c2c344c54fa33f816a6b85b0`. Binding Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7`. Existing production `v13/code/v13/agi/solver.py` blob `66a9419143c456f01747b4796fb327b3b36711b3` is **frozen**; do not modify it, Run24–27 registered source/seed/model hashes or their native evidence.

## Reproduced failure hypothesis (test before candidate)

The existing `confidence(metrics)` uses `max(0.,min(1.,float(v)))` on unvalidated native token probabilities. Python `min(1., float('nan'))` yields 1.0; positive infinity also clamps to 1.0. Thus malformed/nonfinite `field_min_prob` can silently become maximal confidence **before** AG12's downstream nonfinite confidence veto. Booleans are accepted as numeric, and extremely large integers may overflow `float()`. This is a potential wrong-vote / wrong-calibration path, not evidence that the Run27 native runner emitted invalid values. No historical native result may be reinterpreted without raw proof.

## Candidate intervention and frozen tests

Create a standalone, **not integrated** pure `safe_confidence(metrics)` adapter in `v13/agi/solver_confidence_finite_candidate.py`, preserving priority `field_min_prob > field_mean_prob > mean_prob`, default `(.5,'none')` only for genuinely absent token-confidence metrics, and finite valid numeric clipping to [0,1]. If a present highest-priority key is malformed, nonfinite, boolean, overflowed or structurally invalid, return `(0., 'invalid:<key>')` without falling back to a lower-priority key. No exceptions for untrusted metric values, no network/model/Store, no authority. If token_confidence container is malformed, fail closed. Test original NaN/Inf red witness, candidate invalid values, priority poisoning, finite clamp, missing fallback, and side-effect-free deterministic behavior.

Do not edit original `solver.py` or register the candidate as an active voter while SourceHandoff/current native cohorts remain frozen. Later, after independent review, integrate under a new source-bound **disjoint** AG12 native cohort with a genuine valid-confidence parity baseline, invalid-confidence negative control, and exact confidence telemetry; no rescore of Run27.

Gates: Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, jepa_weight=0, no learned German transfer, no Redmi, whole V13 incomplete. No production merge or auto-merge.
