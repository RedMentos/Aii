# Research/Perception handoff — 2026-11-12 15:56 CET

Owner: A-plane / RAW EAR. Base: #1846, head e81cbb657fe8d7985f63e3af2ff3d7cfa1297355. Stacked PR; do not merge without dependencies.

## Change
- New `v13.a5_audio_pipeline.observe_pcm_checked` composes existing synthetic PCM16LE → actual `Store.source/read_source` SQLite → numeric A3 → A4 → A5 observation candidate → integrity-checked B/C SHADOW source view.
- New `checked_projector_audio_view` recomputes A3 embedding from the stored feature vector with the supplied projector, rejecting modified embedding and incompatible projector. This closes a known gap in #1846 where feature digest alone did not authenticate an A3 result.
- Seven integration tests written against actual Store, including restart, revocation, no-consent/provisional no-write, wrong projector no-write, tampered embedding and changed projector.

## Evidence
- New module and tests Python syntax compiled in an isolated local mirror: PASS.
- Exact repository tests / GitHub CI: **UNVERIFIED**. Direct git clone blocked by DNS. No claim of end-to-end PASS until the exact branch tests execute.
- The supplied projector is NOT independently authenticated: `projector_revision_authenticated=False`. Model checkpoint/revision signature and durable receipt are still required.
- Synthetic PCM and a `consent=True` test assertion do NOT constitute Android OS microphone permission. No real mic, speaker, ASR, canonical A5, B/C model inference, voice full duplex, Android device control, or Redmi benchmark proven.
- No new model/dependency/license. Existing synthetic A3 train() updates numeric weights; not teacher-ear or on-device continual learning proof.

## Integration / release dependencies
1. QA: run `cd v13/code && python -m unittest tests.test_a5_audio_pipeline` on exact head and fix failures; also native Termux when available.
2. Boss/Core: resolve canonical A5 PerceptPacket and B1/B2/C2/JEF consumer contract. This module returns SHADOW data only; does not dispatch to production.
3. Android owner: consent-bound capture through Android OS APIs and independent permissions/lifecycle, audit, stop/revoke.
4. JEPA/Memory: source-linked trusted transition/experience with revocation, retention, restart.
5. Perception: approved projector checkpoint receipt; raw-ear prosody/speaker/non-speech and actual modality sources; separate trainable voice decoder/vocoder remain OPEN.

`PHONE_RELEASE_TRAIN_2026-11-12.md` and `AGENTS.md` not found on checked branch; coordinate with Boss to reconcile current release train. No Android RAM/latency measurements were performed.
