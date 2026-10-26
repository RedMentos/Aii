# Run493 — source-provenance precedence in live fixed JEF eligibility (before tests)

Date: 2026-10-26. Independent candidate branch from Run492 PR #490 at `122e1ed62ba2b04841ae567051754da399282c7e`. Do not modify the Run491 registered held-out cohort, native model/runner hashes, or another owner's active PR.

## Pre-registered failure hypothesis

In production `ToolStep._propose_eligibility`, `earlier_parts()` returns (user history oldest→newest, source-verified body quotes), but `read_fixed(text, hist + quotes)` reverses that combined list. Therefore an **older body quote can override a newer direct user rule** when the current question omits that rule. Also two conflicting verified body quotes can silently choose whichever quote appears last. This is an authority/source-order defect, not a model-accuracy finding.

## Authorized candidate correction

Keep `read_fixed(current, earlier)` unchanged for frozen callers; add a new `read_fixed_sources(current, user_history, verified_quotes)` with explicit precedence: current message > newest direct user message > mutually consistent verified body quotes. Conflicting values at the highest available priority return null/UNKNOWN, not an older fallback. For option clauses, current explicit partial/conflicting clauses cannot be repaired from older sources; verified quotes are accepted only if mutually consistent. Switch only live `ToolStep` `eligibility_reader='fixed'` to the provenance-aware reader. Preserve existing model fallback for unparsed options and ensure model-derived rules are still overwritten by fixed rules; no learning/permission/gate promotion.

## Exact expected regression checks

1. Current rule wins over all history/quotes.
2. Newest user-history rule wins over stale verified body quote, with real `Runtime -> ToolStep.plan -> shadow` path, no C3 read when options covered.
3. Conflicting quotes alone cause UNKNOWN, never arbitrary precedence.
4. Conflicting current rule causes UNKNOWN, never older fallback.
5. Partial current option statement cannot be completed from an older quote.
6. Old Run490 live fixed-reader tests and relevant ToolStep/eligibility tests remain GREEN.
7. Source-only GitHub Actions records raw unit/negative-gate/privacy output and SHA256 checksums. No native/Redmi evidence inferred.

Evidence classification: software/source-only; frozen Run491 1050 planned rows unexecuted. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, Redmi unmeasured, Age-0 unchanged. If the regression is reproduced, retain original RED Actions evidence and subsequent fixed GREEN Actions separately. No force push or merge into a frozen active cohort.
