# JEPA & Memory — Run 15 rollback integrity checkpoint (2026-11-23)

## Branch and scope
- Working branch: `jepa-memory/v14-temporal-boss-2443-rebase-20261123-run14`
- Parent PR: #2443 (Boss integration); this JEPA branch remains stacked on the earlier parent snapshot until the combined Boss candidate is green.
- Prior JEPA head before this checkpoint: `bc9eaea5661c0af08de4b85bdec3ab40ec433681`.
- Release-development base remains `8d93236c753f0194224c19edc7411d8d7082b1d6`; the phone receipt confirms that base, not this candidate.

## Implemented code change
- `v13/code/v13/world_jepa_temporal.py`: `rollback()` now loads and verifies the previous checkpoint (safe path, source digest, checkpoint digest) before publishing the rollback state pointer. A missing or corrupt fallback therefore cannot replace a valid active checkpoint and cause pruning of the only usable model.
- After a successful rollback, all same-Store temporal warm caches are invalidated and the invoking consumer is warmed from the verified restored model. This avoids leaving B1/B2's optional warm-only reader pointed at the rolled-back-away checkpoint.
- `v13/code/tests/test_v14_world_jepa_temporal_runtime.py`: the positive two-checkpoint rollback/restart test now asserts warm-cache identity before and after rollback. A parameterized missing/corrupt previous-checkpoint regression asserts that the state version and active checkpoint remain unchanged and the valid current checkpoint is not pruned.

## Verification boundary
- Exact project tests were **not run locally**: this execution environment has CPython 3.13.5, NumPy 2.3.5 and pytest 9.0.0, but no Aii checkout; GitHub DNS resolution from the local container fails. No project compile or pytest result is claimed.
- The new temporal workflow is present on the stacked feature branch, but its exact-head run has not been observed. The PR currently targets the Boss integration branch, while the release-branch staged workflows are configured for the release branch; treat CI as **BLOCKED / NOT_VERIFIED** until the parent integration is green and the stack is rebased onto that exact head.
- Redmi: **REDMI_UNVERIFIED for this candidate**. Latest authenticated private receipt #840/#841/#842 says installed `8d93236c753f0194224c19edc7411d8d7082b1d6`, auto-update enabled, AI runtime `STOPPED_BY_USER`, autostart false, model process stopped. Preserve the stop state; no update request, restart, chat, shell or model/permission mutation was made.

## Research intake for ledger sync — R-115 candidate
Nishit Anand, Ramani Duraiswami and Dinesh Manocha, “What Should World Models Forget? Stratified Retention for Continual Adaptation,” arXiv:2610.03713v2 (2026-11-12), NeurIPS 2026 Workshop: Continual World Models. Full PDF reviewed: https://borowiecki.dev/pdf/2610.03713 ; arXiv record: https://arxiv.org/abs/2610.03713 .

The paper argues that world-model retention must separate invariant knowledge from revisable facts. Its proposed differential-retention protocol reports (1) invariant retention after each adaptation round and (2) revision latency—the observations required to update a changed fact. It is a framing/evaluation proposal, not an experimental method with validated V14 thresholds. Its key warning applies to V14's single blanket old-cohort retention gate: an obsolete state should not be protected as if it were a physical/provenance invariant.

Testable V14 adaptation (not yet implemented): label holdouts by evidence timescale. Keep source provenance, action/permission protocol and validated structural constraints in the invariant probe set; treat volatile environment/instance outcomes as revisable only after repeated, source-disjoint evidence. Report invariant violations and revision latency separately. Keep user-requested source deletion separate from obsolescence (forgetting a source is not concept drift). Compare the current blanket gate with the stratified gate on matched A→B→A shifts, one-off-noise negatives and change-point delays. No code or model weights reused.

## Next executable work
1. Rebase the temporal/episodic stack onto the exact green Boss integration head after its full combined staged, integrated, optimizer-resume, migration, privacy and deployment matrix is complete; do not force-push.
2. Recompute JEPA-owned nested pins from read-back bytes; leave Core stage/deployer ownership with Core.
3. Run the exact temporal + postcommit suites on Python 3.13 and 3.14, then staged/integrated and source-forget/forget-race regressions. Record any retention veto as a valid negative result.
4. Complete the production ActionSelection context SourceRef producer with Core; keep retrieval and B1/B2 adapters SHADOW until real consumer utility and retention are measured.

## Decisions and authority
- Learning/optimizer permissions remain OFF by default. No device action, native GGUF/body-weight update, B3 latent promotion, model swap or release is authorized by this commit.
- No user action is required for this code work.


## Collaboration API limitation

GitHub PR conversation comments and PR metadata updates returned HTTP 403 because the linked GitHub account has no verified email. Contents-API file commits and exact readbacks succeeded. No comment was posted and the PR description could not be refreshed; the authoritative run-15 status is therefore in this handoff, the branch's Board/Next Action/Workplan/Research Ledger/Canon overlay, and the code commit itself. Optional account email verification would restore those discussion/metadata writes; no user/device action is required for the code candidate.


## Exact branch readback after shared-document sync

- JEPA branch head before this final Board refresh: `83475a095072afdd7611f0a5bf2ce60cde97b005`; code-bearing fix is `f56e7067e6f2df5900231324dd5b2d55ea277477` (source commit `3122e30830a94848f4ffe17fb55146d8c5a614d0`); handoff file commit is `05ec1f4527860960677bda93d7736ad0c1a289a1`. The branch is 18 commits ahead / 47 behind Boss #2443 head `cdf6b64067ac426ba32194100d3764f6e74c105f`, merge base `6e9bad8daa9ad9ec97947639600f6c7cdbffb6d4`.
- Core native-probe PR #2457 head `f8d0427` is 10 ahead / 14 behind the JEPA branch, merge base `bf2913b150d8decbf6e33c43920d21acc83439b3`. Do not refresh its stage/deployer pins until the parent and JEPA exact-head matrices are green.
- Exact JEPA code-head CI remains zero runs / zero combined statuses. Boss #2443 combined candidate remains unverified; its child QA results do not substitute for combined-head proof.


## Exact commit roles

- Source fix: `3122e30830a94848f4ffe17fb55146d8c5a614d0`.
- Test update: `f56e7067e6f2df5900231324dd5b2d55ea277477`; this is the code/test checkpoint containing both the source fix and regression tests.
- Initial handoff-file commit: `05ec1f4527860960677bda93d7736ad0c1a289a1` (documentation only). Subsequent commits update Next Action, Board, Workplan, Research Ledger and Canon overlay; none changes the code-bearing checkpoint.
