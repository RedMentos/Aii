# C3 native source-prompt disjoint three-arm diagnostic — preregistration (before runner/fixture)

**Date:** 2026-10-31 UTC. **Owner:** GPT-6 independent review branch from original Run59 exact head `aa0ce5d4808b1afe77a3af373862ae6ea52de052`, PR #1398. This is a *new prospective cohort*, not a Run59 corrective re-score, not a B1/B2/JEPA proof and not a source of human feedback.

## Motivation / hypothesis

Run59 recorded five genuine native B1/B2/C3 calls with structural verifier success but **C6_GROUNDING_RED**. The fused C3 prompt may overload a 350M model; however the status alone cannot attribute cause to prompt, body evidence or C3 capability. Isolate the pinned C3 decoder and compare three *source-equivalent* prompt renderings with disjoint authored project texts, without touching original Run59 source, models, seed467, scorer or result.

## Frozen authored cohort, seed and order

Seed **607** for each C3 generation; max 64 tokens, `CONFIG | OVERRIDES` from Run47/Run52; pinned C3 model `LFM2.5-350M-QAD-Q4_0.gguf` SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`; pinned llama-server runner SHA256 `79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39`. Other installed B1/B2 pins unchanged but **not called**. Three newly authored sources, no overlap with Run51 Cypress/Lark/Delta or Run52 Harbor/Willow/Cobalt:

1. `Ambercrest`: `Project Ambercrest has a budget of 73 Euro. What is Project Ambercrest's budget?`; expected `73`; order PLAIN, SOURCE_FIRST, JSON_ENVELOPE.
2. `Foxglove`: `For Project Foxglove, the approved budget is 28 Euro. How much is the budget for Project Foxglove?`; expected `28`; order SOURCE_FIRST, JSON_ENVELOPE, PLAIN.
3. `Northstarlet`: `The budget for Project Northstarlet is 91 Euro. Please state its budget.`; expected `91`; order JSON_ENVELOPE, PLAIN, SOURCE_FIRST.

No earlier user correction or body offer is present; do not claim second-attempt utility. Each source is persisted through real Store.event and hashed before native generation; output is a non-committed offline diagnostic.

## Frozen prompt arms

- **PLAIN:** system `Answer in English in one short sentence. Use only the user's text; do not invent facts.`; user = exact source.
- **SOURCE_FIRST:** system `Answer in English in one short sentence. Only the current user source is evidence; if a fact is absent, say unknown.`; user = `Current user source: <exact source>\nQuestion: State the named project's budget and currency.`.
- **JSON_ENVELOPE:** system `The current_source text is the only authoritative evidence. Body hypotheses are not facts. State the project budget in English in one short sentence.`; user = JSON `{"current_source":{"text":"<exact source>"},"body_observations":[],"body_hypotheses_are_facts":false}` serialized with project code's `dumps`.

No hidden chain-of-thought request, source alteration, forced answer string, or extra factual hint. These prompts are engineering treatments, not proof of general semantic comprehension.

## Frozen scorer, analysis and gates

For each native output, normalize Unicode casefold. **numeric** success requires the expected amount as a standalone digit sequence, no *other* standalone 1–3 digit integer, no other cohort project name, and no `not/no/never` within 24 characters preceding the amount. **strict** success additionally requires the exact project name and `Euro` or `euros` in output. No source answer may be copied by code as the candidate; scores operate on actual C3 decoded text. Source-level numeric-only copying may succeed and does not prove reasoning. Missing output, wrong amount, invented number, unsupported project, or negation = failure. Preserve raw failures and text in the closed native artifact; final public report can use hashes and scores only.

**Structural gate:** 9/9 real pinned C3 `FINAL` calls, exact source hashes and revision, 9/9 process releases, zero FINAL/OUTPUT_COMMITTED, zero tool/learning authority, closed SQLite audit, and independent report verifier. **Prospective exploratory utility thresholds:** SOURCE_FIRST numeric >=2/3 and SOURCE_FIRST numeric > PLAIN numeric by >=1; otherwise `UTILITY_RED`. Strict per-arm scores are reported separately and not substituted. A structural pass with utility RED remains RED for utility; no STEP2, C6, B3, JEPA or whole-system promotion under any outcome. No Redmi proof.

## Procedure

Preregister this document first; then create frozen JSON fixture with exact 3 rows/arm order, runner, independent verifier, tests and isolated GitHub Actions native workflow. Bootstrap public pinned artifacts, serialize native jobs under existing concurrency group, save raw receipts including failed cases and SHA256SUMS, private Library backup, independent byte comparison. Do not mutate Run59 original report/score/seed. If runner/permissions unavailable, record exact blocker and continue other Canon packages.
