# Run18 preregistration — F9 Sleep explicit batch budget admission (2026-10-30)

Review-only child of Run17 PR #1344 exact head `760f4a4cfa0f26f65c1cbd29202c8c2633eab5a6`. Owner GPT-6. Scope `v13/code/v13/sleep.py`, new `tests/test_sleep_batch_budget_run18.py`, isolated Actions and scoped BUILD_STATE. Canon SHA `218464b12a2d27d92524c751922fa8e1c3fb0ea7`; no model/source/seed cohort changes.

## Bug hypothesis

`SleepCycle.run(...,batch=...)` uses `n=batch or policy_batch` with no type/range validation. `batch=-1` flows into `ReplayQueue.sample` negative quotas and Python negative slices, potentially selecting almost all queued items instead of zero; `batch=True` masquerades as 1; `batch=1.5` and strings can error after entering a cycle; `batch=0` silently becomes default. A caller-supplied batch cannot bypass the explicit policy bounds (`POLICY.batch` 1..64, `POLICY.wake_batch` 1..8) or create more replay work than requested.

Frozen test-first cases:
1. On real SQLite with >=4 correction replay items, `run('a',batch=-1)`, `batch=0`, `batch=True`, `batch=1.5`, `batch='2'`, `batch=65` and `run('wake',batch=9)` must raise ValueError before any `SLEEP_A` packets or schedule mutation.
2. Explicit `batch=1` selects at most one due item; `batch=2` selects at most two, never more. Default `batch=None` preserves existing policy behavior. Wake max8 accepted; 9 rejected.
3. Invalid `batch` on Sleep B/C also fails before side effects, not silently ignored. Real SQLite restart keeps original replay rows.
4. Existing Sleep F9/ContextOS/neuromod tests remain unchanged.

Candidate validates exact Python int and mode-specific BOOT policy maximum before `run` does any work; does not change policy default, Age/resource ceilings, source/approval gates or native work. Original RED and candidate raw hashes, stage exits and private byte-identical backup required. Historical fullsuite RED remains unwaived. Linux software evidence only.
