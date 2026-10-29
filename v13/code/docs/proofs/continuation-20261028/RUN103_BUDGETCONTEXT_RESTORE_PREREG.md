# Run103 prereg — shared BudgetContext restore journal gate for all offline source entrypoints (2026-10-29)

Owner: GPT-6 scheduled continuation; **independent review-only sibling** of Run97 GREEN #1003 exact `8dcec32c4da3c992ebca9d038fabba3009bdda8b`. Run102 #1006 separately tests a standalone `source_exact.main` guard; **do not modify or silently integrate Run102**. Run103 addresses the independently confirmed *remaining* path: `scripts.ask_verified_budget.main` and any direct `BudgetContext(home)` construction currently reach `initialize/Store` before `backup.recover_startup`.

## Scope and frozen changes

One narrow source edit only: `scripts/ask_verified_budget.py` at original blob `75ca7f3f197665f665d9582b7f5c2efb1f598235`, add a fail-closed `recover_startup(self.home)` **before** `initialize(self.home)` in `BudgetContext.__init__`. Preserve all native query logic, model catalog/revision, source grammar, source verification, session semantics, seed13, timeout/token bounds, runtime and user/age/approval gates. No new model call or side effect on ordinary no-journal path. Original `v13/backup.py` `409c4e13ba0754364d708e4dbe803bd740954b69`, `v13/store.py` `0779d986fb8aee8aa01c5df5f656889d4bd56348`, `scripts/source_exact.py` `ab67f77fb988f8a0e48fda390a52e94126e084da` stay unchanged.

## Actual acceptance

1. Real temporary Age0 Runtime/Store/F1/F5 fact `Project Elyra budget = 615 Euro` persisted and closed. Direct `BudgetContext`, standalone `scripts.ask_verified_budget.main` (READY) and standalone `scripts.source_exact.main` (SOURCE_EXACT FINAL) preserve baseline, all model-free.
2. For each entrypoint, path-escaping `restore_pending.json` must cause ERROR/ValueError **before Store opens**, preserve journal and original SQLite DB bytes. Use a Store-construction spy to prove no DB open, not a mocked restore.
3. Valid no-op pending journal must be reconciled under coordinator lock before Store; both CLIs preserve source authority. A concurrent live Runtime lock plus pending journal must refuse. Missing-home existing behavior remains.
4. Existing Run97/source-guard suite and full suite, source hashes, compile, privacy/diff, closed original raw artifact. No native model in this software cohort.

**Fail closed** if journal recovery errors. No promotion of STEP2, B3, Body-JEPA, LP3, jepa_weight, Redmi or whole-system completion. Import into active Run98/Run99 only after independent raw GREEN and integration review; avoid duplicate recovery code where possible.
