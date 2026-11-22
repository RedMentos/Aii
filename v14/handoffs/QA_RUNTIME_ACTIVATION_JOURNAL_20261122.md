# QA: crash-consistent runtime activation journal — 2026-11-22

**Branch:** `qa/v14-activation-journal-currentboss-20261122`  
**Base:** Boss integration candidate `70c04e2a6df21e719bfdf28ab0f3c9f1c6822a39` (`boss/v14-recall-store-pin-rebind-20261122`)  
**Status:** DRAFT / EXACT_HEAD_CI_PENDING / PIPELINE_ROLLBACK_CLI_WIRED / NOT_RELEASED / REDMI_UNVERIFIED.

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

- The Boss base `70c04e2a6df21e719bfdf28ab0f3c9f1c6822a39` had 13 exact-head GitHub workflow runs completed successfully before this QA rebase (the additive-only validator was skipped and the release-event integrator was cancelled as expected).
- Previous isolated runtime-deploy integrity run `44971421509` passed on Python 3.11 and 3.14 with 43 tests per interpreter. That is evidence for the prior code head only, not this rebased head.
- Previous full staged/migration runs on the stale base failed at Boss source-pin composition. Those failures are not attributed to this QA change.
- This worker has no local Aii checkout; `git ls-remote` is blocked by GitHub DNS resolution. Full LOCAL_LINUX project tests are therefore BLOCKED. Exact-head GitHub CI must re-run the complete staged/integrated, Python 3.14 owner-read, Lab-Age, migration and runtime-deploy checks.
- No Redmi/Termux device receipt is available. No phone write, deploy, rollback, model/weight change, SQLite/chat mutation or permission change occurred: `REDMI_UNVERIFIED`.

## Remaining scope

- The dashboard rollback affordance is not wired yet; the explicit runtime-only pipeline CLI exists, but no WebView/dashboard rollback button or private-relay rollback command is exposed.
- Device-native process-death/reboot and rollback tests remain required before Android acceptance.
- The same-turn B1/B2 → C4 → C3 work remains synthetic until real model outputs and Redmi receipts prove delivery and semantic use.

## Next

Run exact-head CI on this rebased candidate. If green, ask Boss to compose it with the current integration branch, then add a UI rollback action only after the runtime API and lifecycle behavior are independently reviewed. No user action is required on current evidence.
