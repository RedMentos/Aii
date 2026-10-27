# Run646 — AG4 exact-once source-event skill outcome (2026-10-27)

Review-only child of PR646 exact head `317c4c95c0a14ba0dbfba39bb9d37f42a0abf075`; no main merge. AG4's Run645 durable answer receipt fixed a false-success condition, but repeated `after_turn` for one event still counted independent skill uses/successes and could inflate procedural learning. The new `SkillLibrary.record_once` verifies source event/session, binds skill identity and a compact outcome receipt, and updates both the receipt and skill state in **one SQLite transaction**. Same-event retries cannot double-count, even after reopen. Legacy unbound `record` for explicit synthetic/other training remains unchanged.

## Preregistered original RED, preserved

Prereg commit `d1ec9982cfc2936d907bc7a070fdaaad2f549362`, tests `4d968eab371996ee741c9ba1616874e91c141536` before source. Actions `40443007972` at `aaf07a2ca0a6aea65bc73e8bdaa585bb83594f2b`: 26 tests, 2 FAIL + 4 ERROR; duplicate FINAL counted (2,2) rather than (1,1), duplicate ERROR then FINAL counted (2,1) rather than (1,0), and four `record_once` controls absent. Original ZIP artifact 12706627355, SHA256 `b8a9b9374c00db8074eb63c2cb63cee27a975535d88eb3a1f3a001427c73a2ed`, CRC/source/exit verified.

## First repair failure retained, narrow amendment

First code `b64cb684bb23bafac1071083244f5aac79fe30cc` produced Actions `40443122694` RED: `sqlite3.Connection` has no `rowcount`. The exception rolled back the transaction, so counts remained zero. The failure was recorded prospectively in `AMENDMENT_1.md` at `1b7c7641871e34d770e98081b96492cead4d5f6f`; the narrow correction uses the returned UPDATE cursor's `rowcount`. Raw artifact 12706369660 ZIP SHA256 `b8866d9ab0b375f261770bac077909a6bf36a3e97739f7912f092ba892ed862b` retained.

## Verified GREEN and private persistence

Actions `40443213855` at `c2d24276a21928077d80d4145481f097b1837eea`: **26/26 PASS**, compile PASS, privacy CLEAN; original ZIP 12706772297 SHA256 `746a9475259333fc6f79b01a37f972709d126cf238b07015ac379ff4cff507e6`. Expanded adjacent AG4/growth/JEF suite Actions `40443317470` at `4d7fe36aeb20d9ff3ec84a34cf64f80c6be545fc`: **74/74 PASS**, compile PASS, privacy CLEAN; original ZIP 12707417550 SHA256 `8033532bcfb366ce3431ec9a8abcbcc86b6edd319f422bde3e37bcb08e28cff9`. Every original ZIP CRC and inner exit/source binding checked. All four original archives saved in private Library `/V13-Checkpoints/2026-10-27/Run646/`; byte-identical readback verified. No secret, model file, or private user data in public GitHub.

## Claim limits and next

This is SQLite/Linux software evidence, **not** native/Redmi/semantic skill correctness. The full suite was already RED on parent (4335 tests; 5 FAIL, 73 ERROR), not promoted. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, `jepa_weight=0`, Redmi UNMEASURED, V13 INCOMPLETE; age/approval rights and frozen model/cohort hashes unchanged. Independent integration review remains required. Next independent issue: AG5 curiosity `goal_turn` still observes repeated same-event terminal reports as independent learning errors; isolate and test separately. Recheck native C3 locality and phone proofs only with their original pinned cohorts.
