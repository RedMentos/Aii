# Research & Perception handoff — RAW EAR consent lease before PCM processing
**Date:** 2026-11-21  
**Stack:** PR #2214 QA branch → this Perception fix PR → PR #2207 Perception producer → current release integration  
**Canon:** A0–A5 / A-plane RAW EAR, A4 attention, C3 admission, consent/provenance, STEP9/G10C/G10D VOICE_AUDIO.

## Reproduced defect
QA PR #2214 exact head `48bbef90e0ae0cf7bcb36deead1dde1b90551bf5` added a deterministic race test. Exact GitHub Actions run `44911185085` failed at `test_consent_revocation_racing_after_initial_check_cannot_process_pcm_unleased`: **1 failed, 25 passed**. The assertion showed `observe_pcm16` and `extract_voice_cues` had already run after revocation won. Compilation passed; the staged/integrated workflow on that head passed, but it does not cover this pre-lease race.

## Implemented change in this branch
- `consume_pcm16_voice_window()` now acquires the provider's linearizable consent lease before `observe_pcm16`, feature extraction, optional Silero VAD state advancement, PerceptPacket construction, temporal updates, persistence, A4 attention and C3 admission.
- The lease remains held across the complete processing/consumer path. If revocation acquired the provider's shared synchronization primitive first, lease entry rejects before any PCM-derived work. If this consumer acquired it first, revocation waits until the operation exits.
- The source ID and consent receipt returned by the Store/event binding validator are checked against the lease identity before persistence. A mismatch fails closed.
- This contract still depends on the provider using the same synchronization primitive for all application-level revocation paths. A boolean callback by itself is not sufficient. This is not an Android OS permission primitive.

## Evidence and limits
- The pre-fix failing test and exact run are above; the new code has not yet been validated by its post-fix CI at this handoff.
- LOCAL_LINUX full repository checkout/tests: **BLOCKED** — `git ls-remote https://github.com/RedMentos/Aii.git HEAD` failed because this environment cannot resolve `github.com`. No full local Aii test PASS is claimed.
- No phone/microphone was connected. No Redmi, Termux, native model, ONNX Runtime or ARM ABI result is claimed. **REDMI_UNVERIFIED / NOT_RELEASED**.
- This producer fix does not yet prove the downstream Core consumer removes derived `AUDIO_ACOUSTIC_CONTEXT` after revocation; Core #2200 still needs that independent cleanup/negative test. P0 #1904 native chat correctness, latency and B1/B2→C4→C3 consumption remain open.

## Research added
- R-031: FD-VAD semantic endpointing (arXiv:2609.35791v1, 2026-09-16), full text and official MIT code/model card reviewed. Strong future full-duplex Continue/Stop idea, but 0.5B Qwen + WavLM bundle (~1.5 GB) and A100-only timing make it unsuitable for an unmeasured phone swap. Keep it a separate future turn-state organ, not a replacement for RAW EAR.
- R-032: S4VAD onset-latency evaluation (arXiv:2609.11110v1, 2026-09-10), full text reviewed. Reported P50/P90/P95 10/90/130 ms on LibriSpeech; hardware test was Apple M4 Max 64 GB, not Android. No official code/license verified. The useful near-term adaptation is to measure onset/offset latency and annotation uncertainty in the existing RAW EAR comparator.

## Next executable steps
1. Read exact post-fix PR-head RAW EAR/Perception CI; fix and retest any failure.
2. Ensure QA #2214's race test passes against the updated producer, then Boss rebases the stacked #2214/#2207 chain onto current release HEAD and runs exact staged/integrated regression.
3. Core rebases #2200 to the new producer blob and removes derived audio context on consent revocation; add a negative test proving no stale derived context remains.
4. Keep the optional Silero model path local/hash-pinned and OFF unless a separately authorized real ARM/Termux comparison is available. Do not change installed models or permissions.

## Post-push CI correction — 2026-11-21

The first exact push on `829637cd26e11bc8fd294e50c0aa9a940c083098` exposed two independent regressions:
1. RAW EAR Python 3.11 and 3.13 each reported 49 passed / 1 failed. The existing commit-boundary negative test expects its third consent check to occur inside the Store transaction. Moving the preflight check out entirely shifted that check to the later pre-C3 guard; the packet had already committed. The metadata-only preflight check is restored before lease acquisition. The authoritative lease recheck still occurs under the shared provider lock, before any PCM-derived work.
2. The comparator's exact source pin still expected the prior producer blob `e75c393939183d2f16e071ebf4a6f5ff65417a61`; the new producer blob changed by design. The workflow pin is updated to `2c7c5ff203afa8da8a6cd6841cc24ccd5db67aed`. The pinned libfvad source and temporal evidence pin are unchanged.

Both failures were real and are not being marked PASS. The next exact-head CI must prove the corrected call ordering, Store rollback, pre-lease revocation behavior and comparator source identity. Full local Aii tests remain blocked by GitHub DNS.
 
## Exact post-fix verification — 2026-11-21 14:16 UTC

**Exact branch head:** `8defa00862bee38190a6a7362d8bad3dbb7052f1`  
**RAW EAR producer blob:** `2c7c5ff203afa8da8a6cd6841cc24ccd5db67aed`

- GitHub Actions run `44912705879`: exact RAW EAR → A4 → C3 suite **50/50 PASS** on Python 3.11 and **50/50 PASS** on Python 3.13; compile step passed. Includes the pre-PCM revocation race and the in-transaction Store rollback negative control.
- GitHub Actions run `44912705872`: comparator suite **8/8 PASS** on Python 3.13 and **8/8 PASS** on Python 3.14. The pinned libfvad C source built on Ubuntu; `make check` passed **13/13**. WebRTC comparator was also available. This is GitHub-hosted LOCAL_LINUX native comparator evidence, not Android.
- GitHub Actions run `44912705940`: Perception public privacy scan PASS.
- GitHub Actions run `44912705906`: offline bridge security PASS.
- GitHub Actions run `44912711686`: staged-runtime **249 passed / 10 skipped / 47 subtests**; staged arithmetic/broker/output-policy **42 passed / 37 subtests**; integrated-regression **415 passed / 3 skipped / 58 subtests**. This is a separate staged Linux candidate/recovery harness, not proof that the live Android installation changed.
- LOCAL_LINUX isolated concurrency harness: PASS for (a) revoked-before-lease → zero PCM processing and (b) revocation during an acquired lease → revoker waits until processing exits.
- Full local repository checkout/test remains BLOCKED by GitHub DNS. No full LOCAL_LINUX Aii test suite PASS is claimed.

**Integration/release boundary:** this PR remains stacked on QA #2214, which targets Perception #2207. The current release-development branch HEAD is `5a141153f7d33906408fd638ce56cfbee459cf08`; #2207 still requires Boss-controlled rebase onto it before integration. No PR was merged and no release SHA was produced: **NOT_RELEASED**. No connected Redmi receipt was obtained during this run: **REDMI_UNVERIFIED**. No microphone capture, installed model, weight, permission, updater state or phone data was changed.

**Remaining system gap:** Core #2200's source-bound acoustic context is rechecked at each view and tombstoned on a later revoked view, but the current staged test is primarily source-pin/string coverage; it does not yet prove an eager revocation callback or execute a full record → revoke → B1/B2/C3 view → Store tombstone/restart sequence. This was reported directly on #2200. P0 #1904 remains open and is not addressed by this audio-consent fix.

