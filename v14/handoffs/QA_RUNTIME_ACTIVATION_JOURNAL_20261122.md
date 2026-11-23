# QA: crash-consistent runtime activation journal — 2026-11-22

**Branch:** `qa/v14-activation-journal-currentboss-20261122`  
**Base:** Boss integration candidate `d06c63794adc0ef802af9c7d91dc683d8a1057bf` (`boss/v14-recall-store-pin-rebind-20261122`)  
**Status:** DRAFT / BOSS_BASE_CI_GREEN / QA_REBASED_HEAD_CI_PENDING / PIPELINE_ROLLBACK_CLI_WIRED / NOT_RELEASED / REDMI_UNVERIFIED.

## Reproduced defect

Runtime deployment and rollback replace the launcher and `runtime-active.json` as separate atomic files. A process death between replacements can leave a mismatched pair. A Python exception handler cannot recover from SIGKILL, process death or power loss; the earlier path also did not reliably restore the marker after a post-replacement failure.

## Implementation candidate

- Added a durable owner-only `.runtime-activation.json` transaction journal with PREPARED, LAUNCHER_SWITCHED and COMMITTED phases.
- Atomic file replacement now fsyncs the file and parent directory.
- Deploy and rollback use the same pair-switch transaction. Recovery either recognizes a fully committed pair or restores the exact previous launcher/marker pair.
- Recovery validates schema, owner, mode, link count, backup names and hashes, and rejects unknown current launcher/marker bytes without overwriting them.
- Added a runtime-only rollback API/CLI, a pipeline-worker recovery hook, and an explicit `pipeline_agent rollback` action. It disables future auto-updates, takes the exclusive pipeline lock, stops only a managed V13 chat, and requests UI resume only after the launcher/marker rollback is confirmed. A failed/uncertain rollback leaves the chat stopped and auto-update OFF. Pending crash recovery runs only while stopped and through the existing enabled/manual update path; it does not turn auto-update on.
- Added process-death, tamper, directory-fsync, pending-journal, rollback and consent/busy-state regressions, plus pipeline rollback success, lock-busy, failure/no-resume and CLI dispatch tests.
- Preserved the current Boss base's exact stager SHA pin (`3c96d70126750500ba2a89c1785fb309e283f453fb55e96fed28abc905a6b9ee`) and removed a duplicate journal-constant declaration while rebasing.

## Verification boundary

- Boss base `d06c63794adc0ef802af9c7d91dc683d8a1057bf` exact-head CI: 17 required workflows PASS; 2 additive-only runs SKIPPED; 1 duplicate release-event run CANCELLED. The same-causal B1/B2→C4→C3 consumer passed on Python 3.13 and 3.14 (3 + 3 + 2 tests per interpreter); staged-runtime passed 252 tests / 10 skipped / 47 subtests; integrated-regression passed 424 tests / 3 skipped / 58 subtests; staged audio/arithmetic passed 52 tests / 26 subtests on each interpreter.
- Pre-rebase QA code head `e1864bfd986a6ff521f10d4e6e2e819322cce6d2` passed runtime-deploy integrity on Python 3.11 and 3.14: 14 activation-journal + 3 deploy-integrity + 31 runtime-deploy + 39 pipeline-agent tests per interpreter (87 total). It also passed owner-read, Lab-Age and two-checkout migration.
- Current rebased QA head adds 3 adversarial journal/backup symlink and unknown-marker tests and rebinds the deployer to the Boss base's exact stager SHA `f5f796a78c96568123e454a4ebd7cfa326b8cdd077c4220eb4fe52a96a17af6d`. Its final exact-head CI is still pending; the prior 87-test result does not include those 3 tests.
- The earlier staged failure on Core PR #2297 was the duplicate observer overlay after the audio builder reset Cognition. Boss d06c fixes the composition by applying audio to the incoming composed Cognition and failing closed if the fair-budget marker disappears; exact 3.13/3.14 same-turn tests pass. This is still synthetic, not a native phone receipt.
- This worker has no local Aii checkout; `git ls-remote` is blocked by GitHub DNS resolution. Full LOCAL_LINUX project tests are therefore BLOCKED. Exact-head GitHub CI must re-run the complete staged/integrated, Python 3.14 owner-read, Lab-Age, migration and runtime-deploy checks.
- No Redmi/Termux device receipt is available. No phone write, deploy, rollback, model/weight change, SQLite/chat mutation or permission change occurred: `REDMI_UNVERIFIED`.

