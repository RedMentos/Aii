# JEPA replay research handoff — 2026-11-21

**Candidate ledger entry: R-053.** This file is a lane handoff so the Boss can append the reviewed entry to the shared research ledger after the current integration branch is finalized. It deliberately does not edit the Boss-owned master, work board or user-next-action file.

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
- **V14 fit:** reuse the scoring/selection idea only. The exact repo revision and Apache license are verified; no dependency, model, dataset or weight was imported.

## 3. Concrete V14 hypothesis

Current `world_jepa_consumer.py` already has a disposable no-replay probe in `_session_loss_demand_scores` and `replay_mode="on_demand_loss"`. It scores old source-disjoint guard cohorts by forgetting, then calls `select_replay_rows` with a **fixed** budget of `len(new_fit_rows)`. It does not yet jointly rank adaptation and replay examples as RoD does, and it has no separate adaptation-specialist reference.

Next bounded experiment, after current-head CI and integration rebase:

1. Extend the disposable probe to measure (a) old-session forgetting on the prior guard fold and (b) reducible loss on the new fit fold. Never use the final holdout for scoring, selection or line-search.
2. Use the two scores to set a replay budget bounded by the existing per-update cap; retain all new T8 rows in the current implementation so no outcome is silently discarded. A later full joint top-k experiment must first add a persistent pending queue for unselected new rows.
3. Compare no replay, uniform fixed-budget replay, current loss-selected fixed-budget replay, and a RoD-like adaptive replay share under equal optimizer-step and maximum-row budgets. Add shuffled/zero-score controls.
4. Measure new holdout utility, each old-session holdout, per-role B1/B2 receiver retention, predictor/encoder/EMA parameter diffs, optimizer-state persistence, checkpoint readback, restart, rollback, and CPU/RSS. Keep the experiment SHADOW and all production learning gates OFF.

This is a testable research hypothesis, not an implemented RoD port or a claim of full JEPA/GGUF learning.

## 4. Current JEPA code checkpoint

- `513b52b3535e31e8782415543a9c28952fdf0df7` adds per-session retention measurement for the numeric B1_DETAIL/B2_GIST/SELF_MODEL receiver heads. The prior and candidate heads are evaluated on the same source-disjoint old-session holdout cohorts; each role's readout gate fails closed if retention regresses or has not been measured.
- Exact-head Python 3.13/3.14, incremental JEPA, staged/integrated and combined workflows were queued at the last readback. This is not a PASS.
- The PR remains based on release base `bdcad466ffea75a2b41f7d23be168f53c7197d20`. It overlaps #2258 in the integrated training, recovery/stage builder and deployer pin chain. Rebase and recompute those pins only after the Boss/Core branch is finalized.
- No local full Aii checkout was available in this run; LOCAL_LINUX project tests are BLOCKED. CI is synthetic Linux evidence. REDMI_UNVERIFIED. No deployment, model/weight change, permission change or device action occurred.
