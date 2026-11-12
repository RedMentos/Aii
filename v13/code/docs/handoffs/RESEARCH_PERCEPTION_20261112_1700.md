# Research/Perception handoff — 2026-11-12 17:00 CET

Base: stacked PR #1849. This branch must not merge independently of its parents.

## Implemented
- Hardened `checked_projector_audio_view`: reject non-list/tuple, wrong-length, nonnumeric or nonfinite A3 projector predictions.
- Compare two consecutive projector predictions to detect mutable or nondeterministic projector output during the SHADOW read. Check source again after both predictions.
- Added regression cases for NaN prediction and projector mutation between reads.

## Evidence and gates
- GitHub source changes persisted. **Exact repository tests NOT EXECUTED**: local git clone cannot resolve github.com; GitHub connector has no test runner. Two tests written, PASS not claimed.
- Double prediction is a bounded stability check, **not** cryptographic checkpoint authentication or synchronization. It doubles projector inference for this SHADOW verification and should be benchmarked on Android before enabling on a hot path.
- Android mic permission, real Redmi, canonical A5, B/C model inference, full duplex, trainable voice decoder and device control remain OFF/UNVERIFIED. Synthetic PCM and consent flag are not OS permission.

## Release integration
- QA: run `cd v13/code && python -m unittest tests.test_a5_audio_pipeline` against this exact head; report pass/fail and Termux metrics.
- Core/Boss: canonical A5 and B/C consumer, checkpoint receipt, and release train coordination still needed.
- JEPA/Memory: source-linked replay, trusted weight-update and revocation semantics.
- Perception: optimize verification to avoid repeated full A3 inference after validated immutable checkpoint receipts, and connect consent-bound Android audio capture.

No new model or third-party dependency introduced. PHONE_RELEASE_TRAIN file unavailable on checked default branch; request coordination through PR rather than inventing requirements.
