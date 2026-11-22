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
