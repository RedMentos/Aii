# QA handoff — JEPA source-lifecycle pin and composer repair (2026-11-22)

## State

The QA branch includes the latest JEPA Run 14 base commit 50e3c8dfe2e270c0e7f6024f2fec64a1970a1f9b via a two-parent merge commit. Current code/test head: 4fc02a69b7ca4cb1d4686da0c8622d2ef2e236b9. PR #2383 remains DRAFT / NOT_RELEASED.

## Reproduced exact-head failures

1. Previous code/test head 71df3dc86017bd05b5f56f4ee06f00461801a594 failed the optimizer-resume and staged/integrated jobs at two downstream pins:
   - Termux recovery expected training-builder SHA-256 27fe2305..., actual 6a72d48d...
   - Integrated stage expected Termux wrapper SHA-256 c6c6bed3..., actual d6ca01fe...
   The stager raised integrated builder hash mismatch.
2. After repairing that chain, exact head ff8ecf3306a43b241fabda67c3ed51ce4a485813 failed Python 3.14 staged startup and Lab Age E2E at:
   ValueError: ambiguous lifecycle candidate anchor: memory.py
   Root cause: JEPA Run 14 had rewritten Memory._forget_source to add combined_source_forget_guard and Store RLock ordering, so the lifecycle composer’s old MEMORY_OLD text no longer existed. The composer rejected it rather than silently applying a partial patch. This was a real integration defect, not a test-only mismatch.

## Implemented repair

- Updated MEMORY_OLD to match the current JEPA-protected Memory._forget_source block exactly.
- The replacement changes only the old direct blob unlink to source_lifecycle_candidate.cleanup_unreferenced(self.s, sid). It preserves combined_source_forget_guard, the Store RLock, transactional tombstoning, dependent packet cleanup and final logging.
- Added a regression that calls the lifecycle composer and asserts the generated memory.py retains the temporal JEPA forget guard, Store mutex and cleanup_unreferenced call.
- Added a sanitized staged diagnostic to the two-checkout migration test. It reports only the stage/selftest phase, exception class and bounded fixed error text in the synthetic test environment.
- Extended the existing chain test to assert runtime_deploy.STAGER_SHA256 matches stage_integrated_candidate.py.

## Verified readback chain on current code/test head

- memory.py SHA-256: 33377446f8dca709c0d829764dac6e1d4f1ca92729b955d8a8ad983a16bb1701.
- source-lifecycle composer SHA-256: 2cc23c1bd1af6188d161491a216556d8878a8a48f57ae4684aa2b40d7968edea.
- memory/world builder SHA-256: 3ee6e434e27df730fbd015a7adc943b861cf0d9092401ca15a6036b94c82e24a.
- feedback builder SHA-256: f23b16e28cb9e9494ee5bb0e5a718d310549cd49bac81f43c69c501f9236e54f.
- context-recall builder SHA-256: 8a70434e8b4a5fdbab62696f28de02f0e745afb002c693cf4026b9386930e154.
- World-JEPA training-resume builder SHA-256: 8312c317b4aee82f4fc97bf3bd6c0a5cd8f52f380b01c25ae37a74b25ac43843.
- Termux recovery-12 Git blob SHA-1: dae6474bb5f1a4c5cbc5663d701fb57362b9bb15; its training-resume SHA pin matches 8312c317...
- Termux recovery-21 SHA-256: 5a6d270c5e73ff6cd44bd8d479d30a927dd35b90a49f1fca75ba1204552bbdba; its base blob pin matches dae6474...
- Integrated stage SHA-256: 8a03b78fd381ef156785d800671bc9f957ea0dddc811fff188f83bcb1d5c98d9; its builder pin matches 5a6d270c...
- runtime_deploy.STAGER_SHA256 matches the integrated-stage digest 8a03b78f...
- All nine source files were fetched back from the current branch and their content digests / Git blob IDs recomputed; every adjacent pin matched.

## Verification boundary

- Exact prior CI head 71df3dc: FAIL on two stale downstream pins.
- Exact prior CI head ff8ecf3: FAIL on the now-fixed missing MEMORY_OLD anchor in Python 3.14 staged startup and Lab Age E2E.
- Exact code/test head 49940d0 failed the old-phone-to-new-runtime job with the stage-builder mismatch; the 4fc02a6 head adds the exact exported-digest diagnostic. All 11 required checks on 4fc02a6 were QUEUED at last poll; no green result is claimed.
- LOCAL_LINUX full Aii suite: BLOCKED / NOT_RUN because this execution environment has no Aii checkout and GitHub DNS/network is unavailable.
- Termux/Redmi: REDMI_UNVERIFIED. No device command, chat, native probe, update request or device mutation was issued.
- No model, weight, SQLite, chat, permission or installed-app state was changed.

