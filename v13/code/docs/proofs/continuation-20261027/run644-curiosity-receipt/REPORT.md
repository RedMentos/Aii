# Run644-AG5 — curiosity needs an actual non-abstaining FINAL receipt (2026-10-27)

**Review-only child of Run643 PR642** at `df96269a179b9942ee517f02cbb7069ed80c5ba5`. Independent of concurrent `codex/gpt6-run644-c3-contrastive-20261027` (different owner/files; no native/model jobs here). Canon and all registered model cohorts unchanged.

## Concrete functional correction
`v13/agi/live.py:goal_turn` previously recorded AG5 curiosity error=0 whenever the caller supplied `status=FINAL`, *before* checking the persisted assistant message. A missing FINAL message, a refusal, and an explicit abstention could all become false evidence of successful learning progress. Now a same-event, same-session, nonempty persisted FINAL assistant message with no `reference_only`, leading explicit non-answer, or abstention is required before zero-error evidence (or a numeric measured grounding error) can be recorded. Otherwise AG5 records error=1. This is a conservative task-failure proxy, **not semantic correctness** and not a new autonomy right. JEF goal completion uses the same receipt validity.

## Original RED preserved
- `tests/test_run644_curiosity_receipt.py` and `PREREG.md` committed before repair.
- Actions **40439220413** at `7a87692de6e63a69c7056fd11eaa02f7567b4457`: **19 tests, 3 FAIL** (missing FINAL, refusal, abstention incorrectly returned curiosity error=0); normal FINAL and ERROR controls PASS; compile0, privacy0. Original raw ZIP GitHub artifact **12705142134**, SHA256 **9890c53ed655f57ded4dbdf0b0f48c4a5d8ecee34d1660c43a2dd9034b33e44d**.

## First GREEN, exact code source
- Actions **40439305110** at `b073fbb87b5d453dbb4d1d3812c98ad2e2dafe56`: **19/19 PASS** including Run633 noanswer and AGI live hooks; compile0; privacy CLEAN.
- Original raw ZIP artifact **12705221912**, SHA256 **f7df9a8d73a223d699f55abf9aef4719170bf23a0291ea804973e46f7bd57404**. Both RED/GREEN ZIPs downloaded, CRC verified, source HEAD and exit flags independently checked; uploaded to private Library `/V13-Checkpoints/2026-10-27/Run644-AG5/` and re-materialized byte-identical.
- Additional **whole-source suite** requested on source+CI head `ad14a3280b6aae3dfd0349c297307eeec3a7da54`, Actions 40439486942: **PENDING at initial report**. Do not claim this run GREEN until raw verified.

## Unchanged negatives and next
STEP2 **UTILITY_FAIL**, B3 L1 **FAIL**, Body-JEPA **UNAVAILABLE**, `jepa_weight=0`, Redmi **UNMEASURED**, V13 **INCOMPLETE**. No native/model test and no automatic main merge.

Next: verify Actions 40439486942 and back up raw; then independent next package should bind AG4 skill outcome credit to a persisted answer/actual measured outcome, or advance another functional World-JEPA/Body path. Keep AG5 task-error proxy distinct from actual answer correctness; do not promote autonomy.
