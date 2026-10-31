# Focal capacity competition diversity candidate — prereg 2026-10-31

Owner GPT-6; independent review-only child of Run102 #1468 exact parent `9fc4a85930b22ddb0c0f306d48bcddfad4806842`. Run103 C3 native cohort and phone bootstrap PR #1469/#1470 are separate owners, untouched. This package targets Blueprint G-FOCAL-CAPACITY-003 and §99 missing capacity-pressure control, not installer integrity.

## Concrete problem
Existing real `v13/focal.py:admit` sorts by **pre-redundancy** priority once, then penalizes each accepted candidate for redundancy with active items. A second near-duplicate may occupy a limited slot even after its marginal priority falls below an as-yet-unseen diverse candidate. The code has no second competition pass. This is a possible measurable capacity-pressure mechanism, not proof of semantic utility.

## Fixed candidate, controls, acceptance before code
Create isolated default-OFF `scripts/focal_capacity_diversity_candidate_20261031.py` that greedily recomputes actual `focal.priority` and `memory.relevance` against selected active items, with deterministic tie-break and explicit high-salience interrupt protection. Preserve original `focal.admit` unchanged and original item refs/status. Test using real `focal.item` payloads and Store-backed exact sources in fixed synthetic cases:
1. Capacity=2, two near-duplicate high raw priority offers + one diverse slightly lower raw priority offer: original selects duplicate, candidate selects diverse if marginal priority supports it; count distinct exact source IDs and summed marginal priority.
2. All-distinct control: candidate must not reduce coverage or drop eligible offers.
3. High-salience interrupt and capacity=1: candidate must retain interrupt even with lower priority.
4. DROPPED, below-threshold and permutation/tie cases; no source ref mutation, no authority escalation.
5. Restart source validation remains Store-owned; candidate does not persist or act on sources.

Claim limits: software-only synthetic capacity pressure, no native model output, no human decision quality, no G-FOCAL-CAPACITY-003 promotion. If candidate fails controls, retain RED and do not integrate. Run focused and adjacent original focal tests on isolated Linux Actions, compile/privacy/diff, raw receipts and private backup. Next: independent native/human utility ablation only after registered design and owner availability; do not silently change baseline.
