# Preregister World-Model finite-vector complex/datetime poisoning refusal (2026-10-29)

Review-only child of PR #1150 branch at `cdf5f48c5bacbca494674a2554e96bf1e4e8dc2b`. Canon, registered cohorts, seed and model pins unchanged.

## Concrete observed bug
`world_model._finite_vector` checks `isinstance(x, np.number)` then `math.isfinite(float(x))`. On Linux NumPy 2.3.5, `np.complex128(1+2j)` is silently cast to `1.0` with ComplexWarning and incorrectly accepted as valid state; `np.timedelta64(1,'s')` raises TypeError instead of failing closed. `coverage` may therefore report support on a complex-valued state, violating the numeric integrity guard.

## Frozen acceptance
1. Reject `np.complex128`, `np.complex64` and Python complex states, including zero imaginary part, without warnings or exceptions.
2. Reject `np.timedelta64` and malformed numeric wrappers without exceptions.
3. `coverage` on invalid state reports `invalid=True`, zero samples, no OOD confidence.
4. Existing finite real Python/NumPy scalar vectors remain accepted, boolean/NaN/Inf rejected.
5. Existing real Store, C5 stage, World-JEPA fixture and World-Model counterfactual tests remain green. No learned weights/fit objective/holdout split/seed/authority changes.

Proposed minimal fix: explicit complex scalar refusal and exception-safe finite real conversion in `_finite_vector`. This is Linux software numeric integrity only, not causal utility or native/Redmi proof.
