# V13 independent pair-clause scope review — pre-registration (2026-10-29)

Owner: GPT-6 isolated review. Parent: Run141 PR #1042 at exact `130f8424f4cc993e4287c7cfb94c4e58e551ac07`; this file MUST be committed before new candidate/test source. Original Run141 candidate blob `7f13f5d01f4df2919e27a0ac24ce89f347a2d328`, frozen runtime eligibility blob `e1f1a2d09a614378a75e397819fdce96a46de22d`. Preserve original Run141 evidence and all registered fixture/model/seed/source hashes.

## Source-observed failure (before candidate)

The Run141 per-entity regex extracts both A and B values from the **same unscoped** clause `Option A and Option B: cost 60 euros, duration 3 days, local true.`, treating each as separately stated. Local independent regex reproduction observed both entries `cost=60,days=3,local=True`; this does NOT demonstrate a native model failure. Reversed pair, comma pair, and later-source overrides are further test cases.

## Hypothesis and implementation limit

Create an isolated, default-off, source-only wrapper around Run141's reader. Reject any selected source text with a typed joint A/B clause where typed values cannot be attributed to an individual option. Newest complete individually scoped options may override an older ambiguous clause. Pure A/B references and separately scoped complete options must continue to work. No production runtime, original candidate, model weights, native evidence, or Age authority may change.

## Predeclared acceptance

- RED witness: original reader returns two identical options for the single typed joint clause.
- Guarded reader: joint A/B typed clauses (A-and-B, B-or-A, comma) => options unavailable, no A/B/NONE commitment.
- Pure pair reference with verified older individual options => two correct options; current individually scoped complete options override old ones.
- Current complete options outrank older joint ambiguity; newest joint ambiguity blocks stale fallback; partial update remains unavailable; invalid inputs raise before reading.
- Source scope: only exact authenticated current/history strings; caller remains responsible for authentication.
- Focused Python unittest exit 0, compileall exit 0, `git diff --check` exit 0, public privacy scan CLEAN, independent review of changed files; full-suite CI if available. Preserve original failed attempts and raw evidence. No benchmark gate promotion.

Claim limit: English deterministic grammar counterexample and software-only defensive candidate; not native B1/B2, not measured on Redmi, not JEPA learning, not proof of STEP2 utility. Negative gates fixed: Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight=0; V13 INCOMPLETE.

Next: implement isolated candidate/tests, run focused and full software CI, independently inspect raw and remote blobs, persist review handoff, continue other canonical work.
