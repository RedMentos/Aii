# WP-Z6d BEFUND: explicit human route rule (`:ersetze route … --sofort`)

Verdict: **Z6D_RULE_ROUTE_PASS** (prereg `PREREG.md`, seed 79, arms fixed / fixed+now / adaptive+now).
Data: `v13/bench-results/z6d-rule-route-20261026/z6d.json` (repo path).

| arm | runtime all | half items | unchanged items | after undo (half) |
|---|---|---|---|---|
| fixed (control, no rule) | 0.625 | 0.00 | 0.781 | n/a |
| fixed+now | 0.825 | 1.00 | 0.781 | 0.00 |
| adaptive+now | 0.800 | 1.00 | 0.750 | 0.00 |

- D1 half items on the runtime path >= 90 %: 1.00 in both rule arms. PASS
- D2 rule touches no other item: 0 non-half items routed by the rule. PASS
- D3 undo removes the rule completely: rule source 0 after undo, half items back to the pre-rule 0.00. PASS
- D4 control without rule fails: 0.00 half items. PASS

## What this does and does not show
- The fixed word rule set by the human makes the changed boundary effective immediately, exactly scoped, and fully reversible.
- It is **not learning**: the route head itself still ends at 0.00 on half items in every arm (Z6c FAIL stands). The rule is a
  human override that bridges the gap until a representation can carry the new boundary.
- Claim limit: route head only, generated German paraphrases, no phone measurement.
