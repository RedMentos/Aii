# Run56 — source-bound, crash-safe SHADOW delta publication candidate

Base PR89 `4303ab074cb1ec2d2a8bffea7f1194e058f96dca`; prereg Git commit `e91eee2c26377f3254397c410d6bac218f5d2bcc`. Own only `v13/code/docs/proofs/continuation-20261024/shadow-commit-run56/*`. No production Runtime, Store schema, Age permissions or model weights modified.

**Functionality:** `ShadowCommit.commit` takes precomputed bounded delta bytes, the exact frozen base hash, full SourceRefs, active generation, unique request ID and explicit SHADOW mode. It fsyncs a content-addressed delta before a `Store.tx()` (`BEGIN IMMEDIATE`) source/generation/base recheck and SQLite receipt commit. Crash after blob before DB receipt leaves an untrusted orphan; crash after DB commit before return yields a recoverable receipt. Idempotent exact replay accepted; conflicting request ID rejected. `verify` revalidates source/generation/base/delta and refuses later-revoked sources. No code writes base model bytes.

**Evidence:** 16/16 synthetic SQLite tests PASS and 16/16 Python `-O` PASS, Linux subprocess `os._exit` fault injections for both publication boundaries PASS, 8 repetitions of concurrent writer + two crash tests PASS. Original 15/15 tests PASS; one adversarial test reproduced **FAIL-OPEN**: forged extra authority field with recomputed in-DB hash was accepted. Closed manifest schema fix makes it PASS. Raw RED and final logs retained.

**Limitations:** This is a candidate and synthetic Store-shaped fixture, **not actual Store/Runtime**, native C3/Bodies, Redmi, full repo suite or official privacy scan. Receipt SHA256 is accidental-corruption detection, not authentication against an adversary who can rewrite the DB and recompute hashes; independent external anchoring would be required. After `verify` returns, source can be revoked; the final consumer must revalidate at actual optimizer/commit time. The candidate has no production migration for `shadow_receipts_run56`, no optimizer integration, no retention utility and no training rights. Orphan blobs are preserved, not automatically deleted.

**Reproduce:** unpack `RUN56_SOURCE_EVIDENCE.tar.xz`, run `cd shadow_commit_run56 && python -m unittest -v test_shadow_commit && python -O -m unittest -q test_shadow_commit`. Tests use synthetic SQLite and Linux subprocesses only.

**Next:** Independent review in full PR89 checkout, exact production Store schema migration proposal (separate, default off), real Store/Runtime source-revocation concurrency tests, then wire to Run48 SHADOW replay with consumer-time source recheck and retention ablation. Do not touch active owners or promote native gates.

**Unchanged:** STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, `jepa_weight=0`, full V13 INCOMPLETE; Age-0 SHADOW only. Primary source: https://www.sqlite.org/lang_transaction.html (access 2026-10-24).
