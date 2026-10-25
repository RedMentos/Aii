# Run351 prereg — plain Termux chat queued notices must flush (2026-10-25)

Base: Run350 review head `027d6b758d9df9e8f12a45a4191f9f0a432cf666`, building on Run349/Run348/Run347; not main. Owner: `v13/code/v13/ui.py`, new `v13/code/tests/test_ui_plain_notice_run351.py`, new workflow and proof folder. Do not edit active owners, age/learning/approval, model/seed/source cohort hashes or native runners.

## User-visible failure mode
In `ui.plain`, a worker notice received while readline has unsent text is appended to `held`. The render thread skips while typing and **never drains held** afterward; only a *subsequent* new notice calls `notify` and flushes the old queue. A terminal operator can therefore miss a completed/cancelled/status notification indefinitely. The list is also accessed from worker/UI threads without synchronization.

## Frozen acceptance
1. RED deterministic test uses a fake Runtime/store/operator and a real render thread. While `typing()` is true, call `r.notify('queued notice')`; then set typing false without any new notice. Expect notice printed within a bounded render interval. Current code fails.
2. GREEN thread-safe FIFO pending-notice queue drains on the next render tick after typing ends, without printing while typing is true or requiring a second notice. A second notice still flushes in FIFO order. Do not change prompt-toolkit UI or message persistence.
3. Run original `test_chat_operator_persistence_run214`, `test_phone_chat_sessions_run89` and new UI tests; source-only CI, privacy scan, exact-head raw evidence, independent CRC/SHA and private backup.
4. No native/Redmi UI proof, no ContextOS/STEP2/B3/Body-JEPA/jepa_weight/AG6/V13 promotion. Keep all original negative gates and historical failures.

Use deterministic small test waits only to allow the existing 100ms UI render interval; no model downloads or paid provisioning.