## Remaining scope

- The dashboard rollback affordance is not wired yet; the explicit runtime-only pipeline CLI exists, but no WebView/dashboard rollback button or private-relay rollback command is exposed. The CLI requests UI resume only after a confirmed rollback; failures keep the chat stopped and auto-update OFF.
- Device-native process-death/reboot and rollback tests remain required before Android acceptance.
- The same-turn B1/B2 → C4 → C3 work remains synthetic until real model outputs and Redmi receipts prove delivery and semantic use.

## Next

Run exact-head CI on this rebased candidate. If green, ask Boss to compose it with the current integration branch, then add a UI rollback action only after the runtime API and lifecycle behavior are independently reviewed. No user action is required on current evidence.


## QA follow-up — failed activation recovery must not restart an unknown runtime (2026-11-22)

**Current QA branch head:** `6a97eca2881046aa646e0b5481863922dcdef6de`  
**PR:** #2298, still DRAFT / NOT_RELEASED. The branch is based on the Boss integration line at the d06c fork point; current Boss head is `91227b171f3e6c2251767f20cd494f34d6ec24fa`. Compare reports the QA branch and Boss head diverged by 9 QA commits / 1 Boss-only commit. Do not rebase until the Boss source-pin blocker is green.

### New reproduced integration defect and fix

The new pending-journal recovery hook could raise on a corrupt journal, unknown launcher/marker, missing backup or I/O failure after the managed chat had been stopped. The existing `run_cycle()` finally block would then request chat resume unconditionally. That could restart an unknown launcher/marker pair. This was introduced by the recovery hook in this candidate; ordinary staging/deploy failures with the previous verified pair still resume normally.

QA fix:
- `_do_update()` records recovery state before attempting recovery.
- If recovery raises, it records only the exception class, disables future automatic updates, and re-raises.
- `run_cycle()` suppresses resume only for failed/uncertain activation recovery and persists `resume_suppressed=ACTIVATION_RECOVERY_FAILED`.
- If auto-update disable itself fails, the private state records `DISABLE_FAILED`; the chat still remains stopped.
- The ordinary deploy-failure recovery path remains unchanged.

Regression added: `test_failed_activation_recovery_keeps_stopped_chat_and_disables_auto_update`.

### Exact-head CI readback for 6a97eca

- Runtime deployment integrity: **PASS** on Python 3.11 and 3.14. Each interpreter ran 17 activation-journal tests + 3 deploy-integrity tests + 31 runtime-deploy tests + 40 pipeline-agent tests = **91 passed**.
- Staged runtime: **PASS**, 252 passed / 10 skipped / 47 subtests.
- Integrated regression: **PASS**, 424 passed / 3 skipped / 58 subtests.
- Two-checkout migration: **PASS**.
- Lab-Age control: **PASS**.
- Private owner-read: **FAIL/BLOCKED by current composed source chain**, not the journal change. The exact staged Python 3.14 failure is `ValueError: context recall streaming source changed` at `integrated_context_recall_candidate_20261111.py:89`. The Boss head 91227 has the same shared source-pin blocker; the QA branch is not to rebind Core-owned generated-source pins.
- Same-turn C4/C3 consumer: **FAIL/BLOCKED by a base workflow syntax/continuation defect**. The current Boss version of `.github/workflows/v14-core-c4-c3-consumption.yml` omits a trailing `\\` after `test_observer_fair_budget_stage_20261116.py`; Actions then tries to execute `test_v14_store_source_blob_serialization.py` as a shell command and exits 126 / Permission denied. The preceding pytest command passes 3/3. QA reported this to Boss on PR #2288 (comment 7073144585); the QA branch does not edit the Core-owned workflow.
- Private bridge tests: **PASS**.

### Proof boundary and remaining actions

- Full local Aii checkout is unavailable in this worker because GitHub DNS resolution failed; full LOCAL_LINUX project execution remains **BLOCKED**, not passed.
- GitHub CI is not a Redmi test. No device connection or authorized private owner-read receipt was available. **REDMI_UNVERIFIED**; no installer, model, weight, permission, chat, SQLite or phone state was changed.
- Boss must first repair the shared source-stream pin chain and the missing workflow continuation, then rebase QA #2298 onto the resulting green exact base and rerun all checks.
- After base integration, the next device acceptance remains actual process-death/reboot recovery, update/rollback and managed chat stop/resume receipts on the Redmi.


