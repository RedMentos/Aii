# JEPA replay research handoff — 2026-11-22

**Research relationship: implementation follow-up to existing ledger entry R-041 (Replay on Demand), not a new R-053 entry.** The shared ledger already records R-041. This lane handoff supplies the implementation-specific evidence and next experiment for the Boss to fold into the shared ledger after integration review. It deliberately does not edit the Boss-owned master, work board or user-next-action file.

## 1. ER-JEPA: episodic replay for JEPA-style continued training

- **Primary source:** [ER-JEPA preprint, arXiv:2609.36952](https://arxiv.org/abs/2609.36952), submitted 2026-09-29. The full paper was inspected. It adds an episodic replay path to LLM-JEPA: retain paired source/target views, retrieve content/uniform/hard examples, re-encode both views with the current model, and train the token and JEPA objectives with replay. It also discusses updating memory significance from replay error.
- **Evidence boundary:** results are on Llama 3.2 1B and text/code tasks, not Android, multimodal T8 outcomes or the Redmi. It is a preprint. No official implementation repository, released weights or software license was located in the paper/full-text search. Do not import code or weights based on the paper alone.
- **V14 fit:** the episodic-memory idea is relevant, but our T8 ActionOutcome records are structured state/action/outcome/provenance rows, not paired token streams. Adapt the memory-selection principle, not the token-level loss or a claim of direct implementation.

## 2. Replay on Demand (RoD): adaptive replay share

- **Primary source:** [Replay on Demand, arXiv:2609.40089](https://arxiv.org/abs/2609.40089), submitted 2026-09-30.
- **Official implementation:** [bethgelab/replay-on-demand](https://github.com/bethgelab/replay-on-demand), read back at commit `9ecc05173a4a5a8b872e18608c319df0eab5db81`. Root LICENSE and `pyproject.toml` declare **Apache-2.0**. The README describes a joint top-k selection in which adaptation examples are scored by remaining learning potential and replay examples by observed forgetting:
  - adaptation: current loss minus an adaptation-specialist reference loss;
  - replay: current loss minus the original/pre-adaptation reference loss;
  - both compete for one fixed training budget, so replay share emerges from the model's state instead of a fixed quota.
- **Dependency/resource boundary:** the implementation is a thin patch over NVIDIA NeMo-RL v0.6.0. The project expects PyTorch/Megatron/Ray, Apptainer/SLURM and GPU nodes; the reported 12B runs use 8×80-GB GPUs (or 8 B200s). Its Python metadata requires >=3.10 and lists pyarrow/wandb, while the heavy stack is supplied by the container. This is not a viable dependency or runtime to import into the Android V14 app.
- **V14 fit:** reuse the scoring/selection idea only. The exact repo revision and Apache license are verified; no dependency, model, dataset or weight was imported. The existing shared ledger R-041 already records the research; this file is a code-level follow-up, not a duplicate research entry.

## 3. Concrete V14 hypothesis and current boundary

The current `world_jepa_consumer.py` still uses `replay_mode="on_demand_loss"` with a disposable no-replay probe and a fixed replay cap. The present implementation does **not** implement RoD's adaptation-specialist reference or joint top-k budget. Do not describe it as an RoD port.

The next RoD-specific experiment is deferred until the missing eligibility/modulator connection is integrated:

1. Extend the disposable probe to measure old-session forgetting on the prior guard fold and reducible current-task loss on a source-disjoint current guard. Never use the final current holdout for scoring, selection or line-search.
2. Use the two scores to set a replay budget bounded by the existing per-update cap. Retain all unselected new T8 outcomes in the persistent pending queue; do not silently discard them.
3. Compare no replay, uniform fixed-budget replay, current loss-selected fixed-budget replay, and a RoD-like adaptive replay share under equal optimizer-step and maximum-row budgets. Add shuffled/zero-score controls.
4. Measure new holdout utility, each old-session holdout, per-role B1/B2 receiver retention, predictor/encoder/EMA parameter diffs, optimizer-state persistence, checkpoint readback, restart, rollback, and CPU/RSS. Keep the experiment SHADOW and all production learning gates OFF.

This remains a testable research hypothesis, not an implemented RoD port or a claim of full JEPA/GGUF learning.

## 4. Current JEPA code checkpoint

Current branch head: `7eb790fabe2e502a8f4323a5746ccf98a599b31c`. Open draft PR: [#2247](https://github.com/RedMentos/Aii/pull/2247), based on release ancestor `bdcad466ffea75a2b41f7d23be168f53c7197d20`; **NOT_MERGED / NOT_RELEASED**.

The PR's current code changes include:

- The A→B→A test helper now propagates the production consumer's actual before/after checkpoint SHA and optimizer/trust-region evidence; assertions were not weakened.
- The Store-backed WorldJEPA consumer now uses a combined source/content-disjoint training guard. Prior-session guard cohorts protect retention; current-task guard cohorts protect adaptation. Neither guard enters predictor gradients or replay.
- Current-task guard rows are excluded from the committed checkpoint's processed IDs/fingerprints/experience rows and remain in the durable pending queue. They can be reconsidered when new T8 evidence arrives; they are not silently marked trained.
- Backtracking requires both prior-session and current-task guards. The independent final holdout remains promotion-only.
- Update scale carries forward the previous accepted scale: `min(0.25, 4 × previous_selected_scale)`, with a floor of 0.015625. This is an explicit bounded trust-region prior, not a holdout-selected scale.
- B1_DETAIL/B2_GIST/SELF_MODEL numeric shadow receiver heads train only on fit rows, not either guard partition.
- The path remains a local numeric WorldJEPA predictor/EMA plus persistent Store/checkpoint/optimizer/replay/rollback and shadow receiver readouts. It does not modify native GGUF B1/B2/C3 body weights and does not provide trained cross-organ latent coupling.

## 5. Exact verification at `7eb790f`

### PASS — GitHub Actions / synthetic Linux

- **V14 JEPA Store A-B-A and Runtime Python 3.13 and 3.14** — run `44963436162`: both Python versions PASS, 13 tests each. The tests cover persisted optimizer resume, Store A→B→A, per-session retention, B1/B2/SELF receiver loop, checkpoint/rollback readback, selective predictor plasticity and idle post-commit Runtime/EMA/replay.
- **V13 combined online JEPA integration** — run `44963436146`: PASS.
- **V13 incremental World JEPA** — run `44963436159`: PASS.
- **V13 runtime deployment integrity** — run `44963436155`: staged-runtime PASS.
- **V13 staged context and integrated regression** — run `44963436160`: integrated PyTorch 2.5.1 CPU / Transformers 4.44.2 / PEFT 0.13.2 regression and staged-runtime PASS.
- **V13 private owner-read Termux bootstrap** — run `44963436170`: CI workflow PASS only; not a live device receipt.
- **V13 Lab Age control state and WebView truth** — run `44963436219`: CI workflow PASS only.
- **V13 Laboratory Age two-checkout updater migration** — run `44963436145`: CI workflow PASS only.

The A-B-A run produced nonzero predictor parameter and EMA deltas, persistent optimizer state, exact rollback readback and source-disjoint holdouts. In the aggregate A2 arm, seeds 13/19/43 were accepted at selected scales 0.0625/0.25/0.125; current guard and prior holdout retention passed. The A-B-A return ablation beat shuffled and zero-update controls, but did **not** restore the original A1 loss in every seed. This is evidence of a working synthetic numeric update/retention path, not complete continual-learning performance.

### NOT_APPLICABLE / POLICY-SCOPE FAIL

- **V13 safe additive candidate tests** — run `44963436171`: FAIL with `not a strictly additive PR`. The validator explicitly requires every changed path to be newly added and rejects modified existing files. This PR is an existing-code integration/bug-fix PR, so that particular candidate-only validator is not an applicable product acceptance test. Do not claim it passed.

### CANCELLED / NOT_A_RELEASE_EVENT

- **V13 integrate reviewed agent PRs on release events** — run `44963436237`: cancelled; no release event was being processed. This is not a code-test failure or a release.

### Environment and device boundary

- **LOCAL_LINUX:** no Aii checkout was mounted in the runner and GitHub DNS lookup returned no address. Python 3.13.5 and Git were present, but project-local execution was BLOCKED because the exact repository source could not be fetched. GitHub Actions results above are CI evidence, not a local run.
- **TERMUX/REDMI:** `NO_LIVE_RECEIPT` / `REDMI_UNVERIFIED`. Private relay issue #447 `PIPELINE_STATUS` remained open with no `device_status` comment at readback; older issue #115 is stale. No current installed SHA, updater status or phone-native behavior was verified.
- **Deployment:** `NOT_RELEASED`. No UPDATE_REQUEST, install, model download/swap, weight change, permission change or device action was performed. Current updater status is unknown/not rechecked. A GitHub push is not deployment.
- **Scope boundary:** no native GGUF body-weight update, no trained cross-organ latent transfer, no actual Redmi benchmark, and no whole-system V14 completion claim.

## 6. Next executable JEPA/Memory step

The existing `SleepCycle` already owns a `Neuromod` instance, and `neuromod.py` exposes the `world_predictor` path. The current `SleepRuntime → WorldJEPAStoreConsumer` path does not yet consume that eligibility/modulator signal.

Next code task, after Boss review/rebase of #2247:

1. Pass the existing `SleepCycle.neuromod` explicitly through `SleepRuntime → world_jepa_runtime.consume_after_commit → WorldJEPAStoreConsumer`.
2. Emit idempotent, source-bound `LearningTrace` and `ModulatorPacket` records from trusted T8 ActionOutcome transitions, keyed by event/action provenance; do not duplicate them on restart/retry.
3. Call `Neuromod.gate("world_predictor")` before the persisted optimizer step. Apply the per-path gate to the actual numeric update scale while preserving the existing current/prior guard and final-holdout promotion rules. A hard veto must leave checkpoint and optimizer state unchanged; no global Age-0 freeze.
4. Persist a `PlasticityState` retention outcome after promotion/rejection so repeated retention failures reduce future local plasticity and successful retention can consolidate.
5. Test source provenance, duplicate suppression, veto/no-eligibility negative controls, parameter/optimizer/EMA diffs, restart/readback, rollback and B1/B2/SELF receiver behavior. Keep production gates unchanged until evidence and independent review.

**User action:** none required now. No model swap/download, Termux command, permission grant or device approval is requested.
