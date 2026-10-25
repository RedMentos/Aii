# Run262 — fitted WorldModel source validation cost (prereg 2026-10-25)

Base: verified PR259 head `28a9ebcbe51661adb716ae5bdd9ca999dbf2af3c`. Exclusive ownership: new benchmark script, workflow, proof directory. No WorldModel/Runtime/Store changes, no native model job, no registered cohort, no new tool authority. This is **Linux actual Store with synthetic actions**.

Problem: PR259 source-bound fitted state validates every training action and source on each load, up to 2048 rows. That is correct for revocation but may cause high per-turn latency on Redmi. Before caching or optimizing, measure actual cost with unchanged production source and preserve revocation semantics.

Preregister: independent fresh temporary Runtime+Store at N=16,128,512,1024, deterministic FINAL actions, one ActionSelection and source per action, fit once, five `load` and `counterfactual` calls each, report median wall-clock milliseconds (not phone energy or latency). Delete one trained source and require load=None plus explicit-state counterfactual TRAINING_SOURCE_UNVERIFIED. Preserve source/script SHA256 and full raw log including failure. No numerical pass threshold or performance claim preregistered; exploratory measurement only.

Next: inspect exact-head CI raw output, compare scaling; if high, propose revocation-safe change journal/generation counter only after a separate threat model and source mutation coverage. Do not bypass per-use validation without a proven invalidation mechanism. STEP2/B3/Body-JEPA/jepa_weight and full-system gates unchanged.
