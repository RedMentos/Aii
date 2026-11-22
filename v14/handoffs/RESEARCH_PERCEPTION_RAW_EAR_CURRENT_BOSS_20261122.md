# Research & Perception handoff — current-Boss RAW EAR rebase
Date: 2026-11-22 05:00 CET
Owner: Research & Perception

## Branch and code
- Branch: `research-perception/v14-raw-ear-currentboss-20261122-run11`
- Code commit: `cfccb91ac9a3ff49f8aae259f92ad8118eaf19c5`
- Base: Boss integration branch `boss/v14-recall-store-pin-rebind-20261122` at `6e6f15322c9fa1931dcf733105d2a32d5372edeb` (docs-only descendant; code-bearing parent `483ef6ddc7140bf76f197d538ec973df42dd95e0`).
- New code paths: caller-supplied audio-only PCM16 ingress; bounded source/generation-bound speaker-similarity diagnostics; A5/A4/C3 audio context in the staged Runtime; optional NumPy pitch backend remains OFF by default.

## Consumer and safety contract
- `audio_input.submit_audio_only(runtime, audio_window)` submits a fixed no-transcript marker and the original caller-supplied window to the staged `Runtime.submit(..., audio_window=...)` contract.
- Source ID, opaque consent receipt, preflight check, lease guard, two-phase revocation subscription and PROVISIONAL/FINAL provenance are mandatory. This adapter does not capture a microphone, transcribe, persist PCM, download models or learn weights.
- Speaker embeddings are caller-supplied and process-local. Uncalibrated thresholds produce raw cosine diagnostics only; A4/C3 remain DEFER. No speaker identity, attention gain, action authority or cross-recording link.

## Exact source-pin readback
- `audio_voice_cues.py` blob: `596d14487b9f2b28609eea79fb8b1b39f8da009c`
- `audio_speaker_evidence.py` blob: `37aa9c392bbb68d60ccff9749c75b41b8783c539`
- integrated audio builder blob: `f79f5c2e36b396fbea2d5d9177729f72c0250c3d`
- recovery wrapper SHA-256: `0ad300e467ecaa0befca6749a1ad9995fe9a715dc49c3556dd0462212a28ca6e`
- stage builder SHA-256: `c24fae1a4cb9b1bc36c3e6064afd15cff432e65833940b46796a41ad697d0623`
- runtime deployer `STAGER_SHA256`: matches the stage builder SHA above.
- VAD comparison workflow expected voice-cue Git blob: matches `596d...`.

## Tests and evidence
- **GitHub source/blob readback:** PASS for the exact files and pin chain above.
- **LOCAL_LINUX full repository suite:** BLOCKED. Environment CPython 3.13.5; no Aii checkout mounted; `git ls-remote https://github.com/RedMentos/Aii.git` fails because github.com DNS cannot resolve.
- **Scratch tests from prior Perception branch:** historical only; not claimed for this new commit. Exact-head CI is pending until PR creation.
- **Native / Android / Redmi:** NOT TESTED. No phone receipt, microphone capture, native speaker encoder, B1/B2/C3 native model execution, TTFT/RSS or install proof.

## Research and decisions
- R-058–R-069 carry the reviewed FASTDIAR, ReDimNet2, eDIAR, TTS/full-duplex, surprise-gated memory, NumPy benchmark, calibration, llama.cpp representation and PACT-Check findings.
- PACT-Check is the relevant cross-organ safeguard: task gains are not communication evidence without dummy, irrelevant, self-communication and receiver-only controls. PLatour is a Linux/CUDA research stack; reuse the evaluation protocol, not the runtime.
- No model, weight, dependency, permission, updater, device state or user data changed.

## Next executable action
Wait for this exact PR head's Python 3.13/3.14 audio, VAD, staged/integrated, migration, owner-read, privacy and deployer checks; fix only exact reproduced failures. Boss/QA then review integration. Keep microphone, model, speaker decision and learning gates OFF until separate evidence and authorization.

Status: DRAFT / NOT_RELEASED / REDMI_UNVERIFIED. User action: none.
