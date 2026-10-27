# PR801 second combined RED — warm recency fixture order

UTC 2026-10-27 23:49. Exact source/test/workflow `9a4108ceef68842131698ab88f263326eeeb1d13`; Actions `40604682367`: **73 focused tests, 1 FAIL**, full SKIPPED_RED, `BLOBS=INSTALL=COMPILE=PRIVACY=DIFF=0`, privacy CLEAN. The first fixture-kind mistake was corrected and its independent-valid-fact test passed. Remaining failure: new cross-organ test added two equal-value facts sequentially and expected the older first fact to be the warm winner, but the bounded recency/activation warm policy selected the newer fact. All 72 other tests, including Run271/274/275 and ContextOS, passed. This is a **test recency assumption**, not a production regression.

Raw artifact `12780501927`, ZIP SHA256 `647fbbfd30da78a35cee1bb1f64e991f451986e16a58955c7738674f82499d92`, CRC/internal SHA256SUMS PASS. Private Library `/V13-Checkpoints/2026-10-28/Automation12-Combined-F5/RED-WARM-40604682367.zip` byte-exact readback PASS. Both failed attempts remain preserved.

Next: create the second same-value fact first and target fact last, so the target is genuinely warm before revocation; preserve production source and exact registered Run271/274/275 cohorts, re-pin only this integration test and rerun full software. No native/Redmi or gate promotion; V13 incomplete.
