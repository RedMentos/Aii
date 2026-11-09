# V13 streamed SourceRef checkpoint — 2026-11-09

Owner: GPT/Codex hourly11. Review-only PR #1650, branch `codex/v13-source-slice-stream-20261109-hourly11`, based on draft #1649 head `6f4e3178b3d314f89f0683bc7d5a2b030a7f7120`. Do not overwrite #1649/#1644 or unrelated worker files.

## Executable package
- `source_slice.verified_source_slice`: bounded 128 MiB stream of plain or zlib source; incremental UTF-8; SHA-256 of **entire** content before returning selected character span; reject invalid range, invalid UTF-8, corrupt/truncated/trailing archive and oversize.
- `Store.read_source` now uses the stream path for archived and plain source, avoiding whole-blob materialization for short SourceRefs. Existing `blob_bytes` retained.
- Tests cover Unicode across 64 KiB boundary, Store archived source, full-hash rejection, trailing bytes, limits/ranges; CI workflow added.

## Evidence / limits
GitHub connector created and read metadata for PR #1650, head `cd8f48d4179bfda88dc7748d60a7fd5be225f18f` at PR creation. Parent archive workflow `42660606591` succeeded on #1649 head `6f4e3178` (9 tests). New head's archive workflow `42671655735` queued at last check; new streaming workflow status unverified. **No claim of green CI for #1650**, exact local checkout, Redmi execution, AGI, B3/JEPA promotion or model-weight updates.

## Next exact commands
```sh
git fetch origin codex/v13-source-slice-stream-20261109-hourly11
git checkout --detach cd8f48d4179bfda88dc7748d60a7fd5be225f18f
PYTHONPATH=v13/code python -m pytest -q v13/code/tests/test_source_slice_stream_20261109.py v13/code/tests/test_archive_blob_bound_20261109.py
python v13/code/scripts/public_repo_privacy_scan.py --base origin/codex/v13-archive-read-bound-20261109-hourly11 --head HEAD
```
Check latest PR head/CI, correct failures, run relevant existing SourceRef/Context tests. Review source path swap and UTF-8 decoder boundary behavior. Reconcile #1644 and other owners before integration. Next independent critical path: B1/B2 parameter training/retention and JEPA runtime integration, not more archive-only polishing. All original negative gates unchanged.
