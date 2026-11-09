# V13 context archive reader — 2026-11-09

Owner: GPT/Codex hourly11 (review-only, independent from #1644 and #1648).
Branch: `codex/v13-archive-read-bound-20261109-hourly11`.
Base: `codex/resume-20261106`.
PR: #1649.
Current head at handoff: `2b194be53c03c6d29e0700ec14a90afd86d1a364`.

## Scope and observed issue

`Store.blob_bytes` previously called `zlib.decompress(..., 64*1024*1024)`, making otherwise valid archived source blobs above 64 MiB unreadable. Source text is preserved on disk but cannot be restored through the existing SourceRef API. Context OS and source-linked long-term memory therefore need a bounded restoration path.

## Candidate

- New `v13/archive_blob.py`: compressed input streamed in 64 KiB chunks; decompressed output bounded at 128 MiB, with zlib EOF/trailing/corruption checks.
- `Store.blob_bytes` now uses the helper for archived blobs. Plain blob and caller-side SHA256 validation unchanged.
- New focused regression tests: >64 MiB roundtrip, exact limit, decompression bomb, truncated, garbage and trailing/concatenated streams.
- New focused CI workflow.

## Evidence and gates

Remote source readback succeeded for helper (blob SHA `7517663c766fd6b84c89e184a4ee298f11a5f3c1`); PR creation returned head `2b194be53c03c6d29e0700ec14a90afd86d1a364`. At handoff, workflow runs for this head were not visible; tests are **NOT yet verified GREEN**. No local exact-checkout test because this environment could not resolve github.com DNS. No native/Redmi experiment or full-suite run. No gate promotion. This is not proof of Context OS completion.

## Next exact commands

```sh
git fetch origin codex/v13-archive-read-bound-20261109-hourly11
git checkout --detach 2b194be53c03c6d29e0700ec14a90afd86d1a364
PYTHONPATH=v13/code python -m pytest -q v13/code/tests/test_archive_blob_bound_20261109.py
PYTHONPATH=v13/code python -m pytest -q v13/code/tests/test_dataset_probe_candidate_20261109.py
python v13/code/scripts/public_repo_privacy_scan.py --base origin/codex/resume-20261106 --head HEAD
```

Check latest Actions on #1649; fix any red before review. Review race/path-swap and total memory overhead, compare #1644 context design, and assess whether a streaming read_source API is required for sources >128 MiB. Preserve frozen registered experiment data, Age0 RECORD_ONLY and all original negative gates. No force push or overwrite of other owners.

## Local algorithm smoke check (separate from exact-checkout CI)

On Linux, a manually reconstructed copy of the new decompression helper passed: >64 MiB roundtrip; four malformed/trailing-stream rejections; decompression-bomb bound; exact-limit acceptance (7 checks). This is **not** a test of the exact GitHub checkout or integrated Store, and must not be represented as CI or Redmi evidence. GitHub workflow run lookup still returned no runs. Exact-checkout pytest and privacy scan remain required.
