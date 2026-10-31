# Focal capacity-pressure marginal-diversity candidate GREEN (software only) — 2026-10-31

Owner GPT-6; review-only child of Run102 #1468 exact parent `9fc4a85930b22ddb0c0f306d48bcddfad4806842`. Prereg `ed214916234b3087d25b1777824467eadce5944c` before implementation. Run103 native owner, original focal Runtime and other review chains untouched.

## Verified original execution
GitHub Actions **41207136835** SUCCESS, exact tested HEAD `3f0201e4677dcf0567f84102ae8bc2180ac00f92`; original artifact **13043614865** ZIP SHA256 `1863ee496f242d41f0d2a660ee635166906b2d08583cb394f2742e8d942caee5`, CRC PASS, **21/21** SHA256SUMS PASS, **9/9** stage exits0, privacy CLEAN, compile/diff PASS. Original ZIP privately saved and re-materialized byte-identical at `/V13-Checkpoints/2026-10-31/Focal-Capacity-Pressure/ORIGINAL_ACTIONS_41207136835_SHA1863EE49.zip`.

Added default-OFF `scripts/focal_capacity_diversity_candidate_20261031.py` and seven Store-backed pressure/control tests. **7/7** candidate tests and **11/11** unchanged original focal tests PASS. Real `focal.item` + `focal.priority` + `memory.relevance` + exact `Store.read_source` used. Under fixed synthetic capacity2: original `focal.admit` selected `A,B` (two items referencing one source), marginal priority sum **1.415**; candidate selected `A,C` (two distinct source IDs), sum **1.620**. This demonstrates one deterministic greedy-selection deficiency under deliberate duplicate pressure, not a model-quality gain. All-distinct, salience interrupt, DROPPED, threshold, permutation, invalid bounds, unchanged source refs and no authority escalation controls PASS.

## Next action and nonpromotion
**No production change** to `v13/focal.py`, Runtime, B1/B2, model prompts, seeds or native weights. The candidate is not admitted to live decision making. A future independent, preregistered native/real-task capacity-pressure study must measure source coverage **and** actual answer correctness, with full-context/retrieval-only/fixed-slot controls, before any activation. The fixed synthetic gain is not G-FOCAL-CAPACITY-003, STEP2 or §99 proof. Run103 C3 native work remains separately owned.

Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; World-JEPA SHADOW; jepa_weight=0; Redmi UNMEASURED; whole V13 INCOMPLETE.
