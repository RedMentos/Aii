# JEF/C3 local CLI I/O and cleanup hardening — preregistration (2026-10-31 UTC)

Owner: GPT-6 scheduled continuation, review-only child of PR #1411 at exact parent `18d0cb58d0ffcf63e1672c3d881df99a9509c7a5`. No production merge or change to the v10.16.1 Canon, original Run63/65 frozen cohorts, native pins, scorer or evidence. This preregistration is committed before code and tests.

## Problem and intended change
The default-OFF local operator CLI currently calls `Path.read_bytes()` before applying its 16 KiB input bound, so a huge untrusted local file may be fully allocated in memory on the target 6 GB phone. The cleanup `finally` block currently calls `pool.unload()` and `runtime.close()` in one `try`: an unload exception skips the Store close. Also a native result can retain `SHADOW_DRAFT_PREFLIGHT_READY` when its recorded native process release is not verified.

Implement strictly bounded streaming input (read at most MAX_INPUT_BYTES+1 before parsing), independent pool and Runtime close attempts, and native fail-closed result classification if the native process was called but its release is unverified. Preserve original synthetic successful SHADOW behavior and restart DRAFT->INTERRUPTED safety. No real TTY, output commit, tools, learning, native inference, or live Runtime router.

## Frozen acceptance tests
1. Oversize input rejected as INPUT_RED before Runtime creation, using a sparse file and a mock that rejects Path.read_bytes. Boundary exactly 16 KiB must still enter JSON validation rather than read all bytes.
2. Synthetic exact source-backed C5/F3 DRAFT and C6 read-only preflight still pass original 48 focused tests.
3. Inject pool.unload exception in synthetic run: Runtime.close must still execute; result is CLI_CLOSE_RED; no live output.
4. Pure software native-finalizer tests: missing, false, or incomplete process-reaped receipts downgrade otherwise-ready status to NATIVE_RELEASE_RED; verified receipt preserves READY. These are not actual native model tests.
5. Existing negative gates unchanged: Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, jepa_weight=0, World-JEPA SHADOW, Redmi unmeasured.

## Verification and persistence
Create a branch-scoped GitHub Actions workflow with pinned Canon and source blobs, focused regression tests, compile, public-repo privacy scan, diff check, closed raw logs, SHA256SUMS and artifact upload even on RED. Read back remote bytes and workflow results; do not claim a GREEN result until observed. If CI is unavailable, preserve RED/unknown and continue independent work.
