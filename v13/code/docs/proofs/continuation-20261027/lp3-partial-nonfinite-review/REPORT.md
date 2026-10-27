# LP3 mixed missing/nonfinite gradient review — RED → GREEN

2026-10-27 UTC. Review-only PR #753, child of PR #750 exact parent `830c35aeeffd50454e99d8ced63619300658cdf0`. Prereg `a24b80df1ad9b5e60a297ab3fb88f27546bc6222` committed before test-only RED `7dc720dc8d7fdce76da6ca183faaa105eb6e3740` and source fix `685515d45b37982a82279972769d98a7c8e9db00`. **No native model job was run.** Original PR #750 registered native diagnostic remains a separate, unchanged cohort.

## Confirmed defect and correction
Old `_grad_stat` returned `finite=True, abs_sum=0, nonfinite_elements=0` immediately when any parameter gradient was missing. A separate present gradient containing NaN, +Inf or -Inf was never inspected. The original `_train_arm` would therefore not hit its nonfinite early-stop and could step AdamW with corrupted gradients. New code first counts nonfinite elements across all **present** tensors, preserving the missing-tensor count; if any are nonfinite, it returns `finite=False, abs_sum=None`, so existing training-arm guard stops before optimizer update. Pure missing-but-finite remains a recorded zero-gradient diagnostic; all-present finite behavior unchanged.

## Closed software evidence
**RED** Actions **40559175505**: exact CI checkout `b01df4297beb0b1717e9902c65ff006ee2458b50`; **33 tests, 3 expected FAIL** for NaN/+Inf/-Inf with one other gradient missing; other 32 tests PASS. UNIT exit1, INSTALL/COMPILE/PRIVACY/DIFF 0, privacy CLEAN. ZIP artifact **12758112323** SHA256 **`e54c2a03fdacfe301db2955a424742be3011e2c670f348ad027901f2d5c0e7dc`**, CRC PASS.

**GREEN** Actions **40559510761**: exact CI checkout `76cd708dce6956ff487086025574ee53492b3e71`; **33/33 focused software tests PASS**, INSTALL/UNIT/COMPILE/PRIVACY/DIFF all exit0, privacy CLEAN. Patched script Git blob **`488cd12de3d5103e2a456f42148697fd15d66bc6`**. ZIP artifact **12758287546** SHA256 **`614cd8fb7db8a2d3e502cb6f629ce953f610a998636031ea316bfaa7553649d8`**, CRC PASS.

Both original raw ZIPs privately backed up under `/V13-Checkpoints/2026-10-27/Automation11W-LP3-Partial-Nonfinite/` and re-materialized byte-identical by SHA256. Rejected anyone-writable Drive destination not used.

## Claim limits and next
This is a **software-only diagnostic guard fix**, not evidence that the original failed LP3 native pilot was caused by mixed missing/nonfinite gradients. No new model load, optimizer trajectory, heldout utility, trained weights, real-world/Redmi run, or Age promotion. LP1 NO_ATTRIBUTABLE_GAIN, LP2 ALIGNS_NO_GAIN, BJ1 NO_SIGNAL, STEP2 UTILITY_FAIL, B3 L1 FAIL, `jepa_weight=0`, Age authority0, whole V13 incomplete. Draft PR, no main merge. Independent full-suite review required. Next: check original #750 native owner and raw trajectory, then consider separately preregistered follow-up; do not silently change its frozen cohort.

## Full software regression closure
Actions **40560033075 SUCCESS**, exact PR checkout `53ccac2f83f909457d1a5597bfcb1b7219be05b9`: **1917 tests OK (1 skipped)** in 210.009 s. INSTALL/UNIT/COMPILE/PRIVACY/DIFF raw exits all 0, privacy CLEAN, patched LP3 script blob `488cd12de3d5103e2a456f42148697fd15d66bc6`. ZIP artifact **12760441944** SHA256 **`b204281e5dc960d4b51b77ffb7cf6ccdc10f96aa46ece89e04b56324cc284300`**, CRC PASS; privately backed up and re-materialized byte-identical at `/V13-Checkpoints/2026-10-27/Automation11W-LP3-Partial-Nonfinite/lp3-partial-nonfinite-fullsuite-40560033075.zip`. Full source-wide **software** regression verified; no native LFM run or utility claim.
