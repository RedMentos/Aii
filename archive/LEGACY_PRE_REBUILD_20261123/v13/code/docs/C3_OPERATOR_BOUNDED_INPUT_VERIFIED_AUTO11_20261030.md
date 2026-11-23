# C3 operator bounded input + original native error preservation — verified 2026-10-30

Review-only child of #1228 at `f9625470aa1ee67ea4356d36a3be8d16a84835e7`. Separate native PR #1229's original pinned source and model are unchanged; this package is software-only. Canon v10.16.1, Age0 and all negative gates unchanged.

## Fix
Before: `Path.is_file()` followed symlinks and `Path.read_bytes()` loaded entire untrusted file before enforcing the 2,000-char/16,384-byte cap. On the Redmi 6-GB floor this could waste arbitrary RAM, and a symlink could redirect the input. Also an unverified raw receipt's original native `error_type` was overwritten by the quarantine reason.

Now: open with `O_NOFOLLOW` and `O_NONBLOCK` where supported, require `fstat` regular file, reject oversized `st_size` before reading, read at most `max_bytes+1`, recheck actual byte count and UTF-8; reject symlinks and special files. Native quarantine still refuses unverified raw, but retains `native_reported_error_type` separately. The original exact UTF-8 source hashing, 0600 exclusive report, replay/native separation and all negative gates remain. Source blob `6f698ef12377b2e92d7c801e80e2648ca8aea78c`.

## Closed raw
- Test-only RED Actions **41021387548** exact HEAD `4ee286c82945b6aee9c0d5d2ac5796cda270e3b4`, artifact **12961940643**, ZIP SHA256 `159d9bff4ee2ea617be0d50d6a9ddde480c6cca5d97f7aa83fade5a177f2f127`, CRC clean 13/13 inner hashes. 31 tests, **3 expected failures + 1 error** (symlink accepted, unbounded read, missing original error field), existing 26 passed.
- Candidate GREEN Actions **41021490375**, exact tested HEAD `49b5a5cbc30c3239e48718b36abc98868d2d345f`, artifact **12961394299**, ZIP SHA256 `84eb00d155518f3659a3ddbb818efd50c8674c72805cdc16898cda45daa6043b`, CRC clean 13/13 hashes, **31/31 PASS**, all six VENV/DEPS/TEST/COMPILE/PRIVACY/DIFF exits0. No model/native/Redmi run.
- Both original ZIPs privately uploaded to `/V13-Checkpoints/2026-10-30/Run11-C3-Operator-Receipt/` and re-materialized byte-identical SHA256. Rejected anyone-writable Drive destination not used.

## Status and continuation
Review-only source/test/CI; no production merge. Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, jepa_weight=0, Redmi UNMEASURED, whole-system INCOMPLETE. The separate actual Linux-native PR #1229 is **semantic RED**: correct process FINAL/reaped, wrong C3 typed read, fail-closed abstention; never reclassify as software GREEN or utility.

Next highest-priority independent substantive work: preregister a disjoint C3 typed-value extraction study with a deterministic no-model baseline and unchanged model, then assess native typed-read accuracy under an improved unambiguous schema/prompt; do not alter frozen seed83 or prior negative raw. Also cross-review whether this bounded input change is appropriate for the phone's symlinked Termux paths (operator may need an explicit source-copy workflow rather than silently following links). Exact next software check: `cd v13/code && PYTHONPATH=.:tests:scripts python -m unittest -v tests.test_c3_operator_bounded_input_auto11 tests.test_c3_operator_receipt_boundary_auto11 tests.test_c3_de_operator_shadow_run11g_20261030 tests.test_listarith_de_closedworld_seed101_20261030`. Remaining platform budget UNKNOWN.
