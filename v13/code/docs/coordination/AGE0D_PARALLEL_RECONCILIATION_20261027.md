# AGE0d parallel-branch reconciliation — independent review (2026-10-27)

**Do not merge the parallel candidate as a replacement.** PRs #755 (answer-aware arithmetic), #757 (stdin-only local CLI) and #759 (locale ambiguity) were built from PR #754's World-JEPA branch. That branch does **not** include older, more advanced Codex AGE0d sibling chains. Those were found during a cross-branch audit after this candidate's software tests; preserving this correction is required.

## Existing canonical chain (separate, not production merged)

- Run134 PR #165: `v13.agi.answer_arithmetic_shadow.evaluate(question,answer)`, English single-operation source-bound exact Decimal checker, `CORRECT/MISMATCH/ABSTAIN`, explicit SHADOW_ONLY and `may_deliver=False`; includes equation echo with operand binding and answer/source spans.
- Run517 PR #515: `SelfSystem.late_offer` invokes Run134 on the authoritative SHA-bound source question, stores bounded deduplicated SHADOW diagnostics, no user notice/learning/age promotion.
- Run521 PR #519 and integration PR #529: require actual persisted same-event/same-session **FINAL assistant text byte-equal to the argument** before recording mismatch. This is stronger provenance than any standalone CLI.
- Run532 PR #531: already supplies a local read-only `:self arithmetic` operator view of the persisted ring.
- Earlier Run183 PR #212 and Run151 PR #182 contain Linux-native answer-cohort evidence. Their negative/insufficient gates must be preserved and cannot be replaced by 32 synthetic examples.

## This branch's distinct, limited contributions

PR #755 supports anchored German `Wie viel ist`/`Berechne`, decimal comma, explicit half-of and `Budget 120 Euro. Berechne die Hälfte.` forms, plus English symbolic x/×/÷; 32 synthetic rows with 0/12 false mismatch, 12/12 wrong detected, 8/8 unsupported abstained. PR #759 adds a conservative ambiguity abstention for `1,234`/`1.234`-style three-digit separators; full source-wide 1953 tests PASS. PR #757 provides a standalone bounded stdin JSON diagnostic. **None** of these add native model utility, source-authoritative FINAL binding or a runtime hook. They are not a substitute for the Run134/517/521/532 chain.

## Integration recommendation and blockers

Treat the German/decimal-comma/half-of parser and locale counterexamples as **candidate extensions** to the already source-bound Run134 evaluator. Preserve its equation-echo binding, source spans, exact FINITE division guard, Run517/521 same-event/same-session persisted FINAL binding, dedup and SHADOW-only rights. Preregister a cross-branch merge with explicit source/test ownership, run original Run134/150/184/517/521 and native heldout cohorts plus new DE/locale cases, and compare false-alarm coverage on genuinely heldout answers. Do not simply add a second evaluator or a second live CLI; do not merge these parallel PRs directly into main. Owner review is required; current branch heads are not production-integrated.

Unchanged gates: AGE0c STAY_SHADOW; LP1 NO_ATTRIBUTABLE_GAIN; LP2 ALIGNS_NO_GAIN; BJ1 NO_SIGNAL; STEP2 UTILITY_FAIL; B3 L1 FAIL; jepa_weight0; Age authority0; Redmi unmeasured; V13 incomplete.
