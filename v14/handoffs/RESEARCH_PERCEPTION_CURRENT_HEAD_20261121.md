# Run 11 final verification update — 2026-11-21 18:25 CET

## Current candidate and test evidence

- PR #2240 remains DRAFT / NOT_RELEASED. Code-bearing SHA: 88220f803178eada2377a06d96420465610d9c3b; later branch-head commits only append R-035/R-036 research and this handoff. Current shared base remains 3b8c8bb671e9b52b22e052fcfa9fdc6e721012ea.
- Exact code-head GitHub Actions: RAW EAR producer → A4/C3-admission compile/regression PASS on CPython 3.11 and 3.13; VAD comparator/source-blob/native Linux libfvad checks PASS on CPython 3.13 and 3.14; consent-revocation PASS; staged Runtime/SQLite/source-recall/revocation/JEPA-restart and recovery-shell syntax PASS; integrated staged-organ/memory regression PASS; privacy scan PASS; offline bridge security PASS.
- Strict safe-additive validator FAIL BY POLICY because the PR modifies existing production modules and workflow paths outside its inert-module-only allowlist. This is an independent manual-review gate; no bypass was made. Model-lab workflow was cancelled by concurrency and is not a pass claim.
- The producer test file contains 34 test functions; temporal evidence has 12 and Silero VAD has 10. The exact RAW EAR workflow compiled all three producer modules and all three test files, then ran the three suites on both Python versions. GitHub reports PASS; exact pytest counts were not available through the accessible job summary.
- LOCAL_LINUX isolated source/receipt binding check: 3/3 PASS (valid binding, wrong source, wrong receipt). Full local Aii checkout/pytest remains BLOCKED because no repository checkout is mounted and git cannot resolve github.com. CI is not local-device proof.

## Code correction

- Fixed an actual NameError on the supplied-lease path: the prior code compared against undefined lease_source_id/lease_receipt. The function now snapshots expected_source_id/expected_receipt before validating the packet and fails closed if either returned binding differs. Added parameterized wrong-source/wrong-receipt negative tests that assert no packet or A4 attention side effect.
- Updated the comparator workflow's expected RAW EAR V3 blob to the exact source blob b62442c6e740d136982b2bc8080cef6227ba266f.
- The branch was synchronized with shared base 3b8c8bb by a two-parent merge commit, no force push. Boss-owned board/workplan/next-action/coverage files were not edited.

## Coordination

- Comment 7066589536 on QA #2238 documents the API contract and full C3 scope requirement.
- Comment 7066670253 on Core #2200 points out that its producer pin 4ddb61865deb56b0048390740d35770d4d89316e is stale and must be replaced by #2240's exact blob. Core must hold the provider lease through producer → derived context → B1/B2 → the complete C3 runner.generate() iterator; no callback re-entry while the lock is held.
- Current Core #2200 remains stacked on an older Perception branch; QA #2238 remains stacked on Core #2200 and still requires Core's nested pin chain to be rebased before its generator-revocation assertions can execute.

## Research ledger additions

- R-034: full-text Counterfactual World Models preprint and official MIT repository/license audit. Proposed same-event residual reuse is simulator-scoped and requires additive action/disturbance channels; no mobile dependency or latent-coupling claim.
- R-035: full-text Age of Learning preprint and official MIT code audit. Error persistence is a verified-correctness modulator, not official Age 0–5; noisy/OOD and rapidly changing sparse streams are failure modes.
- R-036: two primary omission/attention studies plus a review. Preserve PRESENT / EXPECTED_OMISSION / UNEXPECTED_OMISSION / UNKNOWN separately; only a source-bound, high-confidence time-windowed omission is a negative event. Keep low-level sensory mismatch distinct from later attention-weighted contextual update.

## Product boundary / next action

- What works on the candidate: caller-supplied PCM16 → bounded acoustic/prosody/non-speech PerceptPacket → transactional Store → temporal voice state → A4 salience → bounded C3 admission, with optional caller-owned Silero VAD and source-bound lease reuse. This is synthetic/CI validated; it is not an Android microphone path.
- What remains unverified: normal Runtime C3 generation with this lease, microphone/AudioRecord permission, ASR/decoder/vocoder, full duplex, actual trained latent exchange, native model inference, installed SHA, updater deployment and all Redmi behavior.
- Next: Core rebases/adopts the exact producer blob and lease in the ordinary Runtime; QA proves revocation cannot race the complete C3 generator and checks derived-context deletion/cache clearing; Perception then adds only the permitted Android input contract. Do not enable microphone capture or model learning in this PR.

**REDMI_UNVERIFIED / NOT_RELEASED / no user action required.**

---
# Run 11 update — RAW EAR lease repair and new research (2026-11-21 18:25 CET)

## Verified GitHub state

