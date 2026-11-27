# JEPA & Memory — Run 11 release-base handoff (2026-11-23)

## Checkpoint

- Base: gpt6/v13-private-remote-bridge-20261111 at 4dc7595f383e7ba932ee8e9fcf52c5541210ed5e
- Branch: jepa-memory/v14-base-jepa-safe-forget-replay-20261123-run11
- PR: https://github.com/RedMentos/Aii/pull/2429 (DRAFT / NOT_RELEASED)
- Latest branch head at this handoff update: 32837cc647476b222b5792d62887c0aa33098740
- Code blob: 26f7d2eec3799689fdea7afeebd9b59150a8f138
- Test blob: a8c078d10ca4eadbfb9fbd87a8c63b8e8dac65a8
- Run start/end timestamps: UNKNOWN (no wall-clock execution trace exposed by the runtime).

## Implemented path

Changed only:
- v13/code/v13/world_jepa_consumer.py
- v13/code/tests/test_v14_world_jepa_runtime_port.py

The existing Memory._forget_source already calls source_forget_guard; the change is therefore on the actual Memory → WorldJEPA checkpoint consumer path.

The guard now:
1. Checks retained experience_rows and eligible T8 action history up to each checkpoint's own scan cursor. Pending-only action IDs are excluded from the trained-influence check.
2. Fails closed when the source-history scan exceeds the tracked bound.
3. If active is tainted and previous is clean, hash-loads the clean previous checkpoint, restores it, rewinds to its cursor, and clears pending rows so SQLite replay rediscovers all later transitions.
4. If active and previous are both tainted, invalidates both, clears pending rows and resets scan cursor to zero.
5. If only previous is tainted, keeps the verified active checkpoint and drops the tainted rollback pointer.
6. Prunes unreferenced checkpoint files and refuses source deletion if an orphan or symlink remains.

This is direct-source checkpoint rollback plus source-verified replay. It is NOT gradient-based unlearning, native GGUF weight editing, or a guarantee against semantically similar behavior being relearned from correlated retained data.

## Test evidence

### LOCAL_LINUX

- Container repository access: git ls-remote https://github.com/RedMentos/Aii.git failed because github.com did not resolve; no full Aii checkout was available.
- Isolated Python syntax compile of the new guard: PASS.
- Isolated fake-Store state/cleanup matrix: PASS for 4 cases:
  - active tainted / previous clean → restore previous + rewind;
  - both tainted → clear both + reset cursor;
  - previous-only tainted → drop rollback only;
  - pending-only source → remove pending row without invalidating checkpoints.
- The first isolated run had a fixture error in the previous-only case (its fake active cursor incorrectly included the source); the fixture was corrected and all four cases passed. This is not a repository test result.

### GitHub Actions exact head

First run on initial PR head a89bd88c7de0b36d32c721df470bab3a968e6fc8:
- optimizer-resume / source-forget Python 3.13 and 3.14: FAIL.
- The source-forget step ran 20 staged optimizer-resume tests, 14 additional tests and 1 smoke test successfully, then failed 3 pre-existing tests that still expected the old guard to raise ValueError. The implementation intentionally changes those expectations to safe rollback/replay.
- The three old tests were updated to assert deletion + checkpoint invalidation. Two integration cases were added for clean-previous rollback/replay and both-tainted reset/replay.
- Run 45145241673 on code/test head 395067061cb776f10ad833ae804f0ebd10ced08f: FAIL on both Python versions with one NameError in the new both-tainted test (the test assigned first_events but later referenced first_actions). The other 7 selected source-forget tests passed on both Python versions.
- Test fixture corrected in commit 32837cc647476b222b5792d62887c0aa33098740.
- Exact workflow readback for 32837cc had not appeared at the time of this handoff update; no exact-head PASS is claimed.
- Staged context/integrated run 45145241722 was still IN_PROGRESS at the previous poll.

## Current installed-device evidence (private, read-only)

