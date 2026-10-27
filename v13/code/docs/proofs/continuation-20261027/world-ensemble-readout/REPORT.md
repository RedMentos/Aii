# WP-Z12b World-JEPA ensemble centre — review checkpoint

Date 2026-10-27 UTC. Owner GPT-6 continuation. Review-only child of PR #746 candidate exact original parent `46aca17c50e9d291d7757434930f8f08ed85b8e4`. Prereg `1fbc2320476b32a24e85c82e13a860df41d04d7f` preceded test and implementation.

## Result

`WorldJEPA.predict` previously documented its first output as an ensemble mean but returned only the first predictor while using all predictors for disagreement. The readout now returns `ps.mean(0)`, leaving trained predictors, seeds, EMA, targets, uncertainty spread, confidence threshold and SHADOW-only status unchanged. This repairs the point-estimate/disagreement contract, not proven learned utility.

## Exact evidence

- Initial test-only RED `840033520998a5e918a78b4d68ccdf9ae033de75`, Actions `40543833577` CANCELLED before a job (retained; no RED claim from it).
- Independent pinned-source RED replay workflow `abab6cbe2ae319111eda6eae7e788964a4446627`, Actions `40543922897` checking out test-only `840033520998a5e918a78b4d68ccdf9ae033de75`: **4 tests, 1 expected FAIL** (0 returned instead of ensemble mean 2); INSTALL/COMPILE/PRIVACY/DIFF 0. Raw artifact `12752571087`, ZIP SHA256 `e80fc061876e0622d30971d55fd1b7480b107813b96ecd632ec5b4ffe7d73bb8`, CRC clean, private Library backup byte-identical. Original world_jepa blob `a691cae8aa19bf3a0700535c20dc8fc85c649d0d`.
- GREEN source `df2925308fd3ffed642d3997df7113db92f81e7d`, world_jepa blob `9342f2b7922530bc3ab6746855617a609c1c82c0`. Focused Actions `40543850433`: **4/4 PASS**, all five exits 0. Raw artifact `12752635797`, ZIP SHA256 `a447f31be434094f7b95c1d924c39ce9a3dc3f50c37b32e61a1721f094fe85a3`, CRC clean, private byte-exact backup.
- Full software suite workflow `251bcf352bc1923c4fb154a246a4c170dc3f110d`, Actions `40544327201`: **PENDING**, no full-suite PASS claim.

Private artifacts: `/V13-Checkpoints/2026-10-27/Automation11Q-World-Ensemble/`. No raw private data in GitHub.

## Gates / next

World-JEPA remains experimental SHADOW and not runtime-wired. No native model, Redmi, Age promotion or causal utility. LP1 NO_ATTRIBUTABLE_GAIN; LP2 ALIGNS_NO_GAIN; BJ1 NO_SIGNAL; STEP2 UTILITY_FAIL; B3 L1 FAIL; `jepa_weight=0`; Age authority=0; Redmi unmeasured; whole V13 incomplete. Next: inspect full Actions 40544327201 raw exits, private backup, independent review of ensemble calibration and broader connected World-JEPA utility. No main merge.