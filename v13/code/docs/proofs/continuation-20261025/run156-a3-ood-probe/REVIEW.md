# Run156 A3 support-floor stress probe — exploratory synthetic evidence

Independent package based on Run152 `945a4b3c0d957b8cf5599889e619dd31015d3b99`. No edits to the frozen A3 worker, Run152 candidate, models, registered cohorts or Runtime. Reuses Run152's train-only leave-one-out nearest-neighbor P05 minus .02 threshold, clamped to 0.5..0.99.

Two fixed-seed synthetic 512-dimensional regimes, each 64 training, 64 same-distribution ID and 64 OOD vectors: (1) clustered ID vs random OOD: 64/64 ID accepted, 0/64 OOD accepted; floor 0.8825896444. (2) isotropic ID and OOD from the same high-dimensional uniform sphere: **0/64 same-distribution ID accepted**, 0/64 OOD accepted; LOO P05 0.0778724550 clamped to floor 0.5. The 0.5 clamp can therefore make a detector reject every genuine ID example in a valid synthetic regime. This is a counterexample to general calibration, not measured A3 model failure.

Local 7/7 software tests PASS, deterministic repeat, held-out invariance, nonfinite and zero-vector rejection, preserved gates. Original synthetic exploratory result SHA-256 `bf48f4ec8ec354a8f52ca49356eefd37d2872e367c77063af7e568e035c48393`. This run was performed locally before publishing its protocol and is **not** a pre-registered independent holdout.

Primary references checked 2026-10-25: NumPy quantile default linear method (https://numpy.org/doc/stable/reference/generated/numpy.quantile) and Sun et al., ICML 2022 (https://proceedings.mlr.press/v162/sun22d.html). Those do not justify a universal fixed 0.5 floor on V13's untrained hashed raw-byte stem.

**No gate promotion.** STEP2 UTILITY_FAIL; B3_L1 FAIL; Body_JEPA UNAVAILABLE; jepa_weight 0; DS2_H2 FAIL; V13 INCOMPLETE. No teacher, native, Redmi or whole-system measurement. Next: actual A3 raw-stem source-group holdout and measured teacher targets; preserve frozen source and compare calibrated risk without leakage.
