# Run101 — reject refuted arithmetic answers in ToolStep shadow agreement (preregistered)
Date: 2026-10-25 UTC. Base Run100 verified branch head `041cfad68d4ff72842103d1fbce5659f074b7f37` (PR #132). This is a **new independent package**, not an amendment to Run100 or concurrent Run99 Callosum work.

Owner: `v13/code/v13/toolstep.py` `ToolStep.compare` arithmetic branch only, `tests/test_toolstep_negation_run101.py`, isolated workflow and this proof. No edits to Context OS, Callosum, Sleep, World Model, JEF or native files.

## Why this matters
The existing `compare()` uses substring presence of a correct calculator number as `agree=True`. A model response explicitly saying that number is **wrong** is nevertheless counted as agreement in persistent `TOOL_SHADOW_AGREEMENT` SQLite state. This poisons evidence for the Age-1 tool right, even though the tool itself remains gated. This is not a proof of actual math utility.

## Preregistered RED with actual Runtime/ToolStep/SQLite
Create a real event asking `What is 48 times 37?`, obtain an Age-0 policy-refused `calc` proposal and its actual pure shadow result `1776`. Compare final output texts:
1. `No, 1,776 is incorrect; the answer is 1,775.` => **False**.
2. `The result is not 1,776; it is 1,775.` => **False**.
3. `Either 1,776 or 1,775.` => **False** (explicit ambiguity).
4. `I cannot verify 1,776.` => **False** (unverified claim).
5. `The answer is 1,776, not 1,775.` => **True** (the negation applies to the *other* number).
6. `The answer is 1,776.` => **True**.
Check persisted counts and inherited `tests.test_toolstep`. Initial test-only PR expected 4 RED and 2 GREEN.

Candidate: narrowly reject matches explicitly negated/refuted/uncertain in a local lexical window, without making a claim of full semantic verification; retain positive unambiguous matches. Do not modify actual tool permissions, execution, output, or learnable gates. Preserve raw RED/failed attempts and all CI outputs. Source binding remains the existing real event/ToolStep path.

## Claim limits
This is a conservative **software-only shadow telemetry guard**. It cannot infer all natural-language negation, numerical equivalence or final-answer intent; future independent arithmetic answer-aware audit is needed. No native models, Redmi, learned utility, tool rights or age promotion. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, full V13 INCOMPLETE. Public repo privacy scan required. Do not retry rejected Drive backup.
