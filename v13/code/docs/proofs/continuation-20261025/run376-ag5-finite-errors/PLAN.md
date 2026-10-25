# Run376 — AG5 curiosity prediction-error evidence must be finite (preregistered)

Parent: verified Run374/PR369 checkpoint `11a4eb18220d64f7b6ac1c546de0ee854b33ebf4`; independent of Run375 B3 Callosum and Run373 pinned C3 native owners. Review branch only, not main.

Owned: `v13/code/v13/agi/curiosity.py`, new `v13/code/tests/test_ag5_finite_errors_run376.py`, isolated `.github/workflows/run376-ag5-finite-errors.yml`, this proof directory. No shared `clamp01` changes, no model/cohort/seed edits, no Age/permission change.

Observed hazard: `Curiosity.observe(region,error)` passes raw model/measurement error through shared `clamp01`, which intentionally converts NaN/Inf to 0 for *confidence*. For an error signal, NaN -> 0 fabricates perfect prediction and can create false learning progress and misdirect intrinsic exploration. Booleans and numeric strings are also silently coerced.

RED-first actual Runtime/SQLite tests: NaN, +/-Infinity, bool, numeric strings and None must raise ValueError without adding visits, regions or changing state. Finite 0..1 error history, novelty and progress remain unchanged; finite out-of-range errors retain original 0..1 clamping; Age-0 SELF cannot autonomously choose a learning region.

GREEN: check exact int/float (excluding bool) and `math.isfinite` before calling shared `clamp01`; fail closed for malformed evidence. Preserve AG5 reward formula, WINDOW, MAX_REGIONS, Age gate and original state revision. This is input integrity only, not proof of learned curiosity/AGI.

Evidence: source-bound RED/GREEN Actions, inherited AG5 tests, compileall/privacy, closed raw SHA receipts and private Library byte comparison. All original STEP2/B3/Body-JEPA/jepa_weight/Redmi/whole V13 negative gates stay unchanged.
