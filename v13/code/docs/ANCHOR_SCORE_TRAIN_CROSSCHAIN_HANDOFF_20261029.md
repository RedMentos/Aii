# STEP2 × U5 × AG6 cross-chain integration handoff — 2026-10-29

## Provenance
- Base PR #1104 exact `15732a6237187743c9cc6fe8539fdddfed94c6dc`; separate review-only workstream from Context/Sleep PR #1111–#1113. Prereg `8e2fca3d32b8ceb87b9cbc6a25bac569b1a32560` remotely verified before donor imports.
- Donor chain #1094/#1095/#1098 exact final PR #1098 head `aa8f7cfd413979d923e1c600f4a71dde3a1985b2`. Verified original base blobs for all three modified sources equal PR #1104, so no intervening source change overwritten.
- Exact donor source Git blobs: `utility.py` `ff16ab6012b2865e0f3abde2a289aaf00e9aaa53`, `anchor.py` `e7d96e4160d19711f64bf1025fff0930edda0b2b`, `agi/weights.py` `2e8efe1e1c64733f074844ec4a0b623b56be7c45`. Three donor focused tests, three original prereg notes and three donor workflows copied byte-identically and remote blob SHA checked.
- Original donor REDs and negative evidence retained in original PRs: #1094 malformed STEP2 utility/duplicate cohort; #1095 nonfinite/negative U5 anchor policy; #1098 AG6 swallowed invalid anchor exception and reached `trainer.fit`. Donor #1098 focused 17/17 software PASS with raw `40882318794`, no native training. Original donor full-suite runs #1094/#1095 recorded two frozen-source identity errors in run34/run37, not silently fixed.
- Independent new real-Store cross-organ regression `tests/test_score_anchor_train_crosschain_20261029.py`: malformed paired STEP2 score cannot pass, invalid U5 anchor must persist `ANCHOR_INVALID` and veto `trainer.fit` through restart. Synthetic spy only, no weight updates.
- Exact-head focused/full CI pending; retain original raw failures and distinguish focused/source-only from full native/phone proof.

## Next
1. Run focused donor + cross-organ tests, `python -m unittest discover -s tests`, compileall, privacy/diff checks; upload raw SHA256SUMS and verify artifact bytes.
2. If full historical source-identity tests fail due intentional source changes, retain RED and report exact failures. Do not rewrite pinned source identities. Independent reviewer must decide integration of this cross-chain patch before production.
3. Cross-review with current Context/Sleep integration chain; no force-push/production merge. Canon, model/source/seed cohort hashes unchanged.
4. Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight0, AG6 unapproved, Redmi sustained unmeasured, V13 incomplete.
