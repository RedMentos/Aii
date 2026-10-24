# Run48 — verified Sleep replay -> shadow-only learned answer (synthetic)

Preregistered at `a85154aa3eabd9e306d81b9d033369e14b055007`, parent Run47 `cfa41e98e422370126f359746b7c6df046323fbe`. Ownership only this folder. The full V13 blueprint and all frozen runtime paths are untouched.

**End-to-end micro path:** Exact upstream `native_history` with fake Store source refs -> exact Run42 source-verified Sleep staging -> Run47 consumer-time revalidation -> parse only validated JSONL -> copy Run46 3,081-parameter key-binding learner into an ephemeral shadow model -> train 300 steps -> evaluate fresh heldout candidates -> revalidate source refs again -> discard shadow weights. Four upstream Git blob identities checked before execution. No optimizer update touches the base model.

**Predeclared result:** 128 source-verified synthetic training candidates and 128 heldout candidates. Shadow heldout accuracy **0.984375** versus untrained **0.0625**; synthetic utility threshold passed. Base model SHA unchanged. Source revocation **after** training but before final revalidation yields `SOURCE_REVOKED_ROLLBACK`, shadow discarded and base unchanged. Cancellation yields `CANCELLED_NO_COMMIT`. Even positive utility yields only `SHADOW_READY_NO_COMMIT`, requiring human approval and native retention gates.

**Tests:** **9/9 synthetic tests PASS**, **9/9 under Python -O PASS**, offline hash-verified dependency bootstrap PASS, compileall PASS. Original logs and independent source-identity test preserved.

**Reproduce:** Decode `evidence/run48-owned-source-evidence.tar.xz.b64` to `run48-owned-source-evidence.tar.xz` and extract here. Then run `python scripts/bootstrap.py` (offline from Run46 and Run47 persisted artifacts), `python -m unittest discover -s tests -p test_shadow_replay.py -v`, and `python scripts/shadow_replay.py`. Decoded owned archive SHA256 `49c049e211c40a5ffa8d6c77f30fdcb2e7aa7263fb0ffb48cbb3619d4078e7c2`.

**Limits:** This is a toy attention model with synthetic Store, not real C3, B1/B2, JEPA, native training, retention or Redmi. The shadow copy is deliberately discarded; no production weights or Age authority change. A real trainer needs source-consistent atomic commit, human approval, retention, rollback, device proofs and independently validated utility. Original gates stay STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0 and V13 INCOMPLETE.

**Next:** Full-checkout independent review and real Store/Runtime integration, then native C3/B1/B2 learning with preregistered retention/rollback and source revocation race tests.
