# Research & Perception handoff — A3 replay-gated projector updates
Date: 2026-11-24
PR: https://github.com/RedMentos/Aii/pull/2463
Branch: research-perception/v14-vision-current-20261124-run33
Current branch HEAD at handoff: 8a541d06a45d13401969a983c8bc2174607e3722

## Concrete function

A3 global and tile projectors previously replaced the active ridge artifact after each fit without comparing the candidate with the previous projector's learned source/caption set. The update now:

1. Reconstructs the previous projector's replay set from its stored caption targets plus immutable image/region SourceRefs and verifies the recorded source hashes are still live.
2. Requires the same encoder identity and compatible input/output dimensions.
3. Measures old and candidate retrieval on the same replay set, treating duplicate caption strings as the same target class.
4. Searches affine parameter-delta scales 1.0, 0.5, 0.25, 0.125 and 0.0625. It accepts the largest scale whose replay top-1 is no worse than 0.02 below baseline and mean cosine no worse than 0.015 below baseline.
5. Fails closed on missing/invalid replay, changed encoder, insufficient source groups, invalid old artifact or dimension mismatch. A rejected candidate does not replace the old artifact.
6. Persists exact tile caption labels for future tile-projector replay and exposes update_gate status through the read-only vision status surface.

This is a small replay-measured A3 update-effect gate. It is not MANGO's meta-learned lambda, not donor/Fisher grafting, not a learned neural gradient update, not JEPA, and not a B1/B2 update. All artifacts remain LAB_SHADOW_ONLY.

## Code and commits

- de96c28ed25936630ddc977f98adcb56d994612a — add replay-gated A3 projector update path.
- 05defd82bf24b1088771b28fc5520a1248a575f1 — bind NumPy in the replay gate.
- 8a541d06a45d13401969a983c8bc2174607e3722 — add global/tile replay integration tests.
- Updated vision.py Git blob: f269673fccbd4ebbf9734c6969c44a62eb2510a0.
- CI-reported vision.py SHA-256: bb63636c9ae84d345fe1f4e37254de3be87c26990cb320ca058859fd0b51b72f.

## Test evidence

- LOCAL_LINUX/SYNTHETIC: isolated NumPy script passed affine endpoint equivalence, a replay-preserving scaled update, full-scale no-regression and destructive-update rejection. This is a helper-level experiment, not a full local Aii checkout.
- CI / Python 3.13: py_compile + tests/test_vision.py + tests/test_vision_source_lineage.py — 31 passed; frame-ingress suite — 39 passed.
- CI / Python 3.14: same targeted suites — 31 passed and 39 passed.
- Integrated-regression and staged-runtime FAILED because scripts/source_lifecycle_lock_integration_candidate.py rejects the current vision.py with `unsupported lifecycle source: vision.py`. The integrated-regression job failed while staging; the broader staged-runtime suite reported 19 failed, 234 passed, 10 skipped, 2 errors and 41 subtests, with the failures cascading from the same source-lifecycle pin mismatch (including two-checkout migration reporting PARTIAL instead of UPDATED). This is an integration-owner rebind dependency, not a failure in the targeted A3/vision suites. The PR is NOT integration-complete.
- No native model, gradient, Android microphone or Android screen-capture test is claimed.

## Integration dependency

Core/Integrator must add the exact current vision.py SHA-256 above to the source-lifecycle composition and bind the new vision source-lineage/validation/UI-ingress consumers. The branch is based on 8d93236c753f0194224c19edc7411d8d7082b1d6. Do not alter the shared lifecycle file from this lane; coordinate the rebind with Boss/Integrator.

## User effect and remaining limits

When the A3 image operator retrains the global or tile projector, it can now preserve the previous projector instead of silently replacing it with a candidate that regresses on its old source/caption replay set. The A5 UI-frame consumer can continue to use the retained tile projector. The feature is not yet in the installed release and is not yet accepted as an end-to-end chat/Runtime path.

REDMI_UNVERIFIED: no Redmi-side A3 training, screen-frame capture, native embedding, RSS/PSS, TTFT or restart/rollback measurement was run. The installed release must not be inferred from this PR.

## Next concrete action

Boss/Integrator: rebind the exact source-lifecycle pin, compose this branch with the audio/vision source composers, then run staged-runtime and integrated-regression on the resulting exact integration SHA. QA: exercise add → describe → train → look/find → forget → restart with source lineage intact. Only after that, request an authorized Redmi UI-frame/A3 test; do not deploy this branch as-is.


## A3 snapshot-consistency follow-up — 2026-11-24

**Concrete defect:** global and tile A3 training previously read the dataset from one vision-state snapshot, then loaded a newer state/version only after validation. If a teacher caption was updated between those steps, the candidate trained on stale captions could be committed against the newer Store version. The existing CAS therefore did not detect this particular stale-training window.