- PR #2240 is still DRAFT / NOT_RELEASED. Its code-bearing current-base synchronization commit is 88220f803178eada2377a06d96420465610d9c3b. This commit has the previous PR head and shared base 3b8c8bb671e9b52b22e052fcfa9fdc6e721012ea as parents; no force-push was used. The latest PR head 1ce5501b5f3e444342594c46276ea49d45d9744a adds research-ledger text only after that code commit.
- The code fix snapshots expected_source_id and expected_receipt before _validate_runtime_binding, then rejects either mismatch. This replaces the prior undefined lease_source_id / lease_receipt comparison that caused NameError on the supplied-lease path. Added a parameterized negative test for wrong source and wrong receipt; both assert no packet or A4 attention persistence.
- The VAD comparator workflow now pins the exact RAW EAR source blob b62442c6e740d136982b2bc8080cef6227ba266f rather than the stale 9cae3b... blob.
- A coordination comment was posted on QA PR #2238 (comment 7066589536) with the lease API contract: one outer provider scope must cover producer → derived audio-context view → B1/B2 → full C3 generation iterator; the view must validate lease.matches(...) and must not call provider callbacks/reacquire the lock.

## Exact-head test state at code SHA 88220f803178eada2377a06d96420465610d9c3b

- GitHub Actions consent-revocation: PASS (run 44930787843).
- Strict safe-additive: FAIL BY POLICY (run 44930881558); production-module changes are outside the inert-module-only validator scope. No bypass requested.
- Staged Runtime and integrated regression: IN_PROGRESS at last poll.
- RAW EAR prosody Python 3.11/3.13 and comparator Python 3.13/3.14: QUEUED at last poll.
- Privacy and offline-bridge-security: QUEUED; model-lab was cancelled by workflow concurrency. These are not pass claims.
- LOCAL_LINUX isolated source/receipt binding reproduction: 3/3 PASS (one valid binding; wrong-source and wrong-receipt negative controls). This is a minimal helper-level check, not the repository suite.
- Full local Aii checkout / repository pytest: BLOCKED because no checkout is mounted and this runner cannot resolve github.com. No exact full-source local test is claimed.

## New research

- R-034 records full-text review of Counterfactual World Models (arXiv:2611.24778v1) and official MIT code revision 5c84bba92b2ff19d41175070a61238fa1396d10d. The proposed same-event residual correction is limited by additive disturbance assumptions, action support, sufficient context and coordinates; all seven evaluation environments are simulated. The official reproduction needs Linux x86_64/CUDA 13 and about 150 GPU-hours. No code/data/weights imported.
- R-035 records full-text review of Age of Learning (arXiv:2609.32593v1) and official MIT repository revision 686fd16da98c31c5ad601d1b018deeb318f03e97. Its temporal persistence signal is based on verified binary classification correctness and can overemphasize noisy/OOD cases; fast-changing sparse streams can destabilize it. V14 may test a separately named source-bound error-persistence modulator, with PENDING outcomes kept distinct from verified omissions. It is not official Age 0–5 and grants no learning rights. No code/dependency/data/weights imported.

## Remaining acceptance gaps and next owner

1. Research/Perception: finish exact-head CI and repair any real test failure without weakening consent, source pins or privacy checks.
2. Core: rebase the normal Runtime consumer onto PR #2240 and keep the same AudioConsentLease open through audio-context reads and the entire C3 generation iterator. Do not re-enter consent callbacks while the provider lock is held.
3. QA: rebase #2238 after Core refreshes the nested builder/recovery/stager/deployer pins; prove non-reentrant provider behavior, revocation blocked through generation, derived-context deletion and cache clearing after revocation.
4. Only after Core/QA acceptance should the team implement a consented Android AudioRecord input. No microphone capture, ASR, TTS, full duplex or model swap is enabled by this PR.

**Product status:** caller-PCM RAW EAR producer remains synthetic/CI-validated only; no normal Runtime C3 consumer has adopted this lease yet. Android microphone, native inference, installed SHA, updater state and Redmi behavior remain REDMI_UNVERIFIED. No release SHA. No user action required.

---
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

## A5/UI cross-canon audit finding (2026-11-21)

- Read back the current-base files a5_ui_admission_bridge.py, a5_admission.py, a5_context_envelope.py, a5_timed_fusion.py, android_control.py, operator.py and runtime.py. The A5 UI bridge is not imported/referenced by any of those normal consumers; it remains explicitly SHADOW-only.
- Its interface accepts consent_active as a boolean and a consent_receipt_ref string, but does not validate a live AndroidControl observe_ui grant or hold a linearizable revocation lease. The ten unit tests only exercise isolated packet admission. They do not prove screen capture, UI-tree observation, Runtime PerceptPacket delivery or device control.
- Core was notified on PR #2239 (comment 7066765197) and the whole-Canon issue #1984 was updated. Keep A5 UI NOT_IMPLEMENTED/SHADOW until a real authenticated OS-issued observe_ui receipt is consumed by normal Runtime, Perception binds it to a revocable source lease, and QA proves revocation through capture → admission → derived context/cache.
- Do not claim AccessibilityService, MediaProjection, screenshot, UI tree, app navigation or Redmi operation. This gap is separate from the caller-PCM audio lease in #2240.

