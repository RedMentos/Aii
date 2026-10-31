# Gate verdict type-confusion follow-up — prereg 2026-10-31

Owner GPT-6, same review-only STEP2 exit branch. Independent review after original split code and initial CI launch found `v13/gates.py:verdicts` uses Python equality `1 == True` and eagerly evaluates all three operators in a dictionary. Thus a numeric 1 could satisfy a Boolean canonical gate and a valid equality with null could incorrectly raise from unused >=. This is an evaluator correctness issue, not new native evidence.

Before patch, register fixed negative controls: `canonical_gate_pass: 1`, `1.0`, `"true"` must all fail expected Boolean true; `true` must pass, `false` must fail; `null == null` must pass; numeric `>=` still works, Boolean numeric comparisons refuse. Patch only operator dispatch in `verdicts`, preserve graph/source/results, original first CI raw and all failed cases. Re-run focused + original tests with new trigger, audit original ZIP and backup. No STEP2 promotion.
