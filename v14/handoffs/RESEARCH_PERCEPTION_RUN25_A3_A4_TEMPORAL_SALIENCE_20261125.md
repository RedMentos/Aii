# Research & Perception Handoff — Run 25 (2026-11-25)

## Scope and execution record

- Role: Research & Perception.
- Started: 2026-11-25 03:06:51 Europe/Berlin (automation-provided start).
- Last verified checkpoint: 2026-11-25 03:25:17 Europe/Berlin. PR head before this final handoff timestamp update: `0c279e7ab220dce4b8a475158a823870a9c2e46e`.
- Completion time: UNKNOWN; this handoff records the verified checkpoint, not a claim that the platform limit was reached.
- Product branch: `research-perception/v14-a3-counterfactual-probe-20261124-run13`.
- Parent PR: [#2470](https://github.com/RedMentos/Aii/pull/2470), stacked on the current temporal UI-session branch and ultimately the verified `gpt6/v13-private-remote-bridge-20261111` development line at `8d93236`.
- Whole-system trace: [#1984](https://github.com/RedMentos/Aii/issues/1984).

## Functional gap and change

Before this checkpoint, A3 projected tile change was preserved in the A5 temporal evidence packet and visible in the A4 readout, but it was not one of the values used to calculate `attention_novelty`. The existing UI frame consumer already passes `attention_novelty` to the A4 `Attention.modulate` path.

This patch connects that existing consumer:

1. Adds `A3_TEMPORAL_ATTENTION_GAIN = 0.15` as an explicitly BOOT/heuristic gain.
2. Only when the source-bound A3 projected change is `MEASURED`, computes `a3_attention_novelty = min(0.15, 0.15 * change_score)`.
3. Includes that bounded value in the existing `attention_novelty = max(...)` calculation.
4. Exposes `a3_attention_novelty` in the A4 temporal readout.
5. Keeps A3 projected vectors source-bound and diagnostic-only. This path changes A4 attention modulation only; it does **not** grant truth, learning, or action authority, and it performs no weight update.

Code commits:
- `1fe511a4a5790623b5060c97ea4fe62b55ee0d77` — A3 temporal signal contributes to A4 novelty.
- `ad6e3eb81ce99d71058ce0c8a0ebc018d60afbba` — expose the A3 contribution in A4 readout.
- `2b96fb9ce919fd5de1ee0ead6c5c5f1e2fbc4a55` — consumer and negative-control tests.

## Verification

### LOCAL_LINUX

- Environment: Python 3.13.5.
- PASS: isolated A3→A4 gain/negative-control harness, 6/6 assertions.
- BLOCKED: full repository checkout and pytest were not available locally. `git clone` failed because the environment could not resolve/reach GitHub; no local Aii checkout was mounted. The isolated harness is not represented as a full repository test.

### GitHub CI

- PASS, exact code/test SHA `2b96fb9...`: [MediaProjection RAW EYE frame ingress run 45531930259](https://github.com/RedMentos/Aii/actions/runs/45531930259), Python 3.13 and 3.14. Both ran `py_compile` on the exact adapter/test files and `pytest -q -s tests/test_vision_ui_frame_ingress.py tests/test_vision_ui_frame_provider_entrypoint.py`: **54 passed** each.
- PASS, latest docs head `f534b4a...`: [MediaProjection frame ingress run 45532096806](https://github.com/RedMentos/Aii/actions/runs/45532096806), Python 3.13 and 3.14; same focused suite, **54 passed** each.
- PASS: [Perception public privacy scan run 45532097200](https://github.com/RedMentos/Aii/actions/runs/45532097200).
- PASS: [private-bridge security workflow run 45532096814](https://github.com/RedMentos/Aii/actions/runs/45532096814).
- FAIL, latest docs head `f534b4a...`: [A5 UI lease regression run 45532096819](https://github.com/RedMentos/Aii/actions/runs/45532096819), both Python 3.13 and 3.14. Each run reports 17 passed, 5 subtests passed, 1 failed: `ValueError: unsupported lifecycle source: vision.py` from `source_lifecycle_lock_integration_candidate.py`. This is the existing Core/Integrator source-pin/composer mismatch, not the A3→A4 files. Do not bypass the source hash or edit Core-owned composer code from this lane.
- Full staged/integrated system acceptance remains **BLOCKED/NOT VERIFIED** by the source-lifecycle dependency closure.

## Research update

R-150 was appended to `v14/V14_RESEARCH_LEDGER.md`: Sun et al., *Learning Video Foresight Reasoning from Unlabeled Videos via On-Policy Self-Distillation*, arXiv:2611.26954v1 (2026-11-20), full 11-page main PDF and official OSS README reviewed. The method contrasts the same student response under a paired true future and an unrelated reference future, then mixes that contrast with teacher–student distillation. The paper reports up to +14.2 TwiFF and +15.9 SEED-Bench-R1 points on Qwen3-VL/Qwen3.5 under its stated datasets and 8×B200 setup. The official code and one published checkpoint are listed as Apache-2.0; dataset terms remain separate. This is not a Redmi candidate and no code, model, or data were downloaded or imported. The paper's cited Appendix A.3 proof was not present in the 11-page PDF inspected, so that derivation was not independently checked.

V14 follow-up hypothesis: later test a source-bound true-outcome vs shuffled/unrelated-outcome contrast with a distillation/KL anchor, small adapter only, source-disjoint holdouts, omission controls, and gradient/parameter/retention/restart evidence. This is research direction, not implemented learning.

## Device, release and next action

- Release status: **NOT_RELEASED**. PR #2470 is still open; GitHub push is not deployment.
- Redmi: **REDMI_UNVERIFIED**. No fresh authenticated phone receipt was obtained in this run. Issue #1904 remains OPEN; the latest available consented V13OBS snapshot is 2026-11-24 09:28 UTC and reports STOPPED_BY_USER, model process STOPPED, zero valid B1/B2 offers, and native residency unavailable; the 2026-11-24 17:50 UTC issue update reports no fresh receipt. No UPDATE_REQUEST, model download/swap, permission change, or device command was issued.
- User action: **none required** for this code-only checkpoint.
- Next owner/action: Core/Integrator must rebind the exact current `vision.py` hash and full lifecycle dependency closure, then rerun A5 UI lease, staged runtime, integrated regression, both consumers and migration. After that, Perception should add noise/shuffled-frame and source-disjoint negative controls to calibrate the A3→A4 gain before any stronger salience use. No Android capture or learned-weight claim until separately verified.
