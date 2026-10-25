# Run348 preregistration — recoverable, fail-closed `:stillstand aus` (2026-10-25)

Base: Run347/PR343 `6e79f15cc95535b7a9c25b9e4602d94936ef4ddd` (synthetic DS2 lab NOT_SUPPORTED on fresh seeds 501..520, verified Actions 40223421818). New owner: `v13/code/v13/standstill.py`, `v13/code/tests/test_standstill_release_recovery_run348.py`, `.github/workflows/run348-standstill-release.yml`, this proof folder. Do not edit DS2, models, age rights, approval policy, source/model/seed hashes or other agents' owned files.

## Failure mode and hypothesis
Current `standstill.release` unfreezes Age and clears NOTAUS **before** committing the durable STANDSTILL state CAS. A failed CAS therefore raises with `on=true` but two protective guards already off. A crash after clearing durable state but before resuming may strand a paused queue with no retry marker. A durable release intent should be recorded *while all guards are still on*, and an interrupted release should remain recoverable by the explicit user command without silently resuming work on restart.

## Frozen checks
1. Inject a `Store.set_state('STANDSTILL',...)` failure on the **first release write**: all three guards remain on, no queued work resumes, and the original `on=true` ownership record survives.
2. Inject failure while clearing NOTAUS **after** a durable release-intent commit: `release_pending` persists, queue stays paused; an explicit retry completes the exact original release without losing preexisting user guards.
3. Restart from that interrupted state: startup does not automatically resume; `:stillstand aus` explicitly completes, pending marker clears.
4. Re-engage while release is pending: retain ownership of parts originally set by standstill, and do not clear preexisting user NOTAUS.
5. Original `tests.test_standstill` and new tests pass with real Runtime/SQLite; privacy scan CLEAN. Preserve raw RED failure and GREEN exact-head GitHub Actions logs and source SHA256; no native/Redmi/STEP2/B3/Body-JEPA/AG6/V13 promotion.

Minimal implementation: two-phase durable `release_pending` intent; never relax a guard before intent commits; queue resume last. No background recovery that grants permission without an explicit human command. This is an operator safety/recovery correction, not a learning or utility claim.
