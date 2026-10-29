# HB0 / P0 split-information cohort — pre-registration (2026-10-29)

Parent: `9eaccc99448af39aaa534b90c4924f11f8ecb389` (PR #1046 review head). This file is committed **before** source, tests or evaluation. Owner: V13 automation, separate review branch. No production/runtime edits.

## Problem and exact contract

The binding Canon requires measurable complementarity of B1_DETAIL and B2_GIST, not merely a better prompt. Existing small STEP2 fixtures and C3 consumption failures do not establish that a future task requires two separately available information sources. Build a deterministic **software-only** 150-row structural cohort that has both B1 and B2 information necessity, balanced correct actions and explicit cross-project distractors. It is a preflight for a *later*, independently preregistered native/model comparison; not the comparison itself.

Generator `v13/code/scripts/hb0_split_information_cohort.py`: 25 disjoint families, each a 2x3 counterfactual grid (two supplier sheets x three rule sets), exactly 150 rows. Each family must have two A, two B and two NONE oracle outcomes. Within each family, fixing rules and changing the sheet changes the answer in every column; fixing a sheet and changing rules changes the answer at least once per row. Family-specific additive price/budget shifts preserve those constraints. Source strings have unique project identities, a separate earlier rules note, a separate recent options sheet and an explicitly foreign conflicting distractor. Current requests do not contain typed rule/option values. Split views expose B1 sheet-only, B2 rule-only, C3 current-only. Complete verified source view is a separate deterministic control.

Source-visible controls: exact deterministic `eligibility.recipe` oracle, incomplete-view abstention, full-source default-off `context_option_safe_scope_candidate.decide_safe` as a **software parser control**, and counterfactual grid consistency. No models, no train weights, no oracle supplied to any model prompt. The source control is not a substitute for a C3-alone or one-body-native baseline. Dataset/seed/source hashes and all original registered cohorts remain unchanged.

## Tests and falsifiers (registered before implementation)

1. Exactly 150 unique rows, 25 families of six, balanced 50 A / 50 B / 50 NONE; deterministic SHA256 across two constructions.
2. Each family 2x3 counterfactual necessity and oracle equality with original deterministic recipe.
3. Current-only, B1-only and B2-only views cannot obtain a complete deterministic decision; full-source exact parser control must match all 150 or record RED.
4. Foreign distractor must be project-distinct and have contradictory numeric content; deleting the authentic rules/sheet must never yield a committed answer from the foreign source.
5. Family-disjoint calibration/held-out partitions (5 families / 20 families); these are **not** native or model-held-out results and may not be used as evidence of model generalization.
6. Tampered duplicate identity, missing B1/B2 source, corrupted family action and answer-bearing current text must be rejected by structural validation.
7. `python3 -m unittest -v tests.test_hb0_split_information_cohort`, `python3 -m compileall -q` for new files, and full suite + privacy scan + remote GitHub Actions source-pinned CI. All failures retained in raw artifacts.

## Limits and non-promotion

This construction intentionally gives C3 no values, so information necessity is a **synthetic task property**. It cannot establish the proposed P0 criterion of at least 15/150 measured oracle-versus-C3 improvement, nor STEP2 complementarity over one body with two timescales, native utility, memory retention, phone speed, or learning. No model calls or new Redmi measurements. Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight=0; V13 INCOMPLETE. Never change those gates based on this cohort.

## Next real experiment

After source-pinned CI and independent review, preregister an independently generated and nonpublic model-evaluation cohort, real C3-alone / one-body-two-timescales / B1+B2 / shuffled-body / full-source-oracle arms, a fixed source budget and a fresh seed, then measure accuracy, wrong commitments, latency and variance. If native model access is unavailable, preserve this structural package and work on another independent canonical package.
