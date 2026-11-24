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
