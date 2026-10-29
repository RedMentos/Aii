# Run102 prereg — fail-closed standalone SOURCE_EXACT during interrupted restore (2026-10-29)

Owner: GPT-6 scheduled continuation, **review-only sibling** of independently GREEN Run97 #1003 exact `8dcec32c4da3c992ebca9d038fabba3009bdda8b` (Actions `40793807136`, original raw ZIP SHA256 `81928e413a87d1358e38a53fd53dd30daa80fedaf7f2e3310666e815b46131cb`, focused34/full2659 OK). Do not mutate Run97, Run98/Run99, frozen SourceConsumer, Store, Memory or active cohorts. Preregister BEFORE code/workflow/test and retain original source.

## Concrete integrity gap and test

Standalone `python -m scripts.source_exact` currently calls `BudgetContext(home)` directly. Unlike `python -m v13 source-answer`, it does **not** call `backup.recover_startup(home)` first. `Store.__init__` opens and may migrate/modify `data/db/brain.sqlite3` even if `restore_pending.json` indicates a partially completed offline restore. That can expose or mutate pre-restore data before the journal is reconciled.

**Candidate fix:** in standalone `source_exact.main`, after existing-home validation and **before BudgetContext or any Store/SQLite open**, invoke existing `v13.backup.recover_startup(home)`. Keep existing Store lock semantics; if recovery cannot safely complete (invalid journal, lock held, inconsistent state), emit `status=ERROR` with exception type, exit2 and **no source answer**. No changes to `query_exact` or source grammar; no automatic user content deletion or source disclosure. Existing normal no-journal path must retain exact behavior.

**Frozen software controls:** original `scripts/source_exact.py` Git blob `ab67f77fb988f8a0e48fda390a52e94126e084da`; `scripts/ask_verified_budget.py` `75ca7f3f197665f665d9582b7f5c2efb1f598235`; `v13/backup.py`, `v13/store.py`, `v13/memory.py`, `v13/source_consumer.py`, `v13/runtime.py` and Canon remain unchanged. Only modify standalone source_exact.py in new review branch plus new test/doc/workflow.

## Frozen acceptance

1. Actual temporary Runtime/Store with a real F1/F5 fact `Project Elyra budget = 615 Euro`; close Runtime. Baseline standalone CLI `source_exact.main` returns exact `FINAL` with `model_called=false`, `native_calls=0`.
2. Place **invalid, path-escaping** `restore_pending.json` with `stage=../outside`, `old=../outside-old`. Standalone must refuse `ERROR` (no answer, no model) **before BudgetContext**, journal retained for operator intervention; original SQLite DB SHA256 unchanged. Test patch/spying only on BudgetContext construction; actual restore-journal validation must run.
3. Valid no-op pending journal (`stage=tmp/stage-empty`, `old=tmp/old-empty`) must be reconciled under coordinator lock before the original exact answer; journal removed and original DB SHA256 unchanged. This tests actual recovery hook, not mocked restore success.
4. Store lock held by live Runtime plus pending journal must refuse, no output fact; cannot race the coordinator. Missing home must remain missing with exit2. No new source/model permission.
5. Focused `test_run102_source_exact_restore.py` plus original Run97/source-guard tests, full suite, source blob/compile/privacy/diff gates. Closed original raw ZIP, HEAD and SHA256SUMS; preserve any RED attempt and prereg unchanged.

This is a **software data-integrity candidate**, not real native C3, JEPA/Body-JEPA/B3/STEP2/LP3, Android/Redmi, Age promotion or whole-system completion. Run98/Run99 source-exact integration remains separate; import this candidate only after independent GREEN and integration review.
