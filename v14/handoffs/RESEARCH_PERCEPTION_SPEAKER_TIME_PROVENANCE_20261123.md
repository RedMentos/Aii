# Research/Perception handoff — RAW EAR speaker timestamp provenance
Date: 2026-11-23
Owner: Research / Perception
Parent: PR #2369, branch research-perception/v14-fastdiar-rebased-20261122
Release base: aed1d2b826290c95c70356b5d8b864b5ef382be4

## Implemented
- v13/code/v13/audio_speaker_evidence.py: every measured frame now carries lookback_target_ms and exact reference_frame_end_ms; WARMUP carries an explicit null reference timestamp.
- The algorithm remains diagnostic-only and retains its immutable pre-batch history snapshot. It does not classify speaker identity or promote caller thresholds into decisions.
- v13/code/tests/test_audio_speaker_evidence.py: the batch fixture now accepts an explicit frame step/look-back; a new exact 1 s / 2 s reference-time regression compares the same frame under 1 s and 2 s batch tails.
- v14/V14_RESEARCH_LEDGER.md: append-only R-110 research/implementation note. Preserve R-100 and R-108/R-109 entries from the separate ledger integration branches.

## Exact revisions and readback
- Code commit: 6e34b949c0dcf4ddb626c2b0b44233f3ef67678f
- Code blob: f3898f8be22416d83ff093908df1019a39d453c4
- Test commit: eca8d03f471e116680cf021a3d19aa4d99cb8dab
- Test blob: aa0e1ae3f92569259d1ea3764c76f06432bb0705
- CI exact-head readback: pending at handoff creation; do not infer a pass from the prior head.
- Local full checkout/pytest: BLOCKED; no repository checkout is mounted and the execution container cannot resolve GitHub. This is not a local test pass.
- Android/Termux/Redmi: REDMI_UNVERIFIED. No microphone capture or device mutation.

## Cross-lane blocker
Core PR #2370 branch boss/v14-fair-budget-current-base-20261122-run14 at 9e71991acab51c6aa9afc588614953714839cb18 still had stale immutable source pins in v13/code/scripts/integrated_audio_context_candidate_20261121.py:
- audio_voice_cues.py: expected b18e450162b062b09368a12b1ca18924ed8c5025; current Perception blob remains 1fc3ac7b6624fcd0d1aef52a77ae6221fdf43288.
- audio_speaker_evidence.py: expected 37aa9c392bbb68d60ccff9749c75b41b8783c539; new Perception blob is f3898f8be22416d83ff093908df1019a39d453c4.
Core owns the composer and its downstream recovery/stager/deployer pins. Perception did not edit them. Teacher Ear remains optional and absent from the Core candidate; do not make RAW EAR depend on ASR.

## Research boundary
FASTDIAR arXiv:2610.02941v1 (2026-10-02) describes 80 ms causal frame embeddings from a two-second past window and a ten-frame look-back with 960 ms delay. Its reported CPU benchmark is on an AMD Threadripper PRO 5995WX, not Android. The official code repo declares MIT; checkpoint terms remain separately unverified. No model/dependency/weights were downloaded or used.

## Next executable action
After Boss/Core rebind the two exact source pins, rerun PR #2369 staged-runtime + integrated-regression against the exact new head. Keep the focused Python 3.13/3.14 RAW EAR workflow and the no-threshold/unvoiced negatives green. Then verify source/generation/consent/revocation/reset and no-vector-persistence on the exact staged consumer. Only after that can the audio slice move from WIRED_SYNTHETIC candidate toward accepted integration; no Redmi claim is possible yet.

## Shared-file ownership
The V14 master, Workplan, Board and V14_USER_NEXT_ACTION.md remain Boss/Integrator-owned. Boss should sync this exact Perception SHA, exact CI results and Core pin dependency there after review; do not overwrite concurrent branch work.

## Repository hygiene
A handoff-file creation was initially sent to the default branch because the optional branch argument was omitted. The file was immediately deleted from main using its exact blob SHA. The handoff is being recreated on the owned Perception branch; no source code, model, release or device state was changed by that transient documentation commit.
