# B3 explicit promotion L1 evidence binding — RED/GREEN checkpoint 2026-10-27

Review-only child of persisted B3 report revalidation at exact parent `b45194a2e8ad6625b40e4b8a985b0c512414c703` (not main). Prereg `6a3280dc7859870a0c7ad80eceef1dc4d972fa5e` before RED test `bfc31da5875738b290febcf65dfb0d4a5739c550`, source fix `4b25edc8373f2a785a8989636956899f23be80dc`, synthetic fixture correction `421e8b7b8005d4e3d3813f87d12c957570a232c1`.

## Proven defect and fix

`b3degrade.gate_passed`, consumed by explicitly human-authorized `:callosum promote`, accepted a manifest with `l1_gate.verdict='PASS'` and no complete comparator evidence. The existing synthetic test used only a receiver-OOD criterion yet promoted L1/L2. New `gate_passed` requires `b3bridge.l1_report_valid` for L1 and as a prerequisite to higher rungs, while preserving the target-rung PASS, human approval, calibration, revision, training-order and degradation checks. The synthetic positive fixture now includes complete typed L1 criteria; this **is not native proof** and no runtime LATENT injection was enabled.

## Closed focused evidence

- **RED Actions 40590647303**, expected FAILURE: 24 tests, 7 new failures including actual synthetic `D.promote` bypass. Original ZIP artifact `12774371281`, SHA256 `93476f066b94e5dcdf1f1595fe0fd8c0b69d33477684495ff84434504e7197a5`, CRC PASS; HEAD `ae8a1bf727231cb03c019b51fa9e5ab31492659e`, SOURCE_BLOB `6af3ed47cbcdb430f39569901bb56ddcc3571875`, TEST_BLOB `d5f819f6fab02c8a65e308fd62920f8534182b99`; PREREG/INSTALL/COMPILE/PRIVACY/DIFF exits0, UNIT exit1.
- Intermediate `40590751335` failed before fixture correction, preserved.
- **GREEN Actions 40590772444 SUCCESS:** 24/24 PASS, all PREREG/INSTALL/UNIT/COMPILE/PRIVACY/DIFF exits0, privacy CLEAN. Original ZIP artifact `12773892681`, SHA256 `a8823b20bef0cc24a646cfc82cba5bc6af2b9f9f9c660d65fdada3bdc9a31678`, CRC PASS; HEAD `421e8b7b8005d4e3d3813f87d12c957570a232c1`, SOURCE_BLOB `5cc822ecad749887acfad69f5fcba39a5a2dae8f`, same new test blob, corrected historical fixture blob `f40b40f6ef114524d318507a5106f5d03d6c5bcf`.
- RED/GREEN original raw ZIPs privately saved at `/V13-Checkpoints/2026-10-27/Automation11-B3-L1-Promotion/`, re-materialized SHA256 byte-identical; no rejected Drive destination.
- **Full source-wide Actions** `.github/workflows/b3-l1-promotion-evidence-fullsuite.yml` queued/running, raw result pending.

## Gates and next

Software-only operator gate correctness; B3 L1 original FAIL, STEP2 UTILITY_FAIL, LP1/LP2/BJ1 negatives, jepa_weight0, age_authority0, no native receiver/Redmi, whole V13 incomplete. A fully forged internally consistent manifest still needs independent artifact authenticity verification before real acceptance; no production merge, independent review. Exact focused command: `cd v13/code && PYTHONPATH=.:tests python -m unittest -v tests.test_b3_l1_promotion_evidence_review tests.test_b3_l1_report_revalidation_review tests.test_b3degrade tests.test_b3bridge`. Next: close full raw evidence and review sequential integration.
