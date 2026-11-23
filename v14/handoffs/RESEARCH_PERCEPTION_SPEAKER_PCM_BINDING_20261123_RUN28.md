# Research & Perception handoff — run 28
Date: 2026-11-23 23:00 Europe/Berlin
Owner: Research & Perception
Scope: V14-018 RAW EAR speaker evidence, A5 → A4 → C3

## Branch / PR
- Repository: RedMentos/Aii
- Working branch: research-perception/v14-audio-duplex-bridge-20261123-run21
- PR: #2448, DRAFT / NOT_RELEASED
- Base: gpt6/v13-private-remote-bridge-20261111 @ 8d93236c753f0194224c19edc7411d8d7082b1d6
- Verified branch head at handoff preparation: a23366f4ab72feaf53b965c16de9cc9f818ed04d
- Current code blobs:
  - v13/code/v13/audio_speaker_evidence.py: 25474bb202c1209800f5c8a73e36aeca5555efd6
  - v13/code/v13/audio_voice_cues.py: 2693fb9e337c8fbb481a1d077ea30c0b2ede319f
  - v13/code/tests/test_audio_speaker_evidence.py: 3c7db8e5e1ef51422049fc92fa7bf17b80db9e8d

## Implemented function
1. Speaker embedding batch contract is now schema v14.raw-ear-speaker-embeddings/3.
2. A batch must carry the active consent receipt and exact current PCM SHA-256. The caller must supply the current active-lease receipt separately; a batch cannot self-assert consent.
3. audio_voice_cues passes raw.source_ref.sha256 and the active lease receipt to the registry.
4. Only activity_hint == VOICED frames enter the bounded speaker-reference history. SILENCE, UNVOICED_NOISE, IMPULSIVE and UNCERTAIN batches advance the monotonic input clock but are suppressed from speaker history.
5. Non-speech activity remains available to RAW EAR/A4 novelty. The speaker path does not turn it into speaker change or an external interrupt.
6. PerceptPacket stores evidence/provenance only; vectors remain process-local. No speaker identity, calibrated threshold, or action/learning authority is emitted.
7. The PCM hash binds the supplied embedding batch to the current persisted chunk, but it does not attest the caller-supplied encoder, weights, or recurrent state.

## Local evidence
- LOCAL_LINUX: exact updated audio_speaker_evidence.py source compiled successfully with Python compile().
- LOCAL_LINUX: direct registry harness PASS:
  - active-lease receipt is mandatory; batch self-assertion is rejected;
  - exact current PCM hash accepted; mismatched hash rejected;
  - IMPULSIVE/non-voiced embeddings do not enter history;
  - voiced history remains bounded and excludes non-voiced frame timestamps;
  - consent-receipt epoch change resets history;
  - explicit source/generation/receipt reset removes state.
- LOCAL_LINUX: new repository regression block parsed with ast.parse().
- BLOCKED: full repository pytest was not run because no local checkout/runtime was available in this run.
- CI: last visible PR workflow run 45277411451 ended startup_failure with zero jobs. This is CI BLOCKED, not a code-test PASS or FAIL. Current documentation-only head a23366f4 has no workflow run attached.
- TERMUX/REDMI: REDMI_UNVERIFIED. No connected handset or private owner receipt was available; no AudioRecord, microphone, RSS, TTFT, Android control, or updater proof.

## Synthetic E2E scope
Synthetic PCM16 impulse fixture exercises:
RAW PCM source → A5 activity classification → A4 novelty + speaker evidence → C3 admission summary.
Expected behavior: impulse remains novel; speaker history stays empty; speaker decision defers; external interrupt remains low; packet contains no embedding vectors.
This is a synthetic fixture, not a live microphone turn and not Android evidence.

## Research reviewed
- R-120: “Less can be More: What Aspects of Speech Drive End-of-Turn Detection”, arXiv:2609.11066 (2026-09-10), Interspeech 2026, DOI 10.21437/Interspeech.2026-1705. Full paper read. In its proprietary 8-kHz English telephone test, acoustic+prosody outperformed continuous acoustic+prosody+text fusion on false alarms. No public code/data/weight license or mobile measurement verified.
- R-121: “Towards Multilingual End-of-Turn Detection using Frozen Speech Encoders”, arXiv:2610.39755 (2026-10-29), preprint. Full paper read. Multilingual transfer across English/German/Spanish/Mandarin/Japanese is promising, but labels are diarization-derived, overlap is excluded, and no mobile performance or EOT code/data license is verified.
- Practical implication: keep RAW EAR acoustic/prosodic evidence first-class and ASR optional. Learned EOT remains unimplemented; no model download or swap was attempted.

## Remaining gaps / risks
- V14-018 remains IN_PROGRESS_PARTIAL: no calibrated speaker-change threshold, no speaker identity, no Android microphone evidence, and no acceptance of native Android timing.
- Exact-head GitHub Actions is blocked by startup_failure/no jobs. The full repo regression suite must still run on a working CI runner or a local checkout.
- PR #2433 remains on stale base dfa3945 and contains a separate transactional A4 outcome/N10 path plus speaker-history work. The speaker-history portion is being superseded by this current-base #2448 implementation; the A4 outcome/N10 code has not yet been ported. Do not merge the stale branch blindly.
- The remaining 1-s/2-s invariance regression requested by the board is still pending.
- Core/QA must review source/consent pins and ensure no source-pin relaxation.

## Next executable step
1. Core/QA: restore a runnable exact-head CI job and review the schema-v3 source/consent contract.
2. Research & Perception: add the 1-s/2-s invariance regression to this current-base branch.
3. Then port the transactional A4 outcome/N10 path from #2433 onto the current branch, preserving the newer RAW EAR, teacher-ear, temporal receipt, and duplex consumers.
4. Only after calibrated, consented audio evaluation should an EOT candidate influence turn completion. No action authority by default.

## User action
Keine Aktion nötig. No model download, permission change, device action, weight edit, or productive model swap was requested or performed.

## GitHub metadata blocker
- Attempt to append the run-28 summary to PR #2448 and post the coordination comment on stale PR #2433 was blocked by GitHub API 403: “At least one email address must be verified to do that.”
- Code, tests, board, workplan, research ledger and next-action files were committed successfully to the existing branch. The PR body and #2433 comment were not updated; no merge or release action was attempted.
