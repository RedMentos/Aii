
# Research & Perception Run 65 — 2026-11-27

## Ownership and scope
Perception lane on the existing PR #2557 branch. No changes to the V14 master, historical V13 Canon, installed app, model files, permissions or device data.

## Implemented
- Added consume_projected_frame_from_provider_scope(runtime, observation, frame_buffer, *, consent_lease, verify_fn, **kwargs) to v13/code/v13/vision_ui_frame_ingress.py.
- It calls the existing one-shot provider-verifier entrypoint, yields the verified A5 PerceptPacket to downstream code while the caller keeps the outer UIObservationLease active, and revokes only the frame source/cache after the scope exits. Cleanup also runs when downstream code raises. If observation validation fails before provider entry, the mutable caller buffer is still overwritten.
- Added three tests in v13/code/tests/test_vision_ui_frame_provider_entrypoint.py for scope lifetime, downstream exception cleanup and malformed-observation zeroization.

## GitHub evidence
- Branch: research-perception/v14-vision-ui-frame-ingress-20261127-run64
- Code commit: ba79ec7b4fef9b0dc0929725310588f689b747c9
- Test/current branch HEAD: 19ffeb54287627d02255845f9c9e660105e12a78
- PR: https://github.com/RedMentos/Aii/pull/2557
- Readback verified: ingress blob 139a68db835ddde02211dd7b9b4a9985f970dce4; provider-entrypoint test blob ec7bd10e80cb00bff360baccfca47a49b02f7df2.

## Tests and environment
- CI / PASS: workflow 45988257517. Python 3.13: py_compile PASS, 28/28 tests PASS. Python 3.14: py_compile PASS, 28/28 tests PASS.
- CI / PASS: runtime deployment integrity workflow 45988257367.
- CI / FAIL: staged workflow 45988257446. Staged-runtime job: 20 failed / 233 passed / 10 skipped / 2 errors / 41 subtests. Failures point to existing Core audio-composer, arithmetic and observer source pins plus QA migration PARTIAL-vs-UPDATED assertions. No new MediaProjection ingress test failed.
- CI / IN_PROGRESS at last poll: integrated-regression job of workflow 45988257446. No pass claimed.
- LOCAL_LINUX / BLOCKED: full Aii checkout/pytest not run because no repository checkout is mounted and GitHub DNS cannot resolve. No local test pass claimed.
- ANDROID_TERMUX / REDMI: REDMI_UNVERIFIED. No connected phone, Android capture, OS permission or native measurement was available.

## Product impact / Canon
The new scope makes the provider → A5 packet → downstream-consumer lifetime explicit and provides deterministic cleanup when the consumer returns or fails. It does not wire the normal Runtime/C3 callsite, prove OCR/semantic screen understanding, grant action or learning authority, or prove a phone capture. It preserves the A5 UI observation lease, provenance, source revocation and zeroization constraints.

## Research note
- R-183: GoClick (arXiv:2604.23941, 2026-04-27) is a narrow 0.2B-class GUI element grounder. Author code/model cards are MIT; a separate community ONNX INT8 export lists 91+80+132 MB components, but it is not an author-maintained Android release and has no Redmi/732G measurement. No download or reuse occurred. It is only a future optional coordinate-grounding candidate; it cannot replace RAW EYE/A5 or authorize actions.
- R-181 XBridge remains a large-model research analogue, not a Redmi-suitable dependency: 264M bridge parameters with Llama/Qwen 7B bases, CUDA/GPU workflow, no V14 model reuse.

## Existing blockers / risks
- Core #2408 has not yet connected the provider into a normal Runtime → A5 → C3 turn. It must rebase on #2557 and use the new scope helper.
- Shared staged failures remain in Core/QA-owned pins/migration tests; Perception did not weaken or rewrite them.
- Auto-updater/installed phone state has no fresh authenticated receipt. Historical V13OBS #115 (2026-11-24) is not current proof. NOT_RELEASED.

## Next concrete action
Core: rebase #2408 onto #2557 and put normal C3 context consumption inside consume_projected_frame_from_provider_scope(). QA: independently verify permission denial/revocation, MediaProjection onStop, process death, restart and rollback. Perception: after that integration, add A5 audio/UI source-consumer coverage without duplicating capture providers.
