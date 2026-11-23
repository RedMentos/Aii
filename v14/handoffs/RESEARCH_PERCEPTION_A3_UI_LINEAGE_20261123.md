# Perception handoff — A3 lineage gate in consent-bound UI ingress (2026-11-23)

## Product connection

This work composes the Perception RAW EYE frame adapter with the source-bound A3 vision student. It is deliberately stacked on JEPA #2397, which is stacked on Perception #2395, so the UI consumer sees the same A3 lineage contract that the producer and JEPA forget overlay now use.

- A3 producer: #2395 records `training_sources=[{source_id, sha256}]` for global and tile projectors; forget clears any affected or unknown legacy projector before source deletion.
- JEPA composition: #2397 carries the shared invalidation through the overlaid `vision_forget` function.
- UI consumer: #2401 requires every tile-projector training source to remain present in the current VISION image index and in the canonical Store source table as a live IMAGE row with the exact digest before it reads projector bytes.
- UI frame input remains one-shot, consent-lease-bound MediaProjection data. The adapter emits ephemeral RAW EYE/A4/A5 data; no raw frame or derived packet is persisted.

## Exact GitHub artifacts

- PR: https://github.com/RedMentos/Aii/pull/2401
- Base dependency: JEPA #2397 head `f63a5877774f58b6928b4e8dd7125651e9d8173d`
- Branch: `research-perception/v14-a3-ui-lineage-consumer-20261123-run16`
- Code commit: `013544d27b2556bd103906813cce792be59daa0d`
- Test commit: `03cbba317d49fc6aad63fbe42385411999d49a53`
- Workflow commit: `d34a5c659a58baba5278ab76619635c63188dcb7`
- Readback blobs at PR head: `vision_ui_frame_ingress.py` = `71e87a2b16cba6dacd6cc63d335feae9ea82916f`; `test_vision_ui_frame_ingress.py` = `a45e9e0c58e581b5cac671a4764ef171fbf8ff80`.

## Verification boundary

- LOCAL_LINUX isolated helper logic: 6/6 assertions PASS (valid live lineage, forgotten/missing source, source-row absence, missing lineage, malformed hash, duplicate lineage).
- Full Aii checkout/pytest and exact package py_compile: BLOCKED / NOT_RUN; this worker has no mounted checkout and `git ls-remote` fails because github.com DNS does not resolve.
- Exact-head GitHub workflows at `d34a5c659a58baba5278ab76619635c63188dcb7`: MediaProjection ingress and staged/integrated jobs were QUEUED at the last readback. Re-read before claiming any CI result.
- No Android APK, MediaProjection session, microphone, model inference, training, weight write, or Redmi test. REDMI_UNVERIFIED.

## Remaining dependencies and risk

- #2395/#2397/#2391 must first produce one green composed A3 source-forget chain; QA's exact staged source pin had been stale at the last readback.
- Core #2379 still needs a combined companion/A5 base and normal Runtime/C3 dispatch. This Perception adapter is not itself the Android capture provider.
- The Store-level forget/promotion serialization race remains a separate JEPA/QA integrity issue; this consumer check does not replace the required lock/barrier tests.
- Keep A3 authority LAB_SHADOW_ONLY. No student score is calibrated confidence, truth, action authority or learning authority.

## Next executable step

Poll #2401 exact-head CI. If its focused consumer tests fail, repair only the failing Perception code/test. In parallel, let QA compose #2397 into its lifecycle builder and Core combine the one-shot Android frame provider with this exact UI lease contract. Do not merge or release this stacked branch before the base dependency and complete staged/integrated matrix are green.
