# JEPA / Memory — temporal T8 WorldJEPA run 12 (2026-11-22)

## Scope and ownership

Base: gpt6/v13-private-remote-bridge-20261111 at c4eb82deec915f65894c20d6ebbaf0ebf58fa335 (verified release-development branch HEAD before this branch was created).

This is an additive JEPA/Memory lane. It does not edit the Boss-owned integrated candidate, the Perception B3-paired-tap lane, the historical V13 canon, installed models, device permissions, or Age.

## New executable path

- v13/code/v13/world_jepa_temporal.py consumes the existing source-verified verify_committed_temporal_page API. It admits terminal, source-bound T8 ActionOutcome receipts, including known CANCELLED / INTERRUPTED / ABORTED outcomes as explicit censored/omission features. OUTCOME_UNKNOWN is counted and skipped; a missing or unknown event breaks a sequence window.
- It constructs overlapping, contiguous windows at every valid session offset with history lengths 2 and 3. Every window retains event/action/generation/session/source provenance. A source- and session-connected-component split prevents overlapping windows or repeated source digests from crossing train/holdout.
- It trains the existing NumPy WorldJEPA model on 10-D temporal state/outcome features and action-conditioned next-event targets. It uses the existing EMA target, Adam resume state and safe SHADOW NPZ checkpoint implementation; no new dependency or external model/weight is introduced.
- The consumer records parameter and EMA deltas, optimizer steps, checkpoint/source SHA, holdout loss, shuffled-target/action and no-history controls, collapse metrics, replay mode and up to three old holdout cohorts. It enforces a bounded retention gate before publishing a candidate.
- It reuses the existing role-specific ridge receiver contract for B1_DETAIL, B2_GIST and SELF_MODEL. receiver_readout is SHADOW-only and source/checkpoint-bound. It does not claim that this temporal readout is already appended to the native B1/B2 prompt or that native GGUF weights changed.
- SleepRuntime._run_world_jepa now invokes the temporal consumer after the existing one-step learner. The existing scheduler still wakes on an observed terminal outcome; once woken, the temporal page scans all intervening committed T8 rows, including known censored outcomes. A cancellation is therefore ingested at the next observed-outcome wake rather than scheduling a separate job.
- Memory._forget_source now uses a combined guard: it holds the existing JEPA file lock through deletion and refuses to delete a source retained by either the temporal active or rollback checkpoint. Pending-only rows are removed. The non-JEPA updates-table and active-generation checks were also moved inside the same BEGIN IMMEDIATE SQLite transaction as the source tombstone, closing the previously documented precheck-to-delete race. Safe temporal parameter unlearning is not claimed.

## Canon and research mapping

- V14 master §§2.6–2.9: action/outcome and omission learning, EMA/Jepa, local plasticity, replay and sleep.
- V14 master §§18–19 and research entry R-083: bounded dense temporal windows, source/session continuity, multi-shift retention, negative controls, restart and rollback.
- This is an additive small numeric WorldJEPA experiment, not a visual JEPA, not native cross-family latent transfer, not B1/B2 GGUF training, and not a complete self-model.
- Candidate research-ledger follow-up: R-084 (implementation of the R-083 temporal-window gap). The central V14_RESEARCH_LEDGER.md is being edited concurrently by Boss/JEPA/Perception PRs #2343/#2345/#2346; this run deliberately did not overwrite that shared file. Integrator should append the handoff evidence after those branches are reconciled.

## Exact test contract

New test: v13/code/tests/test_v14_world_jepa_temporal_runtime.py.

- Real V13 SQLite Store, source blobs, EventEnvelope, committed ActionSelection and ActionOutcome producer path; all content is synthetic test data.
- Known cancellation/interruption enters temporal windows; unknown outcome is skipped and breaks the sequence.
- Source-disjoint overlapping windows; numeric encoder/predictor and EMA changes; persisted optimizer/checkpoint readback; B1/B2 shadow receiver API; actual Memory._forget_source refusal for a retained temporal source; default-off SleepRuntime wiring; rollback absence is not fabricated.
- Workflow: .github/workflows/v14-temporal-world-jepa.yml, Python 3.13 and 3.14, py_compile plus focused pytest.

