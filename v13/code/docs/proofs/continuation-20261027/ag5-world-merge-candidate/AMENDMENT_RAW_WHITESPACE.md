# Amendment — immutable raw proof whitespace (2026-10-27)

Second complete three-conflict CI Actions **40457859209** at `f76e750bc45ebdd42c69373ebd473f24d7bd9f92` was **RED** after resolving all three conflicts: `git diff --cached --check` failed because many pre-existing **raw evidence logs** added by the AG5/World union contain historical trailing spaces (e.g. `docs/proofs/continuation-20261025/world-timing-run108/CI_RED_FULL_RAW.log`). These are original failed-run receipts. They must **not** be rewritten or stripped to make a style check green.

The exact source-only correction: enforce `git diff --cached --check -- v13/code/v13 v13/code/scripts v13/code/tests`, retaining a non-gating full-diff whitespace report in the CI artifact. This does **not** waive compile, tests, source safety, privacy or unresolved-conflict checks. Keep the full-diff warnings and previous RED artifact. No owner/main merge or age/approval promotion.
