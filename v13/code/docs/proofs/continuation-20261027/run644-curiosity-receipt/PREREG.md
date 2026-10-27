# Run644 preregistration — JEF AG5 curiosity receipt, 2026-10-27

Base: Run643 PR642 head df96269a179b9942ee517f02cbb7069ed80c5ba5 (review-only). Canon remains unchanged. File ownership: `v13/code/v13/agi/live.py`, new `tests/test_run644_curiosity_receipt.py`, scoped workflow and proof only. Do not edit frozen native C3 cohorts, weights, original gates, learning authority or age.

## Observed source defect / falsifiable claim
In `goal_turn`, `g.curiosity.observe(..., 0. if status=='FINAL' and not asked else 1.)` precedes checking the actual persisted assistant FINAL message. A fake FINAL or a stored refusal can therefore become zero-error learning-progress evidence. Even `grounded_error=0` may be based only on the same status. This is a real AG5 state update (not a mere report).

## Prospective acceptance
On fresh SQLite Runtime, five controls:
1. caller FINAL and grounded_error=0 without assistant FINAL => curiosity error **1**;
2. persisted leading "I don't know" => **1**;
3. persisted `metacog_abstain` => **1**;
4. normal same-event same-session persisted nonempty FINAL => **0** (preserve positive path);
5. status ERROR despite persisted FINAL => **1**.
No attempt to classify semantic correctness. Existing Run633 noanswer goal completion tests and AGI live tests must continue to pass. `STEP2 UTILITY_FAIL`, `B3 L1 FAIL`, `Body-JEPA UNAVAILABLE`, `jepa_weight=0`, Redmi unmeasured, V13 incomplete.

## Procedure
Commit RED tests first; execute CI and preserve its failure. Repair only the receipt gating and rerun identical controls plus adjacent regression. Use exact-source GitHub Actions logs and privacy check. Do not call a unit success native/Redmi or full acceptance. Save report and next exact command on a separate review branch; no main merge.
