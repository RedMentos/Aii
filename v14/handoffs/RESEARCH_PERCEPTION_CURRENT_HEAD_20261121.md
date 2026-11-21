# Research & Perception — current-head RAW EAR shared consent lease API

Date: 2026-11-21  
Owner: Research & Perception  
Base: 1185dac228afefd8ace5294cd6f099ac6530b2ed  
Branch: research-perception/v14-raw-ear-shared-lease-api-20261121-run13  
Status: DRAFT / NOT_RELEASED / REDMI_UNVERIFIED

## Product blocker addressed

Core #2200 and QA #2238 identified that the producer's consent lease ended after A4/C3 admission, while the normal Runtime still needed the same provider lease through audio-context reads and the complete C3 runner.generate() iterator. Calling consent_check while a non-reentrant provider lock is held deadlocks; releasing it before C3 generation permits a revoke race.

## Perception-owned implementation

- Rebased the existing caller-PCM RAW EAR producer, temporal evidence, optional caller-owned Silero VAD adapter, VAD comparator, tests and workflow coverage onto the current shared base. Boss-owned board/workplan/next-action/coverage/master files were not changed.
- Added AudioConsentLease and audio_consent_lease(...) to v13/code/v13/audio_voice_cues.py.
- The outer context performs a metadata preflight, then acquires the provider's linearizable guard once. Its ephemeral handle is bound to Runtime identity, source, generation, receipt and creating thread; optional temporal/VAD objects are identity-bound too.
- consume_pcm16_voice_window(..., consent_lease=lease) reuses the active handle and does not call consent_check or reacquire consent_guard. Calls without a supplied handle retain the original self-acquiring path.
- The handle becomes inactive before the outer provider lease is released. It cannot be copied or serialized and is never included in PerceptPacket, Store, context records or telemetry.
- Core can now hold the same scope across producer → derived-context read → B1/B2 → the full C3 generation iterator. Core must pass the handle to its audio-context view and avoid callbacks while the lock is held; this PR does not itself alter Core files or claim that generation is already protected.

## Exact local checks

- LOCAL_LINUX CPython 3.13.5: isolated reproduction of the exact lease-handle/scope logic — 4/4 PASS (non-reentrant lock reuse, revocation serialization, wrong-scope/boolean rejection, thread binding and serialization rejection).
- LOCAL_LINUX py_compile on that isolated helper/test harness — PASS.
- Full Aii checkout and repository pytest — BLOCKED; this runner has no repository checkout and GitHub DNS is unavailable. The repository integration tests added here have not been run locally.
- GitHub Actions on the exact new PR head — pending at handoff creation; do not substitute prior #2233 CI for this new head.
- Android/Termux/Redmi microphone, native model inference, installed SHA and updater — REDMI_UNVERIFIED.

## Research update

- Preserved the prior RAW EAR/VAD research entries R-031/R-032.
- Added R-033: Mamba-FVAD abstract-only review (no full-text or license claim), Soniqo Android voice stack licensing/architecture review, and rejection of VoxRT's proprietary runtime for core reuse. No code, model, weights, dataset or dependency imported.

## Remaining gates and next owner

1. Core rebases #2200 onto this Perception API and keeps the same audio_consent_lease scope open through the complete C3 generation iterator; the Runtime audio-context view must validate lease.matches(...) rather than call provider callbacks under the lock.
2. QA rebases #2238 after Core recomputes the nested recovery/stage/deployer pins, then proves a non-reentrant provider, revoke blocked through the whole generator, and derived-context deletion plus process-cache clearing after revoke.
3. Boss performs manual review. Existing-module edits may fail strict safe-additive policy; no validator bypass is requested.
4. Only after Core/QA acceptance should the team add the timestamped Android AudioRecord frame feed. This PR does not open a microphone, grant a permission, download a model or touch the device.

User action: none required. No manual Termux command, model/weight swap, permission change, updater action or device mutation is justified.
