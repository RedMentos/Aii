# V14 JEPA Store-backed WorldJEPA consumer — handoff 2026-11-21

Owner: JEPA & Memory. Work item: V14-004.
Base: gpt6/v13-private-remote-bridge-20261111 at c3c32c05a0374e970d274f8a777a7ab85c067d66.
Candidate branch: jepa-memory/v14-world-jepa-persistent-consumer-20261121.
Status: implementation candidate; not merged, not released, not wired into normal Runtime.

## Implemented in this candidate

- v14/learning/world_jepa_consumer.py consumes only VerifiedT8Transition receipts from the Store authority.
- The train/holdout split is grouped by source_id, not action ID. Every action derived from one source remains in one fold; cross-fold duplicate (state, action, outcome) content is rejected.
- world_model.transitions(..., return_cursor=True) and verify_committed_transitions_page() add an oldest-first (created, action_id) cursor feed. Invalid raw rows advance the scan cursor but are never admitted as labels. Transient source I/O errors propagate so the cursor is not committed on an incomplete read.
- Small pages are durably buffered under Store compare-and-swap until the source-disjoint cohort is large enough. The cursor, pending numeric experience rows and fingerprints are committed together. The learner no longer silently starves an older unprocessed backlog behind a latest-N window.
- The trainable NumPy WorldJEPA encoder/predictor/EMA target is updated from verified T8 rows. The immutable checkpoint SHA, source cohort SHA, processed fingerprints, replay rows, source-disjoint train/holdout IDs, B1/B2 numeric receiver heads, self metrics and rollback pointer are bound by one Store state CAS.
- B1_DETAIL shadow readout predicts action duration/output size; B2_GIST shadow readout predicts terminal success. The current consumer returns numeric SHADOW readouts only; no native B1/B2 activation or GGUF weight is changed.
- A second update reuses previous experience rows as replay and measures old-holdout retention. restore() and rollback() verify the checkpoint before pointer changes. Rollback also restores the corresponding T8 cursor, so later rows are eligible for reprocessing.
- Learning defaults off and the update requires a separate optimizer_permission=True. These are code-level gates, not an Android OS identity boundary. No Age, model registry, installed model, Termux state, or phone permission was changed.

## Known limitations / exact scope

- The V13 WorldJEPA checkpoint persists encoder, EMA target and predictor weights, but not Adam moments or the temporary inverse-dynamics optimizer head. partial_fit resumes weights and EMA but resets optimizer moments. The metrics explicitly record optimizer_moments_persisted=False.
- The B1/B2 receiver heads are trained numeric shadow readouts; they are not yet read by native B1/B2 bodies or a World/Planner decision consumer.
- The new consumer is not called by normal Runtime. Existing Runtime._worker already calls online_world_update(limit=64) after committed turns, but runtime.py is under the SourceHandoff ownership freeze. The next integration must use an agreed extension point and coordinate with the open #2135 OnlineWorld exactly-once patch; this branch does not overwrite that branch.
- Test rows are synthetic, but the tests use the actual V13 SQLite Store, source blobs, EventEnvelope, ActionSelection, CorollaryCopy, ActionOutcome and T8 authority code. They do not use live user conversations.
- This is not GGUF/native LLM weight learning, not native Redmi execution and not whole-system completion.

## Research consequence

JEPA-TTT (arXiv:2610.00722, 2026-09-30) shows why optimizer-state persistence deserves its own follow-up: in its controlled study, retaining both predictor and optimizer across episodes materially outperforms resetting adaptation at episode boundaries. Its dense replay ablation also reports a smaller additional benefit beyond dense windows. V14 should therefore add a persistent Adam-state checkpoint and compare predictor-only vs encoder+EMA updates, rather than treating weight-only warm start as the final continual-learning design.

ER-JEPA (arXiv:2609.36952, 2026-09-29) reinforces replay as a separate path from current-batch JEPA alignment. Its content-based, uniform and hard replay strategies should become measurable V14 ablations. Neither paper proves mobile performance or licenses a ready-made Android component; no paper code, weights or third-party dependencies were imported.

## Verification

- Exact local repository checkout / py_compile / pytest: BLOCKED in this worker; GitHub DNS checkout was unavailable. No local PASS is claimed.
- The dedicated GitHub workflow must pass on the exact candidate HEAD before review.
- Environment: SYNTHETIC_DATA / REAL_SQLITE_STORE_TEST, not LOCAL_LINUX full runtime, not TERMUX/REDMI.
- REDMI_UNVERIFIED; no private device receipt or authorized device session was available.
- Updater/deployment: no push to release branch and no device update attempted. NOT_RELEASED.

## Next concrete step

1. Run the exact Python 3.13 workflow and repair failures.
2. Have Boss/QA review source-disjoint partitioning, cursor ordering, Store CAS, crash ordering, and rollback cursor restoration.
3. Coordinate a small call-site integration with Core after #2135 is reconciled; route a source-bound WorldJEPA prediction into a real World/Planner or B1/B2 shadow consumer with no-predictor/replay-only ablations.
4. Add persistent optimizer moments and measure the difference against the current weight-only warm start.
5. Keep Android learning disabled until an explicit local per-organ permission and independent rollback path are wired. No user action is required for repository-only work.
