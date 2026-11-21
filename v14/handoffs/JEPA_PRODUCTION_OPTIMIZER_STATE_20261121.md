# JEPA / Memory handoff — production optimizer-state persistence

Date: 2026-11-21  
Lane: JEPA & Memory  
Base: `gpt6/v13-private-remote-bridge-20261111` at `4a471ae40dd9b768c8130fafdba51900b5417800`  
Work branch: `jepa-memory/v14-production-optimizer-state-20261121`

## Product gap addressed

The Store-backed WorldJEPA consumer already had a real T8/ActionOutcome → WorldJEPA/EMA → replay/sleep → B1/B2 numeric receiver path, but its checkpoint only persisted inference parameters. Every continued fit reconstructed Adam moments, inverse-dynamics parameters and RNG state. The runtime therefore did not actually continue the same optimizer trajectory after a checkpoint/restart.

## Production changes

- `v13/code/v13/world_jepa.py`: persist/restore main Adam moments, inverse-dynamics parameters, bootstrap-predictor Adam moments and RNG states across `fit`/`partial_fit`; publish the resume state atomically with the new model/EMA state. Legacy inference-only checkpoints fail closed unless the caller explicitly authorizes optimizer bootstrap.
- `v13/code/v13/world_jepa_training_state.py`: new bounded numeric codec. It validates model revision/objective, parameter shapes, Adam moments/step counts, inverse-head arrays, PCG64 RNG state and ensemble bootstrap state. A legacy bootstrap retains existing model/EMA parameters and initializes only missing optimizer/inverse state; the checkpoint records `BOOTSTRAPPED_FROM_INFERENCE_ONLY`.
- `v13/code/v13/world_jepa_shadow_checkpoint.py`: store resume metadata/arrays in the same atomic private archive; preflight NPY headers and bounded archive size before NumPy allocation; no pickle or public weights.
- `v13/code/v13/world_jepa_consumer.py`: only the already-gated Store update path passes the explicit bootstrap permission after `learning_enabled` and `optimizer_permission` are both true; it reports persisted/bootstrap status.
- The Store consumer returns `optimizer_state_persisted` and `optimizer_state_bootstrapped` in its learning metrics; SleepRuntime forwards those metrics in its structured learning result. SQLite telemetry remains on the existing bounded schema (optimizer step count and target-change evidence), avoiding an unrelated schema/hash-chain change.
- Staged guard/lineage builders are rebound to the production source hashes; their generated test copies no longer overlay a separate training implementation.

No model was downloaded or swapped. No GGUF/B1/B2 base weights were changed. The B1/B2 receivers remain numeric SHADOW readouts, not native body-weight learning.

## Tests added/updated

- `v13/code/tests/world_jepa_training_resume_disposable_cases_20261111.py`: fresh continuation, optimizer/inverse/RNG retention, checkpoint roundtrip, corrupt-state rejection before parameter mutation, failed-gradient non-publication, explicit v2 inference-only bootstrap, and explicit v1 legacy bootstrap with unknown prior step count.
- `v13/code/tests/test_v14_world_jepa_postcommit_runtime.py`: production Store consumer must persist optimizer state; existing restart/rollback/replay, disjoint holdout, negative-control and receiver checks remain.
- `v13/code/tests/test_world_jepa_training_resume_stage_20261111.py`: run the production tests without an environment override that pretends optimizer state is persisted.
- The stage builder pins were refreshed to the exact currently committed dependency bytes. No dependency implementation was overwritten.

## Evidence status

- Local Python/NumPy/pytest are present, but this execution environment has no usable checkout: the attempted GitHub clone failed with `Could not resolve host: github.com`. Therefore exact local compile/tests are **BLOCKED**, not PASS.
- GitHub Actions/CI: **PENDING** until the PR is opened.
- Redmi/Termux and native Android: **REDMI_UNVERIFIED**. No connected-device receipt or authorized hardware test was performed.
- Deployment: **NOT_RELEASED**. A GitHub push/PR is not an Android deployment.
- No user action is required for this code review. No installed app/model/data was changed.

## Coordination

PR #2186 remains a separate draft experiment (source-reference retention, mean-delta/replay-selection work). This handoff ports only the production optimizer-state path; it does not silently absorb or discard those experiments. Do not merge #2186 as-is over the same consumer/test files. Rebase and review its remaining changes after this production path is reviewed.

