# Run86 RED-first amendment — paused verified preflight is deliberately refused (2026-10-29)

**Do not discard the original RED.** Run86 original exact head `9892f67c7cfae583438177b5532b93ab7a5bb5a1`, GitHub Actions `40784995222` FAILED, raw artifact `12859490487`, uploaded ZIP SHA256 `8321e00e8db49c2e3231259b35b63046ce57b8ff4a4a868f1363fff34a00e5d8`. Source hashes and original prereg were bound; focused 22 tests, 1 ERROR. Full suite was SKIPPED after focused RED. Original negative result stays available in Actions.

Observed traceback: while `:stillstand` has paused the queue, `:verified` raises `ValueError("RUNTIME_NOT_IDLE")` in `scripts/ask_verified_budget.py::_age0_only` (checks `not r.idle() or r.store.queue_paused()`). This is an intentional source-bound operator safety restriction; the original prereg's expectation that a source preflight remained callable **during pause** was incorrect. It would be unsafe to weaken `_age0_only` just to make this test pass. The standstill contract says manually typed commands may run, **not** that all commands are authorized to bypass individual preconditions.

## Corrected predeclared assertions for follow-up test revision
- During standstill, before and after restart, human `:verified` must be explicitly **refused** with `RUNTIME_NOT_IDLE`, no native model invocation, and source record retained.
- After explicit `:stillstand aus`, `:verified` must again return READY for the same exact human source id and zero native calls; repeat after restart.
- Preserve original independent ToolRegistry NOTAUS block, persisted Age freeze/queue, and pre-existing human stop preservation checks.
- Update only test and hash-bound CI to match corrected safety contract. No changes to runtime, `standstill.py`, `ask_verified_budget.py`, operator, model, cohort, seeds or acceptance gates. Keep original RED and corrected result separate.
