# Run11 STEP2 cross-arm B1 identity — closed review checkpoint (2026-10-28)

Owner: GPT-6; review-only branch `assistant/v13-step2-crossarm-b1-identity-review-20261028`; parent PR #826 exact `0cc5e59fc1c91a71b0b232b42f70668c562d9d2b`. No changes to parent, main, Canon, frozen Runtime or historical cohorts. Branch-scoped software-only regression.

## Reproduced bug and narrow correction

The four-arm scorer accepted an inconsistent B1 weight across distinct-body TC/TP and shared-body SC/SP arms, even when each pointer pair and all three seeds were internally consistent. This confounded the intended distinct-vs-shared causal control. Prereg committed first `107cd4525d043b4192e746e39e47a9e97eacbc48`; RED test commit `384bf44a7a08534cc723ba533bfed899fb93acc2`; workflow commit `1162cd6f4a90f511fe164684ac4b6161818d7692`.

RED Actions `40624346822`: 7 focused, 2 expected FAIL (`ValueError not raised` for shared-pair and distinct-pair B1 swap), other 5 pass; compile, privacy and diff exit 0. Raw ZIP GitHub artifact 12788712035; SHA256 `ea9a0f61e48705e1fb18a17e5450809a347e0f6b29df7ee22f707f797c2d15fe`; CRC and 10 internal hashes verified.

Source-only fix `4e6a97404dafa7ae8bf9898eb15e6273210db8a6` adds cross-arm B1 identity check in `scripts/step2_longnote_fourarm_analysis.py`; Git blob `64a8ba7fc35b2e16356faed3b7be166f7f550fc8` (parent blob `a1fff2f0989ae84c623aab6a3f6e238c88fad3b8`). GREEN Actions `40624407139`: 7/7 focused PASS, compile/privacy/diff exit 0, privacy CLEAN. Raw ZIP artifact 12788701765; SHA256 `eaa3f28a0d129a21ec211978d7231d304774765287fc196ff46e631c19fa042c`; CRC and 10 internal hashes verified.

Private persistent backup (not rejected public Drive): `/V13-Checkpoints/2026-10-28/Run11-STEP2-CrossArm-B1-Identity/{RED-40624346822.zip,GREEN-40624407139.zip}`. Both Library re-materialized and byte-identical to downloaded GitHub artifacts. No private bytes published in Git.

## Evidence limits / next exact work

This tests a **synthetic scorer contract**, not real native inference. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 heldout FAIL, jepa_weight=0, Age0 RECORD_ONLY; no gate promotion or whole-system completion. Current model-byte proof from parent PR #826 is separate and does not imply native inference. Full-suite Linux regression is still required after integration into the evolving #826 branch; our branch-specific stdlib tests are not a substitute.

Next: inspect latest parent PR #826 head and CI; independently review the B1 identity check against the exact registered model map, then integrate via review (never overwrite the parent). Run `cd v13/code && PYTHONPATH=.:tests python3 -m unittest -v tests.test_step2_crossarm_b1_identity_20261028 tests.test_step2_longnote_fourarm_analysis_20261028` and full `python3 -m unittest discover -s tests -p 'test_*.py' -q` in an isolated environment with pinned dependencies. After saving this checkpoint, pursue an independent substantive V13 organ package, not a STEP2 gate claim.

Actual platform budget remaining: UNKNOWN. Checkpoint is intermediate, not acceptance.
