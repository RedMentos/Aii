# Research & Perception — Run 55 (2026-11-27 02:40 CET)

## Branch / PR

- Repo: `RedMentos/Aii`
- Branch: `research-perception/v14-raw-ear-currentparent-20261126-run52`
- Existing PR: [#2540](https://github.com/RedMentos/Aii/pull/2540), DRAFT / NOT_RELEASED.
- Experiment code commit before documentation updates: `2a6d4d8ede170d669e21e5093970dc143711a4c2`.
- Readback blobs: experiment `a7f1e9401b24561ce11d0704b48b815d46b931b7`; tests `ed79cb765fa8b2a178709aa2572de7c75add04df`; workflow `a98d5ededdd31549977540f7e22f7d05962dbbb0`.

## Implementation

Added a deterministic synthetic A4 temporal source-isolation ablation. It calls the existing `AudioTemporalPredictionRegistry`; no production Runtime code was changed. It measures:
- three independent synthetic speech/non-speech streams;
- parity between isolated execution and interleaved multi-stream execution;
- learned next-cue-delta MAE against the predictor's persistence baseline;
- nonzero numeric parameter deltas and bounded A4 attention novelty;
- no-context reset, provisional-window censoring and consent-rotation reset controls.

Files:
- `v14/experiments/a4_temporal_ablation_20261127.py`
- `v14/experiments/test_a4_temporal_ablation_20261127.py`
- `.github/workflows/v14-a4-temporal-ablation.yml`

## Test evidence

- LOCAL_LINUX full Aii checkout/pytest: **BLOCKED / NOT RUN**. No repository checkout is mounted; `git ls-remote` fails DNS.
- CI: Python 3.13/3.14 workflow was pushed, but no exact run result was visible at the checkpoint. **PENDING / UNVERIFIED**, not PASS.
- Synthetic design: generated cue dictionaries only; no PCM, transcript, speaker identity, user audio or training examples.
- Redmi/Termux/Android: **REDMI_UNVERIFIED**. No microphone, model inference, device command, updater request or deployment.
- The broader #2540 staged Runtime and integrated regression remain FAIL at Core-owned source pins and QA-owned migration assertions. This experiment does not conceal or repair those shared failures.

## Research intake

- R-177: LATER, arXiv:2611.25671v1 (2026-11-19). Abstract and extended rendering checked; original PDF not retrieved. Simulation-only action-conditioned temporal memory idea; no official OSS/license located. No code reuse.
- R-178: When Sounds Turn Heads, arXiv:2611.25960v1 (2026-11-19). Abstract only. Attention-head timing prior may be useful only if a permitted audio model exposes native attention maps; current RAW EAR does not. No code/license located; no reuse.

## Shared ownership / next

- Core owns PR #2544's Recovery→Stage→RuntimeDeploy pin chain; QA owns migration PARTIAL-vs-UPDATED assertions. Perception did not edit those files.
- Next: verify exact A4 workflow result; fix measured failures; after Core/QA rebase, add error-gated versus every-FINAL update and retention/restart ablations.
- No user action required. Keep microphone capture, model swaps and persistent production weight changes OFF.


## Final verification addendum — 2026-11-27

- Latest code/test head: `e270369a04eb20470aa717dc0464b2b03a4320a5`. Documentation-only commits followed; branch head before this handoff addendum was `0a8560067117a28569861cc7c548d662367678c7`.
- A4 workflow run 45924853167: compile PASS + 7/7 tests PASS on Python 3.13.18 and 3.14.10; PR merge candidate short SHA `3d56c9c`.
- A4/A5 feature-set run 45924853182 PASS on both Python versions; RAW EAR fastpath run 45924853240 155/155 PASS on both; RuntimeDeploy offline run 45924853218 PASS on Python 3.11 and 3.14.
- Staged run 45924853105 FAIL: 20 failed / 233 passed / 10 skipped / 2 errors / 41 subtests. The recovery builder pins composer `831080bceec90711bd42e0fa4eba47c669975c98`, but the current Perception composer is `3b71ea51272a3bc1bc82cb12ebae3bd5e96f51e1`; stale arithmetic/observer pins and migration PARTIAL-vs-UPDATED assertions also fail. Integrated regression in the same run FAIL: one setup test at the same composer pin.
- Synthetic metrics: interleaved/isolated parity exact; speech-periodic model MAE 0.21739024 vs persistence 0.33642678; non-speech 0.22605715 vs 0.19615384; mixed 0.28642224 vs 0.26395818. Learning-rate sweep 0.02–0.20 does not remove non-speech/mixed regressions. No default change.
- LOCAL_LINUX full suite NOT RUN; no local checkout/network. No Android/Termux/microphone/native model/Redmi proof. REDMI_UNVERIFIED; NOT_RELEASED.
- The exact A4 workflow is green, but the PR is not integration-ready while staged/integrated fail. Core and QA retain ownership of their source pins/assertions.
