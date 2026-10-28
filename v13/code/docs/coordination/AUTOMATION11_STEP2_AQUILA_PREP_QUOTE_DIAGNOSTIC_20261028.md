# Aquila native STEP2 B2 rule-retention diagnostic (2026-10-28)

**Scope:** read-only examination of original corrected TP/s27 one-fixture Linux-native raw ZIP artifact `12814207610` from Actions `40683211643` at `44eb8e85aa6ac2cc6292cced515f97cad27af9d9`; independently SHA256-verified ZIP `ff05974753c3151e92ed14194c0f254ce6ea721b610fa16e6490a064bd343ea7`. No source or model changes, no fixture re-registration, no gate promotion. **Aquila is one of ten fixtures; these observations are not a utility proof.**

## What actually reached C3

- Aquila's original earlier binding rules were budget **134 euros**, deadline **9 days**, local-only **true**. The later supplier sheet had option A cost **91**, duration **7**, local **true** and B cost **105**, duration **8**, local **false**. The exact decision is A with remaining budgets 43/29 and B ineligible.
- In the *preparation history*, B2_GIST's offer on the original kickoff memo included two verified quotes, one of which was **`Budget 134 euros.`**. It did **not** quote the deadline or local-only rule. B1_DETAIL's offer on that same event quoted only the memo heading.
- On the later supplier event, B2's offer quoted the supplier-sheet introduction and archived-memo heading rather than the earlier budget; the actual `b2_only` C3 consumer messages carried two verified quotes about the current question and sheet, **not** budget/deadline/local-only values. `both_exact` likewise delivered B1's complete A/B option-value quote but no B2 prior-rule quote.
- Thus there are **two distinct possible failure layers**: (1) B2 did produce at least the earlier budget quote, but the current consumer did not receive it (memory/selection/pointer handoff); (2) the B2 offer itself did not capture the full deadline/local-only rule, so perfect transport of the existing budget quote alone cannot satisfy the whole task. These are observed source/quote facts, not a causal attribution of C3's errors.
- Source-native C3's `b1_only` and `both_exact` both scored 8/12 (.6667) on Aquila; both missed project/action and remaining budgets. B2-only scored 1/12 (.0833). These are **descriptive single-fixture scores**. A frozen C3 typed-value tool replay and full ten-fixture TP/s27 70-row native cohort are running separately; do not infer their outcomes.

## Next permitted experiment after frozen full70 closes

Use existing `z2.information_access` / `z2.error_profile` to inspect all 70 original source-bound rows and C3 tool replay. If the full cohort confirms loss of B2 prior-rule quotes, preregister a **new** source-bound comparison that distinguishes prior B2 quote retention/selection from actual B2 rule extraction. Preserve exact original model/fixture/seed/source hashes and failed attempts; never inject oracle rules or directly copy source facts into C3 and count that as learned B2 utility. A deterministic quote-selection ablation is not Body-JEPA or semantic complementarity evidence by itself.

Gates unchanged: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, `jepa_weight=0`, Age0 RECORD_ONLY, Redmi unmeasured, whole V13 incomplete.
