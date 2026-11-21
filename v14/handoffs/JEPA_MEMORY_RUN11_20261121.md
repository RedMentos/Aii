# JEPA & Memory handoff — run 11 (2026-11-21)

## Current candidate

- Repository: `RedMentos/Aii`
- PR: [#2231](https://github.com/RedMentos/Aii/pull/2231)
- Branch: `jepa-memory/v14-store-aba-current-20261121-run11b`
- Last code-bearing checkpoint: `ac92200699e2838d99ccd3dd7036debf2a755414`
- Base shared V14 head at rebase: `9d8f91960c568be7fe7dcf894555ce7250f635f4`
- Code-bearing release lineage: `f279286a4453248004c670fcaabecd85da6ab299`
- Release: `NOT_PHONE_RELEASED`; installed SHA unknown; `REDMI_UNVERIFIED`.

## Implemented candidate changes

1. `v13/code/v13/world_jepa.py`
   - `fit/partial_fit(train_encoder=False)` is allowed only for a warm-started model.
   - Predictor gradients continue; encoder and inverse-dynamics gradients are omitted; EMA target is not advanced.
   - Full encoder + inverse + EMA training remains the default.

2. `v13/code/v13/world_jepa_training_state.py`
   - Adam checkpoint state now carries a per-parameter step counter alongside the legacy total step.
   - Bias correction uses each parameter's own update count.
   - Old checkpoints without the field migrate from their legacy global step; new checkpoints persist the counters.

3. `v13/code/v13/world_jepa_consumer.py` and `world_jepa_runtime.py`
   - `encoder_mode=full|predictor_only` travels through the normal Store-backed postcommit permission state.
   - Default remains `full`; predictor-only fails closed until an encoder checkpoint exists.
   - Consumer reports encoder, predictor and EMA-target deltas separately.
   - Learning and optimizer permissions remain OFF by default.

4. `v13/code/tests/test_world_jepa_predictor_only_resume.py`
   - Full bootstrap → predictor-only update → checkpoint save/load → full plasticity resume.
   - Checks parameter diffs, frozen encoder/EMA/inverse, independent Adam clocks, legacy-safe checkpoint readback and invalid-mode rejection.

5. `v13/code/tests/test_v14_world_jepa_store_aba_replay.py`
   - Four arms: uniform/full, none/full, uniform/predictor-only, none/predictor-only.
   - Three fixed seeds; A→B→A cohorts; disjoint holdouts; negative controls; rollback/replay and receiver readback.

6. Staged consumer pins:
   - Rebound the exact WorldJEPA and training-state SHA-256 pins in `integrated_world_training_resume_candidate_20261111.py`.
   - Recomputed the dependent hash in `termux_runtime_recovery_candidate_20261112.py`.
   - Recomputed the dependent `BUILDER_SHA` in `stage_integrated_candidate.py`.
   - Verified the four-link pin chain by recomputing SHA-256 from the fetched branch bytes. Do not hand-edit one pin without updating its downstream dependent pin.

## Test evidence and limitations

- Earlier A→B→A baseline on the previous PR head: 12 candidate updates across replay/no-replay arms were rejected by the retention gate. No-replay could improve returning A while forgetting B; uniform replay helped B but still failed old-cohort retention. This is a negative result.
- First CI after adding predictor-only mode failed at the staged runtime because the integrated training-resume builder still pinned old WorldJEPA source bytes. The dependent builder/recovery/stager pins were then updated.
- Latest exact Python 3.13/3.14, staged-runtime and integrated-regression jobs were queued/in progress at last readback. Do not claim PASS until the exact latest head completes.
- `validate-additive` is expected to fail because this candidate changes existing production modules and staged consumers. Do not bypass or waive it; require direct Boss review of the source/pin chain.
- Local full-suite test: BLOCKED. No Aii checkout is present and `git ls-remote` failed because github.com DNS could not resolve. GitHub Actions is CI/Linux, not local Linux or Redmi.
- No native GGUF B1/B2/C3 weight change, no cross-organ gradient proof, no real Android deployment, no model swap and no user-data mutation.

## Next executable step

1. Read the latest branch HEAD and all exact check-runs again.
2. If Python 3.13/3.14 fails, inspect its job log and repair the real cause; do not weaken the holdout or staged pin checks.
3. If staged/integrated fails, follow the full pin chain and the exact source consumer that rejected the bytes.
4. Extract per-seed A/B holdout loss, negative-control deltas, encoder/predictor/EMA parameter diffs, optimizer clocks, restart and rollback outcomes. The candidate is accepted only if the new mode improves adaptation without sacrificing retention across prior cohorts.
5. Keep `full` as default and all learning/optimizer gates OFF until matched utility/retention passes and Boss review completes.
6. Then continue the wider source-bound T8 → World/Self/Memory → B1/B2 receiver integration. Do not claim native body-weight learning or whole-Canon completion from this small NumPy predictor.


## Final stager-consumer correction

The first pin update was incomplete: `runtime_deploy.py` also pins `stage_integrated_candidate.py` via `STAGER_SHA256`. The exact staged/old-phone tests exposed this as `Integrated stage builder changed` and `last_result=PARTIAL`. Commit `08a521b2b445af44b13ddd8c0a8ea25ae7652713` updates the runtime-deploy pin to the current stager bytes; workflow path/compile coverage was updated in `d7b5613dc3a3118a3c6a5856478c6e2a665db27c`. The complete chain now reads back consistently. The corrected exact CI was queued at last readback.

## Next architectural gap

The current retention gate uses the prior aggregate holdout, not stable source/session-bound holdouts for each historical cohort. The next JEPA/Memory code task is to persist bounded per-cohort holdout probes and require each prior cohort to satisfy its own retention tolerance after every candidate update. This must be tested across A→B→A, disjoint source/digest controls, checkpoint restart and rollback. Do not accept an update because a recent aggregate masks forgetting of an earlier regime.

## Run 11 follow-up — 2026-11-21 19:01 CET

### New code-bearing candidate

- Branch: `jepa-memory/v14-session-window-budget-20261121-run11-final`
- PR: #2237 (OPEN / DRAFT; stacked on #2231)
- Code-bearing head before this handoff commit: `07f78312eb126b58e65980f67dc24a91bfab7416`
- No release SHA; `NOT_PHONE_RELEASED`; installed SHA UNKNOWN; `REDMI_UNVERIFIED`.

### Actual implementation added

1. `world_jepa.py`: bounded `update_scale` in `(0,1]` is applied to both the main Adam step and bootstrap predictor Adam steps. Default 1.0 preserves prior behavior.
2. `world_jepa_consumer.py`: for an existing checkpoint, tries scales 1.0, 0.5, 0.25, 0.125, 0.0625. Each retry reloads the same persisted checkpoint, so rejected candidate parameters, EMA, Adam moments, inverse head and RNG do not leak into the next attempt. The exact same fit rows and optimizer-step budget are used. Acceptance still requires new holdout improvement, old holdout non-degradation, and shuffled/zero-action negative controls. If all attempts fail, pending experience/cursor may be persisted but no model checkpoint is published.
3. `integrated_world_training_resume_candidate_20261111.py`: clone field validation now allows only optional `_last_gradient_projection` telemetry and validates its values; the canonical `_training_state` remains mandatory and is copied through `training_state.from_model` plus the checkpoint validator. Unknown extra fields remain fail-closed.
4. Added a one-step numeric regression for 0.25 update scaling and unchanged optimizer step count. Added a CI diagnostic step that prints exact SHA-256 values for the four nested builder-chain files.

### Test and deployment evidence

- **LOCAL_LINUX: BLOCKED.** No local Aii checkout is mounted; GitHub DNS resolution failed in the available container. No local compile or pytest command was run.
- **CI: NOT_RUN_AFTER_NEW_HEAD.** No check-run is attached to the new branch head yet. Previous exact head `d91f4683fe96619efa94b5fcd64bc1f55e9c39ec` failed the old-holdout retention gate on CPython 3.13/3.14 and failed staged second-update cloning with `ValueError: unsupported or unbound World-JEPA model`. Those failures are the baseline, not success.
- **SYNTHETIC/CI:** no new passing result yet. The added tests are candidates only until the exact head is executed.
- **TERMUX/REDMI:** not run; no authenticated device receipt. No updater request, shell action, model download/swap or permission change.

### Ownership and next action

- JEPA did not change the parent-owned `termux_runtime_recovery_candidate.py` or `stage_integrated_candidate.py` pins. The PR is stacked; Boss/Core/QA must update the parent pin chain on its owning integration branch after reading the CI SHA diagnostic.
- Next: trigger exact-head Python 3.13/3.14, staged-runtime and integrated checks; inspect failures; then report parameter/EMA/optimizer diffs, disjoint holdout utility, restart, retention and rollback. Keep learning/optimizer gates OFF until the full evidence passes.


- Current PR branch head after the documentation sync is `808751bf7d029629fb9f2781f8880551b942b04a` (docs-only); the code-bearing candidate remains `07f78312eb126b58e65980f67dc24a91bfab7416`.
