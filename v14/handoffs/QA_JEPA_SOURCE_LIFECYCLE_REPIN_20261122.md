# QA handoff — JEPA source-lifecycle pin and composer repair (2026-11-22)

## State

The QA branch includes the latest JEPA Run 14 base commit 50e3c8dfe2e270c0e7f6024f2fec64a1970a1f9b via a two-parent merge commit. Current code/test head: 49940d072e0b21afd9b39719c7472d6b41b97d6f. PR #2383 remains DRAFT / NOT_RELEASED.

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
- Current exact code/test head 49940d0: all 11 required checks were QUEUED at last poll; no green result is claimed.
- LOCAL_LINUX full Aii suite: BLOCKED / NOT_RUN because this execution environment has no Aii checkout and GitHub DNS/network is unavailable.
- Termux/Redmi: REDMI_UNVERIFIED. No device command, chat, native probe, update request or device mutation was issued.
- No model, weight, SQLite, chat, permission or installed-app state was changed.

## Other QA findings / independent blockers

- The two-checkout migration test had separately returned PARTIAL/ERROR at the earlier failing composer. The new diagnostic will identify whether another staged or startup edge remains after this repair.
- PR #2379 (Core one-shot MediaProjection provider) has a separate concrete integration mismatch: it calls Perception’s _issue_provider_frame_verifier with two arguments, while the current Perception API requires (lease, observation, verify_fn). QA posted the exact compatible call and required active-lease regression on #2379.
- PR #2379 also retains the previously reported P1 unbounded ContentProvider writer / stop-vs-openFile race; keep provider OFF until a cancellable pipe/read-lease and zeroization test passes.
- PR #2356’s Android process-restart emulator job failed in its failure-report path because failure_logcat() treated the string returned by run_adb() as a CompletedProcess and accessed .stdout. The actual STOPPED UI text was not observed before timeout, so the underlying stop/restart behavior remains unverified; fix the diagnostic crash first, then rerun the emulator test.

## Next action

Poll exact current-head CI. If staged startup passes but old-phone-to-new-runtime still fails, read the new bounded stage diagnostic and fix the next real edge. Keep PR DRAFT until all required exact-head checks and independent review pass. Do not update or claim a Redmi release from this branch.
