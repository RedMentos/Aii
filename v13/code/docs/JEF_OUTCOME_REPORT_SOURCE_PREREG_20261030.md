# JEF WP-U1 outcome report source-provenance review — prereg 2026-10-30

Parent exact commit `3c9e961d123e5bed1826802fc3e236c19078f5ee` (current-chain Age0 native integration candidate; native job is independent). Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` unchanged.

## Problem
`v13/jefoutcome.py:report` computes `human_overlap` and `human_agreement` by joining feedback to a HumanDecision with matching decision packet ID, but does not check that the feedback's source remains live or is the same exact source referenced by that HumanDecision. A revoked or substituted feedback row may therefore inflate self-label agreement and mislead JEF policy-readiness telemetry. This does not grant learning authority, but violates source-bound evidence accounting.

## Fail-first witness and acceptance
1. Create an Age0 software Runtime, a real fast-head decision, a FINAL self-outcome and human feedback for the same event. Verify initial overlap=1/agreement=1.
2. Revoke the feedback source using Store's transactional source tombstone. Expected: report overlap=0, agreement=null; self-label remains stored and no learning gate changes.
3. In a separate fresh fixture, replace feedback's `source_id` with another live SourceRef while leaving the HumanDecision untouched. Expected: overlap=0/agreement=null, because the receipt source no longer matches.
4. Preserve valid live feedback agreement and disagreement; restart persistence; no model downloads or native execution.
5. Run focused JEF/SkillLive integration and privacy/diff checks, record raw RED before changing production source; then narrow SQL repair and GREEN on exact branch. Original RED evidence is not discarded.

## Claim limits
Software/SQLite provenance only. No native/Redmi, no STEP2/B3/JEPA or Age promotion. Frozen Run34/Run37 full-suite errors remain. No Canon, source cohort, model, seed or JEF authority change. This work is separate from the running connected native integration proof and must not mutate its branch or artifacts.
