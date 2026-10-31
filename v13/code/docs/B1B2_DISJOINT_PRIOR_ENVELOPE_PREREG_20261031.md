# B1/B2 disjoint prior source provenance → C3 SHADOW preregistration (Z2)

**Date:** 2026-10-31 UTC. **Owner:** GPT-6, isolated branch `assistant/v13-b1b2-disjoint-prior-gpt6-20261031` from Run61 verified head `0d0189d52c48af80c76e690e0bcf4904c7f3a459`. Preregister before code/tests/CI. Original Run52/57/58/59, model, source, seed, scorer and Canon unchanged.

## Hypothesis and functional boundary

Existing topic-partitioned real Store `Cognition.offer` can retain role-specific prior evidence. Build an explicit **default-OFF** four-offer orchestrator that gives B1_DETAIL one prior authoritative USER source (fine detail) and B2_GIST a **different** prior authoritative USER source (coarse gist) for the **same project**, then stages current B1/B2 offers and constructs the original C3 source envelope. Require each current QueryPacket's `context_source_refs` to point **only** to that role's assigned prior source, with distinct exact SHA/SourceRefs; reject cross-role leakage, wrong project, stale current, revocation and duplicates. This makes B1/B2 complementary **information paths** testable; it does not prove model-learned complementarity or utility.

## Fixed synthetic real Store controls

Positive: project `Meridian` with two distinct authoritative sources:
- B1 prior: `Project Meridian. Fine detail: Option A requires 17 tokens.`
- B2 prior: `Project Meridian. Coarse gist: the budget ceiling is 24 tokens.`
- Current: `Project Meridian. Choose an eligible option using the earlier detail and gist.`

Run prior B1, prior B2, current B1, current B2 via real `TopicPartitionOfferConsumer` with synthetic schema-compliant Body runners; assert four persisted OfferPackets/QueryPackets, B1 current context **exactly** B1 prior SourceRef, B2 current **exactly** B2 prior SourceRef, both in source-bound C3 envelope and neither cross-role. No output/FINAL/TTY/tool/learning authority. Additional negatives: absent/integer opt-in, forged approval, wrong project/ambiguous current, identical prior source, reversed time order, revoked prior, later authoritative USER, existing current offer, tampered QueryPacket and cross-role context injection. No invalid preflight may call a model or write packets.

## Evidence limits

Software real SQLite/Store and synthetic Body only. This is not native B1 information, C3 correct decoding, STEP2 semantic utility, Redmi or B3/JEPA. Existing REDs remain. Require focused original Run52/57/58 regression, privacy CLEAN, pinned source and fixture, closed raw SHA256 manifest, private byte-verified backup. A later *separately preregistered* disjoint native test must demonstrate each body contributes unique correct evidence and a joint receiver beats both solos and controls; source-path separation alone cannot promote STEP2.

**Exact planned command:** `cd v13/code && PYTHONPATH=.:tests:scripts python -m unittest -v tests.test_b1b2_disjoint_prior_envelope_candidate tests.test_b1b2_topic_partition_candidate tests.test_b1b2_c3_source_envelope_candidate`.
