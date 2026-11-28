# Research & Perception — Run 81 handoff

**Date:** 2026-11-28  
**PR:** https://github.com/RedMentos/Aii/pull/2579  
**Branch:** research-perception/v14-a4-multihorizon-effect-20261128-run81  
**Code/test head:** af951da77c91835d0cd31bf9193352d41585a6d2  
**Parent:** PR #2578 at 7d2e4eb8d798f8dfeef78331728dfaf8c152980c

## Implemented

1. Corrected the existing one-step A4 counterfactual: candidate and no-update baseline now advance through the same current cue delta before future/replay scoring. Added a helper and regression test; bumped experiment schema to v2.
2. Added multi-horizon ridge heads for 1, 3 and 8 future cue windows.
3. Added abrupt-to-smooth recovery sessions, a separate training replay anchor, two disjoint held-out replay anchors, worst-anchor retention, per-horizon precision/recall/regret and abstention reporting.
4. Extended the exact A4 workflow to compile, test and emit the new experiment on Python 3.13 and 3.14.

## Verification

- Exact PR CI #46096825708: PASS on Python 3.13 and 3.14. Each job: py_compile; 10/10 A4 retention tests; 8/8 corrected one-step tests; 7/7 multi-horizon tests; 54/54 production audio-temporal-predictor pytest tests.
- Private-bridge push workflow #46096822412: PASS; not a phone receipt.
- LOCAL_LINUX scratch API-compatible stub: py_compile PASS; 7/7 multi-horizon tests PASS on CPython 3.13.5 x86_64.
- Full local Aii checkout/pytest: BLOCKED/NOT_RUN (no mounted checkout; github.com DNS failure).
- Redmi: REDMI_UNVERIFIED. Private read-only issues #1043–#1045 have no device_status receipt; V13OBS #115 is historical 2026-11-24. Updater UNKNOWN.
- Release: NOT_RELEASED.

## Result and decision

The Run80 v1 result was invalid because the baseline did not consume the current cue window. Corrected one-step v2: 276 training examples, zero positive labels, zero selected updates (69 smooth / 14 abrupt candidates).

Multi-horizon v1: 313 training examples per horizon. Selected updates: 0/74 smooth, 0/16 abrupt, 0/69 abrupt-to-smooth. Utility delta and worst-retention delta versus the synthetic NO_UPDATE reference are both zero. Positive counterfactual candidate fractions rise with horizon in some regimes, but the gate abstains throughout. This is a negative research result, not a performance improvement.

**Decision:** do not adopt the predictor or change A4 defaults. No production Runtime consumer, persistent weight update, microphone, permissions, model files or device state changed. The reference is a synthetic NO_UPDATE checkpoint, not deployed C0.

## Research

- R-200: *Replay can provably increase forgetting*, PMLR 330:15–42 (2026). Official proceedings abstract reviewed; full PDF not reviewed. No code/licence reuse.
- R-201: *Trust Region Continual Learning as an Implicit Meta-Learner*, arXiv:2602.02417v3 / NeurIPS 2026. arXiv abstract and official author-lab page reviewed; full paper not reviewed. No official implementation/licence verified; no code reuse.

## Ownership handoff

- **Boss/Integrator:** review #2579 with parent #2578 and choose convergence ancestry; keep this research PR draft until shared acceptance is resolved.
- **Core:** Recovery-to-Stage-to-RuntimeDeploy composer and arithmetic/observer source pins remain Core-owned.
- **QA:** migration PARTIAL-vs-UPDATED assertions remain QA-owned.
- **Research & Perception:** next test should improve delayed outcome-label calibration and use an authenticated exact deployed C0 when available; do not weaken the abstention rule to force learning.
