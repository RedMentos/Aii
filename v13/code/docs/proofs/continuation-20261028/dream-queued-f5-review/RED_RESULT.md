# Run798 RED — queued Dream F5 authority regression reproduced

UTC 2026-10-27 23:36. Prereg `6e2579e8f8d3af850e6c9a2a391556adf37d7692` preceded unchanged Run275 test import `123a5b811d6dc0ecedd98d04ca10477478a66324` and dedicated workflow `690678ece1ed1f48a25a4bdd537d347398870294`. **No production code was changed** for this RED.

Actions `40603196626` at exact `690678ece1ed1f48a25a4bdd537d347398870294`: 39 focused tests, **4 failures**; deleted route HumanDecision/feedback and revoked world anchor yielded UNVERIFIED instead of STALE, revoked supporting neighbor still yielded SUPPORTED. Valid queued route, independent route, original Run274 Sleep A/B F5, exact-ID, Memory F5 and episodic route tests passed. `FOCUSED_EXIT=1`, `FULL_EXIT=SKIPPED_RED`, `BLOBS=INSTALL=COMPILE=PRIVACY=DIFF=0`; privacy CLEAN. This is an expected software RED, not a green result.

Raw artifact ID `12779496421`, ZIP SHA256 `bf11afd6096e9a6cba48bee203a58684e5013cda21575d8f2465f74aad73d09b`, ZIP CRC PASS, internal SHA256SUMS PASS. Private Library backup `/V13-Checkpoints/2026-10-28/Automation12-Dream-F5/RED-40603196626.zip` materialized byte-exact SHA256 match PASS. Raw failure remains preserved.

Next: wait for PR797 exact CI GREEN, then narrowly transplant prior Run275 `_memory/_neighbors/check_hypothesis` F5 guards while preserving current Sleep A exact-ID and Dream B seed guards. Re-pin Sleep source blob, run focused/full software and independent review; do not merge. No native/Redmi, no learning/age or gate promotion. STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; jepa_weight=0; V13 incomplete.
