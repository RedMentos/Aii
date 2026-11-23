# Research & Perception handoff — RAW EAR → full-duplex bridge (2026-11-23)

## Implemented candidate

- Branch: `research-perception/v14-audio-duplex-bridge-20261123-run21`
- Current code ancestry checkpoint: `f9c5da84de38d933232503dac7e515e4e07d6e41` (merge parents: prior candidate head + current gpt6 base).
- Latest branch head: `744333d9cfcdc44ac71524914c55cb64043b9612`.
- Base: current `gpt6/v13-private-remote-bridge-20261111` at `fb563d771fe2d493c4ec25abe94280981d24ef5c` (the original branch started at older ancestor `b20e9b1f3dd53af472055adb43da628785494ec4`; a no-force two-parent merge commit brought the current base into the candidate).
- New module: `v13/code/v13/audio_duplex_bridge.py`.
- Consumer: wraps the existing `consume_pcm16_voice_window` A5→A4→C3 admission path and feeds its timed RAW EAR voice-onset result into the existing `duplex.record` / `duplex.settle` path.
- Policy: default `duplex_mode=auto` records only an overlap candidate and never cancels. Only the existing explicit `duplex_mode=interrupt` setting turns a fresh VOICED onset into `AUDIO_BARGE_IN`. `off` remains inert. The bridge uses no ASR transcript, speaker identity, learning authority or action authority.
- Consent: a live, thread-bound `AudioConsentLease` must cover both A5/A4/C3 admission and duplex dispatch. It validates source, generation, receipt, stored event, the exact persisted PerceptPacket payload, and A4 onset evidence. No microphone is opened and no raw PCM is persisted by this adapter.

## Evidence

- LOCAL_LINUX isolated harness: exact bridge module and integration-test `py_compile` PASS; 6/6 isolated harness tests PASS using the exact bridge and duplex module plus a local AudioConsentLease/Store stub for the existing `duplex` and `AudioConsentLease` interfaces. This is not a full Aii checkout test.
- Full Aii Runtime integration test is committed in `v13/code/tests/test_audio_duplex_bridge.py`; exact Python 3.13/3.14 GitHub Actions result is pending after push.
- Full local Aii suite: BLOCKED / NOT_RUN because no checkout is mounted in this runner; GitHub DNS is unavailable.
- Android AudioRecord/provider, MediaProjection, native ASR, microphone permission, and Redmi behavior: REDMI_UNVERIFIED. No device command, CHAT_SEND, update request, permission/model/weight change or data mutation was performed.
- Release: NOT_RELEASED. This candidate is not installed.

## Research basis and limits

- Reuses the already full-text-reviewed R-103 preprint, *Enabling Streaming User Transcription in Full-Duplex Speech-to-Speech Models* (arXiv:2609.15759v1, 2026-09-14). Its separate user-ASR and agent-text heads support keeping user audio events separate from C3 output; its reported 374 ms barge-in result belongs to a 9B + 600M model/system and is not a Redmi expectation.
- Reuses the existing V14 text-duplex contract in `v13/code/v13/duplex.py`: interrupted output is CANCELLED/provisional and excluded from native history. This adapter adds a source-bound acoustic onset route, but it does not implement a learned turn-taking classifier or true streaming speech generation.
- A real provider still needs to call the wrapper while its OS-permissioned AudioRecord lease is held, then route the audio event/transcript to a subsequent Runtime turn. Until that provider exists, this is a synthetic Runtime bridge, not working phone voice I/O.

## Next owner handoff

Core/QA should review the lock order and call `consume_pcm16_voice_window_with_duplex` from the future signed AudioRecord provider. Preserve the provider lease → Runtime.lock order; do not acquire the provider revocation lock while holding Runtime.lock. Before Android tests, add provider revoke/zeroization and process-death tests. Boss should add this candidate to the shared board only after exact CI and independent review.
