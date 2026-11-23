# B3 L1 persisted doctor/completion report revalidation — RED/GREEN checkpoint 2026-10-27

Review-only child of strict B3 baseline branch at `80e2dfc1d39256153df6bc6ff316349c705dc65a` (not main). Prereg `1e05eb86895237cfcf06ced69d33fbb720ee7629` before RED test `ad0a87bde3fac23fd3785d9fec88f0f547b90adc`, source fix `b27195dd33a1620e153fa1306f90d11045031c1d`, corrected historical synthetic fixture `b45194a2e8ad6625b40e4b8a985b0c512414c703`.

## Proven defect and fix

`b3bridge.doctor_fields` and `completion_gate` previously trusted a persisted `l1_gate.verdict=PASS` even with absent shuffled/random, exact/control/symbolic, role-retention, OOD or restart criteria. A manually constructed PASS could be reported as L1 shadow or active. New `l1_report_valid` requires every canonical significant criterion plus explicit empty `missing_baselines` and `invalid_evidence`; doctor and completion revalidate on each read. Synthetic complete fixtures still exercise reporting, but this **does not authenticate a native proof** and `latent_authority` remains0.

## Closed focused evidence

- **RED Actions 40590346870**, expected FAILURE: 22 tests, 22 failed subcases. Original ZIP artifact `12773921801`, SHA256 `81a655ee9580f499560efd0165482df3932f6435fd38674ec076772444db46be`, CRC PASS; HEAD `683b7502b4473ec55eb588f5b2272488e855ced9`, SOURCE_BLOB `050ad0e9e3948261a23a752e5379383a13d2e61b`, TEST_BLOB `ba2662593bdf260b5cbed7cb3158793a26638c92`; PREREG/INSTALL/COMPILE/PRIVACY/DIFF exits0, UNIT exit1.
- Intermediate `40590499734` failed after source edit before fixture correction, preserved.
- **GREEN Actions 40590515273 SUCCESS:** 22/22 PASS, all PREREG/INSTALL/UNIT/COMPILE/PRIVACY/DIFF exits0, privacy CLEAN. Original ZIP artifact `12773048825`, SHA256 `d4afff3670d3a5f53d66d4d9e8643fe59c12f2649fccb439f36ec353ed9764e6`, CRC PASS; HEAD `b45194a2e8ad6625b40e4b8a985b0c512414c703`, SOURCE_BLOB `3f0efe54e2087babf267ef3d4ccbd424b897faf8`, same new test blob, corrected fixture blob `188ce376f1012ade7560d058752901afc22da930`.
- Original RED/GREEN raw ZIPs privately saved at `/V13-Checkpoints/2026-10-27/Automation11-B3-L1-Report/`, re-materialized SHA256 byte-identical; not rejected anyone-writable Drive.
- **Full source-wide Actions** `.github/workflows/b3-l1-report-revalidation-fullsuite.yml` running; no PASS claimed pending raw closure.

## Gates and next

Software-only report integrity; original B3 L1 `FAIL`, STEP2 `UTILITY_FAIL`, LP1/LP2/BJ1 negatives, jepa_weight0, age_authority0, no native receiver/Redmi, full V13 incomplete. No auto-merge, independent review. Next: full raw closure, then downstream explicit-promotion gate branch (the operator path previously consumed the same verdict-only record). Exact focused command: `cd v13/code && PYTHONPATH=.:tests python -m unittest -v tests.test_b3_l1_report_revalidation_review tests.test_b3_l1_baseline_completeness_review tests.test_b3_completion tests.test_b3bridge`.
