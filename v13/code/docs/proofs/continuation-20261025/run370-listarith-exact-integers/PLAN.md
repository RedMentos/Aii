# Run370 — R4 list arithmetic rejects non-integer model values (preregistered)

Parent: Run368/PR363 exact `115c12bf00d04dd6cb461a317e29d14e66bf1091`; independent of Run369 native C3 ownership. Branch-scoped review only, not main.

Owner: `v13/code/v13/agi/listarith.py`, new `v13/code/tests/test_listarith_exact_integers_run370.py`, new isolated `.github/workflows/run370-listarith-exact-integers.yml`, this proof directory. No other runtime, cohort, source pin, model, seed, or authority change.

Hypothesis: `encode()` and `compute()` currently call `int(value)`, silently converting bool, fractional float, numeric string, or other model-produced non-integer values. `read_values()` trusts the JSON grammar but can receive an invalid shape from a runner. If a coerced integer happens to appear elsewhere in the user's text, the source-number guard may accept the wrong computation. This violates typed READ_SCHEMA and risks fabricated numeric results.

RED-first: adversarial tests must reproduce acceptance of non-integer values in the model-read and recipe paths. GREEN: require exact Python `int` (excluding bool) at the read boundary, encode boundary, and compute boundary. Preserve existing source-occurrence guard, aggregate skip, deterministic fast arm, operation detection, tool enable/approval/Age, German and English tests. No changes to `decode()` unless a separate regression justifies it.

Test plan: isolated `unittest` for booleans, fractions, numeric strings, valid signed integers and existing number occurrence controls; inherited `test_listarith_german_run362` and `test_listarith_fast_rows_run363`, plus existing R4 tests if available. Capture exact-head GitHub Actions raw output, source hashes, privacy scan, and final negative gates. No native model/phone test; `STEP2_EXIT`, B3, Body-JEPA, jepa_weight, whole V13 remain NOT_PROMOTED. Record any failed CI attempt unchanged.

If RED or GREEN cannot run, retain a candid unverified review branch; do not call it tested. Next independent package: inspect actual native Run369 results and continue a distinct blueprint component.