Boss/integrator: please sync the verified result into `V14_LIVE_WORKPLAN.md`, `V14_WORK_BOARD.json`, `V14_USER_NEXT_ACTION.md`, and the shared research ledger after CI review. Shared master/board files were not edited by this lane.

## Research note proposed for R-025

- **JEPA-TTT**, arXiv:2610.00722: persistent test-time predictor updates retain predictor parameters, optimizer state and a dense replay buffer across episodes; its reported setting keeps the visual encoder/reward head fixed and adapts only the latent dynamics predictor. That supports testing persistence, but does not justify freezing V14 encoders or treating its results as evidence for our broader encoder+EMA+inverse-head path. The project page exposes paper/results but no implementation or license link; no code was reused.
  - https://arxiv.org/abs/2610.00722
  - https://jepa-ttt.github.io/
- **STABLE**, arXiv:2611.10655: its primal-dual optimizer enforces a task-anchor drift budget and may justify a future bounded-drift ablation after multi-seed baselines. The paper's guarantee is for distance-based classifiers under a local score-stability condition, not this WorldJEPA MLP. The official repo is MIT, but its reference setup is Python 3.12 + PyTorch 2.8/CUDA 12.8 on an A100 64 GB; no code was reused for Android.
  - https://arxiv.org/abs/2611.10655
  - https://github.com/atlas-luiss/STABLE
- **Replay on Demand (RoD)**, arXiv:2609.40089: jointly ranks adaptation examples by remaining learning potential and replay examples by observed source-level forgetting against reference-model losses, rather than fixing a replay ratio. Its official implementation is Apache-2.0, but is a thin layer over NeMo-RL v0.6.0/Megatron/Ray and targets an 8-GPU 80 GB cluster (the paper also reports 4×H100 with optimizer offload); it is not a practical Android dependency. Future V14 experiment only: estimate per-source old-holdout degradation and let it compete with new-learning utility under the same bounded update budget. Do not port its training stack or replace the current uniform/no-replay controls; the hard-replay arm already failed retention in the staged cohort.
  - https://arxiv.org/abs/2609.40089
  - https://github.com/bethgelab/replay-on-demand

## Next executable step

Run the exact PR CI/staged test chain. If green, have the Boss review and integrate this branch into the current V14 release ancestor. Then run multi-seed persist-vs-reset/replay ablations and measure CPU/RSS/TTFT on Linux; only after an authorized real Redmi receipt can Android performance or deployment be claimed. Next architectural gap remains actual learned latent B1/B2 coupling and later safe cross-organ weight updates, not native GGUF plasticity.


## Exact-head CI and product checkpoint — 2026-11-21

- PR #2198 exact head: `a6dd9836404e4de8393e76fa31152a00d3a3824b`, based on the verified development branch head `4a471ae40dd9b768c8130fafdba51900b5417800`. GitHub readback confirms the commit and PR head. This is a candidate branch, **NOT_RELEASED**.
- Exact-head GitHub Actions:
  - staged-runtime: **249 passed / 10 skipped / 47 subtests** (Linux, Python 3.11)
  - integrated-regression: **417 passed / 3 skipped / 58 subtests** (Linux, Python 3.11)
  - combined online JEPA: **49 passed** (Python 3.11)
  - JEPA checkpoint retention: **21 passed** (Python 3.11)
  - incremental WorldJEPA: **27 passed** (Python 3.11)
  - two-checkout old-phone/current-phone migration: **2 passed**
  - Lab Age control: **8 + 4 + 7 + 4 tests passed**
  - runtime deployment integrity: **3 + 31 tests passed**
  - private owner-read bootstrap: **Python 3.11 suites passed; Python 3.14 staged runtime startup/SQLite source-reference checks passed (11 tests in the 3.14 job)**
  - generic safe-additive check: **FAIL by policy**, because this PR intentionally changes existing production files; no bypass or waiver was applied. This remains a non-green check and the PR stays draft pending Boss/QA review.
- Two real integration failures were found and corrected before the final head:
  1. The staged resume builder encoded newline anchors as literal backslash-n, so it could not bind the real guard source. The builder now uses actual newline anchors and its downstream exact SHA pins are updated.
  2. The new stage-builder hash was not yet reflected in `runtime_deploy.STAGER_SHA256`; the exact current stage hash is now pinned. The two-checkout migration and runtime-deployment integrity workflows pass after this correction.
