# Research & Perception handoff — RAW EAR temporal gap correction

**Date:** 2026-11-21
**Owner:** Research & Perception / V14-006
**PR:** https://github.com/RedMentos/Aii/pull/2177
**Branch:** research-perception/v14-prosody-attention-current-20261121
**Producer blob:** 7b1d519cd36ede4b520d78e22c0f89132a1c73a5  
**Temporal-state blob:** f693f8b8394558a63d87a35fc67ea3db9dcb1929  
**Code/test/workflow commit:** ce692a87e585c8cc7a6a871dd550ca585a6bac3d
**Base:** release-development branch gpt6/v13-private-remote-bridge-20261111 at 569680bc10eabeb94ea5a1695d4bf77b8584e0a0

## Functional change

TemporalVoiceEvidence.update no longer treats an unobserved time gap as though the current window's VOICED/SILENCE label covered that gap. It decays the previous evidence with release_tau_ms, emits a gap offset when the offset threshold is crossed, and then processes only the newly observed interval. Partially overlapping windows advance only their newly covered suffix. Gaps beyond reset_gap_ms reset state without inventing an observed offset.

The actual existing consumer is consume_pcm16_voice_window in v13/code/v13/audio_voice_cues.py; it calls this state object and uses its voice-active/onset result to modulate A4 attention. The patch changes only temporal A4 salience. It does not add capture, ASR, a trained VAD, speaker identity, learning authority, action authority, full duplex, or Android permissions.

## Regression and negative control

- New tests cover a 500 ms gap followed by voiced input (gap offset then new onset), a gap followed by silence, overlapping windows, and a gap beyond the reset threshold.
- Legacy negative control: the old update rule gives 0.999739 voice evidence after the 500 ms gap and keeps the old active state; the corrected sequence first decays below the 0.22 offset threshold and then reaches 0.661076 after the new 80 ms voice window.
- LOCAL_LINUX isolated mirror of the updated state filter plus six existing and four new state tests: 10/10 PASS; py_compile PASS. This is not a full Aii checkout.
- Exact GitHub Actions code/test HEAD ce692a87e585c8cc7a6a871dd550ca585a6bac3d: focused RAW EAR 23 passed on Python 3.11 and 23 passed on Python 3.13 (run 44888560930); staged-runtime 240 passed / 10 skipped / 47 subtests and integrated-regression 415 passed / 3 skipped / 58 subtests (run 44888560905); privacy scan 44888560951 PASS.
- Safe-additive run 44888560942 fails because an existing module/workflow was changed; this is the expected protected boundary. No bypass.
- Full local Aii checkout blocked by GitHub DNS; Redmi remains REDMI_UNVERIFIED.

## Research

S4VAD, Cohen et al., arXiv:2609.11110 (2026-09-10), full 8-page text reviewed 2026-11-21. Its diagonal S4D state-space VAD explicitly controls evidence decay and evaluates onset delay under noisy timestamp labels. It reports 0.972 AUROC / 39 ms onset latency on LibriSpeech and 0.846 / 114 ms on AVA-Speech; 0.3 ms model inference latency was measured on Apple M4 Max. It used 16 kHz, 32 ms frames, 10 ms hop, 64-dimensional log-Mel features, four 64-dimensional S4 blocks and a 201-step causal kernel. No official code/weights/license were verified; no implementation imported. These are paper results, not Redmi measurements.

## Integration boundary and next owner

- Boss: independently review #2177. Safe-additive rejection is not to be bypassed.
- Core: after review/merge, update #2158 to the exact V3 producer and prove the normal Runtime path, separate text/audio packets, and B1/B2 OfferPacket->C4->C3 delivery.
- Perception: then run matched RAW EAR V3 vs libfvad fixtures and profile onset/offset, FPR/FNR, CPU/RSS and Android ABI. libfvad remains research-only until BSD-3-Clause + PATENTS, ARM ABI and device cost are reviewed.
- No Redmi deployment, device update request, model download/swap, permission change or user-data operation was performed.