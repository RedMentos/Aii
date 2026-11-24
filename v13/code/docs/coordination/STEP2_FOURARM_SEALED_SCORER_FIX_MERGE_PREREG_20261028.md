# Four-arm sealed IO + strict tool-status scorer — integration prereg, 2026-10-28

This is a review-only merge of own PR #820's independent RED-first correction into child PR #821. Do not overwrite any other owner's branch, frozen cohorts or Canon.

Parent scorer #820 latest exact `cfe531e116dfc5307985e12846f513d5c7feccdb`, preceded by RED-first test commit `f6d238d274b6e74a7614a01a2b73fb11ad7cf343`. Counterexample: an unexecuted summary with `tool_status=RUNNING`, `NOT_RUN` or `PREREGISTERED_NO_INFERENCE` passed the original broad negative-list status check. Local isolated RED: 3 failed subtests. Fix now accepts only actual replay completion verdicts `TOOL_UTILITY_FAIL` and `TOOL_UTILITY_PASS_SCOPED`; local scorer+IO suite 9/9 PASS. Original synthetic `SCORED` placeholder replaced by a real status label, not by a native claim.

This branch's sealed input source and tests remain unchanged. Import precisely scorer source blob `a1fff2f0989ae84c623aab6a3f6e238c88fad3b8` and scorer test blob `df02bb9ca7a56635509c09431a212d5bd18463c3` via two-parent merge (first parent this prereg, second parent #820 corrected head). Re-run combined Linux focused/full CI on exact merged source, check raw exits and privacy. All results remain synthetic/software; no model inference, Redmi, B3 or STEP2 promotion.
