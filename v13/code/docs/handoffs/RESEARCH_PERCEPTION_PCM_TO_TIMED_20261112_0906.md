# Research/Perception handoff — 2026-11-12 09:06 CET

Owner: Perception. Parent PR #1830, stacked on #1827. Do not merge independently.

## Code and evidence
- `v13/code/v13/pcm_bridge.py`: converts bounded mono PCM16LE via the existing `raw_ear_pcm.pcm16le_frames` into the exact six-key JSON schema expected by `a3_timed_audio.observe_timed_audio`. Derived feature vector: mean RMS and mean zero-crossing rate. Relative timing is offset by explicit `start_ms`.
- `v13/code/tests/test_pcm_bridge.py`: four deterministic tests. Locally executed on Linux Python with a manually reconstructed copy of the upstream `raw_ear_pcm.py` obtained from GitHub file content: **4 PASS**. Exact GitHub head, repository CI, Android Termux: UNVERIFIED.
- Unknown pitch and speech probability are represented as zero placeholders required by the existing strict timed-audio contract; these must NOT be interpreted as measured zero pitch or no speech. A future schema revision should use explicit nullable/unavailable values.
- No ASR, speaker identity, microphone permission, action authority, voice effector, model quantization, or native Redmi evidence.
- No new third-party code or data; Python standard library only.

## Integration blocker and next action
- Caller must explicitly insert returned JSON into an authorized `Runtime.store` source and construct the actual source reference. This PR does not invent an unverified Store write API.
- Next test must create an authentic Store source and run `observe_timed_audio(runtime, A3Projector(2, ...), ref)` through the existing A3 source verifier, then canonical A5 and B/C contracts.
- Source references, revocation, and Android permissions must remain external to trainable model authority.
- Historical Redmi RAM ~5.84 GB total/~1.78 GB available is not a current measurement.
- Coordination/Canon files were not accessible from this stacked branch or default branch in this run; recheck PR #1668 and canonical integration before merge.