- Local exact repository test: **BLOCKED**. This runner has Python 3.13.5, NumPy 2.3.5 and pytest 9.0.2, but no Aii checkout; `git ls-remote https://github.com/RedMentos/Aii.git` fails with DNS resolution for github.com. No LOCAL_LINUX repository-test PASS is claimed.
- Python 3.14 CI only proves staged startup and SQLite source-reference roundtrip; the new optimizer-resume training tests themselves ran on Python 3.11. A dedicated Python 3.14 optimizer-resume run remains a useful QA follow-up, not an Android proof.
- The exact path now exercised in staged CI is: committed/source-verified T8 rows -> persistent WorldJEPA encoder/predictor/inverse head + EMA and Adam/RNG state -> private atomic checkpoint and Store cursor -> restart/rollback/replay -> source-disjoint B1_DETAIL/B2_GIST/SELF numeric ridge readouts -> World/Planner SHADOW consumer. The readout heads are numeric SHADOW models, not the two native sparse-MoE bodies; no trained cross-organ latent injection, native GGUF weight edit or foreground C3 answer change is claimed.
- User effect: the local postcommit learning candidate can continue the same numeric WorldJEPA optimizer after checkpoint/restart rather than silently restarting Adam each page. Learning/optimizer gates remain OFF by default; all decision authority remains NONE.
- Device/deployment: **REDMI_UNVERIFIED**; no authenticated phone receipt, installed SHA, native Termux training, Android RSS/latency or updater installation was observed. GitHub push/CI is not deployment. No UPDATE_REQUEST, shell action, model download/swap, permission change or user-data mutation occurred.
- Research follow-up: the RoD note above should be mirrored by Research & Perception into the shared V14 research ledger as a dated entry; this handoff does not edit their shared ledger. No third-party code or weights were reused.
- Next executable JEPA step after independent review/merge: matched multi-seed persistent-vs-reset optimizer runs with identical source-disjoint cohorts/update counts/replay bytes, reporting new and old holdout, parameter/EMA diffs and restart equivalence. Keep uniform/no-replay controls; hard replay stays OFF because its staged retention result regressed.
- **User action: none required.** Do not run a Termux command or change model/permissions from this candidate.


## Receiver utility admission — 2026-11-21

The production Store consumer now exposes B1_DETAIL, B2_GIST and SELF_MODEL numeric readouts only when that role's own held-out MSE beats all three controls: the training-fold mean predictor, zero-latent/bias-only prediction and shuffled-latent prediction by a finite numerical margin. Missing, malformed or nonfinite receiver metrics fail closed as `RECEIVER_UTILITY_REJECTED`; the planner therefore cannot treat an unqualified numeric head as a usable receiver. The learner/checkpoint can still advance independently when the WorldJEPA utility/retention gate passes.

This is a role-readout admission gate, not native B1/B2 activation consumption, not a trained B3 latent path and not GGUF body-weight learning. The existing receiver values remain SHADOW with decision authority NONE. A dedicated negative-control regression mutates one persisted role metric and verifies that its prediction is withheld without granting authority.

Exact-head CI is required after this commit. Full local Aii tests remain BLOCKED by GitHub DNS in this runner; Redmi remains REDMI_UNVERIFIED.

## Exact-head follow-up — 2026-11-21 13:25 CET

