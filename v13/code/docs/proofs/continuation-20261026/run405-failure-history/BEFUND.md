# Run405 — RED-first failed-attempt preservation in full STEP2 postflight (2026-10-26)

**Independent finding:** Run403 378-row postflight previously copied `progress.failures_preserved` without verifying that its referenced failed/partial attempt directories existed. A forged complete progress record could conceal missing negative evidence while returning structural GREEN.

**RED-first:** PLAN `37a06eb` preceded adversarial tests `bfd4d98` and workflow `51a5175`. Exact-head Actions `40251633208`, job `121344618505`: **84 tests, 5 expected failures** (missing failed-attempt directory, empty raw directory, symlinked directory, unknown arm, path escape), privacy CLEAN. RED raw artifact `12620517567`, ZIP SHA256 `eef9bb948b4faf1bcfba0ffa7cf249806e9c94369a94461ac76d52c2a8a340ad`, CRC and 6/6 SHA PASS. Original failure preserved.

**Narrow fix:** Commit `2152d453a3cc8fca73a0cf03a61aa90214b1b923` adds `validated_failed_attempts` to Run403. It requires a typed failure map keyed by registered arm/seed, nonempty typed failure records, safe attempt-relative paths, real nonsymlinked directories and at least one retained raw file; existing failed attempts remain accepted/reported without rewriting. No change to Run394 fixtures, model/seed hashes, Run397 runner, scoring or native inference.

**GREEN:** Exact-head Actions `40251684770`, job `121344767004`: **84/84 source-only PASS**, compileall PASS, privacy CLEAN. GREEN artifact `12621436052`, SHA256 `54e0cc92ae5895096b3ff1936985d2befa811d91afb89f3429fef38e81d0bc21`, ZIP CRC and 6/6 SHA PASS. Both RED and GREEN raw mirrored to `/V13_PRIVATE_CHECKPOINTS_20261024/Run405_Failure_History_20261026/` and independently materialized SHA byte-identical.

**Evidence limits:** Entire test cohort synthetic; no native 378-row or actual restart proof. Run401/PR396 first native O_s20 job `40250662450` still active at this checkpoint. No STEP2/B3/Body-JEPA/jepa_weight/Age/Redmi/whole V13 gate promotion. Run389 full-suite RED remains.

**Next:** Observe Run401 exact native artifact ID/SHA and independently validate actual raw; Run402 restore and Run404 P_s20 stage2 only after native owner releases. Run405 does not authorize changing registered data or losing any failed attempts.