# QA handoff — vision source cleanup race rebase

Date: 2026-11-23
Role: QA & Android
Branch: `qa/v14-vision-cleanup-race-rebase-20261123-run17`
Parent: QA PR #2459, exact head `58646862436ba3f69bce81ef4d3710105fc7c12b`
Parent exact-head CI: 7/7 workflow runs SUCCESS (Lab Age migration, Lab Age control/WebView, RuntimeDeploy integrity, controller guard, private owner-read Python 3.14, JEPA optimizer-resume/source-forget Python 3.13/3.14, staged/integrated regression).

## Change

- Updated only the vision cleanup concurrency regression in `v13/code/tests/test_vision.py`.
- The old fixture patched `source_lifecycle_candidate._cleanup_pending_fd`, which is not the canonical blob unlink used by the current path.
- The test now pauses the exact canonical `os.unlink(name, dir_fd=...)` inside `source_lifecycle_candidate.cleanup_unreferenced`.
- It instruments the actual `Store.tx()` context for the re-ingest thread, separately recording transaction attempt and acquisition. While cleanup is paused, re-ingest must have attempted the transaction but must not have acquired it. After cleanup releases the Store lock, re-ingest must acquire it, publish a new live IMAGE source and recreate the exact SHA-verified blob.

## Why this is a stronger QA check

The regression no longer relies on a removed vision helper or on a sleep-only observation. It targets the current cleanup seam and observes the Store transaction boundary used by both cleanup and image ingestion. The post-race assertions still require the old source to be forgotten, the new source to be live, and the canonical blob bytes to match their SHA-256.

## Evidence boundary

- Parent #2459 exact-head CI: PASS, 7/7 workflows.
- This new PR exact-head CI: PENDING; no pass is claimed before its own run completes.
- LOCAL_LINUX full Aii suite: BLOCKED / NOT_RUN; no checkout is mounted in the execution environment.
- Redmi/Termux: REDMI_UNVERIFIED. No device access, model/weight change, user-data mutation or remote action was performed.
- No runtime behavior or model authority changed; this is a regression-test-only change.

## Next action

Run the exact PR-head Python 3.13/3.14 vision, staged/integrated, optimizer-resume and migration checks. Keep this PR stacked on #2459 until Boss integrates the pin-chain repair into #2443; then retarget the test PR to the updated Boss branch for the final integration gate.
