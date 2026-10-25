# Run298 — mixed terminal WorldModel outcome regression: GREEN (software)

UTC 2026-10-25. Owner: GPT-6; branch `codex/world-terminal-outcomes-run298-20261025`; base `codex/ctxos-bound-source-user-run296-20261025` at `2bcb475abcd26e2eef1083f4bf3bde3833dc5196`; review PR #297. Independent of Run297 native Context OS owner.

## Actual defect and repair
`world_model.transitions` extracted non-FINAL terminal observations as success=0, but `_action_binding` rejected all non-FINAL statuses, so the production Store `fit()` returned `SOURCE_UNVERIFIED` when an observed failure was in its training set. The fix applies the same closed terminal status allowlist (`FINAL`, `ERROR`, `DEADLINE`, `CANCELLED`) to extraction and source binding. `DISPATCHED`/unknown statuses are excluded even with a forged outcome. Existing source revalidation, revocation, exact action/selection/outcome digest, numeric filters and hypothesis-only counterfactual authority remain unchanged. Canon, model/seed/source cohorts and persistent WorldModel revision were not changed.

## Actual evidence (no invented native proof)
- RED before source change: commit `7da9c097aaf685c406d3c02421949a4269dea746`; Actions run `40202752914`; artifact `12602132879` (`V13-Run298-WorldTerminal-Raw-1a6173b12983ce9938e7ed85b3a1dc007601d3c9`). **52 tests, 4 FAIL**: expected SOURCE_UNVERIFIED for mixed final/failure fit and unfiltered forged statuses. RED preserved, not rewritten.
- GREEN after source change: commit `8aeb24329ccda9fc8386a357dbcd7f97349363db`; source blob `0176a7b78c267149aec70c3c2be58ca1d5a76db3`; Actions run `40202801867`; artifact `12602876070` (`V13-Run298-WorldTerminal-Raw-a96a37ae31c6a7154c564fb9de020f92974a5946`). **52 tests OK** including 4 new actual Runtime/Store SQLite tests; official privacy scan `CLEAN`. Tests cover source revocation, tampered failed action status/outcome, restart, negative DISPATCHED/unknown status.
- Independent related Actions on GREEN source: Run218 `40202801866`, Run202 `40202801775`, Run209 `40202801791`, fitted lineage `40202801792`, event-source `40202801810` all **success**. Broader focused `40202801794` and full-suite `40202801834` were still running when this report was prepared; do not infer their results here.
- Remote bytes independently fetched: branch head `8aeb24329ccda9fc8386a357dbcd7f97349363db` and exact source blob above. This file is a later checkpoint commit, not the test source SHA.

## Claim limits / open gates
Software/SQLite with synthetic action values; no real model, native inference, Redmi, causal outcome benefit, successful continual-learning or whole-system completion. STEP2 UTILITY_FAIL, B3 L1, Body-JEPA, jepa_weight, all original negative gates remain unchanged. No live action authority introduced.

## Next independent work
1. Verify remaining focused/full-suite conclusions from their run IDs, preserve failures verbatim; review new status allowlist against unexpected statuses and source tamper.
2. On a new owned branch based on this verified checkpoint, address a different canonical functional package; do not overwrite active Run297. Run targeted RED/GREEN, source hash/official privacy scan, remote checkpoint again.
3. Actual Redmi/Termux long-run, B1/B2 native sparse learning and canonical utility gates still require their own registered runs; no substitution with this software test.
