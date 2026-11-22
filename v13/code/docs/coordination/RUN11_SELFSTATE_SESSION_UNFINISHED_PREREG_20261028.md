# Run11 F3 SelfState session-local unfinished action count — prereg (2026-10-28)

**Owner:** GPT-6; independent F3 state correctness package on child branch `assistant/v13-run11-selfstate-session-unfinished-20261028`, exact parent `e7c99eb95c90ac6538c94a7d2611fc5d1b72cae5` (World multi-action recovery candidate, full CI pending). Review-only; neither this nor its parent is merged to production/main. No model, seed, canonical protocol, registered cohort, tool authority or Age change.

**Observed source-level defect:** `WorldState.self_state()` persists a session-keyed `SELF_MODEL:<session>` but `unfinished_actions` counts **all** Store actions with status `DISPATCHED`/`OUTCOME_UNKNOWN`, including another session. A new session can incorrectly report prior session's unfinished action load. Historical separate review PR #422 already used an event-session join; current PR #861 chain does not. Reconcile branches rather than silently asserting production fixed.

**Acceptance test (actual temporary Runtime/Store, synthetic only):** create an unfinished action in session A with an authoritative event and forecast, then create session B. B's `self_state()['unfinished_actions']` must be 0; A's must be 1; adding an unfinished action to B makes B=1 and A=1. A completed FINAL action is not unfinished; switching back and restart retains correct per-session counts. No writes to old action state, no new action processing, no learning or tools.

**Minimal change:** replace only global unfinished count with `JOIN events` and `e.session_id=?` bound to current `r.session`. Keep memory corrections/replay global intentionally, preserve existing profile/model/permissions/authority fields and existing single-session behavior. First reproduce RED before code, then exact-source Linux focused/full suite, compile/privacy/diff and closed raw evidence.

**Negative gates unchanged:** STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 heldout FAIL; jepa_weight=0; Age0 RECORD_ONLY; no Redmi/whole-system proof. Never promote from software test.
