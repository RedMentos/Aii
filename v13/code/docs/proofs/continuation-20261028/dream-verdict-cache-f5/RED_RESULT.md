# PR800 RED — cached SUPPORTED Dream verdict survives F5 revocation

UTC 2026-10-27 23:41. Prereg `992a4673c347307dcfced1e49d89a8c761cd98ce` preceded test-only `e1f997807ac8eaa4d1a38b5a91d9849c49bad87e` and pinned workflow `989821ca0fe72a7e756ebb812f3724b26fc70425`. **No production source changed** for this RED.

Exact Actions `40603768499` at `989821ca0fe72a7e756ebb812f3724b26fc70425`: 42 focused tests, **3 failures**, 0 errors. All three new actual Runtime/SQLite tests demonstrate a previously SUPPORTED queued Dream verdict survives revoked F5 anchor, revoked supporting neighbor, and persisted restart because `validate_hypotheses` skips non-UNVERIFIED cached verdicts. All 39 inherited Run275/274/F5/Memory/Sleep tests passed. `FOCUSED_EXIT=1`, `FULL_EXIT=SKIPPED_RED`; `BLOBS=INSTALL=COMPILE=PRIVACY=DIFF=0`, privacy CLEAN. No full suite PASS claim.

Raw artifact `12780395754`, ZIP SHA256 `afb894524d1350cd622d681f55aad0efdf33818918df97a94d7ccd5f16660448`, CRC/internal SHA256SUMS PASS. Private Library backup `/V13-Checkpoints/2026-10-28/Automation12-Dream-Cache-F5/RED-40603768499.zip` byte-exact readback PASS.

Next: after parent PR798 exact CI GREEN, narrowly change `validate_hypotheses` to recheck cached SUPPORTED through the already verified F5-aware `check_hypothesis`; retain UNVERIFIED daily throttle, retired STALE/CONTRADICTED and budget. Run focused/full software, privacy, private raw backup and independent review. No native/Redmi, learning/age or gate promotion. STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; jepa_weight=0; V13 incomplete.
