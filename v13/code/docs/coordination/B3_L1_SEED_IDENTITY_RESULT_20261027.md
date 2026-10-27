# B3 L1 paired seed identity — verified RED/GREEN and full software checkpoint (2026-10-27)

Review-only child of PR #781, exact parent `6ce9754a418dc85204efed174c1b0ef23e0f8ae4`. Prereg commit `8d94664b9d144ae9a722c8a021f816e2a853e425` preceded RED test commit `1c1b09575ce4dab687bb33ff7bf7627c035a2281` and implementation `f5092cae464e9ea86dc76062275561b7387f82f4`.

**Defect:** L1 diagnostic previously treated same-length accuracy vectors as paired, allowing PASS with absent, reordered, substituted or duplicated seed identities. The boundary now requires all seven canonical arms to carry identical ordered, unique bounded ASCII seed IDs, and NO_MESSAGE byte cost to be zero. Synthetic positive fixtures are labelled with fixed five IDs; scores and negative cases are unchanged. This is declared identity checking, **not** independent row/source authentication; Run483's external SHA pins remain separate.

## Closed evidence (original GitHub Actions raw ZIPs)

- **RED** run `40591571744`, HEAD `1c1b09575ce4dab687bb33ff7bf7627c035a2281`, 36 focused tests, **33 expected failures** on original source; UNIT exit1, PREREG/INSTALL/COMPILE/PRIVACY/DIFF exits0. ZIP artifact `12773464301` SHA256 `38f2cd7c1e36482919b5910b911c27825069525737f841210ea3a8230531160c`, CRC PASS. Source blob `050ad0e9e3948261a23a752e5379383a13d2e61b`.
- **GREEN** run `40591669489` SUCCESS, HEAD `f041f0147acdcae41929f541343aa500c3e295e1`, **36/36** focused tests PASS, all raw exits0/privacy CLEAN. ZIP artifact `12773594342` SHA256 `6ce9d72fde0bdaaa4a53c0ef4c92eae9aee1488505b6968fb64b855739ed7840`, CRC PASS. Source blob `556c0a9f018f183483812e41db96ee4ebcc93258`, seed test blob `3921e38e02e168cddd0e3d4f303664980a936b2c`.
- **Full** run `40591726397` SUCCESS, HEAD `38d76f8fee75cc19c554fdf880074f738744a1b6`, **1997 tests OK (1 skipped)**, all PREREG/RED_TEST_COMMIT/FROZEN/INSTALL/UNIT/COMPILE/PRIVACY/DIFF exits0, privacy CLEAN. ZIP artifact `12774208841` SHA256 `8d86bcce8dabb5e5ea3d97925fe9bf1acd3e5c34f7626a56077ad2ec4cc686e3`, CRC PASS.
- All three original ZIPs were uploaded to private Library `/V13-Checkpoints/2026-10-27/Automation11-B3-L1-Seed-Identity/` and re-materialized byte-identical by SHA256. No rejected anyone-writable Drive upload was attempted.

## Claims, blockers, next

This is **Linux software-only** diagnostic gate correctness, not real B3 native L1 PASS, semantic utility, Redmi validation, receiver injection or permission. Original B3 L1 `FAIL`, STEP2 `UTILITY_FAIL`, LP1 `NO_ATTRIBUTABLE_GAIN`, LP2 `ALIGNS_NO_GAIN`, BJ1 `NO_SIGNAL`, `jepa_weight=0`, Age0 authority 0 and whole-system incomplete. No original model/seed/cohort/raw evidence modified. No production merge, no auto-merge.

Next independent review: compare B3 gate with external pinned rows/metadata (Run483) and downstream persisted report/promotion readers. Integration with C1+World provenance PR #780 is separately preregistered and in review, not main. Exact focused command: `cd v13/code && PYTHONPATH=.:tests python -m unittest -v tests.test_b3_l1_seed_identity_review tests.test_b3_l1_baseline_completeness_review tests.test_b3bridge tests.test_b3_completion tests.test_b3degrade`.
