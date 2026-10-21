# Fixed-plan learning analysis integrity candidate — 2026-10-16

This is a synthetic software correctness check. No models were launched, no
native learning improvement was measured, and no existing gate was promoted.
The original M learning checker and its numerical thresholds remain unchanged.

The original `scripts/tool_forecast_learning_check.py:analyze` reports
`CONTINUAL_LEARNING_CONFIRMED` for the saved four-row input despite its fixed
plan requiring 21 rows. Each world contributes only one shifted action and one
retention action; all experience rows and the other actions are missing. The
original analyzer computes its majority and retention denominators from the
observed scored actions, so those omissions disappear from the decision.

The isolated candidate API is:

```python
from scripts.tool_forecast_learning_integrity_candidate import analyze_checked
report = analyze_checked(all_phase_a_and_b_rows, learn_report, fixed_plan_document)
```

`validate` is also available when a caller needs coverage diagnostics only.
The fixed plan document is the JSON object with its `plan` mapping. The checker
requires all six nonempty arms, distinct planned states within each world, all
four calc or three note actions for every state, unique planned cases and
call/forecast IDs, `SCORED`/`EXECUTED`, finite nonnegative MSE and explicit
adapted MSE after successful learning. Learn world/action metadata and Phase-A
experience counts must agree with the plan. Experience cannot follow test rows.

The saved partial input is rejected before the original analyzer runs: 17 of
21 cases are absent. A complete 21-row synthetic fixture reaches the original
analyzer and produces exactly its existing numerical output. The test suite
also preserves the original strict majority, `<0.90` shifted gain, and `<=1.02`
retention boundaries. Valid zero MSE is accepted as a row value; if the original
ratio computation becomes undefined, the candidate records analysis unavailable
and cannot confirm. It adds no epsilon or substitute numerical gate.

The current `specs/tool_forecast/learning-plan.json` expands to exactly:

| Arm | States | Actions | Rows |
| --- | ---: | ---: | ---: |
| calc_shift_exp | 40 | 4 | 160 |
| note_shift_exp | 30 | 3 | 90 |
| calc_shift_test | 30 | 4 | 120 |
| calc_in_test | 30 | 4 | 120 |
| note_shift_test | 20 | 3 | 60 |
| note_in_test | 20 | 3 | 60 |

Total: 610 rows, including 250 Phase-A experience rows and 360 Phase-B test
rows. The saved grid validation is generated synthetically from that plan;
it is not a 610-row native run.

Run the focused regressions from `v13/code`:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:tests python -m unittest tests.test_tool_forecast_learning_integrity_candidate -v
```

`manifest.json` binds source files and the closed evidence. Integration into a
new checked runner belongs to the coordinator; the original M files are intact.