Local execution boundary: the full Aii checkout is not mounted and git ls-remote fails because GitHub DNS is unavailable in this execution container. Therefore no local full-suite or local integrated-runtime PASS is claimed. Exact branch CI must be read after PR creation; CI is not Redmi proof.

## Device / deployment evidence (read-only)

Latest owner-authenticated private V13OBS issue #115, updated 2026-11-22 15:38:27 UTC:

- Installed SHA remains c4eb82deec915f65894c20d6ebbaf0ebf58fa335; pipeline/runtime/dashboard report UP_TO_DATE, auto-update enabled, last_error=NONE.
- Latest stored turn: FINAL, 57.74 s total, 41.63 s TTFT, 38.95 s C3 prefill, 751 admitted prompt tokens, 2 generated tokens. Correctness is not established.
- B1_DETAIL 4/4 native attempts failed and B2_GIST 2/2 failed; both have zero valid source-bound offers. Native latent exchange is false. The instantaneous sample reports four mapped processes, but its PSS/RSS is not free RAM or a sustained profile.
- Official Age 0; requested lab stage 10 / effective implementation stage 5; physical feature execution false; learning commit authority still requires separate SHADOW mode.
- No update request, chat send, log page, shell, model/weight swap, permission change or device mutation was performed. This branch is not deployed. REDMI_UNVERIFIED for every new temporal feature.

## Current coordination snapshot

- #2345 (jepa-memory/v14-worldjepa-b1-b2-bodyview-receiver-20261122-run11) head 2adc099c86f3cf77ce2eb38a7b3fd843aaf9c533: 6 successful checks, one policy-skipped validator. It contains the one-step B1/B2 prompt receiver work.
- Boss integration #2343 head 55b76c4c79b24b5ac674366d6bcb32aa15ab1f9d: still has 9 failed, 12 successful and 6 in-progress checks at last read. Do not edit its shared runtime.py / store.py / cognition.py / world_jepa_consumer.py chain in parallel.
- Perception #2346 remains open on its separate paired-native-tap branch. No files from that lane were changed here.

## Next actions

1. Read this branch's exact Python 3.13/3.14 CI and fix any temporal learner/test failure before review.
2. Have Boss/Integrator reconcile #2343 source pins and the #2345 one-step receiver, then stack this temporal consumer onto the accepted combined base without overwriting other lanes.
3. Add an explicit A→B→C→A cohort test with matched optimizer steps and compare replay-on/off reacquisition/retention. Current code retains three old holdouts, but this run does not claim a complete multi-shift acceptance.
4. After integration, connect the temporal B1/B2 shadow readout to the existing bodyview consumer behind the same local learning/optimizer gates; measure utility against one-step, no-history, shuffled-action and source-exact controls.
5. Do not request deployment until Boss review, exact push CI, release pipeline proof and explicit device authorization. The current updater is healthy, but that does not make the installed B1/B2/C3 path functionally accepted.


## Run 13 follow-up — 2026-11-22 16:10 UTC

**Code checkpoint:** PR #2351 branch head `e8b12868b5c1478b4faee39a2f75953350c493e1` (draft, not released).

- `TemporalWorldJEPAStoreConsumer.update()` now distinguishes newly scanned T8 receipts from already-persisted pending rows. Pending rows not present in the active checkpoint remain eligible for a deliberate retry after a utility/retention rejection or explicit rollback, even when no new ActionOutcome arrives. `pending_retried` is recorded separately; fresh `verified_receipts` remains truthful. The `replay_mode="none"` selection also includes eligible pending rows.
- `Memory._forget_source()` now holds the shared `Store.mutex` (RLock) from the source tombstone through update-artifact cleanup, the final live-refcount check, blob unlink and audit write, under the existing JEPA file-lock order. This serializes `Store.source()` republishing with revocation. It does **not** close the separate generation-promotion race: Boss-owned `Store.switch_generation()` still performs preflight outside this RLock and must recheck source liveness/status/path/hash/manifest inside the final transaction.
- Added two regression tests: (a) accepted A then B checkpoints, rollback to the exact A checkpoint/optimizer state, restart, and retrain the pending B receipts without a new receipt; (b) a barrier-controlled concurrent source republish that must block until revocation finishes, then recreates a readable blob.
- Exact CI for this head is queued, not passed: `V14 Temporal WorldJEPA T8 Windows` run 45042096354 and `V14 JEPA training-resume and source-forget Python 3.13/3.14` run 45042096413. Other triggered release checks are also queued/cancelled. No local full-repository PASS is claimed: `git ls-remote` to GitHub failed with DNS resolution in this execution container. No local Android/Termux test was run.
- The branch still does not feed temporal receiver outputs into the B1/B2 bodyview consumer and does not change native GGUF weights. Its receiver remains SHADOW; `native_body_consumed=false`, `native_body_weights_changed=false`, `decision_authority=NONE`.

