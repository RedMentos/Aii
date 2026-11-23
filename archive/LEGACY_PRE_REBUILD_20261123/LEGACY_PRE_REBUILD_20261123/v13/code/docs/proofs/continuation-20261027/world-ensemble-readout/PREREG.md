# WP-Z12b World-JEPA ensemble readout semantics — preregistration

Date 2026-10-27 UTC. Owner GPT-6 continuation. Review-only child of PR #746 candidate branch `codex/automation11p-world-for-event-20261027` exact parent `46aca17c50e9d291d7757434930f8f08ed85b8e4`. File ownership: `v13/code/v13/world_jepa.py`, `v13/code/tests/test_world_jepa.py`, new isolated workflow and this proof directory. No native model, frozen runtime, source cohort, seed, age authority, or Canon change.

## Counterexample and intended contract

`WorldJEPA.predict` documents its first return as the **mean prediction** over an ensemble. It stacks all trained predictors to calculate spread but returns `ps[0]` rather than the ensemble mean. Therefore every additional predictor changes uncertainty but never changes the point estimate, violating the documented ensemble contract and making reported model disagreement inconsistent with the reported centre.

RED synthetic test: three deterministic predictors produce latents 0, 2, 4; returned mean must be 2 with spread equal to the standard deviation across all three in target-latent std units. Existing code should return 0 and fail. Single-predictor output must remain unchanged. GREEN candidate: return `ps.mean(0)` while keeping bootstrap training, seeds, target normalization, spread and confidence thresholds unchanged. Existing learned-action/control and confidence tests must still pass; if ensemble averaging worsens the registered synthetic task, preserve the failure and investigate rather than claim improvement.

Proof: focused RED/GREEN, full software suite, raw source/exit/hash evidence, private byte-exact backups, independent review. Software/synthetic only; no World-JEPA causal utility, STEP2, B3, Body-JEPA or age promotion. LP1 NO_ATTRIBUTABLE_GAIN; LP2 ALIGNS_NO_GAIN; BJ1 NO_SIGNAL; STEP2 UTILITY_FAIL; B3 L1 FAIL; jepa_weight=0; Age authority=0; Redmi unmeasured; V13 incomplete.