- **Current PR branch head:** `c071663e748e41bcda5d59cdb6373008def99af3`; the last two commits after code/test head `cd0b54053f51d5227f7860a80f5f6adbd3973598` update only this handoff and `V14_USER_NEXT_ACTION.md`. PR #2198 remains draft/open on base `4a471ae40dd9b768c8130fafdba51900b5417800`. This is a candidate branch, **NOT_RELEASED**.
- **Planner bypass fixed:** `world_jepa_receiver_matrix.receiver_matrix()` now applies the same per-role `receiver_utility_gate` as the single-readout API. A B1_DETAIL, B2_GIST or SELF_MODEL head that fails held-out vs mean/zero/shuffled controls returns `RECEIVER_UTILITY_REJECTED` without a prediction; `_candidate_score` therefore cannot rank an action using that role.
- **Stale idempotency fixed:** planner-shadow schema is now /2. Its fingerprint binds status, full candidate readouts, ranked actions and memory recall as well as source/checkpoint identity. A changed receiver-admission result can no longer be hidden by a previous record with the same model-checkpoint SHA.
- **Regression coverage:** the staged end-to-end test establishes passing synthetic role metrics, then independently makes each role's shuffled control equal its holdout and verifies no candidate is ranked, no prediction leaks through, authority remains NONE, and readback changes back to READY after restoring the metrics. Existing postcommit tests now derive Planner readiness from actual role gates rather than assuming every random cohort qualifies every receiver.
- **Python 3.14 blocker closed for this candidate:** new read-only workflow `.github/workflows/v14-jepa-training-resume-py314.yml`, run **44903330976**, Python 3.14.10: outer staged test 1 passed; disposable optimizer-resume cases 14 passed; postcommit Runtime cases 13 passed.
- **Exact current-head CI:** run **44903330765** staged-runtime 249 passed / 10 skipped / 47 subtests; integrated-regression 418 passed / 3 skipped / 58 subtests. Also: combined online JEPA 49 passed (44903330723); checkpoint retention 21 passed (44903330810); incremental JEPA 27 passed (44903330756); runtime deployment integrity 3 + 31 passed (44903330795); two-checkout migration 2 passed (44903330760); owner-read/bootstrap suite passed, including the prior Python 3.14 staged-startup checks (44903330791).
- **Non-green by policy:** safe-additive run **44903330714** fails because the PR changes existing production modules and adds a workflow outside the inert-module/test/handoff allowlist. No waiver or bypass was used; Boss/QA review is required before integration.
- **Local environment:** exact full Aii checkout remains unavailable because GitHub DNS resolution fails. Local isolated source compile/receiver-matrix harness passed for the positive path and three role-specific negative controls; test-function AST and workflow YAML parse passed. These are isolated local checks, not a full local Runtime suite.
- **Actual scope/effect:** production candidate now has source-bound T8 -> numeric WorldJEPA/EMA + Adam/inverse/RNG checkpoint -> restart/rollback -> gated numeric B1/B2/SELF Planner SHADOW readouts. This is not native B1/B2 sparse-MoE weight learning, not trained B3 latent coupling, not GGUF editing, and not a fix for foreground C3 answer delivery or #1904. Some role heads may correctly be withheld if their own synthetic held-out utility gate fails.
- **Device/release:** **NOT_RELEASED / REDMI_UNVERIFIED**. No owner-authenticated phone receipt, installed SHA, Termux training, Redmi RSS/latency or updater installation was observed. No phone action, model swap, permission change or user-data mutation. **User action: none required.**

### Research and next experiment

- **JEPA-TTT** (arXiv:2610.00722; https://arxiv.org/abs/2610.00722 ; https://jepa-ttt.github.io/) supports persistent predictor/optimizer state and dense replay, but its project page explicitly leaves return-to-old dynamics and sequential shift retention outside the evaluated scope. V14's next matched experiment should therefore be **A -> B -> A**, not another one-way A -> B test: old-A and new-B source-disjoint holdouts, equal optimizer steps/replay bytes, persistent-vs-reset moments, uniform-vs-no-replay, multiple seeds, gradient/parameter/EMA diffs and rollback equivalence.
- **STABLE** (arXiv:2611.10655; https://arxiv.org/abs/2611.10655 ; https://github.com/atlas-luiss/STABLE) proposes a primal-dual parameter-drift budget. Its stated guarantee is for distance-based classifiers under a local score-stability condition, so this is a bounded-drift ablation hypothesis for our numeric heads, not a drop-in proof or Android dependency. Repo license is MIT; no code imported.
- **Replay on Demand** (arXiv:2609.40089; https://arxiv.org/abs/2609.40089 ; https://github.com/bethgelab/replay-on-demand) allocates a shared budget between new examples with remaining learning potential and old examples with observed forgetting. Its repo is Apache-2.0 but built around NeMo-RL/Megatron/Ray and large-GPU training; do not port that stack to Android. The useful V14 hypothesis is a small source-level forgetting-vs-new-utility selector, evaluated against uniform/no-replay. Hard replay remains OFF because the earlier staged cohort regressed retention.
- **Next owner action:** Boss/Integrator reviews #2198, decides the safe-additive policy path without waiver, and synchronizes the verified state into the shared board/workplan. JEPA's next code experiment is A->B->A after review; P0 chat/offer delivery remains a separate whole-system blocker.
