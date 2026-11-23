# JEPA & Memory — run 16: persisted B1/B2 receiver retention

Date: 2026-11-23 (Europe/Berlin)

## Code checkpoint

- Branch: `jepa-memory/v14-temporal-boss-2443-rebase-20261123-run14`
- Current code/test checkpoint: `d60fcb66b24f44b061a48c173b5de87fc05ecbe0` (documentation commits follow on the same branch)
- PR: [#2454](https://github.com/RedMentos/Aii/pull/2454), DRAFT, NOT_RELEASED, mergeable=false.
- Latest file commits:
  - `v13/code/v13/world_jepa_learning_intent.py`: `477ba539c8196d7934ed0895fbb31c18ec7f6def`
  - `v13/code/v13/world_jepa_temporal.py`: `166ffa1a4e141653d91e6d190e1e82dc5cd707f7`
  - `v13/code/tests/test_v14_world_jepa_temporal_runtime.py`: `d60fcb66b24f44b061a48c173b5de87fc05ecbe0`

### Implemented in this candidate

1. A successful first temporal update persists one fixed B1/B2 receiver-retention cohort in the temporal Store record: raw `X/A/Y`, window/action IDs, direct and transitive SourceRef IDs/hashes, creation checkpoint SHA and a canonical cohort SHA256.
2. On later updates, training excludes that fixed cohort by lineage source IDs, source hashes and transition IDs. The prior model plus prior B1/B2 heads are measured before training; the updated model plus new heads are measured on the same old cohort after fitting.
3. A committed update requires both B1/B2 roles to stay within the provisional **[DEFAULT] 5% relative old-cohort MSE tolerance**, recorded in the v3 receipt and subject to calibration against real update data. If the previous receiver had passed its utility gate, the updated pair must also beat mean, zero-latent and shuffled-latent controls. A non-disjoint cohort fails closed; it is not silently treated as unmeasured. The 5% threshold is an engineering default, not a paper-derived or Canon-locked constant, and must be calibrated against real update data.
4. `WeightDeltaReceipt` schema v3 records per-role old-cohort MSE, updated MSE, mean/zero/shuffled controls, cohort hash, source-disjoint status and pass flags. The The 5% threshold is an engineering default, not a paper-derived or Canon-locked constant. The first checkpoint correctly records `NOT_MEASURED / NO_PRIOR_CHECKPOINT`, while persisting the cohort for the next update.
5. Source-forget reference discovery now includes the receiver-retention cohort, so its provenance remains discoverable even if the bounded replay-row list later rolls forward.
6. Tests were added for first-checkpoint cohort persistence, same-cohort utility, encoder drift requiring receiver compensation, degraded-head rejection, source-overlap veto, cohort digest tampering, source-forget after replay-row eviction, and v3 receipt validation.

The adapter target is still the small float receiver head consumed through `bodyview._temporal_world_jepa_body_readout`. This is not a native B1/B2 GGUF/base-weight update, not a trained inter-body latent transfer, and not permission to promote the SHADOW adapter.

## Verification

| Environment | Result | Evidence |
|---|---|---|
| GitHub exact-head CI | **BLOCKED / startup_failure** | Latest push run [#45272190117](https://github.com/RedMentos/Aii/actions/runs/45272190117) ended `startup_failure` with **0 jobs**. Combined commit status has 0 contexts / pending. This is not a code-test failure and not a pass. |
| Local Aii project suite | **NOT_RUN / BLOCKED** | Container has Python 3.13.5, NumPy 2.3.5 and pytest 9.0.2, but no `/mnt/data/Aii/.git` checkout; `github.com` DNS resolution fails. No project compile, pytest, staged or integrated test was run. |
| Synthetic numeric control | **PASS** | Python tool checked unchanged adapter retention, encoder scale drift with old head, compensated head after encoder drift, degraded-head rejection, and source-overlap detection. This is a small numerical reproduction, not execution of the Aii implementation. |
| Termux / Redmi | **REDMI_UNVERIFIED** | No device command, update request, CHAT_SEND, shell, model/weight swap or permission change was performed. |

### Git/CI integration state

- Boss parent PR #2443 branch head read back as `cdf6b64067ac426ba32194100d3764f6e74c105f`; its combined code head had Actions `startup_failure` attempts with no jobs, and its documentation descendant has no workflow runs.
- PR #2454 still has merge base `6e9bad8daa9ad9ec97947639600f6c7cdbffb6d4`; against current Boss head `cdf6b64067ac426ba32194100d3764f6e74c105f`, the branch is **59 ahead / 47 behind**. It remains DRAFT / mergeable=false.
- Core PR #2457 is stacked on an older JEPA head and must be rebased only after the Boss parent and JEPA stack have exact-head verification. No force-push or rebase was attempted.
- No release SHA was created: **NOT_RELEASED**. The source-pinned stage/deployer chain was not modified by this change; the stage copies the complete `v13` tree. Core retains stage/deployer ownership.

## Latest available private device evidence

Private V13OBS issue #115 was last updated at `2026-11-23T19:52:16Z`. It reports:

- Pipeline installed commit `8d93236c753f0194224c19edc7411d8d7082b1d6`, auto-update enabled, dashboard/runtime UP_TO_DATE, last error NONE.
- Runtime state `STOPPED_BY_USER`, autostart false, model process STOPPED; preserve this state.
- Last stored turn: 6.295 s total, 2.046 s TTFT, 358 prompt tokens, 7 generated tokens. This is a stored diagnostic sample, not a new acceptance run.
- B1_DETAIL and B2_GIST each had two native attempts and two failures, with zero valid offers and zero final-C3 contribution turns. Native model residency was unavailable.
- Correctness and installed-model quality remain UNKNOWN.

A fresh four-command owner-read could not be requested: private issue creation returned GitHub HTTP 422 because the linked account has no verified email. Record this as `NO_LIVE_RECEIPT`; do not infer a fresh phone state. No LOG_PAGE or device mutation was attempted.

## Research note

R-115, *What Should World Models Forget? Stratified Retention for Continual Adaptation* (arXiv:2610.03713v2), remains a conceptual evaluation proposal. This implementation adds a fixed historical ActionOutcome cohort for receiver-adapter stability; it does **not** implement the paper's full invariance-timescale stratification or revision-latency protocol, and does not change the World Model's truth policy.

## Remaining gaps / next executable step

1. Wait for a complete green exact-head Boss #2443 matrix. Then rebase #2454 onto that exact head without force-push and resolve any current memory.py / source-authority composition changes.
2. Rebase Core #2457 onto the verified JEPA head; coordinate its native-probe/stage overlay with Core because that stack currently points to an older base.
3. Run the exact temporal and postcommit suites on Python 3.13 and 3.14, then optimizer-resume, source-forget, restart, positive rollback, missing/corrupt rollback, staged-runtime and integrated-regression.
4. Add a true second-update Store integration assertion showing a committed `MEASURED_PASS` receipt after the fixed cohort is replayed. Keep the current first-update `NOT_MEASURED` result as the correct bootstrap state.
5. Keep B1/B2 adapters SHADOW and all native body-weight promotion OFF until the exact test matrix and actual runtime consumer prove utility and rollback.

**User action: none required.** No manual Termux command, phone restart, model download, model swap, permission change or update request is appropriate for this unverified draft.