## Last completed Redmi receipt available before this run

Consented private owner-read evidence timestamped 2026-11-22 21:35 Europe/Berlin (read-only; no new device command was issued):
- Pipeline auto-update enabled; runtime/dashboard UP_TO_DATE; last_error NONE; installed commit aed1d2b826290c95c70356b5d8b864b5ef382be4.
- Service/model process reported RUNNING, but the instantaneous native-residency sample mapped 0 native processes (PSS/RSS 0; child-group readability UNKNOWN).
- Last turn FINAL in 57.74 s, C3 TTFT 41.63 s, prompt 751 tokens, only 2 generated tokens.
- B1_DETAIL 53.2 s TIME_BUDGET; B2_GIST 54.2 s TIME_BUDGET; no valid source-bound offers; C3 3.1 s OK; native probe SMOKE_PARTIAL.
- Resource snapshot: 5,569 MiB RAM total, 1,494 MiB available, 1,291 MiB free disk.
- Lab test selector was active at stage 10, but official stage remained 0; physical feature execution was unverified and learning commit authority required separate SHADOW mode.

This is a timestamped failure snapshot, not a current live claim and not acceptance. The candidate branches in this handoff are not installed on Redmi. Public technical summary was added to #1904 and linked from #1984 without copying any private transcript or user input.

## Other QA findings / independent blockers

- After the composer repair, the two-checkout migration test still returned PARTIAL/ERROR on exact head 49940d0. The bounded diagnostic identified the next failure as RuntimeDeployError: “Integrated stage builder changed”. The exact-head 4fc02a6 test now exports the commit’s Git blobs independently and prints the expected STAGER_SHA256, actual exported SHA-256, Git blob ID and deployer module name before the stage attempt; this will distinguish a stale pin from an export/path mismatch.
- PR #2379 (Core one-shot MediaProjection provider) has a separate concrete integration mismatch: it calls Perception’s _issue_provider_frame_verifier with two arguments, while the current Perception API requires (lease, observation, verify_fn). QA posted the exact compatible call and required active-lease regression on #2379.
- PR #2379 also retains the previously reported P1 unbounded ContentProvider writer / stop-vs-openFile race; keep provider OFF until a cancellable pipe/read-lease and zeroization test passes.
- PR #2356’s Android process-restart emulator job failed in its failure-report path because failure_logcat() treated the string returned by run_adb() as a CompletedProcess and accessed .stdout. The actual STOPPED UI text was not observed before timeout, so the underlying stop/restart behavior remains unverified; fix the diagnostic crash first, then rerun the emulator test.
- PR #2356 follow-up fixed that diagnostic crash on branch qa/v14-companion-final-qa-20261122: failure_logcat now filters the string returned by adb(), and two unit regressions cover filtered/empty logcat output. Current exact branch head 3833e155dd7a93486444076230c980b674686b30 has all eight required workflows queued; the next emulator run must still prove the full persisted OFF/ON/force-stop/restart sequence.
- PR #2375 Perception frame ingress has a new exact-head CI failure on f87ebac407a19c147da7eb52bc63f10e9eed25d2: Python 3.13 and 3.14 both report 11 failed / 7 passed because consume_projected_frame calls an undefined _summary(observation). Two more failing zeroization assertions occur before the consumer is entered, when the test provider-verifier factory rejects an invalid lease/observation; the wrapper needs to erase the mutable buffer on factory failure. QA posted exact root causes and a bounded metadata-only summary recommendation on #2375. Keep the adapter DRAFT until the frame tests pass.
- QA opened stacked PR #2384 on #2375 from branch qa/v14-perception-ingress-fix-20261122. It imports the existing A5 content-free _summary helper, zeroes the test/provider-owned bytearray if verifier issuance rejects before adapter entry, and adds an exact metadata-only summary regression. PR #2384 is DRAFT; five exact-head workflows were queued at last poll. No real MediaProjection provider is added.
- PR #2377 native-probe approval QA branch now includes O_NONBLOCK with O_NOFOLLOW before fstat, a bounded FIFO subprocess negative test, and workflow triggers for Core PR #2381. Current code/test head 45f08a3c0da564f12cdddef89f99fde245657d61; seven exact-head checks were queued at last poll. The path-based TOCTOU remains unresolved and B3 stays OFF.

## Next action

Poll exact current-head CI. Poll exact 4fc02a6 CI and read V13_STAGE_PIN_DIAGNOSTIC. If expected and actual differ, correct the real pin or export path; if they match, trace why runtime_deploy loaded a different stager. Then rerun staged Python 3.14, optimizer resume and two-checkout migration. Keep PR DRAFT until all required exact-head checks and independent review pass. Do not update or claim a Redmi release from this branch.
