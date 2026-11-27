# Research & Perception Run 56 — A4 update gating, retention and restart
Date: 2026-11-27
Run started: 04:02 CET (03:02 UTC)
Checkpoint: 04:23 CET (03:23 UTC)
Completion time: not yet measured at this checkpoint

## Branch / PR
- Repository: RedMentos/Aii
- Branch: `research-perception/v14-a4-error-gated-plasticity-20261127-run56`
- PR: [#2548](https://github.com/RedMentos/Aii/pull/2548), DRAFT, stacked on [#2540](https://github.com/RedMentos/Aii/pull/2540)
- Current code/test head at this checkpoint: `c73d18bc626abacdf9eb56fd09b2a65b905cdad1`
- A4 predictor blob: `c2df22ce5906db3f3596d39719aa8e9d8e5647fa`
- Audio composer blob: `a50f975161d359a6cde5b4ed88cb187672c3c8bc`
- A4 direct-test blob: `fdc29a14474756cfb2bc82dc1ee81329c18aeaeb`
- Experiment blob: `e2b8beb223ae8da79c6988362b7456c15cded23e`
- Experiment-test blob: `4eda10c09c8376ba2e9c3e98eef161878c9453e1`
- A4 workflow blob: `6bb875983c32c7729051f2fac24ad457be89d2fb`
- Model-lab PYTHONPATH fix blob: `e9d9137fd1d931b33a29e73845d5f290fee812ec`

## Product change
- `AudioTemporalPredictor` and `AudioTemporalPredictionRegistry` now accept opt-in `update_policy="MEMORIZED_ERROR"`; default remains `EVERY_FINAL`.
- The experimental regression rule updates when model MAE exceeds the persistence baseline or when the same quantized previous→target cue-delta transition was previously mistaken in the current stream.
- The process-local transition fingerprint memory is bounded (default 128; ablation 64), excluded from `state_dict`/persistent storage, and cleared by reset, consent/gap/chronology replacement and restart. Hashing is not anonymisation.
- `allow_update=False` advances temporal context for read-only evaluation without changing weights, update count or gate memory.
- The experiment includes `NO_UPDATE` as a negative control and reports gradient-L2 sum, total weight-delta L2, parameter-diff L2, retention drift and restart equality.
- The integrated audio-context composer manifest was refreshed to the exact new predictor blob. Core's downstream recovery pin is still stale and requires Core ownership/rebase.

## Exact CI evidence at code/test head
- A4 update-gate/retention: 6 tests PASS on Python 3.13 and 3.14.
- RAW EAR fastpath: 161 tests PASS on Python 3.13 and 3.14.
- Audio feature-set probe: 15 tests PASS on Python 3.13 and 3.14.
- Model-lab: 73 tests PASS, 4 skipped because native libfvad/WebRTC wrappers were not built; privacy scan CLEAN.
- VAD comparison: 172 tests PASS on Python 3.13; Python 3.14 was still in progress at this checkpoint.
- Latent-cache-tiny and offline-bridge-security: PASS.
- Staged Runtime: FAIL, 20 failed / 233 passed / 10 skipped / 2 errors / 41 subtests passed. The failures include the stale downstream audio composer pin, Core-owned `v13/contracts.py` and `v13/cognition.py` pins, and QA two-checkout migration expecting UPDATED but receiving PARTIAL.
- Integrated regression: FAIL, one selected regression because `termux_runtime_recovery_candidate_20261121.py` still expects composer blob `831080bceec90711bd42e0fa4eba47c669975c98`, while this branch's composer is `a50f975161d359a6cde5b4ed88cb187672c3c8bc`. Core was notified on PR #2547; do not patch Core-owned recovery files in this Perception lane.
- Earlier intermediate failures caused by stale pins/test context were corrected before the current focused green checks. The remaining staged/integrated failures are explicit cross-lane blockers, not evidence of Redmi success.

## Synthetic ablation results (60 observations per stream; Linux CI)
| Stream | EVERY_FINAL updates / MAE | MEMORIZED_ERROR updates / MAE | NO_UPDATE MAE |
|---|---:|---:|---:|
| Periodic speech | 59 / 0.20170 | 7 / 0.25575 | 0.21605 |
| Non-speech impulses | 59 / 0.20631 | 41 / 0.20158 | 0.27251 |
| Mixed activity | 59 / 0.27233 | 26 / 0.28714 | 0.32116 |

- Update count falls by 30–88% on these fixtures, but MAE worsens on periodic speech and mixed activity; only non-speech is slightly better.
- Periodic speech parameter-diff L2 from zero: 1.06464 EVERY_FINAL vs 0.63463 MEMORIZED_ERROR. Gradient-L2 sum: 12.87747 vs 3.17314. This is the 182-parameter A4 predictor, not a B1/B2/C3 master.
- Old-pattern MAE drift after a new non-speech task: +0.06792 EVERY_FINAL vs +0.04350 MEMORIZED_ERROR. However gated MAE starts at 0.29879 and ends at 0.34230, versus 0.16741→0.23533 for EVERY_FINAL. The lower drift is not a quality/retention win.
- Forward prediction still runs for every cue window; no energy or latency savings are claimed. Default policy remains EVERY_FINAL.

## Local environment
- LOCAL_LINUX scratch, CPython 3.13.5: py_compile PASS; direct gate/replay, no-error skip, bounded-memory, evaluation-only, no-update and restart-state checks PASS.
- The scratch was not a full Aii checkout. Container GitHub DNS resolution failed, so the exact repository tests were run by GitHub Actions instead.

## Research
- Reused the full-text review already recorded in R-175: Pache & van Rossum, “Mistake gating leads to energy and memory efficient continual learning”, bioRxiv 2026-04-20, DOI 10.64898/2026.04.16.718919; journal version 2026-11-05, DOI 10.1162/NECO.a.1602. This A4 regression adaptation is not paper-exact.
- New full-text review R-179: Li & van Rossum, “Energy efficient synaptic plasticity”, eLife 2020;9:e50804, DOI 10.7554/eLife.50804. It proposes transient and persistent synaptic components with thresholded consolidation; results are modelled energy-cost simulations, not phone power measurements. The upstream simulation repository is GPL-3.0. Aii has no root LICENSE, so no code was reused.

## Device / release
- No new Redmi or Termux proof. Private read-only relay issues #1003 (PIPELINE_STATUS) and #1004 (HEALTH) had no device_status receipt at this checkpoint. Existing private V13OBS #115 is only a historical snapshot updated 2026-11-24 and says STOPPED_BY_USER.
- REDMI_UNVERIFIED. Current updater/installation state is not verified; do not infer it from GitHub CI or the old auto-update flag.
- RELEASE: NOT_RELEASED. No model, weights, permissions, phone data or installed package changed.

## Next actions
1. Poll remaining VAD comparison Python 3.14 CI.
2. Core rebase PR #2547 onto #2548 after Perception focused checks, refresh the exact composer/recovery pins, and rerun staged/integrated regression.
3. QA owns the two-checkout migration PARTIAL-vs-UPDATED assertions.
4. Perception next: source/session-disjoint A4 omission false-positive tests, then A5 screen/UI event-to-PerceptPacket path. Keep Android microphone/screen capture unverified until explicit device receipt and OS consent.
5. No user action required.
