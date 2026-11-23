# JEPA & Memory — vision-forget overlay handoff (2026-11-23)

## Dependency and ownership
- Based on Perception PR #2395 head `26ccaf0825d4ebf02aedcdae781a9164b04f53d5`, which adds `vision_source_lineage.py` and source-bound `training_sources` to the global/tile vision projectors.
- JEPA owns the staged `source_lifecycle_candidate.vision_forget` overlay. QA owns `source_lifecycle_lock_integration_candidate.py` and its PINS/materialization list; this change deliberately does not edit that QA-owned file.
- Integration dependency for QA: add `v13/code/v13/vision_source_lineage.py` to the staged source PINS and copy list with its exact SHA-256, then rebind the exact `vision.py` source pin from PR #2395. Until that is done, direct module tests can pass while the staged composer remains blocked.

## Implementation
- The old JEPA overlay removed only the global projector's caption references. It did not clear `projector` weights or `tile_projector`, so forgetting an image could leave source-trained weights usable.
- The new overlay calls `invalidate_projectors`: exact lineage preserves proven-disjoint projectors; missing/legacy/malformed lineage is treated as unknown and invalidated; both global and tile projectors are handled.
- Revocation is persisted before blob/artifact deletion. Projector artifact paths are kept in `pending_projector_cleanup` until safe unlink succeeds, so a failed cleanup can be retried by repeating the same forget request after restart.
- Image blob cleanup still uses the existing Store-locked `cleanup_unreferenced` path, preserving a blob while another live source references the same hash.
- Added four integration tests: both projectors invalidated, legacy unknown invalidated with disjoint tile preserved, failed artifact cleanup retried, and shared blob retained.

## Evidence boundary
- New exact-head CI is pending after PR creation. No local full checkout or Redmi execution is claimed.
- The test uses the actual SQLite Store/Runtime and filesystem with synthetic PPM bytes; it is a local-runtime integration test, not native vision model training or Android proof.
- No installed model, weight, device permission, or user data was changed.

## Next step
- QA must add the new helper to staged PINS/copy list and rerun the full source-lifecycle composer; then Boss can integrate this overlay with PR #2395 and the current JEPA branch.
