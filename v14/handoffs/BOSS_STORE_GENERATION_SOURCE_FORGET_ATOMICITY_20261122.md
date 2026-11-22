# Boss handoff — Store generation/source-forget atomicity (2026-11-22)

## Defect

Memory._forget_source now serializes source tombstoning and dependent-update quarantine under the JEPA file lock followed by Store.mutex. Generic Store.switch_generation and Store.rollback previously performed preflight reads and artifact validation outside that Store lock, then rechecked only the active generation in the final SQLite transaction. A pending update could therefore be quarantined/source-tombstoned after preflight and still be promoted from stale state; rollback could also reactivate a parent component whose update/source lineage had been quarantined.

## Change in this stack

- Store.switch_generation now holds the shared Store RLock from its first update read through validation and commit.
- Its final transaction re-reads exact update status/base/path/hash/manifest and verifies every declared source_ids row remains present and undeleted.
- Existing active component update rows are rechecked as committed and source-live before replacing a component.
- Store.rollback now uses the same Store lock and validates the rollback target plus every parent component's committed update/source lineage inside the final transaction.
- Lock order remains JEPA file lock -> Store RLock for source forget. Generation promotion/rollback take only Store RLock and do not acquire the JEPA lock, avoiding lock inversion.

## Acceptance tests added

- test_memory_forget_cannot_race_pending_update_promotion: promotion pauses during artifact validation; source forget acquires the JEPA guard but must block on Store RLock; promotion commits, then forget refuses because the source is now in active weights.
- test_memory_forget_wins_and_promotion_rejects_quarantined_update: forget commits first; promotion must reject the quarantined pending update.
- test_memory_forget_tombstone_is_rechecked_after_artifact_preflight: a second SQLite connection tombstones a declared source after artifact preflight; final transaction must reject promotion.
- test_memory_forget_cannot_be_undone_by_rollback_to_parent_component: a parent update is quarantined/forgotten; even after restoring the artifact bytes, rollback must not reactivate that parent lineage.

These are synthetic SQLite/Store tests. They do not establish native Android, model-weight learning, or Redmi behavior. Full local execution is unavailable in this run because no repository checkout is present and GitHub DNS resolution fails in the container; exact GitHub Actions results are pending.

## Dependency and integration

This PR is intentionally stacked on JEPA temporal PR #2351 because its Memory._forget_source implementation owns the other side of the lock order. It must not be merged independently of that base. After #2351 passes its temporal/source-forget tests, run this stack's Python 3.13/3.14 tests and the full staged integrated regression, then rebase/integrate onto the release line and rerun exact release CI. Redmi remains unverified until a fresh private device receipt and a real device acceptance test.
