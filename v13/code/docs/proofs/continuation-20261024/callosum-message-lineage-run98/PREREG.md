# Run98 — B3 Callosum utility requires source-bound MessagePacket

Base Run97 PR #129 `5a059600a8311f8dd24f1d942bcb5564d5e87d5e`. Run94 World Model independent owner untouched.

Owner: `v13/code/v13/callosum.py` only `Callosum.outcome`, new `tests/test_callosum_message_lineage_run98.py`, isolated workflow `.github/workflows/v13-run98-callosum.yml`, this proof. No canonical or shared workflow changes.

Hypothesis: `Callosum.outcome` looks up a pending message by id, but if absent uses rowid=0 and still credits the next receiver OfferPacket; wrong packet kind, foreign event, reversed sender/receiver, corrupt payload and deleted source may also poison B3 channel utility. The learned channel policy can then prefer a channel without valid causal evidence.

Preregistered RED: six real SQLite counterexamples must return scored=0 with no B3 utility update. Positive valid source-bound message after note must score once and be idempotent on repeated outcome. Existing B3 LATENT=0, default SHADOW and explicit ACTIVE approval unchanged.

Narrow candidate: require exact MessagePacket kind/event/generation/sender/receiver/channel, intact source refs and source blobs before selecting the receiver offer; verify the receiver OfferPacket event/role and valid lineage; malformed JSON fail closed. Never synthesize a rowid fallback. No native/Redmi/utility gate claim.

STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, Z6a/Z8 FAIL, full V13 INCOMPLETE remain.

**Legacy fixture adaptation after GREEN candidate:** Existing Run66 CAS/once integration fixture used only a four-column `packets` table and no `events` table, incompatible with required source/event/generation validation. The original assertion and test name remain intact; the fake SQLite schema and packet payloads now include event/generation/source lineage. The first post-fix CI error (run 40137855991) is retained, not reclassified as a product failure. This extra file `tests/test_callosum_outcome_integration_run66.py` is owned only for this minimal fixture update; no production code beyond `Callosum.outcome` is touched.
