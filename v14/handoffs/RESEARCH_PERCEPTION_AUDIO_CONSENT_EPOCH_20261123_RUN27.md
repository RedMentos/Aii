# Research & Perception — RAW EAR consent-epoch isolation (2026-11-23, run 27)

## Ownership and ancestry

- Product base: `gpt6/v13-private-remote-bridge-20261111` at `8d93236c753f0194224c19edc7411d8d7082b1d6`.
- Perception PR: [#2448](https://github.com/RedMentos/Aii/pull/2448), branch `research-perception/v14-audio-duplex-bridge-20261123-run21`.
- Exact code/test head: `bfb36812b9d849fd002a886f24ca79e6dbbf5012`.
- Research-ledger append: `f455be2f2c6811b8cba129df93cb0054a991dd54` (R-119).
- PR remains DRAFT / NOT_RELEASED. No force-push and no changes to the release branch.

## Defect and hypothesis

The Runtime's ephemeral `AudioConsentLease` already binds a source, brain generation and opaque consent receipt. However, the A4 temporal voice filter, temporal registry, speaker-history registry and Silero recurrent stream key previously used only source/generation. Reusing those labels under a renewed receipt could carry voice-activity, speaker-similarity or recurrent VAD state across consent epochs.

Hypothesis: a new receipt for the same source/generation must begin with fresh ephemeral state, and caller-supplied speaker embeddings must be rejected unless their receipt exactly matches the currently held lease.

## Executable changes

- `audio_temporal_evidence.py`: `TemporalVoiceEvidence.update()` now resets on receipt changes; `TemporalVoiceEvidenceRegistry` keys by source/generation/receipt, evicts superseded same-source epochs, and reports `CONSENT_RECEIPT_CHANGED`.
- `audio_speaker_evidence.py`: embedding schema bumped to `v14.raw-ear-speaker-embeddings/2`; batches require the exact active receipt; the bounded registry includes the receipt epoch and reports its reset reason.
- `audio_voice_cues.py`: the actual `consume_pcm16_voice_window()` consumer passes the active receipt into both registries and caller-held temporal state. Silero's recurrent stream ID is a SHA-256 over source/generation/receipt, so the receipt is not exposed in the stream key. Invalid, empty or overlong receipts fail before VAD, packet persistence or A4.
- Benchmark fixtures now carry a synthetic receipt.
- The focused audio workflow now compiles and runs the temporal, speaker and A4/C3 consumer regressions on Python 3.13 and 3.14.
- Research ledger R-119 records the provenance finding and evidence boundary.

## Exact regression coverage added

- Explicit `TemporalVoiceEvidence` object resets when the receipt changes.
- Runtime-local temporal registry starts fresh on receipt renewal.
- Speaker-history registry starts in WARMUP under a new receipt instead of comparing against the old receipt's embeddings.
- Mismatched and missing speaker receipt fields are rejected; schema v2 is asserted.
- The real synthetic RAW EAR Runtime consumer rejects speaker embeddings carrying a different receipt.
- Reused Silero stream object reports `STREAM_CHANGED` when the receipt changes despite contiguous audio timestamps.
- `None`, empty and overlong receipts are rejected before the fake VAD session runs or Store/A4 side effects occur.

## Test evidence — keep environments distinct

- **LOCAL_LINUX:** CPython 3.13.5, NumPy 2.3.5, pytest 9.0.2 are available, but no Aii checkout is mounted. `git ls-remote https://github.com/RedMentos/Aii.git` and direct GitHub/raw URL attempts fail with DNS resolution errors. The exact repository pytest suite and project `py_compile` therefore remain **BLOCKED / NOT_RUN** locally.
- **LOCAL_LINUX isolated contract reproduction:** `python3 /tmp/v14_audio_consent_epoch_contract.py` — **3/3 PASS** for direct temporal reset, registry reset and opaque receipt-derived VAD stream-key change. This harness reimplements only the narrow contract and is not the repository suite.
- **CI:** exact code head `bfb36812b9d849fd002a886f24ca79e6dbbf5012` triggered workflow runs `45265811619` and `45265804183`; both ended `startup_failure` before any job was allocated (jobs endpoint returned an empty list). The same infrastructure failure affected preceding commits on this branch. **No CI PASS is claimed.** GitHub refused retry because the startup-failed runs had no retryable jobs.
- **TERMUX / REDMI:** REDMI_UNVERIFIED. No authorized live device receipt was obtained in this run. No AudioRecord/microphone capture, Android VAD inference, Termux test, RSS/latency measurement or audible playback test.
- **Release / deployment:** NOT_RELEASED / NOT_DEPLOYED. GitHub push is not deployment. No UPDATE_REQUEST, manual command, model download/swap, weight edit, permission change, device restart or user-data mutation.

## Consumer and Canon impact

This is a real code-path correction in RAW EAR A5→A4: temporal voice evidence, optional speaker-similarity evidence and optional Silero state now share the current consent epoch before the A4 salience/interrupt path and C3 admission. It does not add a microphone provider, calibrated speaker identity, semantic turn endpoint, ASR truth, trained latent exchange, weight learning or full-duplex audible output. Those remain open Canon requirements.

## Research note

R-118 remains the relevant fully reviewed FD-VAD preprint (arXiv:2609.35791, submitted 2026-09-16; not peer-reviewed). Its semantic Continue/Stop endpoint is distinct from RAW EAR voice onset. Its 0.5B Qwen + WavLM bundle and A100 timing are not a Redmi candidate; no code/weights were downloaded. No new paper was fully reviewed in this run.

## Coordination and next action

1. **Boss/Core:** when composing the audio branches, preserve this schema-v2 receipt requirement. The separately maintained FASTDIAR adapter must add the active `consent_receipt_ref` to its embedding batch before it is connected to this consumer; do not weaken exact receipt validation.
2. **QA/Core:** rerun the focused workflow on a healthy GitHub runner, then stage the real provider revoke callback so `reset_runtime_temporal_voice_states()` is invoked for the revoked source/generation. Test renewed-receipt behavior, provider revoke, restart, zeroization and same-turn C3 on one exact composed head.
3. **Perception:** after the provider/consumer composition is green, verify the exact A5→A4→C3 path with a caller-supplied synthetic PCM fixture; later, only with explicit device authorization, measure Android AudioRecord lifecycle, CPU/RSS, latency and revocation.
4. Boss owns the shared work board and `V14_USER_NEXT_ACTION.md`; this handoff and R-119 are the Perception evidence to port there.

**User action:** none required. No model, permission or device change was requested or performed.


Additional LOCAL_LINUX sanity: invalid receipt values `None`, empty string and 257-character string were rejected; a valid bounded receipt was accepted; the opaque VAD key changed across receipts and did not contain the receipt literal. PASS (small isolated Python check; not a repository test).


Coordination limitation: attempts to post the PR/whole-Canon comments and update PR metadata were denied by GitHub with HTTP 403 because the connected account requires at least one verified email address. No comment or PR-body update is claimed. This branch handoff and R-119 are persisted/read back; the shared work board and `V14_USER_NEXT_ACTION.md` remain Boss-owned and were not modified in this run.
