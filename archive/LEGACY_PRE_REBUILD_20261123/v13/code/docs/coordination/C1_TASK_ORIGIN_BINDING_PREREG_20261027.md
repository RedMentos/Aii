# C1/JEF active-task origin binding — independent review prereg (2026-10-27)

Review-only child of PR #773 at exact parent `86c440a5607b0610adfdd6ca8605186db4d6a56a`; not `main`. Owner: GPT automation11 independent C1 review. New tests, dedicated workflow, minimal `v13/code/v13/executive.py` fix, and coordination evidence only. Do not alter frozen runtime/model/learning cohorts, previous RED/GREEN artifacts, or shared BUILD_STATE.

## Risk / falsifiable RED

`Executive._clean` currently treats any hash-valid `active_task.source_ref` as an authentic task, and `begin` carries it across events if its persisted `origin` equals `EXPLICIT_OPERATOR_TASK`. Thus corrupting *only* the persisted C1 state can turn an unrelated valid source (including another session's) into a fake operator-pinned task, or resurrect an operator task after `:task clear`. It can also replace a current user task with a valid but foreign source. These are source-origin authority violations, even though the blob hash is correct.

RED tests: (1) foreign valid source + forged `EXPLICIT_OPERATOR_TASK` is rejected; (2) genuine decision packet from a *different session* is rejected; (3) previously valid pinned task cannot reappear after a later clear decision; (4) `SOURCE_USER_REQUEST` task must equal current event's exact source; (5) positive controls preserve current user task and genuine latest pinned operator task across later events. Existing #773 goal/action and continuity tests must still pass.

## GREEN contract

For ordinary tasks, require origin `SOURCE_USER_REQUEST` and exact current event/source/session binding. For explicit operator tasks, require origin `EXPLICIT_OPERATOR_TASK`, exact source bytes, and the **latest** session-bound `HumanDecision` packet with `kind=executive_task`, matching `source_ref` and `value`; a newer clear decision revokes an earlier task. Reject malformed or unbound tasks to `None`. Preserve valid same-session operator task across new user turns. No new tool rights, no auto-correction, no learning/age authority.

## Evidence and gates

Run focused tests RED before source change, preserve raw failures. Then GREEN focused and source-wide software regression, compile, privacy and diff checks on a separate branch. All evidence explicitly SOFTWARE_ONLY; no Redmi/native model, STEP2/B3/LP1/LP2/BJ1/JEPA utility or V13 completion promotion. Independent review required before integration. Remote bytes must be verified.