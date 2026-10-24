# Run68 raw evidence / independent review

Base PR100 Run67 `e6104c8cff892cd110c126fc4f2c13c51fc58a06`. Original source `learning.py` blob `30e546ee14b26608ef40b06e20bcaa0b5979a8bb`; patched blob `7c84899e0418b61c45e4362aab017db0ebf36f09`.

Original source passes `{k for k,_,_ in data}` to `jefoutcome.training_rows`. Since `data` contains only human `permission=='learn'`, a newer `record` human decision cannot block lower-authority self-labels. Isolated reproduction: 4 tests, one RED `test_record_permission_blocks_lower_authority`, observed `[set()]` instead of `[{'ctx1'}]`. No optimizer executed.

After patch `set(unique)`, isolated replay 4/4 PASS. Negative controls: human learn remains blocking; no HumanDecision does not block; stale revision does not claim current context. The first patched replay failed 1/4 because a fake Store incorrectly returned an ExecutiveDecision even for a NULL packet id; that reviewer/test-double failure was preserved and corrected.

Test class `tests/test_jef_human_precedence_run68.py` is committed for actual full-checkout integration, **NOT RUN** here because GitHub DNS blocks a full checkout. Isolated prologue was manually transcribed from the exact Run67 source and tested with Python 3 + NumPy. No real V13 Store, full suite, official privacy scan, native models or Redmi measurement. `compileall` PASS on scratch/tests.

Open review: the 512-row human-feedback limit may still exclude an older RECORD decision, allowing a later self-label to fill the context. Follow-up separately; do not mark human precedence globally proven.

Gates unchanged: STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; jepa_weight=0; V13 INCOMPLETE.
