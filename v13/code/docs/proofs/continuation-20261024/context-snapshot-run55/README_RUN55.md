# Run55: bounded transactional Context OS history candidate

Base: PR88 `a90acdc3ab3ab3fa7646a2d1634750f527d02853`, prereg `dabcf2f6e68a6cdd8a1c111957016e9af8f62fd0`. New owned folder only; **not installed**. The upstream `v13/code/v13/history.py` remains untouched, blob `a7138080e19b439331bf4c5da68e7e62f823f169`. Exact `Store.tx()` from `v13/code/v13/store.py` blob `0779d986fb8aee8aa01c5df5f656889d4bd56348` uses `BEGIN IMMEDIATE` under `RLock`.

**Problem:** `native_history` reads approved rules under mutex but performs subsequent history/event/source reads separately. A concurrent source revocation can cross that boundary. An unguarded source-shaped two-phase reader demonstrably returns a ref already revoked by a writer.

**Candidate:** `snapshot_native_history(store,session,event_id,turns,reader)` wraps the *unchanged* native reader in `Store.tx()` and checks all returned SourceRefs again before commit. Bounded `turns` 0..64, rejects nested transactions, malformed identities, missing Store contract and busy SQLite writer. The wrapper is opt-in and must be independently reviewed in a full checkout before runtime use.

**Evidence:** Linux x86_64, Python 3.13.5, SQLite 3.46.1. Initial exploratory 12/12 tests passed before prereg; subsequent 15/15 final and 15/15 Python `-O` tests passed. The 2 predeclared new race tests include an external SQLite connection and a separate Python process; concurrency tests repeated 10x before final test edits. Logs are included. No real `Store` instantiation, no actual Runtime/Model, no Redmi, no full suite or official privacy scan. A post-return revocation still invalidates refs: **consumer-time revalidation remains mandatory**.

**Limitations:** `BEGIN IMMEDIATE` reserves SQLite writer ownership and can block unrelated writes during source/blob I/O. A real Store latency/budget test is required before enabling it. External non-Store filesystem mutation is not locked. This is not a durable source lease or proof of training utility.

**Reproduce:** unpack `RUN55_SOURCE_EVIDENCE.tar.xz` and run `cd context_snapshot_run55 && python -m unittest -v test_history_snapshot_guard && python -O -m unittest -q test_history_snapshot_guard`. All tests use synthetic Store-shaped SQLite fixtures.

**Next:** Full checkout on PR88 exact head; run actual Store/Runtime history replay with concurrent `Store.tx()` rule/source revocation, official privacy scan and full suite. Decide whether a short SQLite read snapshot plus mandatory consumer revalidation can avoid a long `BEGIN IMMEDIATE` writer lock. Never promote any original gate from this package.

**Gates:** STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; jepa_weight=0; V13 INCOMPLETE. Age-0 SHADOW, no training or action authority.

**Primary sources:** SQLite transactions https://www.sqlite.org/lang_transaction.html and isolation https://www.sqlite.org/isolation.html, accessed 2026-10-24.
