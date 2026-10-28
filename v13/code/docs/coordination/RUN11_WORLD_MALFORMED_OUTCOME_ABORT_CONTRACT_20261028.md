# Run11 World malformed-outcome candidate — ABORTED AFTER CONTRACT REVIEW

This is a **preserved failed hypothesis**, not an accepted fix.

The preregistration assumed `Store.finish_action` could persist non-dict `actual` values. Independent source review disproved it: `Store.finish_action` calls `self.add_packet('ActionOutcome', packet(..., actual=actual))` **before** writing the action row; `Store.add_packet` calls `validate(kind,p)`, and `contracts.REQUIRED['ActionOutcome']['actual']` is `dict`. Therefore `[]`, `null`, string and integer values are rejected before the durable outcome write. The proposed crash/recovery test cannot create the alleged state via the authorized Store API. No evidence shows this bug exists in the valid runtime path.

Do not change or weaken `ActionOutcome` schema to make the test pass. The candidate source/test are retained on the review branch as a negative attempt, but PR #862 is closed without merge. Its separate CI, if it runs, must be preserved as RED rather than reinterpreted. The distinct numeric duration integrity #861 **remains valid**, because negative and boolean values are valid JSON numbers/bools inside an `actual` dictionary and pass the dict-type contract.

No production/main changes, native inference, Redmi, learning or gate promotion. Next: finish #861 CI and continue a different authorized canonical package.
## Closed negative software evidence

Run **40644181764** at `6663fe8c18db09aaee4c342564f1dc84f25779d0` **RED** exactly as the independent contract review predicted: focused 8 tests, **1 failure and 5 errors**, including `ValueError: ActionOutcome.actual: fehlt/falscher Typ`; full suite intentionally **SKIPPED_RED** after focused failure. Source pins/install/compile/privacy/diff exit0. ZIP artifact `12797081613`, SHA256 `63abd9eb78a6624ba680a73cf014be45dbb426d36127fe9877f762625fd03bc5`, CRC clean, **16/16** SHA256SUMS valid, private Library `/V13-Checkpoints/2026-10-28/Run11-World-Integrity/WORLD_MALFORMED_OUTCOME_RED_40644181764_sha63abd9eb.zip` re-materialized byte-exact. The failure is a useful proof of existing contract containment, **not** a reason to weaken it. #862 remains closed/unmerged.
