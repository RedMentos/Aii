# Run646 — AG4 skill outcomes exactly once per durable source event (2026-10-27)

Parent: PR646 head `317c4c95c0a14ba0dbfba39bb9d37f42a0abf075`. Isolated review child; no edits to Claude branches, canonical cohorts, source/model hashes, age, approval or body learning. Ownership: `v13/code/v13/agi/skills.py`, one call site in `v13/code/v13/agi/live.py`, new `tests/test_run646_skill_event_once.py`, isolated workflow and evidence.

## Hypothesis / concrete defect
After Run645 corrected AG4's missing FINAL receipt, `after_turn` still calls `SkillLibrary.record` on every invocation. Replaying the same event twice (restart/retry/duplicate hook) increments `uses` and `successes` twice and can inflate procedural promotion evidence. A second terminal report for one event must not count as an independent experience.

## Preregistered acceptance
1. Two same-event `after_turn` calls with a real FINAL receipt count exactly one use and one success.
2. Duplicate ERROR/failure counts exactly one use and zero success; later FINAL for the same terminal event cannot rewrite the first receipt.
3. Reopening the SQLite store and replaying the same event does not count again.
4. A receipt cannot be reattributed to a different skill, or a different session; invalid event IDs fail closed.
5. A failure inside the state update leaves neither the skill counter nor the event receipt committed; retry can succeed.
6. Distinct source events still each count; existing Run645/Run644/AGI tests remain passing.

Implementation constraint: skill state and unique per-event receipt must be written in ONE SQLite transaction under the existing store lock; a separate state marker before/after a non-atomic `record` is insufficient. Keep legacy `SkillLibrary.record` behavior for explicitly unbound synthetic/manual samples. Event receipts store IDs/outcome only, never user text. No new autonomy, rights, STEP2/B3/Body-JEPA promotion.

Evidence: Linux SQLite/source-only Actions; no native weights or Redmi. Preserve RED and GREEN outputs and negative gates. Existing parent full-suite is RED (5 FAIL, 73 ERROR), not a passing baseline.