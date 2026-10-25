# Run314 preregistration — current exact-chain Termux source ZIP

2026-10-25. Owner `assistant/current-phone-source-run314-20261025`.
Base `46e2a20f6d16b181380d29c0692566d808d079ba` (Run313b 46/46 GREEN, Run312 45/45 GREEN), not production main.
Only new `.github/workflows/run314-current-phone-source.yml` and this proof directory. No production, Canon, model/seed/cohort, active-owner, approval or learning gate edits.

Build a source-only Termux ZIP with the *existing canonical* `v13/code/scripts/package_source.py --phone-install`; verify every ZIP member's CRC/SHA and checkout byte parity using the existing independent `verify_phone_zip_current_run268.py`. Extract to fresh directory, run offline setup in SOURCE_ONLY_DIAGNOSTIC (no native/model downloads), run actual extracted Runtime/SQLite/phone tests: Run312 FastForward exactly-once (including fault injection), Run313 JEF source-row+receipt atomicity (including restart/concurrency), Run308 Attention receipt, Run307 Sleep retention, Run306 WorldModel source split, Run304 backup, Run302 operator, phone CLI and operator journey. Verify immutable Canon hash and exact head.

Retain ZIP, raw logs, per-file hashes, source commit and exit codes in Actions artifact. CI failure is evidence, not a gate pass. No Redmi, actual native B1/B2/C2/C3, Body-JEPA, STEP2/B3 or whole-system claims. Artifacts are 30-day retention; persist hashes/IDs in branch checkpoint. Continue another independent package after verification.
