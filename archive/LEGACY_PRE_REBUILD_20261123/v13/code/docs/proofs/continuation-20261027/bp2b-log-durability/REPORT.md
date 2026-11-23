# BP2b raw native log fsync before checkpoint — 2026-10-27

**Owner/scope:** GPT-6 independent software-only child of PR #714 exact `2b3a4b934fa0283aa9a24fd25879b7bea6504588`; branch `codex/automation11-bp2b-log-durability-20261027`, review-only, no native model job. Native owner Actions `40506115941` remained separate.

## Finding

`bp2b_native_batch.execute()` used atomic fsynced `STATE.json`, but after a subprocess finished it merely closed and SHA256-hashed `log-s<seed>-<arm>.txt`. Without an `fsync` on the log file itself, a crash can leave a durable COMPLETED/FAILED checkpoint referring to raw log bytes that were not durably committed. The original claims of fsynced state did not cover the log.

Fix: after the subprocess completes (success, nonzero exit, timeout or exception), flush and `os.fsync(stream.fileno())` **inside the open raw log context** and only then calculate its SHA and publish the state checkpoint. If fsync itself fails, no successful checkpoint is written; existing RUNNING attempt remains immutable. No model, cohort, seed, arm, scoring or authority change.

## RED/GREEN and false-positive correction

An initial inode-only fsync test passed falsely because temporary `.state-*` inode numbers can be reused by a newly created log. This invalid test was not counted as proof. The corrected regression records the **actual `/proc/self/fd/<fd>` path at each fsync** and tests both COMPLETED and FAILED attempts.

- Original strict **RED** branch `codex/automation11-bp2b-log-fsync-red-20261027` exact `586f5a92df51b728ffefb8c4d28a09712ec2b715`, with **unmodified batch source**. Actions `40509034227`: 31 tests, **2 expected failures** (completed and failed log paths absent from fsync calls). ZIP `12735997848`, SHA256 `92918ca02130c5d56334abcd4b8b29f435ccf961fc10ef29f85264fbadb52304`, CRC PASS, privacy CLEAN.
- **GREEN** branch exact `320e9b8c8d0b1c216e24ede82f3121e84492a0f0`, Actions `40508999107`: **31/31 PASS**, dry-run no output writes, compile0, privacy CLEAN. ZIP `12736062758`, SHA256 `1765cebe19200a06b03f78f59a901058e755cb92b9c4a09087548aee3da818a5`, CRC PASS.
- Both raw ZIPs privately uploaded to ChatGPT Library `/V13-Checkpoints/2026-10-27/BP2b-Log-Durability/`, re-materialized and compared byte-exact with original downloads (PASS). Raw evidence is not committed to public Git.

**Evidence:** SOFTWARE_ONLY; no native model run, learned utility, Q4/Redmi, STEP2, B3, BJ1, Body-JEPA or age/full-V13 promotion. `jepa_weight=0`, `age_authority=0`, `full_acceptance=false`.

**Next:** verify `bp2b_native_batch.execute` calls the real `bp2b_master_preflight.verify(master_dir, pin_path, metadata_only)` with the required pin path; current direct call supplies only one argument and therefore cannot start a native batch. Test signature and exact master SHA guard before any heavy job. Command: `cd v13/code && PYTHONPATH=. python -m unittest -v tests.test_bp2b_native_batch tests.test_bp2b_native_runner tests.test_bp2b_transfer_score`.
