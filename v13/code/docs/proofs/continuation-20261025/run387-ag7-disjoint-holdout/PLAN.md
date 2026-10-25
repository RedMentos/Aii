# Run387 / AG7 transfer induction must use disjoint holdout evidence — preregistration (2026-10-25)

Independent owner GPT continuation, branch `codex/ag7-disjoint-holdout-run387-20261025` from verified Run386 checkpoint `e2ff37b5cb452906c661fbd5b4a234be149c6229`. Review chain PR381→PR380→PR379; not main. File ownership: `v13/code/v13/agi/abstraction.py`, new `tests/test_ag7_disjoint_holdout_run387.py`, dedicated source-only workflow and proof directory. No edits to AG2/AG4, frozen cohort/model/source/seed hashes, Age/permission or live learning.

## Problem
AG7 `Abstraction.induce` selects the last ~34% of clustered episodes as held-out tests but does not require disjoint episode IDs or input examples across train and test. Duplicate replay items can be counted as unseen successes. `_save` merges all later same-program/domain rules and unions support/tests, even when a formerly held-out episode becomes training evidence; its persisted `VALIDATED` status can then have the same ID on both sides. This invalidates an evidence claim, especially for future model-based inducers that can memorize examples.

## RED-first requirements
Actual Runtime/SQLite tests must demonstrate: (1) duplicated IDs across train/test in one induction yield no VALIDATED rule and no stored rule; (2) duplicated exact inputs with distinct IDs across train/test likewise yield no validation; (3) a clean six-example reverse rule still validates with fact_write_authority=0; (4) a second induction of the same program/domain with swapped train/test roles must not contaminate the earlier rule's support/tests — keep separate evidence records instead of merging overlapping roles; (5) existing `tests.test_growth.G7Abstraction` and `tests.test_agi_live` remain green. Check both role sets in each saved record.

Fix narrowly: reject contaminated within-cohort holdouts, and merge only compatible independent evidence; create a separate rule when train/test role reuse conflicts. Do not alter DSL, clustering threshold, holdout share, promotion authority, model learning or canonical gates. No native/Redmi or whole V13 proof.

Evidence: pinned Actions source CI with Python Runtime/SQLite, exact HEAD, compileall, privacy scan, raw RED/GREEN ZIP with member hashes, private Library byte-verified backup. All negative gates remain unchanged.
