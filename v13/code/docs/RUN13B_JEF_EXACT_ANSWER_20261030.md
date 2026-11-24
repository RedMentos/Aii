# Run13B — exact-source JEF human-readable budget answer (2026-10-30)

Review-only prospective software package. Owner: GPT-6 automation; files owned only under `v13/code/v13/agi/budget_answer_shadow_run13b.py`, `v13/code/tests/test_budget_answer_shadow_run13b.py`, `v13/code/docs/RUN13B_JEF_EXACT_ANSWER_20261030.md`, and a dedicated workflow. Base: `assistant/v13-g13-fullsuite-review-20261030-auto11` at `95470883a74672530f75f5c8e0623dd25c9da6d1`. No change to original Run13A native cohort, scorers, models, learning weights, runtime or Canon.

## Problem and test-before-claim contract

The registered Run13A 32-turn Linux-native result has structurally valid 32/32 rows but fails the preregistered full-task utility comparison (F auto numeric 0/16, strict 0/8; B2 numeric 6/16, strict 2/8). Existing Run11Y JEF `budget_en_source_shadow.propose` correctly extracts both budget remainders and the faster option from eight Run13A source prompts, but it returns only a structured SHADOW candidate. Build a separate human-readable, exact-source answer renderer that cannot silently promote the native model or STEP2. This tests an actual full-answer data path without claiming model understanding or end-to-end native utility.

Prospective checks: for all eight **unchanged** seed211 sources, independently create Store SourceRefs for exact source and exact query, render a text answer, require the frozen Run11V numeric contradiction-veto scorer to award 2/2 and frozen Run12N explicit faster-choice parser to select the expected option (8/8 strict *software answer-form* only). Verify no native pool acquisition, no new source rows from rendering, zero authority, zero learning, and all original negative gates. Counterexamples: foreign-project query, unsupported source paraphrase, altered source, query/source alias, and a changed result between first and second source verification all abstain. No output may contain unverified numbers or external action suggestions.

## Scope and acceptance

The renderer is an **opt-in pure Store-backed API**; not a Runtime turn, CLI output, tool, C5 authorization, active answer repair, JEPA learning, native inference, Redmi evidence, or production integration. It uses the existing closed-world JEF grammar, verifies source/query before rendering and again immediately afterward; no claim that double-read eliminates all concurrent revocation races. Fail closed to no answer on any mismatch. No frozen scorer/model/source/seed hash changes, no waivers to historical fullsuite RED.

Tests: `cd v13/code && PYTHONPATH=.:tests:scripts python -m unittest -v tests.test_budget_answer_shadow_run13b tests.test_run13a_fulltask_prereg`. Run `python -m py_compile`, `public_repo_privacy_scan.py --base 95470883a74672530f75f5c8e0623dd25c9da6d1 --head HEAD --no-worktree`, and `git diff --check`. Source-only GitHub Actions original logs, exit codes and SHA256SUMS must be retained even if RED. No test grants STEP2/B3/Body-JEPA/jepa_weight/Redmi or whole-system completion.

Next independent package after this checkpoint: an operator-only, explicitly requested existing-home interface with exact SourceRef arguments and no model calls, if the source renderer is GREEN; independently check source revocation/Store semantics before any live UI integration. Full native utility requires a NEW disjoint preregistered comparison; original Run13A remains RED.
