# Run299 — FastForward Sleep CAS: RED → GREEN (software)

UTC 2026-10-25. Owner GPT-6. PR #298, branch `codex/fastforward-sleep-cas-run299-20261025`; based on verified Run298 checkpoint `3523fecea8d0b4c0bcacbd51fd70e9eebd2934f9`.

## Fixed actual state race
`FastForward.consolidate()` previously trained a Sleep candidate from a state snapshot and committed it through `_mutate()`, which reloaded a newer live state but replaced its weights with the stale Sleep candidate. Concurrent `learn()` updates could disappear. New behavior uses one `Store.set_state(KEY, snapshot, expected=source_version)` CAS against the exact version read before replay. A changed version returns `SKIPPED_STALE_LIVE_STATE` without overwriting live weights or procedural state. Valid uncontended consolidation still commits once; insufficient replay still skips. No Runtime changes.

## Closed tests / hashes
- RED commit `bbae979425cfe6f02b7ed32ca9e03710f12192ed`: Actions run `40203034483`, artifact `12602732144` (`V13-Run299-FastForwardCAS-Raw-58ff1557551ae219083643715ff2514629a6f89f`). **59 tests, 2 FAIL**, both interleaving controls; no false claim of a passing baseline. Official privacy scan CLEAN.
- GREEN source commit `fd4b3dcfc8a0acaa09a4c2b4014effea79c4d218`; source blob `15b992056145e63e1a98ac7a1a0d6a85a42921f2`. Actions run `40203094089`, artifact `12602627487` (`V13-Run299-FastForwardCAS-Raw-c5b280f8a8bd03b5cf91fde3fe1975fecfd4a7ff`). **59 tests OK** (4 new, 55 existing), official privacy scan CLEAN.
- Actual production Runtime/Store SQLite; synthetic timing outcomes. Tests explicitly interleave `learn()` and `record_turn()` during the Sleep checkpoint; verify live state version, replay, weights, and no false sleep-update increment. Uncontended candidate persists.
- Remote source blob fetched and matched. Canon, source/model hashes, active cohorts, Age permissions, B3/STEP2 negative gates unchanged. Broader focused workflow may still be running independently; do not infer its result.

## Limitations and continuation
This is software evidence of correct persistence and concurrency, not measured native or Redmi continual-learning utility. Sleep candidate quality is not improved by CAS; stale work is discarded instead of silently overwriting online learning. Canon completion, Body-JEPA, jepa_weight and B3 remain open.

Next: inspect focused CI and Run298 pending full suite, retain failures; then choose a separate canonical package with explicit ownership and RED/GREEN tests. Do not interfere with active Run297 Context OS native probe.