**Current device receipt (private RedMentos/Aiiii V13OBS #115, updated 2026-11-22 16:08:33 UTC):** installed SHA `c4eb82deec915f65894c20d6ebbaf0ebf58fa335`; runtime/dashboard UP_TO_DATE, auto-update enabled, last_error NONE. Latest observed turn: 57.74 s total, 41.63 s TTFT, 38.95 s C3 prefill, 751 admitted prompt tokens, 2 generated tokens. B1_DETAIL 4/4 native attempts failed, B2_GIST 2/2 failed, zero valid offers; both show TIME_BUDGET in the diagnostic. Native latent exchange is false. Official Age 0; requested Lab Age 10/effective implementation stage 5; physical feature execution is false; learning commit authority still requires separate SHADOW permission. This is a read-only receipt, not proof of this branch or a new deployment. REDMI_UNVERIFIED for the temporal feature.

**Research candidate R-084 — LATER (Zhou et al., arXiv:2611.25671, submitted 2026-11-19):** the paper separates storage of completed real transitions from action-conditioned readout; the partitioned memory is held fixed during candidate rollouts, while a state–action response bridge reads it and multi-cut auxiliary losses train the writers. It reports improvements on delayed-evidence PushT/TwoRoom tasks and controlled history interventions. The paper uses an online encoder (no EMA), a visual CF-JEPA backbone and H100-class experiments; no official implementation/license or reusable checkpoint was verified. It is not a direct Android dependency and does not justify removing V14 EMA. Candidate V14 experiment: source-bound, read-only action-conditioned retrieval over committed T8 experiences for B1/B2, with action-swapped, source/history-swapped, zero-memory and no-history negative controls; write only after completed outcomes and preserve the current EMA/checkpoint/rollback gates. No dependency or model was changed. Primary source: https://arxiv.org/abs/2611.25671.

**Coordination:** Boss PR #2343 currently points at `863e751ff5410dc555006c8aeb9ef6c7b28d2a88`; its CI was queued at last read. The one-step B1/B2 bodyview receiver from #2345 is present on that integration branch, but the temporal receiver is not yet connected. The source-republish race fix above is on #2351 only until integration. Boss must add the same Store RLock around generation promotion and recheck source/update liveness under the final transaction. The central research ledger is concurrently owned/edited by the integrator; this handoff supplies the R-084 evidence for append after #2343/#2345/#2346 are reconciled rather than overwriting their shared ledger.

**Next:** read exact Python 3.13/3.14 CI for `e8b1286`, fix any failures, then stack this branch on the accepted Boss integration base. Next functional milestone is temporal readout into the real B1/B2 bodyview consumer, followed by A→B→C→A matched-step replay/retention and source/action negative controls. No deployment request or user action is needed.


## Superseding branch readback — 2026-11-22 16:10:08 UTC

- Boss PR #2343 moved from `863e751ff5410dc555006c8aeb9ef6c7b28d2a88` to `9a1424bbf11f3306ce1a50f1e88cbb5c3765bca2`. Exact `store.py` readback at the new head still shows `Store.switch_generation()` doing update-row/manifest/artifact preflight before `with self.tx()`; it still does not acquire `Store.mutex` and still does not re-read the quarantined update/source liveness inside the final transaction. The promotion-vs-forget race therefore remains OPEN; the latest Boss-head Python 3.13/3.14 workflow run 45042303309 is queued, not a pass.
- JEPA PR #2351 remains at `042b935ae0ab92f674d6bf4f0696bccea19e7506`; exact focused temporal workflow 45042289493 and training-resume/source-forget workflow 45042289497 are still queued. No CI PASS is available yet.
- The coordination comment was posted on #2343 with the lock-order requirement and R-084 research summary. No shared Boss-owned `store.py` changes were made by JEPA.
