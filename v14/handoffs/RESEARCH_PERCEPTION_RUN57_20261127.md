# Research & Perception — Run 57 handoff (2026-11-27)

## Branch / integration

- Repository: `RedMentos/Aii`
- Branch: `research-perception/v14-a4-error-gated-plasticity-20261127-run56`
- Parent PR: [#2548](https://github.com/RedMentos/Aii/pull/2548), stacked on Perception #2540.
- This run extends only Perception-owned `v13/code/v13/audio_temporal_prediction.py`, its existing tests, and the dated research ledger. It does not edit Core recovery/stage/deployer files or the shared V14 master.
- New policies are opt-in only: `TRANSIENT_CONSOLIDATE` and `TRANSIENT_NO_CONSOLIDATION`. Existing `EVERY_FINAL` default and `MEMORIZED_ERROR` behavior are preserved.
- The transient matrix is bounded by `max_transient_norm`; only when its L2 norm crosses `consolidation_threshold` does the consolidating policy transfer it into the persistent numeric weights. The no-consolidation policy is the negative control.
- Existing `state_dict`/SQLite schema persists only consolidated weights and the committed-update count. Pending transient deltas and temporal state are discarded on load/restart. The existing source/generation/consent reset path clears both matrices.

## Runtime wiring and exact source pins

- Runtime config keys: `raw_ear_temporal_update_policy`, `raw_ear_consolidation_threshold`, `raw_ear_max_transient_norm`; absent keys preserve `EVERY_FINAL`, invalid values fail closed.
- Exact Git blob readback: `audio_temporal_prediction.py=24e2c867613a33c33a58a779529c629ecfde37ef`; `audio_voice_cues.py=4bfcf31a7738bb390781babab8e11518896a3580`; candidate builder `019992e2e200b0c5c52d7f18fb5f38ff4185e396`.
- The composer source manifest pins both exact blobs. This means the new policy is reachable through the existing caller-PCM Runtime consumer when explicitly configured; it is not active by default.

## Verification

- LOCAL_LINUX scratch algorithm reproduction: **3/3 PASS** for thresholded consolidation, no-consolidation, and restart discard. This is a standalone reproduction, not repository pytest.
- Exact repository A4 update-gate workflow on the new code/test SHA: **PENDING** at handoff creation; read exact Python 3.13 and 3.14 results before claiming acceptance.
- Full local Aii checkout and full pytest: **BLOCKED / NOT_RUN** (no mounted checkout; GitHub DNS/network unavailable in the execution environment).
- TERMUX/REDMI: **REDMI_UNVERIFIED**. No microphone capture, native model, phone command, owner-read request, update request, installation, or device mutation.
- Release: **NOT_RELEASED**. No model/weight swap or new permission.

## Why this is not an energy claim

The implementation is a bounded two-timescale plasticity ablation inspired by Li & van Rossum, *Energy efficient synaptic plasticity*, eLife 2020, DOI 10.7554/eLife.50804. The paper's energy benefit comes from a modelled cost function and simulations, not measured Android power. The upstream simulation repository is GPL-3.0; no code was reused.

## Known blockers

- PR #2548's previous staged Runtime and integrated regression failures are still owned by Core/QA: stale Core composer/contracts/cognition source pins and migration PARTIAL-vs-UPDATED assertions. This Perception change does not modify those owners' files.
- The Run 56 `MEMORIZED_ERROR` ablation reduced updates but worsened MAE on periodic speech and mixed activity. Keep it opt-in; the new transient policy is a separate ablation, not a demonstrated quality improvement.
- No trained cross-organ latent exchange, native B3 utility, persistent B1/B2/C3 master learning, Android AudioRecord, speech decoder/vocoder, or Redmi acceptance is established.

## Next step

Read exact-head A4 CI and the new staged/integrated results. If focused tests pass, ask Core to rebase #2547 onto the new #2548 head and refresh only its owned pins; QA retains migration assertions. Then evaluate source/session-disjoint A4 omission false positives and continue the A5 UI-event-to-PerceptPacket path.
