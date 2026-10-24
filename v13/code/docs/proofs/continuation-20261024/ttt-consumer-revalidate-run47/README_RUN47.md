# Run47 — Sleep TTT consumer-time lineage revalidation (isolated)

Preregistered at `a29d38da3a09d3ef243c1729a01a8062e403f6f3`, parent Run46 `b1951ad8c97e508aa1a9314f2089855f5dec2fe9`. Ownership only this folder.

**Problem:** An export verified by Run42 may become stale after source deletion or fixed-rule removal. A training consumer must not trust that cached JSONL solely because it was valid when staged.

**Candidate:** `ttt_consumer._consume` reads a bounded local export under `Store.mutex`, rejects symlinks, duplicate JSON keys/rows, unknown identities and non-candidate statuses, then reruns the exact Run42 staging function against **current** `native_history` and compares each selected row against the fresh verified row. Any invalid row rejects the entire batch; no partial training, weights, Age or commit authority. The actual production adapter is not wired to a trainer.

**Tests:** **17/17 PASS** with exact byte-for-byte `v13/history.py` Git blob `05455f297205b40fe8e0f818c4657f1fedcd9fa3` and Run42 stage blob `8dcd4b36cbe58f06ea330a510f1735b37f0ad600`, but a synthetic Store. Revoked target/prior/transitive sources, removed fixed rule, hash mismatch, tampered target/context/status/requirements, duplicate row/JSON key, unknown session, malformed JSON, symlink, deterministic and empty exports all checked. **17/17 PASS under Python -O**, compileall PASS.

**Evidence:** `evidence/run47-source-evidence.tar.xz.b64` contains source, exact upstream dependencies, tests and initial/final/optimized raw logs. Decoded tar.xz SHA256 `0077e265dd10e4229362b1be511351c079eb24f20d0b2bcde3dc6b0f50fe3211`. Decode: `base64 -d evidence/run47-source-evidence.tar.xz.b64 > run47-source-evidence.tar.xz && tar -xJf run47-source-evidence.tar.xz`.

**Limits:** This is not a real Runtime/SQLite test, and consumer-time validation does not make an asynchronous future optimizer step safe if sources change again. A production integration needs transaction-bound source snapshot/revalidation, human approval, retention, rollback and exact native TrainRunnerProof. No source/model weights are written here.

**Next:** Run with actual Store and a source deletion race between verification and optimizer step. Keep original STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0 and V13 INCOMPLETE until independently proven. No production runtime files were changed.
