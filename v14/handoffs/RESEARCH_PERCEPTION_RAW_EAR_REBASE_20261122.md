# Research & Perception handoff — 2026-11-22

## Integration checkpoint

- Base: `boss/v14-recall-store-pin-rebind-20261122` at `d06c63794adc0ef802af9c7d91dc683d8a1057bf`
- Working branch: `research-perception/v14-raw-ear-rebase-d06c637-20261122`
- New commits: 13 ahead of base at checkpoint; no merge, release or deployment claimed
- Scope: Perception-owned RAW EAR input API, speaker-change evidence and A4 voice-cue integration, rebased without overwriting the Boss-owned fair-budget Cognition overlay

## Code now on the rebased branch

- `v13/code/v13/audio_input.py`: caller-supplied mono PCM16 audio-window ingress, bounded sample rate/duration, source and consent provenance, provisional/final event path. This is an API adapter, not Android microphone capture.
- `v13/code/v13/audio_speaker_evidence.py`: calibrated, source-bound speaker-change evidence with batch isolation, age checks and no speaker identity persistence.
- `v13/code/v13/audio_voice_cues.py`: integrates the conservative A4 decision with acoustic/prosody cues; no transcript-only substitution.
- `v13/code/scripts/integrated_audio_context_candidate_20261121.py`: source pins for the exact voice-cue and speaker-evidence blobs; retained the current Boss `cognition = result.get(...)` overlay so audio composition does not erase the fair B1/B2 budget result.
- Recovery, stage and deployer hashes were rebound and read back as a complete chain.

## Exact pin verification

| Link | Verified value |
|---|---|
| Audio overlay Git blob | `bec483911d2b28d386240e6b7798edf85b3ee2ff` |
| Recovery AUDIO_BUILDER_BLOB_SHA1 | matches overlay blob |
| Recovery SHA-256 / stage BUILDER_SHA | `7d5c7c770049ca0c1f75f7c2802033d0773aa0a795085b18dc50b82094ef566b` |
| Stage SHA-256 / deployer STAGER_SHA256 | `26ff96fdf1ec93a7db9bba7ff5060d68bebef64fea3f939aa099ed6e343e1ab3` |
| Voice-cue / speaker-evidence source pins | match exact Git blob SHAs |

## Test and deployment state

- Base candidate `d06c637`: 14 successful, 2 skipped, 1 cancelled workflow run in its current PR-triggered matrix. This is base CI only.
- New rebased branch: exact-head CI pending PR creation. Do not inherit the old branch's 64-test pass as proof for this SHA.
- Local full-repository test suite: BLOCKED; no Aii checkout is mounted in the execution environment. No repository-local Python/native test was run.
- Native llama.cpp model execution: NOT RUN.
- Redmi/Termux: `REDMI_UNVERIFIED`; no live receipt or connected device proof in this run.
- Deployment/release: `NOT_RELEASED`; the Boss base remains a candidate, and a GitHub push is not a device deployment.

## User-visible function and Canon mapping

The rebased candidate adds a bounded audio-window ingress and a conservative speaker-change cue into the existing staged audio-context route. It does not yet capture the Redmi microphone, decode speech, speak, barge in, learn speaker identity, or prove B1/B2/C3 semantic use. Canon paths: A0-A5 audio perception; STEP9/G10C/G10D VOICE_AUDIO remain OPEN; B1/B2/C3 delivery and B3 learned latent coupling remain unaccepted.

## Research next step

The new R-065 ledger entry reviews Draft-KV, FlyGCL, LatCom, StateBridge, NinaXander, Portable Semantics, cross-model negative results and the llama.cpp/gguf-py boundary. The highest-value latent experiment is a matched-versus-deranged receiver-utility test, starting with same-checkpoint B1/B2 StateBridge-style input-prefix alignment, then pair-specific adapters only if a native extraction path and receiver-side utility gate are available. Draft-KV requires a future native KV-side-memory hook; LatCom belongs after sender interfaces work. No model weights were downloaded or changed.

## Coordination request to Boss/Integrator

1. Review this branch against the exact Boss base and merge only after the new exact-head audio and staged/integrated workflows pass.
2. Update `v14/V14_WORK_BOARD.json`, `v14/V14_USER_NEXT_ACTION.md` and the shared coverage index after independent review; these shared coordination files were not edited here to avoid crossing Boss ownership.
3. After integration, obtain a fresh private device receipt before making any Redmi/Termux or microphone claim.
