# Core handoff — source-bound exact arithmetic C5 fastpath

**Date:** 2026-11-21  
**Owner:** Core & Harness  
**Base:** gpt6/v13-private-remote-bridge-20261111 at 4a471ae40dd9b768c8130fafdba51900b5417800  
**Status:** implementation checkpoint; exact-head CI pending; NOT_RELEASED; REDMI_UNVERIFIED.

## Defect and integration hypothesis

Issue #1904 records a wrong Redmi result for the simple arithmetic query 2+2. The current release has an operator-approved fixed-answer policy consumed before the normal native answer path, but it has no built-in exact arithmetic producer. The existing arithmetic reflex can classify/compute expressions, but it is not a source-bound C5 answer policy.

A narrow deterministic evidence function can create a C5 policy for one complete binary integer expression, then reuse the existing OutputPolicyDecision, source-reference, ActionOutcome and Runtime transaction path. Nontrivial, multi-step or explanatory prompts return no policy and remain eligible for the normal multi-organ route.

## Implementation

- v13/code/v13/exact_arithmetic.py: bounded integer +, -, * and × evidence; no eval, floating point, division, native model call or action authority; ambiguous bare year-month/month-day forms rejected.
- v13/code/v13/output_policy.py: active operator-authored exact rules keep precedence. Only after they fail to match does the built-in arithmetic evidence create exact SYSTEM_DETERMINISTIC_QUERY and SYSTEM_DETERMINISTIC_ANSWER SourceRefs. The policy is consumed by the existing Runtime C5 direct path; no Runtime or global packet schema edit is needed.
- v13/code/tests/test_v14_exact_arithmetic_runtime.py: pure positive/negative controls, operator precedence, real Store source persistence, and a real Runtime/SQLite turn asserting 2+2 -> 4, no native runner use, persisted OutputPolicyDecision and normal ActionOutcome/PredictionOutcome/ExperienceRecord path.
- .github/workflows/v14-core-exact-arithmetic.yml: Python 3.13/3.14 compile, exact policy, Store and Runtime tests, plus existing arithmetic/focal regressions.

## Evidence boundaries

- LOCAL_LINUX exact repository checkout: BLOCKED; git ls-remote https://github.com/RedMentos/Aii.git failed because github.com could not be resolved.
- LOCAL_LINUX isolated arithmetic-module compile and focused positive/negative tests: PASS 2/2 on Python 3.13.5. This was a reconstructed isolated module test, not the full repository or Runtime integration.
- CI: pending on exact branch head.
- REDMI/TERMUX: UNVERIFIED; no owner-consented live receipt, no installed SHA and no native device measurement.
- No model, weight, permission, device state or user data changed. This is a deterministic code path, not learned reasoning and not whole-system completion.

## Next step

Run exact-head CI and review any Runtime regressions. If green, request Boss review because output_policy.py is an existing C5 production module and the safe-additive gate may reject the path. Do not merge or deploy without independent review. After approval/release, use the normal verified updater route only if a fresh owner-read receipt proves installed SHA and consent; then test 2+2 and nontrivial multi-organ turns on the authorized Redmi.
