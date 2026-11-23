# C6 source-bound lexical v2 SHADOW — prospective software preregistration

**Date:** 2026-10-31 UTC. **Owner:** GPT-6, isolated review branch `assistant/v13-c6-lexical-v2-shadow-gpt6-20261031` based on Run60 audit `de79f3314844c88a9289528998272362df081aaa`. This document is committed **before** implementation, tests and workflow.

## Problem and non-goals

The original C6 positive-assertion guard admits only two narrow affirmative templates. It refuses some plausible, source-correct short answers (e.g. `The budget for Project Cypress is 64 euros.` and `Project Cypress's budget is €64.`). A broader *bounded* grammar may increase eligible SHADOW candidates without changing the frozen source, stored DRAFT, F1/F5 correction, temporal checks or egress authority. This is not a replacement of the seed607 native scorer or its original RED; **no output, FINAL, TTY approval, tools, training, or production Runtime wiring**.

## Frozen grammar treatment and baseline

Use a new default-OFF candidate module alongside unchanged `c6_positive_assertion_candidate.py`. Require a **single full sentence**, exact one source project name, exact source amount, one Euro currency expression, no extra clause/number/project, no negation/question/uncertainty. Accept only these syntactic forms, with case-insensitive fixed tokens and a period:
1. `Project NAME budget is N Euro|Euros|EUR|€.`
2. `The budget for Project NAME is N Euro|Euros|EUR|€.`
3. `The project budget for Project NAME is N Euro|Euros|EUR|€.`
4. `Project NAME's budget is €N.`
5. `The budget for Project NAME is €N.`
6. `Projekt NAME Budget beträgt N Euro|EUR|€.`

The exact project and N are parsed only from an independently admitted F1/F5 source via `entities(topic)` and `BUDGET_VALUE.fullmatch(value)`. Do not infer facts from B1/B2 hypotheses or decoded text. Existing `preflight_temporal_draft` must succeed **before and after** the new lexical check, with identical candidate/fingerprint. A fresh Store read must bind the staged DRAFT hash, source memory ID, session/event and status. A returned fingerprint is NOT a TTY approval token.

## Prospective disjoint software fixtures and expected results

**Positive (8):** Cedar 42 Euro canonical; Cedar 42 euros; Cedar 42 EUR; Cedar 42 € suffix; `The project budget for Project Cedar is 42 Euro.`; `Project Cedar's budget is €42.`; `The budget for Project Cedar is €42.`; `Projekt Cedar Budget beträgt 42 Euro.`.

**Negative (at least 14):** `not` before amount, wrong amount 43, wrong project Birch, extra second project, extra number, second sentence/tool intent, question mark, no currency, missing project, missing period, contradictory suffix, `€42 EUR` double currency, source with two projects, malformed amount, newline plus appended instruction. All negative fixtures must be rejected; 8/8 positives should be accepted by the new pure grammar, while original v1 behavior remains unchanged.

**Real SQLite integration:** reuse original Run51 Cypress seed467 as a frozen setup **only** (no change to its native cohort/scorer). Verify DRAFT stage through actual Store, temporal F1/F5 checks, no output/FINAL/action dispatch/learning, revoked source, tampered DRAFT, competing DRAFT, forged approval, opt-in `1` rejection, and baseline v1 rejection of a newly accepted v2 phrase. All claims software/synthetic, no native/Redmi utility.

## Evidence / acceptance / rollback

Use a new `v13/code/v13/c6_budget_lexical_v2_candidate.py` and `v13/code/tests/test_c6_budget_lexical_v2_candidate.py` with a pinned GitHub Actions software workflow on this review branch. Require unit and real SQLite integration tests, compile, source pin, privacy scan, diff check, and closed raw SHA256 manifest (including RED). Do not mutate original registered seed607/Run59 source/fixture/scorer. No source, model, seed or age gate may be promoted from software tests. If any negative fixture is admitted, retain RED and do not enable. Future native utility requires a separately preregistered disjoint cohort.

**Gates unchanged:** Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, jepa_weight=0, World-JEPA SHADOW, Redmi unmeasured, whole-system incomplete.
