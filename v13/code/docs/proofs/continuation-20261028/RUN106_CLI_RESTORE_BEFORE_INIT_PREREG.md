# Run106 prereg — source-answer CLI must recover pending offline restore before initialize (2026-10-29)

Owner GPT-6 scheduled continuation. Review-only sibling of Run105 on Run104 #1008 exact `4ddf364e127dd274884338835d2cf0407b2944d6`. **Run104 parent original raw GREEN is a prerequisite to execute/promote Run106**. Original Run96 RED preserved. Separate Run103 #1007 independently GREEN fixes `BudgetContext` direct/standalone callers; Run106 addresses a different confirmed ordering gap in the `python -m v13 source-answer` wrapper. Do not silently combine or duplicate fixes.

## Confirmed gap and scope
Current `v13/__main__.py` source-answer branch checks existing home, then calls `initialize(home)` before `backup.recover_startup(home)`; interrupted offline restore may expose/mutate partial SQLite/config before recovery. Add a **source-answer-only** fail-closed call to existing `recover_startup(home)` immediately after existing-home check and before `initialize(home)`. If recovery raises, return JSON `{"status":"ERROR","reason":"<exception type>"}` and exit 2 without touching Store. Keep all other command routes unchanged and retain later common `recover_startup` (no pending journal after successful recovery). No new background or model call.

## Acceptance before code
- Real temporary Runtime/Store with human F1/F5 Elyra=615; close.
- Invalid `restore_pending.json` path escape: source-answer must refuse with JSON ERROR and zero calls to `initialize`/Store, journal and DB SHA unchanged.
- Valid no-op pending journal: reconcile before initialize, then source-answer READY with same SourceRef, journal gone; do not assert raw DB file bytes unchanged after legitimate Store read.
- Active coordinator lock with pending journal: ERROR before initialize; no migration, journal preserved.
- Missing home still errors without creation; normal source-answer READY, zero native; existing Run94/95/Run104 suites remain.
- New pinned CI with focused/full/compile/privacy/diff, raw SHA256SUMS and original artifact. No native or Redmi; preserve failed attempts.

File ownership: one narrow `v13/code/v13/__main__.py` source edit and new `v13/code/tests/test_run106_cli_restore_before_initialize.py`, workflow and branch state only. Do not modify Run103/Run105 branches, Runtime/Store/backup/Memory/SourceConsumer, model catalog, frozen Canon. Age0 RECORD_ONLY, STEP2/B3/Body-JEPA/LP3/jepa_weight/Redmi/whole-system remain negative.
