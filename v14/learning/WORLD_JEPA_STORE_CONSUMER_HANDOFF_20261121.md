# V14-004 JEPA & Memory handoff — 2026-11-21

**Lane:** JEPA & Memory  
**Base:** `gpt6/v13-private-remote-bridge-20261111` at `c3c32c05a0374e970d274f8a777a7ab85c067d66` (latest verified branch HEAD at implementation start)  
**Candidate branch:** `jepa-memory/v14-world-jepa-source-disjoint-paginated-20261121` at code commit `2311b039eb49375829876e1bea8f2ac2d6975fe8`  
**PR:** [#2143](https://github.com/RedMentos/Aii/pull/2143) (ready for independent review)  
**Historical V13 files:** unchanged; no runtime.py or online_world.py edit in this slice

## Implemented in this candidate

1. **Source-bound oldest-first T8 feed.** Added `verify_committed_transition_page` to the merged Store authority. It keyset-pages SQLite actions by monotonically increasing local rowid, verifies each candidate through the existing persisted event/source/CorollaryCopy/ActionOutcome authority, and does not repeatedly read only the latest N rows. The scan cursor is numeric Store position, not a learned action ID.
2. **Censoring at the read boundary.** Only observed terminal outcomes (`FINAL`, `FAILED`, `ERROR`, `DEADLINE`, `REJECTED`) can enter the WorldJEPA learner. `CANCELLED`, `ABORTED`, `OUTCOME_UNKNOWN`, and `INTERRUPTED` are excluded before receipt creation; a skipped count is telemetry only. They create no training label, processed ID, prediction error or receiver update.
3. **Source- and content-digest-disjoint holdout.** Experience rows now retain verified `source_id`; the deterministic split hashes `source_id`, not `action_id`, so actions from one source cannot be distributed across train and holdout. Source digest changes, content overlap, ID overlap and incomplete persisted splits fail closed.
4. **Persistent cursor + rollback.** State schema v2 persists the scan cursor alongside the active/previous JEPA checkpoints. Restart resumes the next oldest page. Rollback restores the previous checkpoint and its scan cursor, so the rolled-back page can be replayed.
5. **World/Self/Memory and body readouts.** The trainable WorldJEPA online encoder/predictor and EMA target continue to receive verified numeric T8 outcomes. Separate numeric shadow heads now expose B1_DETAIL, B2_GIST and SELF_MODEL readouts. A source-linked episodic `recall()` API retrieves nearest persisted numeric experiences with source/outcome digests; it returns no raw chat content.
6. **Python compatibility.** The dedicated workflow tests Python 3.13 and 3.14.

## Follow-up review correction — 2026-11-21

QA found that two distinct source_id values can still carry the same source_sha256. This child change partitions on source_sha256, keeps source_id-to-digest stability checks, validates source digest disjointness again on checkpoint readback, and adds a regression where two differently partitioned source IDs share the same digest. The earlier source_id-only rule was insufficient.

## Evidence required / current boundary

- Targeted GitHub Actions run `44848998581` passed on tested PR head `a2788aacdae09bb675fff220cbda4ba74d400912`: Python 3.13 — `57 passed in 4.35s`; Python 3.14 — `57 passed in 7.83s`; `py_compile` passed on both. New regressions cover source grouping, all four censored statuses, a 2,050-action backlog with two oldest-first pages, restart/cursor continuation, numeric parameter/EMA deltas, negative controls, receiver readouts, checkpoint retention and rollback. The additional `v13-private-remote-bridge-tests` run `44848994421` passed. A subsequent docs-only commit records this evidence.
- No local Aii checkout is available in this runner; no LOCAL_LINUX pytest result is claimed. These are GitHub Actions/Linux CI results, not local-device proof.
- No Redmi/Termux connection or owner-authenticated device receipt is available. `REDMI_UNVERIFIED`.
- The consumer is not wired into the normal `Runtime.online_world_update -> OnlineWorld.update` postcommit call. The #2135 exactly-once OnlineWorld candidate remains blocked by its nested SourceHandoff builder hash chain.
- Numeric WorldJEPA/EMA checkpoint changes are real trainable parameters in the isolated Store-backed experiment; B1/B2/SELF heads are readout adapters, not native B1/B2 GGUF weight updates. No GGUF or installed model changed. Learning defaults OFF; no device permission, Age, model or updater setting changed.

## Next executable step

After this PR is reviewed, compose this consumer with the #2135 exact-once OnlineWorld checkpoint in the automatic postcommit path without modifying frozen `runtime.py`. Expose source-bound World predictions to a real cognition/world/planner consumer in SHADOW, compare against no-predictor and replay-only baselines, then test restart/rollback and resource use. Keep the learning/optimizer gates closed by default until the actual runtime opt-in and device proof exist.

**User action:** none.


## Action-conditioned negative-control correction — 2026-11-21

- The source-digest child PR #2147 fixed the identified train/holdout byte-identity leak, but its exact CI run `44852394807` failed on both Python 3.13 and 3.14 in the end-to-end test's `negative_controls_separated` assertion. The trained holdout loss was slightly worse than the shuffled-action control (3.13: 0.480152 vs 0.479097; 3.14: 0.511960 vs 0.510329); zero-action loss was worse in both runs. The source/digest disjointness assertions passed before this failure.
- This exposes a weak action-identifiability signal in the old synthetic fixture, not a reason to relax the negative control. The follow-up branch `jepa-memory/v14-action-conditioned-control-20261121` makes the synthetic transition's route effect explicit in duration and output size, keeps independent nuisance variation, and raises the first JEPA update from 40 to 120 steps. This is a controlled positive test fixture only, not a claim about real-user outcome distributions.
- Follow-up code commit: `52690943522df331b20ab3990c7dd8ee72c1ba84`. Exact CI is pending until the stacked PR is opened. No full local checkout is available because the container cannot resolve `github.com`; no LOCAL_LINUX exact-repository test is claimed. No Redmi receipt, normal Runtime consumer, or native B1/B2 body-weight update is claimed.
- Keep the action-shuffled negative control strict. If the follow-up still fails, investigate action-conditioned predictor/encoder gradients and the synthetic source split rather than weakening the assertion.
