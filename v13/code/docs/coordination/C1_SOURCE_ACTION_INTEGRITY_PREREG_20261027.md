# C1/JEF persisted goal/action source-binding independent review — prereg (2026-10-27)

Review-only child of PR #768 exact parent `2a7c5448df432f73a2cde225e97078c5188f8711`, not main. Independent owner GPT automation11; only `v13/executive.py`, new `tests/test_executive_source_action_integrity_review.py`, a dedicated CI workflow, and coordination notes/delta. No modification to existing test cohorts or negative gates.

**Observed code risk:** `Executive._clean` validates `goal_source_ref` exists but trusts persisted `goal` text without equality to source; a corrupted stored goal can be rendered as current executive goal. It also passes persisted `current_action_intent` through untyped, so `report_context` can crash on truthy non-dict and unbound action IDs may be surfaced as legitimate action metadata.

**RED counterexamples before fix:** mutate only persisted C1 state while preserving a valid source ref: (1) replace `goal` with attacker text, assert view recovers original exact source, (2) replace `current_action_intent` with list/int or fabricated dict, assert fail-closed no crash, (3) reuse an action from a different event, assert rejection. Positive control: real `update(...,action_id=...)` same event remains `LOCAL_TEXT_REPORT` after restart; human-pinned task and original source remain valid. No new permissions or authority.

**GREEN candidate:** in `_clean`, derive `goal` from the verified source bytes rather than persisted text; require action dict with fixed type `LOCAL_TEXT_REPORT`, exact current `last_event_id`, session and DB-backed action/corollary binding. Reject malformed/unbound intents to None. Preserve existing source/session validation, event order, and Age-0 gates.

**Evidence:** software-only RED/GREEN on a branch-scoped GitHub Actions runner, full suite if feasible, privacy and diff checks, raw exit artifacts. No native, Redmi, learning utility or Age promotion. Do not merge without independent review or overwrite other owner work.
