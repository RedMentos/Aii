# Canon core and organ recovery review — 2026-10-24

Review base: Claude `cb959052433e01c29afc007e02b93aef373deb7f` (PR #38), with read-only comparison to the PR #41 design note at `a67a81d0c3be3ff19c350e0270cf173435a5c65c`.

## Scope read and preserved

The reviewer read **lines 1–7000, inclusive**, of `docs/canon/V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md` in complete bounded chunks. This is the first half, **not a claim to have read the entire canon**. Read alongside `AGENTS.md`, `v13/AGENTS.md`, current ROADMAP sections, ZIELABGLEICH, HANDOFF_CURRENT, BUILD_STATE, the latest continuation decisions, and PR #41's complete scope clarification. The latter is additive; no runtime feature from that note was activated.

| Canon core | Obligation retained by this review |
| --- | --- |
| W0–W10, IH-H0 | Executable and testable implementation, no silent deletion; code/state/persistence/tests/telemetry and relevant measured baseline required for completion. |
| A0–A5 | Raw and source-bound ingress, segmentation, separate frozen semantic teacher, learnable student ports, perceptual attention and exact recovery. New modalities stay behind text-core gates. |
| B1/B2 | Distinct full bodies and preferred fine/gist integration scales, native tokenizer/router authority, independent mutable state, measured complementarity and role retention. |
| B3/B4/B5 | Direct cross-body channels, message-space rather than private-state alignment, bounded workspace and support interfaces; source/control/symbolic/no-message baselines remain mandatory. |
| C0–C7 | JEF is the executive subsystem; C2 control and C3 language remain separate roles with role-specific learning. Persistent state, broadcast, focal coalition, one authorized action/report stream and modular effectors remain required. |
| F1/F2 | Attention, salience, reflex and focal recruitment are distinct; amplification conveys neither truth nor learning permission. |
| F3 / Context OS | Exact, warm/native, episodic, staging and archival views retain source links, constraints and deletion lineage; native re-entry differs from re-prefill and from experimental neural layer re-entry. |
| F4 / learning | Actual local prediction errors/gradients, eligibility, typed modulators, correct EMA, separate self/teacher/human/world lanes, replay/dream/homeostasis/consolidation and shared-path regression. Heads-only gains do not close body plasticity. |
| F5/F6 | Age and capability ceilings, immutable user caps, explicit permissions, source/truth distinctions, proposals for hard-rule changes and approved commit/rollback. |
| F7 / IH hardening | One coordinator, bounded queues, independent deadline governor, actual runner/resource proof, source/manifest integrity and transactional generation state. |
| STEP plan and gates | Existing STEP0–11 dependencies and all later obligations stay in scope. A successful small repair does not make STEP2, B3 or the full system pass. |

## Confirmed defects and repairs

1. **Active artifact integrity was inferred from metadata.** Snapshot a current component, then delete or corrupt the component file without changing its generation manifest. `organ.check` returned `identical=true`, and `restore` returned `ALREADY_IDENTICAL`; the real generation failed `Store.validate_artifacts`. The original tests missed this because they changed the generation before deleting the file.
2. **Saved artifact integrity was skipped on the identical fast path.** Delete a saved bridge or corrupt a saved component while active files remain unchanged. The old checker still advertised the checkpoint as restorable, and restore could return success without checking the saved bytes.
3. **A refused path collision could overwrite another organ.** If a saved component path is now owned by a different component/organ, old restore copied the snapshot to that path before checking ownership. It then raised the expected collision error, but the other organ's active file had already been overwritten. The explicit counterexample verifies both unchanged generation and unchanged current file bytes.
4. **Per-component checks were insufficient.** Coordinator review supplied a second counterexample: an earlier component was repaired before a later component's path collision or dependency mismatch was refused. A generation-commit refusal also left repaired historical bytes behind. The entire restore plan is now checked before any copy; missing/corrupt artifacts are copied to fresh immutable paths for the new generation. Rejected copy/commit operations remove only newly created staging files. Existing active and historical file bytes are never overwritten.
5. **Flat backup basenames collided.** Two valid component paths ending in `candidate.npz` overwrote each other in the snapshot directory. New v1 snapshots add a per-component `component_files` map with disjoint backup paths. Old v1 snapshots without that additive map remain readable through their flat-basename layout; already lost bytes cannot be reconstructed from an old colliding backup and are correctly refused by the integrity check.

`v13/organ.py` now inspects active component file bytes and all saved component/bridge bytes before its identical/restorable decision. Missing/corrupt active artifacts are restored from verified saved bytes at fresh checkpoint paths and published in a new generation. Snapshot copies and staged recovery copies are verified and fsynced; the snapshot manifest is written atomically. Missing/corrupt backups refuse before writes. All component ownership, destination containment, dependency and retained-generation checks occur before copying. Existing model-revision checks, per-organ component scope, generation compare-and-swap and closure of global LIFO rollback remain in place. `:organ check` also names damaged backups in its text output.

No runtime/store/runner source was modified for this repair. No model inference, weight training, bridge activation or gate promotion was performed.

## Verification

Commands run in `v13/code` with bytecode writes disabled:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:tests python -m unittest tests.test_organ tests.test_standstill
# Before changes: 23 tests, OK.
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:tests python -m unittest tests.test_organ_artifact_integrity tests.test_organ tests.test_standstill
# After changes: 29 tests, OK.
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:tests python -m unittest tests.test_organ_artifact_integrity
# After the final test wording adjustment: 6 tests, OK.
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:tests python -m unittest tests.test_organ_artifact_integrity tests.test_organ tests.test_standstill
# After coordinator counter-review, whole-plan preflight, immutable recovery and basename fix: 35 tests, OK.
git diff --check
# PASS.
```

The six new tests were also run against the original module loaded from `git show HEAD:v13/code/v13/organ.py` in an isolated module namespace: **6 tests, 6 behavioral failures, 0 errors**. Fixtures use real Store metadata and filesystem bytes, with explicitly artificial component artifacts and no model calls. They exercise missing/corrupt active files, restart after repair, corrupt/missing backups, missing saved bridge, and cross-organ path ownership.

Four additional counterexamples were run against the intermediate repair before whole-plan validation: later path collision, later dependency refusal, rejected generation commit and duplicate snapshot basenames. **4 tests, 4 behavioral failures, 0 errors.** The final 12-test artifact-integrity suite additionally checks cleanup after an injected second-copy failure and successful recovery from an old flat-basename snapshot. Historical-path tests now verify the new active artifact and preservation of the prior bytes, rather than demanding in-place repair of an old generation file.

Full-suite integration and public-repository scan belong to the coordinator's final checkpoint. These focused checks alone do not certify the full runtime or phone behavior.

## Standstill and branch observations

The current `standstill.py` focused tests passed: confirmed coordinator parking, cancellation honored versus ignored, queued turns held, previous user switches retained, restart and background-resume disclosure. This review found no additional confirmed standstill defect. A wait timeout correctly leaves `confirmed_still=false` while work continues.

The PR #38 ROADMAP contains a WP-UI1 section naming `phone_halt.py` and widget buttons, but that file is absent from this PR #38 checkout and from the separately inspected PR #39 head. WP-UI1 is assigned to PR #34/`claude/project-thread-e53fle`; absence here means **not integrated into this branch**, not “never implemented.” Its code was therefore not functionally reviewed in this package.

Remaining organ limitations stay explicit: GGUF files and offline optimizer state are referenced/excluded, slot assets are metadata only, and generation commit plus B3 bridge filesystem replacement is not a single crash-atomic transaction. A broader crash-consistency/idle-exclusion audit is still needed before claiming complete per-organ recovery under interruption.

## Next implementation priorities

The latest ROADMAP is more current than historical BUILD_STATE narrative. It records STEP2 complementarity still failing, LP1 `LP1_NO_ATTRIBUTABLE_GAIN`, LP2 `LP2_ALIGNS_NO_GAIN`, adaptive effort `Z6A_EFFORT_ADAPTIVE_FAIL`, Age reopening FAIL, and dream policy-only `Z9_POLICY_DREAM_NO_GAIN` / `FACT_WRITE_CARRIES`. None is changed by recovery tests. Older “built”/PASS descriptions in ZIELABGLEICH and historical handoffs require reconciliation with subsequent replication results.

Continue the existing packages: finish the resumable WP-Z7 phone measurement package and its honest evidence verification; measure remaining STEP2 controls and capability utility; preregister WP-LP3 so output actually depends on the predicted state with matched controls; add genuine body training ports and retained body plasticity rather than substituting predictor or router training. Native runner/model prerequisites and actual Redmi measurements remain separate blockers. No new user decision is required for this scoped integrity repair.
