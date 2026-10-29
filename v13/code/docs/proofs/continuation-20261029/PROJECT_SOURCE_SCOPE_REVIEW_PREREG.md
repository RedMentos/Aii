# V13 Context OS project-scoped source selection — pre-registration (2026-10-29)

Owner: GPT-6 independent review. Exact parent Run141 PR #1042 head `130f8424f4cc993e4287c7cfb94c4e58e551ac07`, Run141 candidate blob `7f13f5d01f4df2919e27a0ac24ce89f347a2d328`, frozen eligibility runtime blob `e1f1a2d09a614378a75e397819fdce96a46de22d`. This prereg must be committed before any new implementation/test. Independent sibling of pair-clause scope PR #1043; do not overwrite it.

## Source-observed issue

Run141's `read_fixed_reference` scans all prior exact history without checking project identity. Current `Project Beta` rules and bare A/B reference may therefore combine with older `Project Alpha` option values and commit a decision about Beta using Alpha's supplier sheet. This is a deterministic cross-project source-selection hazard, not a model experiment.

## Frozen test design

Isolated, default-off `context_option_project_scope_candidate.py` filters prior source by a unique explicit exact `Project <single-token>` label matching the current request. A source with absent or multiple conflicting project labels is not trusted as history for this reader. If current project is absent or ambiguous, do not borrow history; current complete options may be used only when identity is absent (not ambiguous), with current rule values. Preserve Run141 original unchanged. Tests: original cross-project RED witness, refusal of foreign-only history, matching-project success, interleaved projects, foreign latest rule cannot override, missing current project cannot borrow, conflicting current labels fail closed, current complete options without history still work, invalid input, and untouched negative gates. Explicit project alias resolution and multiword names are outside scope; abstain rather than guess.

## Acceptance / limits

Prereg first; candidate + tests isolated; pinned source hashes, focused/full software CI, privacy CLEAN, closed raw SHA256SUMS, independent review, remote byte verification. No model/seed/fixture/source modifications, no new native or Redmi claims, no runtime activation, no user-authority change. Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight=0, V13 INCOMPLETE.

Next: run exact-head software tests and compare with Run141 and pair-clause guard; do not merge independent siblings without combined source-scoped review.
