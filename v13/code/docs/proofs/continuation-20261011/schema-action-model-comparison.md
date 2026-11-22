# Identical native schema probe: 350M versus 1.2B Instruct

Both 32-call cohorts completed. The comparison verifies identical preregistered cases/oracles, arms, diagnostic source, runner/serializer source bindings, launcher/shared libraries and every actual native completion request payload. Only model weights differ: 350M SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`; 1.2B Instruct SHA256 `bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1`, revision `6767265158422fb8a19c62ceb45f16f05363615b` (actual installed ModelManager binding).

Actual GGUF headers contain identical ChatML templates, SHA256 `ba551d58630afa3190b1be3602e28301f3d2e9bbac978dfc49d6d825171648b6`, BOS1/EOS7 and lfm2 architecture. The server-rendered prompts match byte-for-byte in all paired request payloads. Both isolated servers were reaped and both model/launcher/shared-library bindings remained unchanged. Each server used one CPU thread; other cloud workers could run concurrently. This proves comparable semantic inputs, not latency, RAM-residency or Redmi performance. Neither model was installed anew or assigned a new production role.

## Explicit copy cases

Each count has denominator four. Copy tasks explicitly request an action label and ordered two-entry remaining/eligibility vectors; they do not authorize learning and are not real-user labels.

| Model | Arm | Action | Remaining vector | Eligible vector | Whole requested output |
|---|---|---:|---:|---:|---:|
| 350M | Free JSON | 4 | 4 | 4 | 0 |
| 350M | Action only | 4 | — | — | 4 |
| 350M | Action first | 4 | 4 | 4 | 4 |
| 350M | Facts first | 3 | 4 | 4 | 3 |
| 1.2B Instruct | Free JSON | 4 | 4 | 2 | 0 |
| 1.2B Instruct | Action only | 4 | — | — | 4 |
| 1.2B Instruct | Action first | 4 | 4 | 2 | 2 |
| 1.2B Instruct | Facts first | 4 | 4 | 1 | 1 |

Free JSON outputs fail whole-object equality because of extra keys and, in the 1.2B cohort, additional eligibility swaps. The 1.2B model reverses the supplied `[true,false]` eligibility assignment in two action-first copy cases and three facts-first copy cases. Its correct action labels therefore cannot be treated as intact entity-wise copying of all fields. The 350M facts-first NONE copy produces UNKNOWN instead. All enum labels are demonstrably available; the original 70×NONE collapse is not a fixed enum prohibition.

## Arithmetic decision cases

Each count again has denominator four; the input cases span expected A/B/NONE/UNKNOWN. Action-only has a smaller requested task, so its whole-output count is not comparable to a complete decision JSON.

| Model | Arm | Action | Remaining vector | Eligible vector | Whole requested output |
|---|---|---:|---:|---:|---:|
| 350M | Free JSON | 1 | 0 | 0 | 0 |
| 350M | Action only | 2 | — | — | 2 |
| 350M | Action first | 1 | 0 | 2 | 0 |
| 350M | Facts first | 1 | 1 | 2 | 0 |
| 1.2B Instruct | Free JSON | 1 | 0 | 2 | 0 |
| 1.2B Instruct | Action only | 1 | — | — | 1 |
| 1.2B Instruct | Action first | 1 | 0 | 1 | 0 |
| 1.2B Instruct | Facts first | 1 | 1 | 0 | 0 |

Neither model completes any of the four arithmetic JSONs correctly in either full-schema order. The 1.2B facts-first A case gets the chosen label right but outputs remaining `[6,13]` instead of `[16,13]` and eligible `[false,true]` instead of `[true,true]`. Its own action A then contradicts its own eligibility array. In the 350M facts-first arm, every arithmetic action is UNKNOWN, including cases with a supplied numerical budget. The unknown-budget case also fails its required null eligibility vector. These raw errors are preserved in both reports and the comparison JSON; no gate, oracle, case or scorer was retuned.

## Consequence

This fixed generic diagnostic does not support either a global schema-order fix or a production switch to the existing 1.2B Instruct model. The bigger model does not overcome the full instruction/decision task, and facts-first does not establish a quality advantage. The result is scoped to these eight authored inputs under the frozen multi-task prompt, seed, sampling and schema. It is not a general ranking of all capabilities or a full language benchmark.

The concrete next research question is whether a separately preregistered clearer single-task prompt or another verified language candidate produces correct source-grounded decisions and stable entity assignments. Any such new experiment must remain distinct from these failures and from the original STEP2 cohort. Existing positive slot-firing proofs, transport fixes or source delivery do not establish semantic correctness of the consumer. B1/B2 distinct-body utility, Age0/authority, training and Redmi gates remain unchanged.

Reproduce the comparison (no model calls):

```bash
python3 scripts/compare_schema_action_probes.py --baseline docs/proofs/continuation-20261011/schema-action-350m/report.json --candidate docs/proofs/continuation-20261011/schema-action-1p2b/report.json --out docs/proofs/continuation-20261011/schema-action-model-comparison.json
```

Evidence: `schema-action-350m/report.json`, `schema-action-1p2b/report.json`, `schema-action-model-comparison.json` (all seven comparability checks pass, exact report hashes and field-level failures), `schema-action-template-metadata.json` (actual raw GGUF template text), and the separate execution logs. Canonical gate pass and production activation remain false.