## Follow-up — interrupted recovery is also fail-closed (2026-11-22)

QA head `aab911955280f7e9b7eb15b84f2c6d9fa22d6e2b` additionally catches `BaseException` around the recovery attempt, re-raises it after attempting to disable auto-update, and preserves the no-resume marker. This covers a local Ctrl-C/SystemExit during recovery as well as ordinary I/O/validation exceptions; a hard process kill still relies on the durable activation journal on next start.

Regression: `test_keyboard_interrupt_during_activation_recovery_keeps_chat_stopped`.

Exact-head runtime-deploy integrity: **PASS** on Python 3.11 and 3.14; 17 activation-journal + 3 deploy-integrity + 31 runtime-deploy + 41 pipeline-agent tests = **92 passed per interpreter**. Staged runtime, Lab-Age, two-checkout migration, owner-read and offline bridge tests are PASS on this merge ref. Remaining merge-queue blockers at this head:
- Python 3.14 staged startup: **FAIL** because `world_semantic_evidence_candidate.py` expected SHA `dba236187245eafad518d936e728c74f01746f7551345c418f7671c1dfd31e66`, actual `22594294c9b6bb8447b25ceaa0d9c7da129e29b9280880927141c0c8b549dd06`.
- Same-turn consumer Python 3.13: **FAIL** at shell line 4 trying to execute `test_v14_store_source_blob_serialization.py` (missing YAML continuation in the current base workflow).
- Same-turn consumer Python 3.14 and integrated regression were still running at this readback.
These are shared-base source/workflow issues, not failures in the QA rollback test suite. No rebase or merge until the full current base is green.


## Current Boss-base refresh — 2026-11-22

This section supersedes the stale d06c637 / 91227 base references above.

- Current Boss integration base: `d0d7baaa14fcf871f3eac647df8ce6718ed82a8e` on `boss/v14-recall-store-pin-rebind-20261122`.
- Exact Boss-head workflows: **16 SUCCESS, 1 expected SKIPPED, 0 FAIL**. This includes the corrected full-composer same-turn C4/C3 workflow, audio/arithmetic Runtime, staged/integrated regression, owner-read, migration, Lab-Age, deployment integrity, privacy and controller guard. This is CI/synthetic evidence, not a phone release.
- PR #2298 now targets that exact Boss head. GitHub reports the PR mergeable; the QA branch has not been rebased by force-push.
- QA branch head before this handoff update: `a09f0717ccf89d9dd24681fd609b0c9e78a1dddf`. The shared `V14_USER_NEXT_ACTION.md` and `V14_WORK_BOARD.json` were synchronized byte-for-byte from Boss d0d7ba so this QA PR cannot overwrite the newer shared status with its older snapshot.
- On that pre-handoff QA head, the new current-base workflow set was still queued/in progress: runtime-deploy integrity run `44981078044`; same-turn C4/C3 `44981078117`; owner-read `44981078196`; Lab-Age `44981078181`; staged/integrated `44981078139`. These results must be re-read on the final post-handoff commit; no pass is inferred from the earlier d06c637 runs.
- The prior QA implementation's runtime-deploy tests passed on Python 3.11 and 3.14 (92 tests per interpreter) on its earlier merge ref. The exact current-base result remains pending.
- Full local Aii checkout remains unavailable in this worker; no LOCAL_LINUX full-repository suite is claimed. No Android/Redmi receipt, installer, rollback, model/weight, permission, chat or SQLite mutation occurred. **REDMI_UNVERIFIED / NOT_RELEASED**.
- The private read-only V13READ request `RedMentos/Aiiii #460` has no authenticated device reply. No LOG_PAGE, UPDATE_REQUEST, shell or device mutation was attempted.
- Dashboard/WebView rollback remains unimplemented. The CLI/runtime-only rollback path is not a phone-verified UI action.

### Next QA action

Read exact-head checks for the final QA commit. If all required checks pass, request Boss integration review for #2298; retain the explicit distinction between runtime-only rollback and dashboard rollback. No user action is required on current evidence.
