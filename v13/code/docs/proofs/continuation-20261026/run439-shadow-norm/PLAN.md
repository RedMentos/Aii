# Run439 — F7 external shadow learner native-embedding norm integrity

Date 2026-10-26. Owner GPT. Independent source-only learning-path integrity package on corrected Run434 checkpoint `7916b29f7f3904689fd2d484f397bd3db1b00a27`, no changes to active Run437 native owner, registered STEP2 model/seed/source hashes, age or learning approval gates.

## Counterexample

`v13.learning_worker.features` validates every raw embedding coordinate as finite but then uses `np.linalg.norm` (sum of squares) without checking that the norm itself stayed finite. A vector with finite coordinates `[1e308,1e308]` overflows to infinity; dividing by infinity silently returns an all-zero feature row. That is a materially false representation of the input and can poison external shadow-route candidate training without a clear diagnostic. The native encoder normally yields modest vectors, but integrity should fail closed under corrupted/extreme inputs.

## RED-first and fix

Add focused tests before modifying worker: reject finite-coordinate overflowed norms and any nonfinite coordinate; preserve exact normal-range normalization and route-head training behavior. Record actual RED Actions and raw artifact. Then check `np.isfinite(norm)` after `np.linalg.norm` and before normalization, raising `ValueError` for overflow. Do not change normal-range math, weights, optimizers, learning budgets, checkpoint schema, or default RECORD_ONLY. Run inherited learning_worker, exact-label and plasticity tests; privacy scan; closed raw SHA. This is software NumPy integrity only, **not** native sparse body training, C2/C3 online learning or JEPA proof.

All negative gates unchanged: STEP2 UTILITY_FAIL, B3 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, Redmi unmeasured, whole V13 incomplete.
