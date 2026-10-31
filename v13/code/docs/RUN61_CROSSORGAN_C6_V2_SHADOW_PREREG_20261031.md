# Run61 — B1/B2 OfferPacket lifecycle + C3 + F1/F5 + C6 v2 DRAFT SHADOW preregistration

**Date:** 2026-10-31 UTC. **Owner:** GPT-6, review-only `assistant/v13-run61-crossorgan-c6-v2-shadow-gpt6-20261031` based on C6 v2 candidate `a6c24adc0649e7229c96cb5d56dfe24aad7cc309`. This preregistration is committed before Run61 code/tests/CI. No original Run58/59, seed607, original C6 v1, model/fixture/scorer changes.

## Functional problem

Run58 can stage a real SQLite DRAFT with source-bound B1/B2 evidence and temporal F1/F5 correction, but its v1 C6 lexical guard rejects safe short answer phrasings; separate PR #1399 shows B1/B2 OfferPacket drift after C3 generation was not rechecked by original Run58. Run60/C6 v2 added a newer-authoritative-USER refusal. These pieces need one *default-OFF, software SHADOW-only* cross-organ consumer, not a claim of native or delivered utility.

## Planned path and frozen negative controls

New `v13/code/v13/run61_crossorgan_c6_v2_shadow_candidate.py` calls real existing `build_c3_source_envelope`, original temporal F1/F5 atomic DRAFT staging/checker, and new `preflight_budget_lexical_v2`, without editing the frozen Run58 or Run59. Before invoking the callback, refuse existing assistant output/TEXT_REPORT action; source envelope and exact role/OfferPacket/retained state must be stable before/after callback, after staging and after C6 preflight. Revalidate current USER source and newer-authoritative-USER guard. Return only status/hashes/IDs and `delivery_authority=0`; never return candidate text. No model call in any negative preflight.

**Frozen positive synthetic fixture:** original Run51 Cypress correction/followup seed467, original real SQLite source and B1/B2 OfferPackets from `TopicPartitionOfferConsumer` using synthetic schema-compliant bodies; C3 callback returns `The budget for Project Cypress is 64 euros.`. Expected new result `RUN61_C6_V2_PREFLIGHT_ONLY_NEEDS_REAL_TTY` with DRAFT persisted, no FINAL/output/TTY approval, while original Run58 v1 yields `CROSSORGAN_C6_GROUNDING_RED` for that phrasing.

**Negative controls (at least):** opt-in absent or integer 1; forged TTY approval; wrong/duplicate offer ID; preexisting DRAFT or TEXT_REPORT; B1 OfferPacket tamper inside callback; B2 retained state drift; newer authoritative USER inside callback; F1/F5 correction revocation; wrong budget/negation/tool sentence; competing DRAFT. All must refuse preflight, with no live delivery or tool/learning authority. Persist original RED tests without waivers.

## Proof boundaries

Real SQLite/Store and actual source/event/packet DRAFT lifecycle, **synthetic** B1/B2 and C3 callback only. No native C3/B1/B2 run, no Redmi, no actual TTY approval or output commit, no STEP2 second-attempt utility. Existing Run59 C6 RED and seed607 utility RED remain. No B3/JEPA/age/whole-system promotion.

**Acceptance:** focused new+original Run58/C6 v1/v2/F1/F5 tests pass, privacy CLEAN, source pins, diff check, compile, closed raw SHA256 manifest and independent ZIP backup. Exact next command: `cd v13/code && PYTHONPATH=.:tests:scripts python -m unittest -v tests.test_run61_crossorgan_c6_v2_shadow_candidate tests.test_c6_budget_lexical_v2_candidate tests.test_run58_crossorgan_c6_shadow_candidate`. No live model weights required.
