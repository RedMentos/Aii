# World-Model counterfactual output-domain validity — preregistration

UTC 2026-10-29. Review-only child of PR #1134 at `7160d03393510e47db8f2587ade0d4c9b810b101`. Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` unchanged. No production merge, native/Redmi claim, learning/age authority, model/source/seed/cohort rewrite.

## Concrete functional counterexample

`world_model.counterfactual` accepts finite ridge predictions even when the predicted `log1p(duration)` is negative, `log1p(output_chars)` is negative, or `success` is outside [0,1]. It can then return a **negative duration_s** while declaring `SIMULATION_SUPPORTED` with high in-support confidence. Such an output is not a physically meaningful digital action/outcome forecast. Existing input-finiteness and train-only support guards do not cover output domain.

## Registered tests

1. With 16 train-only support points at/near the query and identical ensemble weights, an in-support predicted `log_duration=-0.5` must **not** return a negative duration or a supported forecast.
2. Same support with predicted `log_chars<0`, `success>1` or `success<0` must be `SIMULATION_UNCERTAIN`, zero confidence, no prediction and an explicit invalid-evidence reason.
3. A valid prediction with `log_duration>=0`, `log_chars>=0`, `success in [0,1]` remains supported with original numbers; a valid exact zero remains allowed.
4. Original `test_world_model.py` suite, no-model/OOD/fitted-support tests, privacy and diff checks stay passing. Existing negative gates and source pins unchanged.
5. Preserve test-only RED and corrected GREEN CI raw, hash/CRC/private backup. No synthetic test is promoted to learned utility or native proof.

## Minimal candidate

Validate the predicted target domain **before** converting `log_duration` via `expm1` and before returning any confidence or `SIMULATION_SUPPORTED`. Return the existing `_invalid_numeric` uncertainty envelope on violation. Do not silently clamp out-of-domain predictions, refit weights, change `fit`, touch historical registered datasets, change `REVISION`, or update runtime defaults. This is a read-only output validity rule, not a world-model utility improvement.

Owned files: `v13/code/v13/world_model.py` (counterfactual domain guard only), `v13/code/tests/test_world_model_output_domain_20261029.py`, `.github/workflows/v13-worldmodel-output-domain-20261029.yml`, this prereg, dedicated BUILD_STATE.
