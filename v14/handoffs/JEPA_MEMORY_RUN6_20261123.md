# JEPA & Memory — Run 6 handoff (2026-11-23)

## Execution record

- Run started: 2026-11-23 02:01:42 Europe/Berlin.
- Completion time at this checkpoint: not yet measured; this is an in-progress handoff.
- Working branch: `jepa-memory/v14-postcommit-worker-contract-20261123-run5`.
- Parent: JEPA #2372 exact head `d88bfe3fe0cce9f55fc5ff0775c80f3798c356d2`.
- Current code head: `00870d648f33e09ba378ed9cdfae26081978f19b`.
- PR: #2396, DRAFT / NOT_RELEASED.

## New runtime change

### 1. Postcommit event cursor is now scan-bound

`v13/code/v13/sleep.py` now reads the target action's SQLite `rowid` and compares it against both the base WorldJEPA consumer's and temporal JEPA consumer's persisted `scan_cursor`.

- `last_learning_event_id` advances only when every enabled consumer has scanned through the target action and neither consumer has another page.
- A real `has_more` page remains eligible for the existing bounded continuation path.
- If a consumer has no further page but remains behind the target row, the worker emits `T8_SCAN_CURSOR_BEHIND_TARGET`, records the scan evidence and does **not** mark the event consumed.
- Disabled/cancelled consumers are not treated as a scan failure.

This directly addresses the QA finding that a `NO_NEW_TRANSITIONS` result could previously advance the event cursor even when its action-row cursor had not reached the target.

### 2. Runtime-produced T8 outcomes now enter the temporal JEPA integration test

`v13/code/tests/test_v14_world_jepa_postcommit_runtime.py` now:

- creates 32 completed turns through the actual Python Runtime worker across eight independent sessions;
- verifies the real Runtime rows through the committed T8 source / CorollaryCopy / ActionOutcome verifier before training;
- keeps those Runtime-produced rows inside the JEPA learner's scan instead of moving the learner cursor past them;
- adds 48 independent synthetic sessions to balance the four action routes and provide source-disjoint train/holdout support;
- requires both base WorldJEPA and temporal JEPA updates in the same postcommit worker result;
- checks nonzero encoder, predictor, EMA-target and total parameter deltas, held-out improvement over shuffled-target and shuffled-action controls, source-disjoint partitioning, retention acceptance, optimizer/checkpoint persistence and restart readback;
- reconstructs the exact training/holdout window split and verifies that at least one real Runtime ActionOutcome is used as a training-window target;
- includes a negative control where both consumers report scan cursors behind the target with no further page; the event must fail closed rather than be marked consumed.

The existing separate B1_DETAIL/B2_GIST offer-prompt regression remains the consumer-side proof that the numeric temporal receiver readout reaches actual body prompt construction. That path is still SHADOW prompt context, not native B1/B2 model-weight learning or a trained cross-organ latent channel.

## Exact test and platform evidence

- New exact-head GitHub Actions for `00870d6`: queued at last readback — workflow runs `45093956564`, `45093956560`, `45093956563`, `45093956556`. No PASS is claimed for the scan guard or expanded Runtime cohort until those exact-head runs complete.
- Previous tested code SHA `3a1cecb0ddb4de3791d4ea6b66dc5d2038b3830c`: Python 3.13/3.14 `py_compile`, temporal T8/JEPA 21/21, and postcommit Runtime/continuation/restart 15/15 passed. Those results predate this run's changes and are not a substitute for the current exact-head CI.
- LOCAL_LINUX full Aii checkout: BLOCKED. The environment has Python 3.13.5 but no `.git` checkout. `git ls-remote https://github.com/RedMentos/Aii.git` failed at GitHub DNS resolution. No local compile or pytest result is claimed.
- CI is not Redmi. No Android device was connected or mutated, no Termux update was requested, no native GGUF token/gradient/weight test ran, and no B1/B2 native weights changed.
- Latest private installed-state observation read during this run reports release `aed1d2b826290c95c70356b5d8b864b5ef382be4`, updater enabled, Runtime/Dashboard `UP_TO_DATE`, and no updater error. It is not this candidate. The same observation still reports long C3 prefill and B1/B2 `TIME_BUDGET` with zero valid offers; semantic use and native latent exchange remain unproven.
- Three new private read-only relay requests for HEALTH, PIPELINE_STATUS and DIAGNOSTICS were issued with a ten-minute expiry. They are pending; no phone receipt is claimed yet. No LOG_PAGE request was made.

