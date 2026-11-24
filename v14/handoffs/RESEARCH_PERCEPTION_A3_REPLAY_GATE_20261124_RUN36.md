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