**Change on exact branch head 776dee972b92f0ac76afcdf4e9b0be7e408b1f5c:**
- dataset() and tile_dataset() now accept and validate a Store-bound _VersionedVisionState snapshot.
- train() and train_tiles() capture that snapshot before reading rows and use it for captions, source lineage, previous projector and final CAS publication.
- If a concurrent describe() changes a caption while cross-validation is running, final publication fails with Stale state write; the candidate artifact is removed, the newer caption remains, and no stale projector is committed.
- Added separate global and tile concurrency regressions using an interleaved opposite-caption update. This is persistent Store-snapshot consistency, not a neural gradient/JEPA learning claim.

**Exact CI evidence at 776dee972b92f0ac76afcdf4e9b0be7e408b1f5c:**
- Vision source-lineage workflow 45349128200: Python 3.13 33 passed, Python 3.14 33 passed; py_compile PASS on both. Exact vision.py SHA-256 from CI: 23243f6a8e8d3ac79a40644aab186fcb4cff7a5e7d56f9b67bcae7cda2a1f8ae.
- MediaProjection RAW EYE ingress workflow 45349128231: Python 3.13 39 passed, Python 3.14 39 passed.
- Perception privacy scan 45349128338: PASS.
- Staged Runtime workflow 45349128416: FAIL — 19 failed / 234 passed / 10 skipped / 2 errors / 41 subtests. Exact root error remains ValueError: unsupported lifecycle source: vision.py in scripts/source_lifecycle_lock_integration_candidate.py:172; migration cases report PARTIAL rather than UPDATED. This is the integration-owner source pin/composer mismatch, not a failure in the focused A3 tests. Integrated-regression was still running at the last poll; no pass is claimed.
- Full LOCAL_LINUX Aii checkout is not mounted; full local suite NOT_RUN/BLOCKED. No Redmi test, model, weight, permission, data or deployment change.

**Integration handoff:** current vision.py is already an atomic/versioned Perception implementation: ingest serializes source/blob publication in store.tx; forget atomically tombstones the image source, invalidates affected global/tile projectors, and safely removes unshared artifacts; load/save use a Store-version CAS. Core's old lifecycle composer still expects the obsolete unversioned VISION_OLD, VISION_FORGET_OLD and VISION_STATE_OLD anchors. Updating only its pin will therefore not be sufficient: Core/Integrator must remove/rework those obsolete vision replacements, pin the exact SHA above, and include the Perception lineage/validation/RAW EYE modules in the staged source set. Keep the source pin fail-closed; do not bypass it.

**Next:** Core/Boss rebind the source-lifecycle composer to this exact Perception implementation; QA reruns staged, integrated, migration and source-forget/restart checks on one exact integration SHA. PR #2463 remains DRAFT / NOT_RELEASED / REDMI_UNVERIFIED.


## Final exact-head poll — board checkpoint 5a2cd1f252f36f7220def2369be142fdcbb16916

- The V14 work board now records PR #2463 under Research & Perception ticket V14-006 and the A5 UI-ingress evidence under shared ticket V14-009. The V14-006 status remains IN_PROGRESS_PARTIAL; no Canon acceptance was promoted.
- On this exact board checkpoint: vision source-lineage workflow 45350475598 PASS on Python 3.13/3.14; MediaProjection RAW EYE ingress 45350475533 PASS on both; Perception privacy 45350475626 PASS; runtime deployment integrity 45350475751 PASS.
- Staged/integrated workflow 45350475519 FAIL on both staged-runtime and integrated-regression. The exact failure remains unsupported lifecycle source: vision.py; staged suite reports 19 failed / 234 passed / 10 skipped / 2 errors / 41 subtests. Core same-turn workflow 45350475641: Python 3.13 FAIL (3 failed / 2 passed) and Python 3.14 FAIL (3 failed / 2 passed), both because the same source-lifecycle builder refuses vision.py.
- The final board checkpoint does not change the tested code bytes: vision.py SHA-256 remains 23243f6a8e8d3ac79a40644aab186fcb4cff7a5e7d56f9b67bcae7cda2a1f8ae; code/test SHA remains 776dee972b92f0ac76afcdf4e9b0be7e408b1f5c. PR #2463 is OPEN / DRAFT / NOT_RELEASED.
- This confirms the remaining block is shared source-composition integration, not a green end-to-end runtime. No merge, release, auto-update, model swap or device action was performed.


## A5 multi-frame platform research follow-up — 2026-11-24

R-109 reviews the official Android MediaProjection guide (updated 2026-11-19). Android describes capture as a stream rendered to a VirtualDisplay Surface; an ImageReader can consume frames in real time. A session is one createVirtualDisplay() call and requires user consent; the token is used once, and onStop/process death must release the Surface and VirtualDisplay. Therefore the current Core provider's one-frame limit is not imposed by Android: a future provider can use one user-started session with a bounded two-frame ImageReader queue, one stable session/consent lineage, unique per-frame nonce/sequence/timestamp/digest, drop-oldest backpressure, no raw disk persistence and immediate stop/revoke cleanup. This remains a design recommendation only; provider #2408 is still one-shot and Redmi is unverified.
