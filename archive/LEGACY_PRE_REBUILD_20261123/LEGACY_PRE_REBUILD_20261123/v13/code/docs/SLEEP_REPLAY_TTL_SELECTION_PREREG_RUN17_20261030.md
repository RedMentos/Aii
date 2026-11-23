# Run17 preregistration — F9 Sleep replay TTL at selection (2026-10-30)

Review-only child of Run16 PR #1343 exact parent `6a5093a604b14e9d1bd288af504064ea29d72830`. Owner GPT-6; scope `v13/code/v13/sleep.py`, new test `tests/test_sleep_replay_ttl_run17.py`, isolated Actions workflow and checkpoint. Canon SHA `218464b12a2d27d92524c751922fa8e1c3fb0ea7`. No other owners' files or frozen cohorts changed.

## Defect hypothesis

`ReplayQueue.sync` persists an `expires` timestamp, but `ReplayQueue.due` only checks `next_due`, priority, type and retirement. TTL is enforced later in `sleep_c`; wake/a-only cycles never call C and full Sleep A runs before C. Therefore a human correction that has expired by TTL can still be replayed (and considered for consolidation) before retirement. The existing replay packet, memory and Store must remain intact; expiration only removes the item from due selection, and C remains responsible for durable TTL retirement.

Frozen tests before source patch:
1. Real SQLite feedback produces a due replay item just before `expires`; at `now==expires` and later, `due` and `sample` must exclude it (including `wake`).
2. Mixed expired and valid entries: only valid item selected in `run('a')` and `run('wake')`; no `SLEEP_A` packet for expired item; original replay rows and F5 memories untouched.
3. Reopen Runtime/Store with persisted schedule: expired item cannot reappear as due; `run('c')` retires it with reason `TTL` without deleting raw provenance.
4. Existing Sleep scheduler/retention/TTL/CAS and cross-organ tests remain unchanged.

Expected original RED: expired item included. Candidate changes `ReplayQueue.due` only (with explicit `expires>now`), no clock rewrite, no change to source/model hashes, no implicit learning/approval, no Age0 promotion. Linux SQLite software evidence only, not native/Redmi. Historical fullsuite RED remains unwaived. Next: independent review, exact raw/CRC/SHA private backup, full-suite comparison, continue other organs.
