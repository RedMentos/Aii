# AGE0d exact-result representability — closed software review (2026-10-27)

## Ownership / source / lineage
- Review-only PR #762; parent #759 exact `6c1e0e985c7fa5ba5e477d95743cf1e21b718831`, **not main**.
- Prereg first: `76fab1a1c2e9a344345ecf2cc9121d5cb8e25a7f`.
- Original source blob: `b1a58497ccf508784ded8fb478935cd664859f7a`.
- Minimal GREEN source commit `47e413a6d0c4260dcf9f8bd10c29fd6de72b171a`, source blob `0d46595bbd166feb0152dc60b67595cfedcf9b10`.
- New test blob `6f60738d4e5e69a6ad76f2a567f228732350da62`; original frozen tests/fixtures unchanged.

## Failure and fix
Original exact arithmetic audit can report MISMATCH even though the true result is outside its own 12-integer/12-decimal-digit answer grammar. Test-only RED `d25ac53587b293bb1225d1d78cf8137bf42dd2ac` at Actions **40566368633**: 16 tests, 4 expected FAIL (1E-24 product, 5E-13 quotient, 13-digit sum, 13-digit product), other tests PASS; UNIT exit1, COMPILE/PRIVACY/DIFF exits0. Original ZIP artifact `12762848368`, SHA256 `f3b6f01e6c92029cce382cc3d0f9c74af359a3bdfbb2961179860c1f9989d94f`.

GREEN source uses a 64-digit local Decimal context for binary arithmetic and rejects results that cannot be expressed in the parser's exact answer grammar; it never rounds an answer or grants delivery rights. Actions **40566557818** exact source `47e413a6...`: **16/16 PASS**, all UNIT/COMPILE/PRIVACY/DIFF exits0, privacy CLEAN. Original ZIP artifact `12762723233`, SHA256 `94177fbe37428345a740b07bf1d1795c9fcb72d08d75e3b650ea6512b89504a4`.

Full source-wide Actions **40566885856** at exact head `5f0d4b250b393592bbeb75f24419f6de637226e3`: **1956 tests OK (1 skipped)**, INSTALL/UNIT/COMPILE/PRIVACY/DIFF exits0, privacy CLEAN. Original ZIP artifact `12763402535`, SHA256 `5eff0a376cbce202bce4c80e0390a5dada2b291f443dfc7ca436add4a96fd495`; ZIP CRC clean, source blob verified `0d46595...`.

All three original raw ZIPs privately saved under `/V13-Checkpoints/2026-10-27/Automation11ZF-Age0d-Exact-Review/` and **re-materialized SHA256 byte-identical**. No private prompts, native model outputs or real-user data in these CI artifacts. Separate local deterministic exact-answer sweep: 20,000 generated cases, 17,186 representable; 14,349 CORRECT, 2,837 conservative ABSTAIN, **zero MISMATCH for correct exact answers**. This sweep is local software only, not a frozen real-user calibration cohort.

## Gates / handoff
AGE0d remains a **manual offline SHADOW diagnostic** with no live hook, no automatic correction or message delivery. Original AGE0c STAY_SHADOW, LP1 NO_ATTRIBUTABLE_GAIN, LP2 ALIGNS_NO_GAIN, BJ1 NO_SIGNAL, STEP2 UTILITY_FAIL, B3 L1 FAIL, `jepa_weight=0`, Age authority0, Redmi unmeasured, whole V13 incomplete. No SSOT, model/seed/source cohort, training or Age rights changed.

Next exact command: `cd v13/code && PYTHONPATH=. python -m unittest -v tests.test_age0d_exact_representability tests.test_age0d_answer_audit tests.test_age0d_cli tests.test_age0d_locale_ambiguity_review`. Independent review of PR #762 and source-wide frozen-runtime owner approval required before integration. Genuine user-answer false-alarm calibration and Redmi validation remain separate open gates. Do not auto-merge or promote utility.
