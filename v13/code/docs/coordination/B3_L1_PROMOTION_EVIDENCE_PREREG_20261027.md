# B3-H10 explicit promotion must reject incomplete L1 evidence — prereg (2026-10-27)

Review-only child of B3 persisted L1 report revalidation at exact parent `b45194a2e8ad6625b40e4b8a985b0c512414c703` (not main). Owner independent B3 review, file ownership `v13/code/v13/b3degrade.py`, new `tests/test_b3_l1_promotion_evidence_review.py`, existing synthetic `tests/test_b3degrade.py` fixture, CI/coordination only. No model/source/seed/cohort or original negative evidence overwritten.

## Falsifiable defect

`b3degrade.gate_passed(man,'L1')` currently checks only `man['l1_gate']['verdict']=='PASS'`. The operator's explicitly human-approved `:callosum promote` consumes this boolean; the existing synthetic `test_b3degrade.Live.bridge` creates a PASS with only one `receiver_ood` criterion and still tests promotion into L1/L2. This bypasses the now-strict L1 complete-comparator contract if a persisted manifest is malformed/forged. The operator approval alone is not a substitute for objective proof.

## RED

1. A PASS label with no full L1 criteria or nonempty missing/invalid markers must fail `gate_passed('L1')`.
2. A complete L1 gate returned by `b3bridge.l1_gate` remains acceptable as a **synthetic protocol control**; no production promotion.
3. Promotion into L2/L3/L4 cannot rely solely on a higher-rung PASS when the required L1 record is absent/incomplete.
4. A synthetic Runtime with otherwise satisfied calibration/order/revision but incomplete L1 record must reject `:callosum promote` with `GATE_L1`.
5. Existing synthetic promotion tests are updated to carry full typed L1 gate records while preserving explicit-human and degradation behavior; original native B3 L1 `FAIL` remains.

## GREEN

`gate_passed` reuses the B3 L1 report validator for L1 and requires it as a prerequisite for higher rungs; existing higher-rung verdict/age/calibration/order gates remain unchanged. No new native receiver, no automatic promotion, no LATENT message injection or production authority. Focused RED/GREEN and full source-wide software evidence with raw exits/private backup; all STEP2/B3/LP1/LP2/BJ1 negatives, `jepa_weight=0`, `age_authority=0`. Independent review, no auto-merge. Residual: a fully forged but internally consistent manifest still requires artifact-authenticity proof before real native acceptance.
