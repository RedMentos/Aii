# Run141 prereg — multi-turn option-reference fallback, deterministic Context OS control

Date 2026-10-29. Owner `codex/v13-run141-context-option-reference-20261029`. Exact base Run138 PR #1039 at `61b498ae2f7499740acdf32ebb6935b64469b474`. Independent of Run139/140 review branches, with disjoint new files. Frozen runtime `v13/code/v13/agi/eligibility.py` blob `e1f1a2d09a614378a75e397819fdce96a46de22d` is NOT edited.

## Source-observed gap

The current `fixed_option`/`read_fixed` selects the *first* `Option A/B` clause in the newest text. A current user request like `Decide between Option A and Option B from the earlier supplier sheet` mentions both entities without any typed option values. The fixed reader stops on this incomplete reference and returns None or raises, even when an earlier exact source states complete options. This is a multi-turn functional gap in Context OS source consumption, not a model capability. The source-only Run140 candidate worked around it by reading option values from verified quotes. The gap was observed in code before this prereg; results from any later fixture replay are post-observation, not fresh native evidence.

## Fixed algorithm and acceptance

Implement an isolated default-off deterministic candidate `scripts/context_option_reference_candidate.py` that uses existing `eligibility.fixed_rule` unchanged, and for options:
- Search newest source first. Skip a **pure reference** clause only when it contains no typed option fields or numbers and the source explicitly pairs `Option A and/or Option B`; then fall back to older exact source. Do not skip partial numerical updates, unknown rewordings, or contradictory complete clauses.
- Complete typed option clause must uniquely contain cost, days and local bool for the named entity. Two distinct complete values in one source are ambiguous and refuse. A partial latest update blocks fallback, preventing silent stale option use.
- Current complete option values override older ones; missing/ambiguous -> `options=None`, no guessed action. Rules use the existing newest exact-source reader; ambiguous current rules remain None. No model call or oracle is used to extract values.
- Source authenticity is an upstream Store/source-ref obligation; this candidate does not claim to authenticate untrusted history.

Focused tests: pure task reference + earlier complete source, current complete override, partial current update, conflicting current clauses, missing older values, newest earlier partial update, rule conflict, input immutability. Optional frozen Run116 six-fixture full-history upper-bound diagnostic must use exact original SHA and count output only after reading; score with oracle *after* predictions. This is not a fair B2-limited control or a new native cohort. Never alter registered fixture/model/seed/raw or enable live path.

Branch-only source-pinned CI with original Run138 raw hashes, focused/full/privacy/diff and closed evidence. Preserve RED. No production runtime change, native inference, training, Redmi test or gate promotion. Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight=0, Redmi UNMEASURED, V13 INCOMPLETE.
