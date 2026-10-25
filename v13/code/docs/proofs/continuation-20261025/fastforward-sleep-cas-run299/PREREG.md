# Run299 — FastForward Sleep consolidation must not overwrite newer live learning

Owner GPT-6 automation. Base: Run298 checkpoint `3523fecea8d0b4c0bcacbd51fd70e9eebd2934f9` / PR #297. Files owned: `v13/code/v13/fastforward.py`, new `v13/code/tests/test_fastforward_sleep_cas_run299.py`, `.github/workflows/run299-fastforward-sleep-cas.yml`, this proof directory. Run297 Context OS native owner and Run298 WorldModel code are not edited.

## RED bug hypothesis
`FastForward.consolidate()` reads a replay/weight snapshot, performs offline updates, then uses `_mutate()` to write its candidate. `_mutate()` refreshes a newer state and blindly overwrites `w`, so an online `learn()` that occurs during Sleep is lost, despite the Store's existing optimistic version/expected CAS contract. This violates independent online learning retention. No native/model assumptions.

## Fixed tests before patch
- Actual Runtime/Store SQLite: >=12 observed FastForward outcomes. During the Sleep training checkpoint, inject one new online `learn()` update. Use `lr=0` so held-out score always ties and original code chooses `KEPT`; require that the live update weights remain byte-for-byte unchanged and the stale candidate returns `SKIPPED_STALE_LIVE_STATE` (RED on current source).
- During the same checkpoint, inject a procedural `record_turn()` update; require the versioned state remains intact and Sleep refuses stale candidate.
- No concurrent mutation: `consolidate(epochs=1,lr=0)` remains `KEPT`, increments `sleep_updates`, and does not change weights. Too-few replay samples remains skipped.
- Existing `tests.test_fastforward_reflex`, `tests.test_sleep_scheduler`, `tests.test_sleep_validation` remain green; official privacy scan CLEAN. Actual failures preserved in raw GitHub Actions artifacts.

## Intervention constraints
Replace the final optimistic rebase of stale weights with one Store CAS against the exact version read at the beginning. On stale version, return a bounded explicit non-promoting status; do not retry or overwrite the live state. No change to runtime, policy, predictor math, model/source cohorts, Canon, permission/age gates, or native processes.

Evidence: software with actual SQLite persistence and synthetic outcome values. No real model/Redmi/JEPA or whole-system proof. Keep all original negative gates. Next: independent review, durable checkpoint, then next unrelated canonical package.
