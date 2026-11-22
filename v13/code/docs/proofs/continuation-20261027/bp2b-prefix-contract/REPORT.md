# BP2b batch prefix ↔ native child contract — independent review, 2026-10-27

**Scope/owner:** GPT-6 review-only child of PR #713 exact `c13aee9b1ab29bb197b9a8c4a42bb664e1a353fc`. Branch `codex/automation11-bp2b-prefix-contract-20261027`; not production-integrated. No model run, no source/seed/score/master/cohort changes.

## Counterexample and repair

`bp2b_native_batch.registered()` accepted prefixes up to 24 characters and periods; `bp2b_native_runner.run_arm()` accepts only `[A-Za-z0-9][A-Za-z0-9_-]{0,31}` as a **complete** attempt ID. For example, `'x'*18 + '-s41-bp2b_minor'` has length 33, and `x.y-s41-bp2b_minor` contains a period. Both passed batch preregistration and later failed at the real child before training; existing fake subprocess tests missed this. The longest suffix is 15 characters, so the safe prefix maximum is **17** characters, with no periods. Source fix changes only `PREFIX` validation; canonical `SEEDS`, `ARMS`, plans, weights, hashes and negative gates are unchanged.

## Original RED / GREEN evidence

- **RED** Actions run `40508297873`, source `457ca46a795acfa2f58ba5091110d549daa52057`: 29 software tests, **3 expected assertion failures** for 18-character and dotted prefixes. Original ZIP artifact `12736720128`, SHA256 `90bbae84cbcfda45dd43ac61ad03a5420f0f1980204cbaf24d3adfc4040a2c32`; ZIP CRC PASS, privacy CLEAN.
- **GREEN** Actions run `40508433741`, source `30dfceb5b5584ea03369dd73f06790c8c4df6905`: **29/29 PASS** (including actual child-format counterexample), dry-run exit 0 without output directory, compile exit 0, privacy CLEAN. Original ZIP artifact `12735064061`, SHA256 `33e4b33d473b50757c11d64e67b8e981fb5fcf265d3ced0e15b054fdb1510cee`; ZIP CRC PASS.
- Both original ZIPs were downloaded, SHA256/CRC/exit logs checked and uploaded privately to ChatGPT Library `/V13-Checkpoints/2026-10-27/BP2b-Prefix-Contract/`; read-back files compared byte-for-byte with the original downloads (PASS). Public repo contains report/source/tests only.

**Evidence class:** SOFTWARE_ONLY. This is an operator validation bug fix, not BP2b native learning, Q4/Redmi, STEP2, B3, BJ1, Body-JEPA, age or full V13 proof. Preserve `jepa_weight=0`, `age_authority=0`, `full_acceptance=false`.

**Next command:** `cd v13/code && PYTHONPATH=. python -m unittest -v tests.test_bp2b_native_batch tests.test_bp2b_native_runner tests.test_bp2b_transfer_score`. Independently review native seed41 legacy owner Actions `40506115941` before any new heavy run; do not overlap that owner. Further package: fsync raw per-arm log before publishing checkpoint, and verify evidence sidecars on resume. Continue all canonical scope; no promotion from this review.