Private RedMentos/Aiiii V13OBS issue #115 was updated 2026-11-23T09:02:03Z:
- Installed runtime SHA: 4dc7595f383e7ba932ee8e9fcf52c5541210ed5e (matches the release base, not this PR).
- Auto-update enabled; Runtime and Dashboard report UPDATED / UP_TO_DATE; no pipeline error.
- Last observed turn: 57.74 s total; 41.63 s TTFT / 38.95 s prefill; 751 prompt tokens; 2 generated C3 tokens.
- B1/B2 probes still TIME_BUDGET (53.2 / 54.2 s); zero valid offers in the reported sample; native latent exchange not proven.
- Native residency reports zero mapped native processes, with child-group readability unknown.
- No new turn, UPDATE_REQUEST, permission change, model swap, or device-side action was sent.

PR #2429 is therefore REDMI_UNVERIFIED; the installed device is still on its parent SHA.

## Canon / user effect

- Canon family: Memory source deletion; WorldJEPA/EMA checkpoint persistence; replay/retention; rollback; B1/B2 numeric shadow readouts.
- If Boss/QA integrate this PR, a direct source that influenced the current numeric WorldJEPA checkpoint should no longer force Memory forget to refuse. The learner will restore a clean prior checkpoint or rebuild from the remaining source-verified T8 history.
- No change to Age, learning permissions, native B1/B2 GGUF files, user model files, updater, or Android capabilities.
- No claim of trained native latent coupling or B1/B2 body-weight learning.

## Remaining critical gap: derived-source lineage

On release HEAD, v13/code/v13/focal.py ActionGate.select still commits ActionSelection with provenance [e['source_ref']] only. It does not persist the complete set of Memory/history/observer/Enlightened-Space sources actually admitted to the selected action.

Therefore this PR only handles the event's direct source. It cannot yet invalidate every trajectory influenced by a recalled or observer-derived source. The Core producer must attach a bounded complete source-ref set before ActionSelection commit; JEPA must validate every ref against Store source/hash/span and persist the full dependency set in T8 rows, replay state and checkpoints. Forgetting any member must then invalidate/rebuild every dependent checkpoint. This was also reported to PR #2426; no Core-owned files were changed here.

## Research note for the shared ledger (proposed R-081; not yet appended)

- Xu et al., “Unlearning Isn’t Deletion: Investigating Reversibility of Machine Unlearning in LLMs”, ICML 2026 / PMLR 306, pp. 142657–142704: task-level accuracy/perplexity can hide reversible suppression; the paper studies PCA similarity/shift, CKA and Fisher information and shows recovery can occur after limited fine-tuning. Source: https://proceedings.mlr.press/v306/xu26cd.html
- Siddiqui et al., “From Dormant to Deleted: Tamper-Resistant Unlearning Through Weight-Space Regularization”, NeurIPS 2025: retain-only fine-tuning can restore forget-set behavior in their vision setting. Source: https://proceedings.neurips.cc/paper_files/paper/2025/hash/bbeafbaa60ee03f2c3135be71ebd5d06-Abstract-Conference.html
- Wu et al., “Lethe: Principled Dual-Stream Update for Persistent Knowledge Erasure in Federated Unlearning”, arXiv:2601.22601v4 (2026-10-04): explicitly studies knowledge resurfacing during continued training. Federated setting differs; treat as a hypothesis source, not a direct V14 recipe. Source: https://arxiv.org/abs/2601.22601
- V14 adaptation: after the direct-source rollback/replay path passes, add a retain-only continuation probe and compare it with a clean-from-history retrain. Track both task outcomes and representation drift. Keep correlated-data relearning distinct from direct-source re-entry. No paper code or weights were reused.

## Next executable actions

1. Read exact-head CI for 3950670; repair failures and rerun both Python 3.13/3.14 source-forget and staged/integrated checks.
2. Ask Boss/QA to review and compose PR #2429 on a fresh release-derived integration branch; do not merge or deploy from this draft.
3. Coordinate the missing complete ActionSelection context-source producer with Core, then extend JEPA proof/checkpoint lineage and add source-A→derived-B forget/replay regression.
4. Add retain-only relearning/representation probes before claiming durable semantic unlearning.
5. Keep installed Redmi SHA and all native/latent claims unchanged until a separately authorized update and private device receipt prove otherwise.
