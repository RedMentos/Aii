# Z12c calibration review follow-up: control confidence separation (2026-10-27)

Parent exact reviewed SHA: `293ccf7dd8b24a9dd25e0ceffac1792e8e14cc53` (PR #649, NOT main). Independent child branch, file ownership: `scripts/z12c_slot_world_jepa.py`, `tests/test_z12c_control_calibration.py`, scoped workflow/proofs. Canon, models, seeds 201/202/203, cohorts, thresholds and trained weights remain unchanged.

## Discovered regression before patch
PR #649 correctly rejects `SlotWorldJEPA.confidence()` without per-operation calibration. But existing `z12c_slot_world_jepa.run_seed` still evaluates two deliberately uncalibrated controls via `cf_eval`, which unconditionally calls `confidence`: NO_ACTION has no observed operation classes except UNTOUCHED and cannot meet the calibration requirement; SHUFFLED_ACTION has no calibration call. Therefore the registered Z12c ablation runner now fails instead of producing its control retrieval comparisons. Do NOT manufacture a calibration set for NO_ACTION, relax the new calibration gate, or alter the original experiment.

## Acceptance before edits
1. A control evaluator can obtain `predict`, `latent` and `slot_errors` without calling `confidence`; its returned confidence must be 0 and label `SIMULATION_UNCERTAIN`, not fabricated model authority.
2. Primary JEPA evaluator still calls calibrated `confidence` and refuses an uncalibrated primary. Existing confidence/error records and original preregistered C1–C7 calculations remain unchanged.
3. Original NO_ACTION and SHUFFLED_ACTION calls explicitly select no-confidence control mode, with no changes to model fitting, action information, seeds, data, thresholds or metric denominators.
4. Focused mock counterexamples and original slot/calibration/checkpoint tests pass in isolated Linux CI. If a full experiment is run later, preserve exact original 201/202/203 registered data and negative gates.
5. Privacy scan CLEAN, closed raw CI output, branch-specific BUILD_STATE note and remote-byte verification required. This is a software regression repair only; no native/Redmi/Body-JEPA/STEP2/B3 promotion.

RED should demonstrate that the existing runner's control calls fail on the calibrated parent before the repair. GREEN must prove that they no longer call confidence. No claim of full-suite PASS without a full-suite run.
