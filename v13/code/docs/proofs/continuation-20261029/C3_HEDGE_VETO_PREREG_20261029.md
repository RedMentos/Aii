# V13 C3 F1/F5 sourced budget lexical contradiction/hedge veto — prereg (2026-10-29)

## Parent and reproduced failure
- Review-only child of PR #1153, exact parent `c5052795070ccf36b5273b4907562fd3220f51a0`. Owner files only `v13/code/scripts/ask_verified_budget.py`, dedicated new test/proof/workflow. No other owner file touched.
- Current script Git blob `22d479e83478fd8a7581f26732301fa272edecc2`; Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` unchanged.
- Independent local replay from public source archive at `cdf5f48c5bacbca494674a2554e96bf1e4e8dc2b` (same script blob) shows `_answer_uses_euro_source` returns True for five contradictory/uncertain responses despite verified source `Project Elyra budget = 615 Euro`: `isn't 615 Euro`, `615 Euro is false`, `I doubt ... 615 Euro`, `may have 615 Euro`, `615 Euro was rejected`. Exact affirmative `The budget for Project Elyra is 615 Euro.` also returns True. These are source-consumer software witnesses, **not** native C3 outputs.
- Existing focused ContextOS/C3 suite 36/36 PASS locally on the parent archive, showing the missing lexical veto is not covered by those existing tests.

## Registered tests and intended change
- Add fail-first adversarial test for contractions, refutation, doubt, hedge and conditional language, including curly apostrophe. Existing unambiguous positive English/German budget answers must remain accepted. Integrate one synthetic native generator mock through `query()` to confirm that a contradictory output is withheld after one call and native release.
- Extend the **conservative lexical veto only**. Do not claim general semantic truth verification; exact source identity, number, project and currency checks remain unchanged. Reject uncertainty/negation markers such as `isn't`, `false`, `doubt`, `may`, `might`, `rejected`, `unconfirmed`, `allegedly`, `perhaps`, `vielleicht`. Prefer fail-closed false negatives to falsely sourced answers in this narrow budget lane.
- Run prereg RED before source change, then focused GREEN with original raw, hashes, privacy/diff, Canon, existing C3 tests. No native model download; no learning/age/approval changes.

## Limits
No arbitrary user messages are rewritten; this only gates opt-in native source-budget outputs. Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight0, Redmi UNMEASURED, V13 INCOMPLETE. Historical registered source/model/seed/cohort hashes remain preserved.
