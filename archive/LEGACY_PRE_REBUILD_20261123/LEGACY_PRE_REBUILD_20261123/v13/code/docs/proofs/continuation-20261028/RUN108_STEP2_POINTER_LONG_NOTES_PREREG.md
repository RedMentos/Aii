# Run108 prereg — STEP2 B2 pointer long-note/revision structural stress (2026-10-29)

Owner: GPT-6 scheduled continuation. Independent **software-only diagnostic** on independently GREEN Run105 exact `e56753ffe8fc3b78e341659a19e7af02302d9bb8`, not part of Run107 integration. WP-Z2d earlier raw (`bench-results/step2-z2c-b2-rule-20261021`) established CQP B2 rule quotation .969 on short fixed notes, but longer/revised notes and same-B2 one-body control remain untested. **No STEP2 gate promotion**, no new native inference, no changes to registered cohorts/model/seed.

## Predeclared deterministic fixtures/metrics
Use frozen `v13.cognition.quote_choices(sources,cap=24)` and `quote_span(header,source,context_chars=200)` exactly as current production. Public synthetic project Kestrel; three explicit cases plus cap stress:
1. **SHORT**: 96-char kickoff note with Budget 100 euros, Deadline 5 days, Local-only true. Pointer to header expands to include all three rule values under 200 chars. Baseline positive transport.
2. **LONG**: same header followed by >=12 independent filler sentences, then same three rule values. Header-pointer 200-char expansion cannot include all rules; this is an expected **coverage failure**, not hallucination.
3. **REVISED**: original three rules followed by an explicit later revision to Budget 120, Deadline 7, Local-only false. The exact header quote must not be treated as proof of *which* revision is authoritative; measure whether the expanded span contains both versions and report ambiguity, not auto-choose.
4. **CAP24**: source with >=30 filler sentences before the three rules; `quote_choices` truncates at 24. Report whether any rule-bearing sentence is selectable; expected no.

Each fixture is source-exact, fixed deterministic, no model. Output per-case: total source chars, sentence count, available choice count, header span, whether old/new rule values are present in expanded source span, rule-bearing choice coverage, and `semantic_truth_authority=false`. Fail test if a span is not an exact substring of its own source or if any model call is made. Expected short full coverage, long and cap failures, revision ambiguity (do not infer a corrected answer). Distinguish structural transport from native model selection.

## Ownership / proof
Only new `v13/code/scripts/run108_step2_pointer_long_notes.py`, `v13/code/tests/test_run108_step2_pointer_long_notes.py`, branch state, pinned software CI and closed raw SHA256SUMS; no changes to `cognition.py`, B1/B2/C3, config, source corpus, model hashes, Canon or previous Z2d raw. New native STEP2 one-body/two-state vs two-body pointer cohort with fresh episodes/seeds requires a separate prereg and serialized model run after this diagnostic.

Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA/LP3 unproven, jepa_weight=0, Redmi unmeasured, whole V13 incomplete.
