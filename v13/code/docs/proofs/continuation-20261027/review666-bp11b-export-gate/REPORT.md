# Independent Claude BP11b module export hard-ban review — 2026-10-27

## Source and confirmed defect

Review-only child of Claude PR #666 exact `e505364c78d6ef222eb287d84d84aed81ecc53e3`. Scope owned: `v13/code/v13/module_learn.py`, new test/workflow and this proof folder. No Claude/main overwrite, no native/model/network/Redmi, no age or learning-authority promotion.

BP11b's `:modul export <Datei>` calls `module_learn.export_dataset` and performs a local `atomic_write`. Original code did not check the fixed **exact tool** prohibition `:verbot werkzeug module_export`. With released synthetic knowledge and learning switch on, that ban did **not** stop the export; this is a confirmed bypass of the typed tool-specific rule. The new `_export_gate` checks the fixed `module_export`/WRITE_LOCAL/user-rule gate before corpus access and again immediately before writing, refusing with PermissionError. Unaffected explicitly typed export remains tagged JSONL and performs no training.

**Important negative correction:** Original prereg hypothesized that a broad `:verbot art WRITE_LOCAL` would also allow export. RED inspection disproved that: existing `modules_gate.corpus` already gates module learning as WRITE_LOCAL and returned an empty corpus, preventing the file write (though with a misleading ValueError). It also conservatively suppresses read-only module recall under that ban. We did **not** change that behavior. `AMENDMENT_RED_INTERPRETATION.md` preserves the correction before the source fix.

## Original REDs and exact GREEN

- RED1 Actions **40460829626**, head `7604514b17c24053ec9b38d557f41087654167a1`: **48 tests, 2 FAIL / 2 ERROR**, compile0/privacy CLEAN; ZIP artifact **12714206674**, SHA256 `be29cda177ab48445a879a7c2ae7af13bd3a88d2faef76b646dd560dac6da402`. Includes the incorrect read-only expectation, which was corrected after prereg amendment.
- RED2 Actions **40460973215**, head `cfaba938a13f3bc8db1c785e4296e346593472aa`: **48 tests, 1 FAIL / 2 ERROR**, compile0/privacy CLEAN; ZIP artifact **12714197603**, SHA256 `91b377c920c97937aee036311244cf7c2a1687e160c82818ae76d2e23027d48f`. Exact module_export ban still bypassed; Notaus/WRITE_LOCAL produced ValueError instead of PermissionError.
- RED3 Actions **40461002336**, source fixed at `b48eb40341da1f2bd4d02f33b4201ad5dfc02b15`: **48 tests, 1 FAIL** from a stale test assertion expecting two readable corpus items under WRITE_LOCAL ban; source behavior correct, test-only fix `36294ea855627f48abe22e243934d1a075a29426`. ZIP artifact **12713924611**, SHA256 `70cce25fc385cd9600e224072cbe1b30b00fbc8ccbbb8979ab88a39212141e6c`.
- **GREEN** Actions **40461135118** on exact `36294ea855627f48abe22e243934d1a075a29426`: **48/48 PASS**, compile0, privacy CLEAN. ZIP artifact **12713994555**, SHA256 `462dab7aee44104e7e75ac882a37ee42325a9059eac4bf7b4e0b71dce7ff6b38`.

All four original ZIPs CRC clean, HEAD/exits inspected; private Library `/V13-Checkpoints/2026-10-27/Review666-BP11b-Export-Gate/` contains them, and byte-roundtrip SHA verified. No raw artifact or failure rewritten/deleted.

## Claim boundary / next owner

This proves **Linux synthetic fixed-rule enforcement** for an explicit module export, not arbitrary concurrent linearizability, real module learning, C3/Body-JEPA utility, or an integrated V13. `module_export` remains a TTY-only operation; no model tool may call it. Other module/revoke races and already-exported training data remain open. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, `jepa_weight=0`, Redmi UNMEASURED, V13 INCOMPLETE.

Next exact command: `cd v13/code && PYTHONPATH="$PWD:$PWD/scripts" python -m unittest -v tests.test_review666_bp11b_export_gate tests.test_modules_gate tests.test_guard2`. Independent owner GPT-6; next owner Claude/GPT cross-review and three-way AG5+World+Claude integration coordinator. No main merge without integrated full review.
