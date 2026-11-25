# Research & Perception — run 25 handoff (2026-11-25)

## Scope and ownership

- Whole-system epic: [#1984](https://github.com/RedMentos/Aii/issues/1984).
- Active candidate: [PR #2484](https://github.com/RedMentos/Aii/pull/2484), branch `research-perception/v14-a3-source-stats-dirfd-create-20261124-run20`.
- Release base: `gpt6/v13-private-remote-bridge-20261111` at `8d93236c753f0194224c19edc7411d8d7082b1d6`.
- Code/test SHA: `1e10e7d92a9b5eb3d48d29689763dc5b04d9989b`. Documentation/board/workplan/coverage commit: `b64d4b916dabe062657b2f649613b26ef33b57c1`. Handoff-file commit at creation: `a1a70bfd6420d5960a9b5b4905725eabd4e3e0f3`; re-read PR #2484 for the current branch head before continuing.
- Run start/end instrumentation unavailable: UNKNOWN.
- No edits to V14 master, historical V13 appendix, release branch, Core-owned source-lifecycle composer, installed models/weights, permissions or user data.

## New executable code

Added a per-projector 32 MiB budget for A3 source-scoped fp64 sufficient-stat artifacts in `v13/code/v13/vision_projector_stats.py`. The estimate uses raw array byte counts plus 8 KiB per source for NPZ/NPY headers and metadata. If the complete set exceeds the budget, the helper returns `SOURCE_STATS_BUDGET_EXCEEDED` before creating/writing statistics files. Normal global and tile projector training remains available. A later source-forget sees that exact stats are unavailable and takes the existing conservative projector invalidation path; it does not claim an exact rebuild.

Changed files:

- `v13/code/v13/vision_projector_stats.py`
- `v13/code/tests/test_vision_projector_stats.py`
- `v13/code/tests/test_vision.py`
- `v14/V14_RESEARCH_LEDGER.md` (R-150)
- `v14/V14_WORK_BOARD.json`
- `v14/V14_USER_NEXT_ACTION.md`
- `v14/V14_LIVE_WORKPLAN.md`
- `v14/V14_CANON_COVERAGE_INDEX.md` (append-only evidence overlay)
- This handoff

## Exact code and test commits

- Helper budget code: `f1355ec1d639890f25ec7adcb0e079542327d711`.
- Helper tests: `2f6f21440d9e2227ed0d1b0dc18b96fb05767a97`.
- Runtime consumer test: `1e10e7d92a9b5eb3d48d29689763dc5b04d9989b`.
- Final documentation/handoff head: `b64d4b916dabe062657b2f649613b26ef33b57c1`.
- Exact source SHA-256 values from CI: `vision.py` `329bdacc068bf7059c87ef74425fbbfc9538ad85d494264c3f73cc89bb0c793d`; `vision_projector_stats.py` `bb987ff4b12f7c5622e3890a62a3afc145d82d7401f5a0518d9f04d2786ad10f`.

## Tests and environment

- GitHub Actions run `45551382106`: `tests/test_vision_projector_stats.py`, `tests/test_vision.py`, `tests/test_vision_source_lineage.py` plus exact `py_compile`: **58/58 PASS on CPython 3.13** and **58/58 PASS on CPython 3.14**.
- GitHub Actions run `45551381858`: RAW EYE / MediaProjection frame-ingress **PASS on Python 3.13 and 3.14**.
- GitHub Actions run `45551381910`: offline runtime-deployment integrity **PASS on Python 3.11 and 3.14**.
- GitHub Actions run `45551381822`: staged-runtime **FAIL** (19 failed / 234 passed / 10 skipped / 2 errors / 41 subtests); integrated-regression **FAIL** (1 test). Both stop at Core-owned `source_lifecycle_lock_integration_candidate.py:179` with `ValueError: unsupported lifecycle source: vision.py`.
- LOCAL_LINUX: CPython 3.13.5 / NumPy 2.3.5 formula+NPZ reproduction **PASS** for `d=37,c=768`, `d=117,c=768`, and `d=512,c=1024`; conservative estimates exceeded measured NPZ bytes.
- Full local Aii pytest/compile: **BLOCKED / NOT_RUN**; no checkout is mounted and local raw-GitHub download is unavailable.
- No Termux or Redmi execution occurred for this candidate.

## Cross-agent handoff

Comment `7153498421` on Core PR #2465 provides the exact current `vision.py` and `vision_projector_stats.py` hashes. Core/Integrator owns the immutable source-lifecycle composer and must rebind both files and include the new helper in the staged closure. Perception must not modify Core-owned composer files or weaken hash pins. After that rebind, rerun staged, integrated, consumer and two-checkout migration tests.

## Device and deployment

- Private V13OBS #115 snapshot at `2026-11-24T09:28:11Z`: base `8d93236` installed, auto-update enabled, Runtime/Dashboard UP_TO_DATE, last_error NONE.
- Fresh read-only relay requests #895 HEALTH, #896 PIPELINE_STATUS and #897 DIAGNOSTICS returned NO_LIVE_RECEIPT. No fresh health, native residency, learning or current-turn quality claim.
- PR #2484 is DRAFT / NOT_RELEASED / NOT_INSTALLED. GitHub push is not deployment. No UPDATE_REQUEST, model download/swap, runtime restart, permission change or data action.
- Redmi acceptance for PR #2484: **REDMI_UNVERIFIED**.

## Research — R-150

Full MobileMoE paper arXiv:2605.27358v1 and official MobileMoE-S-PTE model card reviewed. The PTE is 0.95 GB, projected INT4 weights 0.68 GB, 272M active / 1.3B total, 8k context, English text-only, ExecuTorch 1.6.0. Android runner needs custom NDK r28c, torchao INT4 and fused-MoE kernels; prebuilt Maven ExecuTorch lacks these. Only Galaxy S25 / iPhone flagship results are reported. FAIR Noncommercial Research License and gated HF account-information sharing apply. No download or code/weight reuse; not a production recommendation or a Redmi benchmark.

## Next action and user decision

1. Core/Integrator rebind the exact Perception source files and helper in the immutable source-lifecycle closure.
2. Rerun staged/integrated/consumer/migration on the composed candidate; do not issue an update request while those gates fail.
3. Continue the next independent A-plane / RAW EAR integration task and screen only candidates with a viable ARM64 runtime and compatible license.

**User action required: NONE.** No manual Termux command, model download/swap, permission change or device action is needed.
