# Run53 — World-JEPA SHADOW action-permutation provenance (2026-10-28)

Review-only child of Run52 #960 source `c13169bd1305489e57fc313a645f5c898af1ea12`; conditional on Run52 exact-head source-only GREEN. Owner GPT-6 continuation. No production merge, no Store/Runtime authority, no new cohort/model/seed.

## Reproducible defect and RED-first plan
Run51 `world_jepa_action_outcome_shadow_fit.run` creates `perm=rng.permutation(n)`, then if the action matrix is unchanged it uses `np.roll(np.arange(n),1)` to build shuffled actions but **does not update `perm`**. Its report `action_permutation_sha256` then hashes a different permutation than was used for control training. A caller may read an incorrect audit provenance hash. Probability of hitting this branch in a normal 89-row fixture is low, but an explicit deterministic counterexample must be covered.

Before changing production source, add a focused test forcing the first RNG permutation to identity and then delegating all subsequent WorldJEPA RNG calls to the real NumPy generator. Assert report digest equals the effective rolled permutation, not the initial identity. Original test-only CI must be RED at this assertion, preserving its raw ZIP.

After original RED, change exactly the fallback branch to update `perm` before creating `shuffled`. Re-run exact-head focused and full software suite, source pins, privacy/diff, closed raw evidence. Keep default-seed observed/control outputs and report structure unchanged except correct provenance in fallback. Keep frozen `world_model.py`, `world_jepa.py`, Run50 adapter and Run48 holdout bytes unchanged. No native/Redmi claims; Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight=0, full V13 incomplete.

## Acceptance
Explicit RED then GREEN on identical test with only fallback provenance fix; report digest represents actual effective permutation, no input mutation or decision authority. Independently inspect source and raw CI. Next package: assess meaningful synthetic World-JEPA action-conditioning against persistence and shuffled controls, without claiming causality.
