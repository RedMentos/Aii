# Isolated V13 package reliability checkpoint — 2026-10-12 V10

**Review branch only:** `assistant/evidence-streaming-20261012` targeting `codex/authority-live-comparisons`, draft PR https://github.com/RedMentos/Aii/pull/2. The production packager, frozen SourceHandoff runtime and model gates are unchanged.

## New implementation and observed failure
- Added `scripts/package_source_streaming_candidate.py`: bounded 1 MiB stream-based checkpointing and verification instead of keeping a full in-memory `contents` dictionary and using `ZipFile.read` / `Path.read_bytes()` on arbitrarily large proof archives.
- Preserves the original `V13-Phone/` prefix and `WORKSPACE_FILES.json` schema; excludes known model caches, live SQLite/WAL, secrets and user data folders; rejects symlinks, corrupt source/path conditions and overwrite of existing checkpoint.
- The first packager negative test **FAILED**: deleting a source while rereading the finished ZIP was not caught. Preserved `packager-initial-failure-v9.log`. Candidate fixed with final inventory and source stat fingerprint recheck immediately before immutable publication. Retest **PASS**.
- 24 MiB synthetic closed proof packaged with a bounded Python heap; memory stress test PASS, not an Android measurement.

## Tests and historical source parity
- **56/56 focused CPU-only tests PASS** on Linux Python 3.13, in standalone staged test layout and again in a **historical October 11 V13 code snapshot** with all candidate modules and tests staged.
- Source selection parity against the historical baseline package_source filter: **505 original selected files, 505 candidate selected files, 0 added and 0 omitted**. Historical ZIP successfully saved: **506 archive entries including manifest**, 4,716,393 bytes, SHA-256 `be5e03c5964a137e0b1c79a4f3b83c4a19c91abd63dd7b499e8eab8b455d91a2`.
- Attempted broad historical `unittest discover` run but **did not complete within the bounded run**; its partial log is preserved, and no full-suite PASS is claimed. Two intermediate targeted setup attempts failed because the staged integration directory initially omitted one test and its script; after copying the exact missing files the complete focused **56/56 PASS** was verified. All failure and corrected-run logs are preserved.
- Earlier original STEP2 UTILITY_FAIL, B3 L1 FAIL, SourceHandoff 16-case native inference pending, NumPy seeds13/21/34 pending, Dream2 only 2/15 completed. No claim of learned utility, phone measurements or Canon completion.

## Checkpoint and Work review
- Combined source/tests/logs plus historical verified ZIP in local `V13_WORK_REVIEW_20261012_v10.zip`, SHA-256 `38b8120f299e819a82f2f1dd8c0cb4f12bc4ff73a6709a2e307dce785b695d7e`. Also mirrored under the user's persistent ChatGPT Library folder `/V13/`.
- Before touching authority: re-read current remote HEAD, `AGENTS.md`, `HANDOFF_CURRENT.md`, original Canon/roadmap. Review the new packer for compatibility with current 2026-10-12 source/proofs and real source archives; run full V13 package tests and real 12-part archived native proof audit. Do **not** merge automatically or modify frozen source.