## Research findings for the shared ledger

### JEPA-TTT — arXiv:2610.00722

Full primary paper and project page reviewed. The method retains predictor parameters, optimizer state and dense replay across episodes, while updating only the action-conditioned dynamics predictor and holding its visual encoder/reward head fixed. It reports an 83% mean reduction in five-step latent prediction error and a 153% mean best held-out planning-score improvement over a frozen baseline across eight dynamics shifts/four environments.

**V14 experiment:** add a predictor-only adaptation ablation against the current joint encoder+predictor+EMA update, with equal replay/compute budget, source-disjoint holdouts, old-cohort retention, parameter diffs, restart and rollback. This is an experiment, not a recommendation to make the encoder permanently frozen. No official code repository was linked by the primary project page; no code or weights were imported.

### Learning What to Recall / Future-Aware Recall — arXiv:2609.34677

Primary paper, project page and `sony/far` repository inspected. FAR trains query-dependent cue scorers using the predictive utility of the realized future, while keeping inference future-blind. This is relevant to episodic recall: future outcomes can supervise which time/vision/audio/other cues were useful without leaking future data at retrieval time.

**License/resource boundary:** `sony/far` is CC BY-NC 4.0, and its THIRD_PARTY_NOTICES carries additional upstream restrictions. Its environment expects Python 3.11+, PyTorch 2.7+, CUDA 12.8 and a quickstart around 14 GB GPU memory. It is not suitable for direct Android/Termux reuse and is not cleared for product code reuse. No code, weights, datasets or dependencies were downloaded.

**V14 experiment:** a small source-bound retriever may learn cue weights from held-out predictive utility, but must be future-blind at inference and compare against recency/uniform baselines with equal memory budget, disjoint episodes, deletion/revocation, restart and retention.

### Sandwich-Residuals — arXiv:2609.21740

The preprint reports small learned residual corrections around a frozen predictor, with 97–99% fewer adapted parameters than selected-layer adaptation and comparable performance in its evaluated settings. No official reusable implementation/license was identified in this review.

**V14 experiment:** compare a small residual adapter against predictor-only and joint updates as a resource-efficiency condition. Do not freeze the V14 learning architecture or adopt this mechanism without a source-bound holdout, retention, memory/latency and rollback result.

No external code, model, weights or dependency was imported.

## Integration dependencies and next executable step

1. Poll all exact-head workflows on #2396 `00870d6`; repair any new failure and rerun the exact head.
2. QA #2391 must then rebase/recompose its immutable source chain after the final JEPA bytes. It must include the Perception #2395/#2397 `vision_source_lineage.py` helper and final `vision.py` source-forget bytes, plus the changed training-resume builder from #2396, and recompute Termux12 → Termux21 → stage → runtime-deployer pins. Do not blind-merge the diverged branches or weaken source checks.
3. Boss/Integrator should refresh V14-004 and V14-011 in the shared board, workplan and `V14_USER_NEXT_ACTION.md` with the new #2396 head, current CI state and remaining source-pin dependency. The shared docs are Boss-owned; this handoff is the JEPA evidence source for that update.
4. After the combined exact-head staged/optimizer/integrated matrix is green, Boss can decide whether a release candidate is eligible. GitHub push alone is not deployment. No UPDATE_REQUEST should be sent before that gate and a separate authorized device receipt.
5. Continue whole-Canon work after this integration: the temporal JEPA path remains only one partial family; Self-model learning, semantic/procedural memory, sleep/dream consolidation, cross-organ weight updates, native latent transfer, voice learning and Android control remain open.

## User action

**Keine Aktion nötig.** No model download/swap, weight change, permission change, manual Termux command or device operation is requested by this checkpoint.
