# C6 / B1-B2 offer lifecycle independent SHADOW audit — preregistration, 2026-10-31

**Owner:** GPT-6 independent sibling of verified Run58 PR #1397, base commit `74f9610d279f1b06d670376cb28c330a061d8b42`. Separate from active Run59 PR #1398 and its native runner. **Preregistered before implementation.**

## Observed source-level risk

Run56 `build_c3_source_envelope` checks the two persisted current-turn B1/B2 OfferPackets and topic-partition retained states while constructing C3 input. Run58 `stage_crossorgan_c6_shadow` calls this once before invoking its generator, then F1/F5/C5/C6 recheck the USER correction/source and DRAFT but **not the B1/B2 offers**. A generator callback could modify an OfferPacket, its retained state, or create a newer authoritative USER event after the C3 envelope is built. The source-bound C6 positive budget assertion alone does not attest that the body evidence remained valid.

## Registered test questions / expected outcomes

1. Baseline unmodified Cypress seed467 correction/followup, two real SQLite persisted synthetic B1/B2 offers, source-exact C3 envelope, synthetic callback returning `Project Cypress budget is 64 Euro.`: lifecycle wrapper returns read-only `NEEDS_REAL_TTY` challenge; no FINAL, output commit, tool dispatch, learning or native claim.
2. During the callback, mutate only the B1 OfferPacket payload (leave original USER correction intact): original Run58 may still return a read-only C6 challenge; **new wrapper must downgrade** to an explicit body-evidence RED.
3. During callback, mutate only B2 topic-partition retained state: wrapper RED, even if packet payload is unchanged.
4. During callback, create a newer authoritative USER event in the same session: wrapper RED despite unchanged prior USER correction/source.
5. If source/offer is already invalid before callback, reject without invoking callback. If operator opt-in or callback opt-in is not literal `True`, or approval receipt is supplied, refuse without callback.
6. Check non-authority invariants and no candidate text in all wrapper returns; compare raw DB write counts on pre-callback rejection. Keep original Run58 implementation and frozen seed/model/source unchanged.

**Implementation boundary:** independent default-OFF wrapper, never installed in Runtime. Validate the source envelope before generation, immediately before and after callback, and again after Run58 staging; require exact original envelope fingerprint and both role/packet identities. A post-stage failure is a **read-only rejection, not rollback**; any existing DRAFT remains SHADOW and cannot be treated as valid for delivery. There remains a transaction race between last check and future output commit; no output commit exists here, and a future real C6 writer must atomically recheck all inputs plus genuine TTY approval. Do not claim full atomicity, native utility, or semantic truth.

**Evidence plan:** focused Python `unittest` on real Store/Memory/FakeRuntime with isolated CypressBody synthetic callback; frozen upstream tests; Python compile; pinned-source hash check; privacy scan; diff check. Linux software only. Preserve original Run54 native RED, Run58 original test RED and corrective GREEN, Run59 native RED if observed, unfiltered full-suite RED. No change to Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, jepa_weight=0, World-JEPA SHADOW or Redmi unmeasured.

**Next after prereg:** implement `v13/code/v13/c6_body_offer_lifecycle_candidate.py`, `v13/code/tests/test_c6_body_offer_lifecycle_candidate.py`, isolated CI workflow, run and archive closed raw evidence, write scoped BUILD_STATE and verify remote hashes. Do not overwrite another owner's files.
