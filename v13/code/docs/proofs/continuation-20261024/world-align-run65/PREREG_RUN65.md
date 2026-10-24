# Run65 prereg — fail-closed World-Model state-align numerical stability

2026-10-24. Base Run64 PR97 db29745e408b9fde751e8d54ce7a1af45030483e. Owner only `v13/code/v13/world_model.py`, `v13/code/tests/test_world_align_finite_run65.py`, `v13/code/docs/proofs/continuation-20261024/world-align-run65/*`. No other owner's files or native jobs.

Independent Run64 review RED: 24 otherwise valid synthetic SQLite actions with finite latent=[1e308,1e308] produce ridge matmul overflow; `fit` persists `state_align.status=MEASURED` and NaN R² values. This violates truthful measured evidence. Original RED and exact Run64 source retained.

Fix plan: isolate optional state-align fitting in a numerically checked computation; use NumPy errstate(over/invalid/divide='raise'), reject nonfinite metrics and ill-conditioned/nonfinite results with `state_align.status=UNAVAILABLE`, explicit reason, no fabricated scores. Keep valid forward/inverse fit and heldout split, targets, source rows, authority and gates unchanged. For latent dimension larger than training sample count, use mathematically equivalent dual ridge to avoid a dense (d+1)^2 Gram solve, with numerical parity checks on a small fixed dataset. Do not alter native weights, model outputs or preregistered cohorts.

Predeclared tests: huge finite latent red -> UNAVAILABLE no NaN persisted, valid small latent -> MEASURED finite, primal/dual parity on fixed matrix, no-latent unchanged, original Run64 14 regressions, Python -O. Exact current source test, full suite/privacy/Redmi separate. Gates STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, V13 INCOMPLETE.
