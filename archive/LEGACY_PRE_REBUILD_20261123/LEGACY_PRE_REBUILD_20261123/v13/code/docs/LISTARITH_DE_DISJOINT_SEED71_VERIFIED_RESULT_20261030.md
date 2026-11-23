# Seed71 German list_arith disjoint generalization — verified RED, 2026-10-30

Review-only child of #1217, branch `assistant/v13-listarith-de-disjoint-stress-seed71-20261030`. Immutable prereg at `d1266cca670ea2e0ce10b3be2d5f27ec0690b54f`, **36 disjoint questions frozen before evaluator** at `c34db2dca64811f8b8012fac4c5f5dcc6e3c2d79`, fixture Git blob `406013716d90411704c1dcc2a51c56e7b96cbb64`. Existing seed67 detector blob `d13120bcd6be6572b6e63af5f2b5a3242e7d0b98` and seed67 fixture blob `264805f54b697f693dc0e9730f0448f447fa8141` unchanged.

## Verified original evidence
GitHub Actions **41010250307 GREEN for test/integrity execution** at exact source head `64b754d0ad12282cb8acf031b38f39e256372f1f`. Original artifact **12956839350**, ZIP SHA256 `f5781b4143ebbce605ba68b3f159ac5fe827a8b4c294a345f47979030d455428`, CRC clean, **20/20 inner SHA256SUMS**, all **8/8 stages EXIT0**, privacy CLEAN, diff clean, **14/14 tests PASS** (8 new seed71 + 6 frozen seed67 regressions). Original ZIP backed up in private Library `/V13-Checkpoints/2026-10-30/Run12-Listarith-GermanStress-Seed71/`.

**Frozen generalization result: `SHADOW_GENERALIZATION_RED`**, **25/36 exact (69.44%)**, macro-F1 **0.70547**. Class correct: total **8/12**, max-min difference **9/12**, unsupported/None **8/12**. **Four false-positive operation proposals on 12 unsupported questions**, including an explicit negation (N01, “Addiere die Werte bitte nicht”) and metalinguistic sum questions (N04/N08/N09). Seven false-negative supported paraphrases: T03/T04/T10/T11 and D05/D07/D11. Full original row predictions/reasons, confusion matrix, source blobs and negative gates are in `REPORT.json` in the original CI ZIP. No labels, predictions or scores were changed after the run.

This demonstrates **seed67 24/24 narrow synthetic holdout did not generalize** to these new templates; it does not measure native C3 or real German users. Existing detector was not retuned or connected to a live tool. Do not merge/activate as a utility proof.

## Next substantive work
Preregister a **separate** candidate for German negation/metalinguistic abstention and broader total/max-min phrasing, train/develop only on the now-exposed seed71 failures, and test on a **fresh, independent seed73** holdout. A candidate must not silently alter seed67, English list_arith, age/approval, C5 or any live consumer. Also pursue native C3 German typed-value extraction and tool-result answer quality independently, not by assuming this regex score implies it.

Gates unchanged: Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; jepa_weight=0; Redmi UNMEASURED; whole V13 INCOMPLETE. Remaining platform budget UNKNOWN.
