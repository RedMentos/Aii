# Research & Perception Run 41 — RAW EAR temporal chronology

**Started:** 2026-11-26T05:54:29+01:00 (automation context). **Checkpoint:** 2026-11-26T06:08:28+01:00.  
**Branch:** `research-perception/v14-audio-temporal-window-order-20261126-run41b`  
**PR:** [#2527](https://github.com/RedMentos/Aii/pull/2527), DRAFT, child of Perception #2524.  
**Current head:** `998a8f02e3011b63581c2888316b4073b589d474`.  
**Base:** parent branch head `b298719af8faf75811d03d486de7725395a590b0`.

## Defect and implementation
The A4 temporal voice filter accepted a later window whose `start_ms` moved backward as long as `end_ms` increased. That allowed an out-of-order interval to advance temporal voice state. `TemporalVoiceEvidence` now tracks the last accepted start and end per source/generation and rejects backward starts before mutation. Equal starts for cumulative windows remain valid; forward-moving overlaps still count only the new suffix; source/generation/long-gap resets clear both clocks.

Existing consumer: `audio_voice_cues.consume_pcm16_voice_window()` imports and uses `TemporalVoiceEvidenceRegistry`; its temporal voice evidence feeds A4 salience modulation. This is still caller-supplied PCM16, not a normal Android microphone provider or normal-turn C3 path.

## GitHub artifacts
- Source blob: `f8ebe2c7d0a196642f0383a54a97025b4c1bbaeb`
- Test blob: `fe7a716b4ce88ed2868337deda9f2c454360561b`
- Perception comparator source-pin commit: `998a8f02e3011b63581c2888316b4073b589d474`
- Old attempt #2526 was closed as superseded because it started two docs commits behind current parent b298719; no force-push or history rewrite.

## Local tests
Environment: LOCAL_LINUX, CPython 3.13.5, pytest 9.0.2.
- Reconstructed exact fetched source/test files in `/tmp/v14-audio-chronology`; local Git blob hashes match the remote blobs above.
- `python -m py_compile`: PASS.
- `python -m pytest -q tests/test_audio_temporal_evidence.py`: **14 passed**.
- Baseline negative control: the new backward-start test fails against the previous source with `DID NOT RAISE`; patched source passes.
- Stress: 10,000 monotonic overlapping windows PASS; 1,000 backward-start negative cases rejected; source/generation reset accepts a lower new time origin.
- Full Aii checkout/full suite local: NOT_RUN; no checkout mounted and GitHub DNS unavailable.

## CI status at checkpoint
- Initial exact PR comparator workflow `45759546574` failed only because its Perception-owned expected temporal blob still pointed to old `098ce2...`; workflow pin corrected to `f8ebe2...` in commit `998a8f0`. Rerun `45759867790` queued.
- Initial staged-runtime workflow `45759546449`: **16 failed, 237 passed, 10 skipped, 2 errors, 47 subtests passed**. All relevant failures report `audio source blob changed: v13/audio_temporal_evidence.py`; the downstream two-checkout migration reports PARTIAL rather than UPDATED. This is the Core-owned recovery/stage/RuntimeDeploy source-pin chain. Rerun `45759867775` queued.
- Perception does not edit Core/QA-owned recovery, stage or deployer pins. Core/Integrator must rebind those pins bottom-up to the new source blob and rerun the exact stage/migration gates.
- Parent #2524 focused tests are 26/26 PASS, but its shared staged/integrated chain also fails on the separate Core-owned `v13/native_latent_receiver.py` source pin. Core #2523 is a manual local-TTY diagnostic, not a normal-turn hook.

## Research
R-163 records FASTDIAR (arXiv:2610.02941, 2026-10-02 preprint) as an optional frame-level speaker-embedding candidate. Only abstract + official repository were reviewed; no full-text claim. Code repo MIT; checkpoint weights license not separately confirmed; 2.4M small model, PyTorch/torchaudio/torchcodec and FFmpeg; no Android/ARM64 evidence. No code or weights reused/downloaded.

## Device and deployment boundary
Last available private V13OBS snapshot is issue #115 (2026-11-24 09:28 UTC): auto-update enabled and dashboard/runtime UP_TO_DATE at `8d93236c753f0194224c19edc7411d8d7082b1d6`, but AI STOPPED_BY_USER and model processes stopped. New private read issues #862–#864 have no comments. Current install/runtime/updater status remains REDMI_UNVERIFIED. No UPDATE_REQUEST, CHAT_SEND, shell action, restart, model/weight/permission/data mutation. GitHub push is not deployment.

## Actual status / next step
- New behavior: out-of-order RAW EAR windows are rejected before A4 state mutation.
- Not delivered: microphone capture, normal-turn audio provider, C3 lease-through-generation, ASR, speech output, full duplex, audio learning, native GGUF, trained latent exchange, Redmi verification.
- B3 OFF; NOT_RELEASED; REDMI_UNVERIFIED.
- Next: Core refreshes audio and native-receiver pin chains; Perception polls exact CI. After integration, Core wires the normal-turn caller while holding the revocable audio lease through the entire C3 generator. No user action required.
