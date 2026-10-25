# Run312 checkpoint — FastForward outcome exactly once (software/SQLite only)

UTC 2026-10-25. Owner `assistant/fastforward-exact-once-run312-20261025`.
Base exact commit `300e0aab05b81833300645137275e05d7982d237` (Run310 review branch, **not** production main).
Preregistration commit `36d0a75ab9be797212032684d3427b96ab3bf27f` predates RED tests `359cf3387909c984d2d5a4a00bd23ca80ed4143a` and CI `733aada27f560e4687939fd8d931f0ae41cb1b01`.
Implementation `bdd68446f91c1555ee65d504cf40fbe0d7323eca`; remote `fastforward.py` blob `28600c2889f3d94d179fcd3b26429e69623e6be8`, fetched and verified at exact commit.

## Actual evidence
- RED: workflow run `40207751340`, head `733aada27f560e4687939fd8d931f0ae41cb1b01`: **44 tests, 5 FAIL** (same-event replay, conflicting replay, >256/restart, concurrency, N10 repeat); expected distinct-events positive PASS. Official privacy CLEAN. Raw artifact ID `12604751357`; Actions ZIP SHA256 `058a708cdcd3dcf2676f42b1452cf41245d38b9f4b5620868ffb103bef188546`.
- GREEN: workflow run `40207824435`, exact checked-out head `bdd68446f91c1555ee65d504cf40fbe0d7323eca`: **44 tests OK**, official privacy CLEAN. Raw artifact ID `12604116839`; Actions ZIP SHA256 `f2f2d4995f3ce9a10ea3ce3ed200b79edab26becb2474a6d64e5f3367eb8483e`.
- Other exact-head CI: Run299 Sleep CAS `40207824537` SUCCESS; Run300 procedural latency `40207824445` SUCCESS; focused source-bound `40207824437` SUCCESS.
- Raw ZIP artifacts are stored by GitHub Actions with 30-day retention (not indefinite backups); their hashes and IDs are preserved here.

## Concrete change
The existing `FastForward.learn` now uses a per-event hash-keyed receipt in the existing SQLite `states` table and commits receipt + predictor state in one `BEGIN IMMEDIATE` transaction. Identical replay returns the original result without weight, replay, version or N10 re-update. A changed payload for the same event raises `ValueError`. Receipts outlive the bounded 256-item replay and Runtime restarts. Existing historical observations predating this change cannot be retroactively deduplicated. N10 post-commit signal is **at-most-once on normal calls**, not a transactional delivery guarantee if the process crashes between commit and emission.

## Claim limits and integration
Synthetic timings + actual Runtime/SQLite Store, not native model inference or Redmi. No Canon, source/model/seed/cohort, Age, approval or policy mode changes. The entire blueprint remains binding. STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA unavailable; jepa_weight=0; whole V13 incomplete. Run310 independent full suite at original base `300e0aab` remains **2864 tests: 2 FAIL, 36 ERROR, 14 skipped**, artifact `12604380388` SHA256 `2eaaf11170f533c471307e7bf237c5afdeb5d29b39368d7b798822fbe6749652`; see PR308 review comment for frozen-source and Run284 cancel triage. Do not call this run a full-suite PASS.

## Next command / prerequisites
Review PR309 and the exact-head RED/GREEN CI, then add a fault-injected SQLite crash-window test and rerun focused suite. Subsequently pick a different unowned canonical module, run its real Runtime/SQLite RED-first tests, preserve original negative gates, and checkpoint again. Run284 Runtime cancellation owner is separate; do not overwrite it. No Redmi is available in this environment; current device acceptance remains blocked.
