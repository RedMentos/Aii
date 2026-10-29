# C3 F1/F5 budget contradiction and hedge veto — observed result (2026-10-29)

## Scope and source
- Draft PR #1154, review-only child of PR #1153, parent `c5052795070ccf36b5273b4907562fd3220f51a0`. Original `ask_verified_budget.py` Git blob `22d479e83478fd8a7581f26732301fa272edecc2`; candidate `704b2a0c0dc90f06a842d5a828984b7e72692ae2`. Canon `218464b12a2d27d92524c751922fa8e1c3fb0ea7` unchanged.
- Local original-source replay proved false positives for `isn't`, `false`, `doubt`, `may`, `rejected`. The patch adds a narrow conservative lexical veto for negation, refutation, hedging, conditional and German uncertainty words. Existing exact project/number/currency and source/dispatch/release checks remain unchanged.
- This is a conservative veto, **not** a semantic truth verifier. It may reject some harmless sentences to avoid affirmatively presenting an uncertain or contradictory generated answer as a verified source fact.

## Preregistered RED/GREEN evidence
- **RED before source edit:** Actions `40961347313`, exact HEAD `91b98095d7bb47aba53c36fe9d2bb5725e19871f`, **42 tests / 12 FAIL** (11 adversarial lexical cases plus one mocked native answer wrongly released). Artifact `12936420999`, ZIP SHA256 `f577db756c8e7a02108aa2626b6a5ffe3bb1e594885a25737da36bd3906b94bc`, CRC clean, **18/18** inner hashes; CANON/VENV/DEPS/PIP_CHECK/COMPILE/PRIVACY/DIFF exit0, FOCUSED exit1.
- **GREEN after source edit:** Actions `40961608754`, exact HEAD `dedc2b41315a615d1e79ac88ad9a6f0e64baded1`, **42/42 PASS**; all eight stage exits0. Artifact `12935602244`, ZIP SHA256 `f8ed06b06c8a8bff845191b71bd0acc7299027b2a467b99211adbbf3ab99d867`, CRC clean, **18/18** inner hashes.
- Both original ZIPs retained privately under `/V13-Checkpoints/2026-10-29/Run10-C3HedgeVeto/` and re-materialized byte-exact SHA256 matched. No source/test/cohort/seed/model pins were retroactively rewritten.

## Next work and limits
- The next independent full cross-organ software replay is preregistered in PR #1155 (Body-JEPA and C3 changed sources together), after this focused GREEN. Expected discovery count 3311, with frozen Run34/Run37 negative pins still RED; do not claim full-suite PASS.
- All native calls in the integrated test are mocked. No actual C3 generation, source-use quality improvement, learning, STEP2/B3/LP3/Body-JEPA gate promotion or Redmi proof is inferred.
- Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight0; AG6 unapproved; V13 INCOMPLETE.
