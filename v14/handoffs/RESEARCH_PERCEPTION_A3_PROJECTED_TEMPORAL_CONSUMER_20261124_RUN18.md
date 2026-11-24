# Research & Perception — A3 projected temporal consumer (2026-11-24, run 18)

## Defect and implementation

The existing MediaProjection RAW EYE consumer already invokes the source-verified LAB_SHADOW_ONLY tile A3 Projector to produce per-tile embeddings and goal margins, but temporal history compared only handcrafted 37-value RAW EYE features. This left the actual A3 output outside the temporal/A4 evidence path.

This checkpoint adds a bounded process-local cosine-delta readout over the actual A3 tile-projector outputs. It is attached to the same consent/session/generation-bound TemporalVisualEvidenceRegistry transaction and committed only after the PerceptPacket reaches the existing A5 context consumer. The packet and A4 diagnostic include only numeric per-tile deltas plus current/previous frame SourceRefs and exact projector SHA; embeddings are not persisted or exposed. A projector hash/dimension change or missing projector re-baselines instead of comparing incompatible states. Session revocation clears the A3 history with the existing temporal registry reset.

This is a diagnostic over the existing trained ridge projector, not a JEPA temporal encoder, native hidden-state exchange, gradient update, neural-weight learning or production attention authority. It does not alter A4 modulation or action/learning/truth authority.

## Exact evidence

- Base: bc3b6fb8e9c18cf96140f031f9d441b76e1cc84a (research-perception/v14-a3-counterfactual-probe-20261124-run13), PR #2470 stacked on PR #2469 / PR #2463.
- Changed consumers: v13/code/v13/vision_temporal_evidence.py, v13/code/v13/vision_ui_frame_ingress.py.
- Tests: v13/code/tests/test_vision_ui_frame_ingress.py adds actual A5 frame-consumer coverage using the repository's vision.Projector, same-session frame receipts, exact projector SHA, source-pair lineage, missing/projector-change rebaseline, bounded dimension, non-finite, malformed source, and revocation reset.
- LOCAL_LINUX full project checkout/tests: BLOCKED / NOT_RUN; this runner has no repository checkout and git ls-remote fails because GitHub DNS cannot resolve. No local PASS is claimed.
- Exact Python 3.13/3.14 and staged workflows are pending after this commit; only report their observed outcomes after polling the exact head.
- Android/Termux/Redmi: REDMI_UNVERIFIED. No microphone, MediaProjection OS grant, APK, model, weight, permission, user-data or device action was used.
- Deployment: NOT_RELEASED. GitHub branch/PR updates do not deploy to the phone.

## Next

1. Run exact Python 3.13/3.14 RAW EYE ingress and A3 counterfactual workflows; fix failures without relaxing source/consent pins.
2. Keep the diagnostic SHADOW-only. A future temporal encoder/JEPA adapter requires source-disjoint paired-frame utility, no-change/shuffle/zero controls and an independently reviewed consumer.
3. Core/QA must reconcile the separate exact staged builder pin failure on Perception PR #2472; the A4 focused workflow itself passed, but its controller/staged/integrated checks failed because the recovery builder still pins the previous record-only controller-guard bytes.


## Follow-up hardening

- API defaults now infer NO_PROJECTOR only when A3 embeddings are absent, so callers supplying valid embeddings need not override a default status.
- The live ingress skips only the A3 temporal readout (without failing RAW EYE/A5) when any projected tile vector is zero; the negative test rejects zero vectors at the registry boundary.


## CI readback and falsification controls

- Exact head 9b69aa5a86fe7f4b3a50dd3ac33fae997e30de2e: GitHub Actions PASS for v14-vision-ui-frame-ingress on Python 3.13 and 3.14 (54 tests each); v14-vision-source-lineage on Python 3.13 and 3.14 (39 tests each); v14-privacy-regression PASS; offline-bridge-security PASS. The frame-ingress jobs included the A3 WARMUP→MEASURED, projector-change/missing-projector, malformed source and zero-vector tests.
- The follow-up adds a third identical frame as an explicit no-change control; its CI is pending on the next exact head. Do not count that new assertion as passed until its run completes.
- LOCAL_LINUX project tests remain NOT_RUN/BLOCKED because this execution has no checkout and github.com DNS is unavailable. CI is not a local measurement.

## Research additions

- MotionJEPA/DISReg full paper reviewed (arXiv:2609.23881v1, 2026-09-20, CC BY 4.0). Its dynamic-difference prediction is a training-only anti-feature-suppression objective; its ViT-Tiny/10M-episode CUDA training is not an Android implementation. The root OSS repo has no license; only its separate planning submodule is MIT.
- engramBNN full APL Machine Learning paper reviewed (published 2026-11-06, CC BY 4.0). Sparse context-dependent stochastic gates plus metaplastic updates are a promising small-adapter experiment, not a direct B1/B2 replacement. The author code is AGPL-3.0 and stale relative to the 2026 paper; no code or weights were reused.

## Current-head CI and integration blocker (0711ef81de25d72f7a45864c66c77a51e6c10e2b)

- `frame-ingress`: 54/54 PASS on CPython 3.13 and 54/54 PASS on CPython 3.14. This includes the identical-third-frame no-change control, which returns zero A3 projected delta after a changed frame.
- `privacy`: PASS; `offline-bridge-security`: PASS.
- `a5-ui-lease`: FAIL on both Python versions (17 passed, 5 skipped, 1 failed). The failure is `test_staged_store_read_open_is_linearized_with_revocation` → `source_lifecycle_lock_integration_candidate.py:172` → `unsupported lifecycle source: vision.py`. The #2469 base carries the old `PINS['vision.py']` SHA-256 758cfc26387bd92da6c1c73d1d53224e76827ba70289c3c9e440f62557c209e5; Core PR #2465 carries the updated pin 350573e65eb445b8b83f5517e3bfe07ece04e036055c55fc3e23c79d5b0cc728. This is a missing stacked Core dependency; no pin bypass is requested. Commented on #2465 and #2470 for coordinated integration.
- A separate #2472 blocker remains: the recovery builder expects guard SHA-256 86ad7838d15eb9a038fec629c340936edde78d65d921507e10cec29fed74b9d9 while #2472 changes the guard source. Core/Integrator coordination was posted on #2465 and #2472.
- Source-lineage tests 39/39 passed on Python 3.13 and 39/39 on 3.14 at parent checkpoint 9b69aa5; those files were not changed in the no-change-control follow-up.
- LOCAL_LINUX full project tests NOT_RUN/BLOCKED; no repository checkout and github.com DNS unavailable. CI is not local evidence. REDMI_UNVERIFIED; NOT_RELEASED.

## Private device/updater receipt

Read-only private owner-relay requests for HEALTH, PIPELINE_STATUS and DIAGNOSTICS expired without a device_status reply: NO_LIVE_RECEIPT. Installed Redmi SHA, updater health and current installation are unknown. No UPDATE_REQUEST, shell command, model/weight change, permission change or user-data access was attempted. REDMI_UNVERIFIED / UPDATER_UNVERIFIED / NOT_RELEASED.