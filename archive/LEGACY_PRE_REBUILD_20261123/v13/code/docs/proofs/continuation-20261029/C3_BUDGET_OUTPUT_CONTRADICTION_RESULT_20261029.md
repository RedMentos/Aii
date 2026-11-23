# C3 / F1-F5 opt-in generated budget output contradiction veto (2026-10-29)

## Scope and source
- Parent PR #1144 exact head `de9bd8206cb6294187f42ca46c20ea5434b43fd1`; review branch `codex/v13-c3-budget-output-guard-20261029-auto10ag`. No parent/main overwrite or production merge.
- Preregistered before source `193463514d1f859266c8894d19abfa6faa11756f`, new test `b7b8c55927da2df4de203d684b0d93f6dbf8b1ce`.
- Source bug: `_answer_uses_euro_source` accepted contradictory native C3 text such as `615 Euro is not the budget` and mixed `615 Euro and 615 dollars` because the verified number still appeared and all numeric tokens equalled the source amount.
- Conservative veto in `scripts/ask_verified_budget.py`: reject question marks, explicit negation/uncertainty words and unsupported currency names/symbols before considering a C3 generated budget response `FINAL`. Existing amount/project checks, F1/F5 admission, C3 model pin/deep hash, native unload and Age0 gates remain unchanged. No semantic truth guarantee; false negatives deliberately allowed.
- Final script Git blob `87b1addd06680ce01f8247df735fa305371ceb93`, test blob `0bb4cb5f1566e389b6ed59adb839405d7637a195`. Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` unchanged.

## RED and GREEN
- **Original RED**: Actions `40949673704`, head `e1cff47e0dbe16b2e4607c6415da546de6ba5367`, 36 tests, 9 failing assertions/subtests for negation and same-numeral foreign currency. Artifact `12931795097`, ZIP SHA256 `c2e0c05f7318b8185cbe2f81d72b872741845ced4ff09f51603221bb68ab6a7b`, CRC clean, 18/18 inner hashes.
- **Candidate RED**: Actions `40949729998`, head `1104d7c012ededa0fbbc6fa4ed2b37e8e0288bc4`, 36 tests, 4 FAIL due to mistakenly double-escaped regex word boundaries in the first candidate. Artifact `12931171094`, ZIP SHA256 `c589e086ac96865ad8c9849bc38804006116a0a0146e7b4404a8ee8adebef41b`, CRC clean, 18/18 hashes. Corrected in `5623e42ebf57a0c0e74b4aedd617b456c79b12fb`; failed evidence preserved.
- **GREEN**: Actions `40949778639`, head `5623e42ebf57a0c0e74b4aedd617b456c79b12fb`, 36/36 software tests PASS. Artifact `12929849764`, ZIP SHA256 `08d66b7d9eb7fc4bc6f1d13e8fdaa6ce8eb7367716bbcbd751e66b22568171cd`, CRC clean, 18/18 hashes. CANON/VENV/DEPS/PIP_CHECK/FOCUSED/COMPILE/PRIVACY/DIFF exits all 0. Integrated fake native runner exercises actual Runtime and Memory with one simulated generated answer; not real C3 inference.
- All three raw ZIPs privately saved in `/V13-Checkpoints/2026-10-29/Run10-C3BudgetOutputGuard/`, re-materialized and SHA256 byte-exact verified.

## Gates and next work
- REVIEW_ONLY SOFTWARE / fake native C3 runner, not real-weight Linux native and not Redmi. No model/seed/source/cohort pins altered. No general answer correctness or language gain claim.
- Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight0; Redmi UNMEASURED; V13 INCOMPLETE.
- Next command: `cd v13/code && PYTHONPATH=.:tests:scripts python -m unittest -v tests.test_c3_budget_output_guard_20261029 tests.test_ask_verified_budget tests.test_verified_exact_standalone_cli_20261029 tests.test_verified_exact_budget_20261029 tests.test_source_consumer_admission`.
- Next prerequisites: independent full cross-organ software review, and separately registered pinned real C3 native evaluation of this conservative veto if the current source cohort permits; no promotion from these fake-runner tests. Continue other canonical organs when native prerequisites are blocked.
