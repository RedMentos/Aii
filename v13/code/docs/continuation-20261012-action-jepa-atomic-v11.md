# V13 Action-JEPA atomic restore review — 2026-10-12

Workbranch `assistant/evidence-streaming-20261012` / draft PR #2 only. No production native source or original preregistered evidence modified.

## What changed
Existing `scripts/action_jepa_delta_storage.py::restore` performs complete validation and then creates the destination directory and writes restored files one at a time. A late filesystem failure after directory creation can leave partial output visible at the destination, although the original validation before this step remains correct.

New isolated `scripts/action_jepa_delta_atomic_publish_candidate.py` wraps the existing `restore(base, archives, dest)` call by restoring into a private temporary directory and publishing it **only after the original verifier returns a success receipt**, via Linux `renameat2(RENAME_NOREPLACE)`. Unlike `os.rename`, this refuses replacement even of an existing empty target. On unsupported platforms it fails closed, requiring separate Android capability proof before integration. Removes private scratch on unsuccessful restore. No receiver authority or quality gate promoted.

## Actual tests
- 9 new synthetic publication tests PASS: successful atomic commit, mid-write crash, false receipt, empty/preexisting destination, symlink output, two concurrent competing writers, no delta and low-level rename failure.
- **65/65 focused tests PASS** in the standalone staged Python 3.13 Linux test layout and a separate older October 11 V13 code tree with these files overlaid.
- No actual recovered 1875-row NPZ restoration was run with this wrapper; the original report's closed real recovery exists separately and is not being reinterpreted as this candidate's test.
- The broader historical suite attempted earlier did not finish before timeout. Preserve that negative/uncompleted result.
- All original STEP2 UTILITY_FAIL, B3 L1 FAIL, SourceHandoff frozen 16-case preregistration and Dream2 2/15 remain pending unchanged.

## Persistent checkpoint
`V13_WORK_REVIEW_20261012_v11.zip`: SHA256 `0159c749d24b443bffccba3cd67bc40d719b822559fe1c86ed1cdc5eb207a24e`, includes all isolated candidate source/test files, focused logs, failed historical full-run and original packager failure log. Independently ZIP CRC + per-file SHA checked, saved under ChatGPT Library `/V13/`.

**Work review:** Before integrating, run against the actual pinned NPZ recovery artifacts, verify an Android/Termux renameat2 no-replace primitive or supply a separately proven equivalent, rerun full suite and compare original frozen registration and source hashes. Never claim this wrapper is active in the production runtime.
