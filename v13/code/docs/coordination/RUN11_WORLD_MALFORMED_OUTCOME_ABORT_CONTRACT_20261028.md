# Run11 World malformed-outcome candidate — ABORTED AFTER CONTRACT REVIEW

This is a **preserved failed hypothesis**, not an accepted fix.

The preregistration assumed `Store.finish_action` could persist non-dict `actual` values. Independent source review disproved it: `Store.finish_action` calls `self.add_packet('ActionOutcome', packet(..., actual=actual))` **before** writing the action row; `Store.add_packet` calls `validate(kind,p)`, and `contracts.REQUIRED['ActionOutcome']['actual']` is `dict`. Therefore `[]`, `null`, string and integer values are rejected before the durable outcome write. The proposed crash/recovery test cannot create the alleged state via the authorized Store API. No evidence shows this bug exists in the valid runtime path.

Do not change or weaken `ActionOutcome` schema to make the test pass. The candidate source/test are retained on the review branch as a negative attempt, but PR #862 is closed without merge. Its separate CI, if it runs, must be preserved as RED rather than reinterpreted. The distinct numeric duration integrity #861 **remains valid**, because negative and boolean values are valid JSON numbers/bools inside an `actual` dictionary and pass the dict-type contract.

No production/main changes, native inference, Redmi, learning or gate promotion. Next: finish #861 CI and continue a different authorized canonical package.